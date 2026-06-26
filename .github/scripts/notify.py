# .github/scripts/notify.py
"""
notify.py — Tập trung toàn bộ thông báo Telegram của hệ thống.

Loại thông báo:
  notify_sync(processed_apps, processed_tweaks, stats)  ← main.py gọi
  notify_clean(ran_theos, ran_logs, success)             ← clean.py gọi
  notify_release(tag, release_name, body, assets)        ← main.py gọi khi trigger release
"""

import os
import json
import datetime
import logging
import urllib.request
import urllib.error
import re

import config
import gemini

logger = logging.getLogger(__name__)

# ── Global cache for time (computed once per workflow run) ────────────────────
_CACHED_TIME_STR = None

def _get_ict_time_cached() -> str:
    """Get ICT time, cached globally during workflow run."""
    global _CACHED_TIME_STR
    if _CACHED_TIME_STR is not None:
        return _CACHED_TIME_STR
    
    ict = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=7)
    thu = ["Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy", "Chủ nhật"]
    _CACHED_TIME_STR = f"{ict.strftime('%H:%M')} {thu[ict.weekday()]} {ict.strftime('%d/%m/%Y')}"
    return _CACHED_TIME_STR


# ── HTML escape optimized (single regex pass + str.translate) ──────────────────
_HTML_ESCAPE_TABLE = str.maketrans({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
})

def _esc(text: str) -> str:
    """Escape HTML for Telegram (optimized single pass)."""
    return str(text or "").translate(_HTML_ESCAPE_TABLE)


# ── Format file size (global scope for reuse) ───────────────────────────────────
def _fmt_size(b):
    """Format bytes to human readable size."""
    if not b or b <= 0:
        return "?"
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} GB"


def _send(html: str, inline_button: dict = None) -> bool:
    token   = os.getenv("TELEGRAM_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_TO", "").strip()
    if not token or not chat_id:
        logger.warning("⚠️ Thiếu TELEGRAM_TOKEN hoặc TELEGRAM_TO — bỏ qua gửi.")
        return False

    payload = {
        "chat_id": chat_id,
        "text": html,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if inline_button:
        payload["reply_markup"] = {"inline_keyboard": [[inline_button]]}

    url  = f"https://api.telegram.org/bot{token}/sendMessage"
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(url, data=data,
                                   headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            if not result.get("ok"):
                logger.error(f"❌ Telegram API lỗi: {result}")
                return False
        logger.info("📨 Đã gửi thông báo Telegram.")
        return True
    except urllib.error.HTTPError as e:
        logger.error(f"❌ Telegram HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        logger.error(f"❌ Telegram kết nối lỗi: {e.reason}")
    except Exception as e:
        logger.error(f"❌ Telegram lỗi: {e}")
    return False


# ── Loại 1: Thông báo đồng bộ repo (Phase 1 — push/workflow_dispatch) ────────

def notify_sync(processed_apps, processed_tweaks, stats):
    """Gọi Gemini sinh nội dung → gửi Telegram tổng kết Phase 1."""
    logger.info("🤖 Đang kết nối Gemini để tóm tắt thay đổi...")
    msg = gemini.generate_update_summary(
        processed_apps=processed_apps,
        processed_tweaks=processed_tweaks,
        stats_data=stats,
    )
    _send(msg, inline_button={
        "text": "🌐 Thêm Nguồn Kyic Store",
        "url": "https://2kgt.github.io/",
    })


# ── Loại 2: Thông báo dọn dẹp repo (Phase 2 — clean.py) ─────────────────────

def notify_clean(ran_theos: bool, ran_logs: bool, success: bool):
    """Gửi Telegram tổng kết Phase 2. Không cần Gemini."""
    status_icon = "🟢 Hoàn thành" if success else "🔴 Có lỗi xảy ra"

    lines = ["🧹 <b>TỔNG VỆ SINH REPO</b>", "──────────────────"]
    if ran_theos:
        lines.append("🧹 <b>Theos:</b> <code>✅ Đã xóa ghost submodule</code>")
    if ran_logs:
        lines.append("🗑️ <b>Commit:</b> <code>✅ Đã reset lịch sử</code>")
        lines.append("🗑️ <b>Actions:</b> <code>✅ Đã xóa workflow runs</code>")
        lines.append("🗄️ <b>Cache:</b> <code>✅ Đã xóa cache</code>")
    lines += [
        f"📊 <b>Trạng thái:</b> {status_icon}",
        "──────────────────",
        f"⏰ <b>Thời gian:</b> <code>{_get_ict_time_cached()}</code>",
    ]
    _send("\n".join(lines))


# ── Loại 3: Thông báo phát hành phiên bản (release trigger) ──────────────────

def notify_release(
    tag: str,
    release_name: str,
    body: str,
    assets: list[dict],
    release_url: str = "",
    repo_name: str = "",
):
    """
    Gửi Telegram khi có release mới được publish/edit trên GitHub.

    Tham số:
        tag          — tên tag, vd: "v2.1.0"
        release_name — tiêu đề release
        body         — nội dung release notes (markdown → cắt ngắn)
        assets       — list dict {name, size, download_count, browser_download_url}
        release_url  — URL trang release trên GitHub
        repo_name    — "owner/repo"
    """
    tag_esc  = _esc(tag or "unknown")
    name_esc = _esc(release_name or tag or "New Release")
    repo_esc = _esc(repo_name)

    # Release notes: cắt ngắn 300 ký tự, tránh vỡ HTML
    notes = (body or "").strip()
    if len(notes) > 300:
        notes = notes[:297] + "..."
    notes_esc = _esc(notes) if notes else "<i>Không có release notes.</i>"

    lines = [
        "🚀 <b>PHÁT HÀNH PHIÊN BẢN MỚI</b>",
        "──────────────────",
        f"📦 <b>Phiên bản:</b> <code>{tag_esc}</code>",
        f"📝 <b>Tên:</b> {name_esc}",
    ]

    if repo_esc:
        lines.append(f"🗂️ <b>Repo:</b> <code>{repo_esc}</code>")

    lines += [
        "──────────────────",
        f"📋 <b>Release Notes:</b>\n{notes_esc}",
    ]

    # Danh sách file đính kèm
    if assets:
        lines.append("──────────────────")
        lines.append(f"📎 <b>Files đính kèm ({len(assets)}):</b>")
        for a in assets[:10]:  # tối đa 10 files
            a_name  = _esc(a.get("name", "unknown"))
            a_size  = _fmt_size(a.get("size", 0))  # ✅ Dùng global function
            a_dl    = a.get("download_count", 0)
            lines.append(f"  • <code>{a_name}</code> — {a_size} · {a_dl} lượt tải")
        if len(assets) > 10:
            lines.append(f"  <i>... và {len(assets) - 10} file khác</i>")

    lines += [
        "──────────────────",
        f"⏰ <b>Thời gian:</b> <code>{_get_ict_time_cached()}</code>",
    ]

    btn = None
    if release_url:
        btn = {"text": "🔗 Xem Release trên GitHub", "url": release_url}

    _send("\n".join(lines), inline_button=btn)


# ── Auto-detect release và gọi notify_release() từ env ───────────────────────

def notify_release_from_env():
    """
    Đọc toàn bộ thông tin release từ env vars (yml inject),
    gọi GitHub API lấy danh sách assets, rồi gửi thông báo.
    Được main.py gọi khi GITHUB_EVENT_NAME == 'release'.
    """
    token      = os.getenv("GITHUB_TOKEN", "").strip()
    repo       = os.getenv("GITHUB_REPOSITORY", "")
    tag        = os.getenv("RELEASE_TAG", "")
    name       = os.getenv("RELEASE_NAME", tag)
    body       = os.getenv("RELEASE_BODY", "")
    release_id = os.getenv("RELEASE_ID", "")
    server_url = os.getenv("GITHUB_SERVER_URL", "https://github.com")

    if not tag:
        logger.warning("⚠️ notify_release_from_env: Không có RELEASE_TAG — bỏ qua.")
        return

    release_url = f"{server_url}/{repo}/releases/tag/{tag}" if repo else ""

    # Lấy danh sách assets qua GitHub API
    assets = []
    if release_id and token and repo:
        try:
            api_url = f"https://api.github.com/repos/{repo}/releases/{release_id}/assets"
            req = urllib.request.Request(api_url)
            req.add_header("Authorization", f"Bearer {token}")
            req.add_header("Accept", "application/vnd.github+json")
            with urllib.request.urlopen(req, timeout=10) as resp:
                assets = json.loads(resp.read().decode())
        except Exception as e:
            logger.warning(f"⚠️ Không lấy được assets: {e}")

    notify_release(
        tag=tag,
        release_name=name,
        body=body,
        assets=assets,
        release_url=release_url,
        repo_name=repo,
    )
