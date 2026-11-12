# .github/scripts/core/sileo_engine.py
import os
import json
import subprocess
import bz2
import sys
import hashlib
import re
import urllib.request
import logging
import tempfile
import datetime
import gzip
import lzma
import html as _html
import config

logger = logging.getLogger(__name__)
from collections import defaultdict
from . import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _iso8601_z(dt):
    """Chuẩn hoá datetime → chuỗi ISO8601 kết thúc bằng 'Z' (không phải '+00:00')."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_iso8601_z():
    return _iso8601_z(datetime.datetime.now(datetime.timezone.utc))


def _file_mtime_iso8601_z(path):
    """Lấy ngày sửa đổi cuối của tệp .deb cục bộ làm 'versionDate'."""
    try:
        ts = os.path.getmtime(path)
        return _iso8601_z(datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc))
    except Exception:
        return _now_iso8601_z()


def calculate_hashes_from_url(url):
    """Tải tạm file cloud, tính MD5/SHA1/SHA256 bằng streaming."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        md5, sha1, sha256 = hashlib.md5(), hashlib.sha1(), hashlib.sha256()
        with tempfile.NamedTemporaryFile(suffix=".deb", delete=False) as tmp:
            temp_path = tmp.name
            with urllib.request.urlopen(req, timeout=30) as resp:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    tmp.write(chunk)
                    md5.update(chunk); sha1.update(chunk); sha256.update(chunk)
        os.remove(temp_path)
        return md5.hexdigest(), sha1.hexdigest(), sha256.hexdigest()
    except Exception as e:
        logger.error(f"⚠️ Lỗi tính hash cloud [{url}]: {e}")
        return "0" * 32, "0" * 40, "0" * 64


def calculate_hashes_from_local(path):
    """Tính MD5/SHA1/SHA256 file local bằng streaming."""
    md5, sha1, sha256 = hashlib.md5(), hashlib.sha1(), hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                md5.update(chunk); sha1.update(chunk); sha256.update(chunk)
    except Exception as e:
        logger.error(f"⚠️ Lỗi tính hash local [{path}]: {e}")
        return "0" * 32, "0" * 40, "0" * 64
    return md5.hexdigest(), sha1.hexdigest(), sha256.hexdigest()


def extract_deb_control_data(path):
    """Đọc control fields từ file .deb bằng dpkg-deb."""
    info = {
        "Package": "", "Name": "", "Version": "1.0",
        "Description": "Một tweak tuyệt vời từ Kyic Store.",
        "Author": "Kyic Store", "Section": "Tweaks", "Architecture": "iphoneos-arm"
    }
    f_name = os.path.basename(path)
    try:
        result = subprocess.run(
            ['dpkg-deb', '-f', path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, errors='ignore', timeout=5
        )
        if result.returncode == 0 and result.stdout:
            current_key = None
            for line in result.stdout.split('\n'):
                if not line.strip():
                    continue
                if line.startswith(' ') or line.startswith('\t'):
                    if current_key and current_key in info:
                        info[current_key] += "\n" + ("" if line.strip() == "." else line.strip())
                elif ':' in line:
                    k, v = line.split(':', 1)
                    current_key = k.strip()
                    info[current_key] = v.strip()
    except subprocess.TimeoutExpired:
        logger.warning(f"⚠️ Timeout khi đọc: {f_name}")
    except Exception as e:
        logger.error(f"❌ Lỗi đọc .deb: {e}")

    if not info.get("Package"):
        info["Package"] = f"com.kyic.{f_name.split('_')[0].lower()}"
    if not info.get("Name"):
        info["Name"] = f_name.split('_')[0]

    section_map = {
        "tweak": "Tweaks", "tweaks": "Tweaks", "patched": "Tweaks",
        "theme": "Themes", "themes": "Themes",
        "addon": "Addons", "addons": "Addons",
        "system": "System", "utilities": "System"
    }
    raw_section = info.get("Section", "").strip().lower()
    info["Section"] = section_map.get(raw_section, info.get("Section", "Tweaks").strip().capitalize()) or "Tweaks"

    return info


def clean_string_for_match(text):
    if not text:
        return ""
    return re.sub(r'[^a-z0-9]', '', text.lower())


def extract_tweak_name_from_filename(filename):
    """Lấy tên tweak từ filename: cc18_0.0.3_iphoneos-arm.deb → cc18."""
    name_no_ext = filename.rsplit('.', 1)[0]
    tweak_name = name_no_ext.split('_')[0]
    return tweak_name if tweak_name else name_no_ext


def resolve_display_name(deb_info, fallback_id):
    """
    Ưu tiên field Name từ control file. Bỏ qua nếu Name trùng với bundle ID
    (com.x.y) — fallback về đoạn cuối bundle ID, viết hoa chữ đầu.
    """
    def _is_bundle_id(s):
        return bool(re.match(r'^[a-z0-9]+(\.[a-z0-9]+){2,}$', s.strip()))

    name = (deb_info or {}).get("Name", "")
    name = name.strip() if isinstance(name, str) else ""
    if name and not _is_bundle_id(name):
        return name

    base = fallback_id.strip().split('.')[-1] if fallback_id else fallback_id
    base = base or fallback_id or "tweak"
    return base[:1].upper() + base[1:] if base else base


def _save_desc_file(path, content):
    """Ghi file text, tạo thư mục nếu cần. Trả về True nếu thành công."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.warning(f"⚠️ Không ghi được {path}: {e}")
        return False


def _read_file(path):
    """Đọc file text, trả về chuỗi hoặc rỗng nếu lỗi."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return ""


# ══════════════════════════════════════════════════════════════════════
# 🆕 HELPERS: mô tả / "Có gì mới" / định dạng APT chuẩn
# ══════════════════════════════════════════════════════════════════════

# Commit message "rác" (tự sinh / mặc định của GitHub web) — KHÔNG dùng làm changelog.
_NOISE_COMMIT = re.compile(
    r'^(add files via upload|upload |create |update |delete |rename |merge |initial|'
    r'🚀 auto sync|🔄 tối ưu|fix: remove ghost|🚀 initial clean)', re.IGNORECASE)

# Field control của .deb cần chuyển nguyên vào Packages (thiếu → Sileo không tự
# cài dependency, Cydia/Zebra không hiện Maintainer/Homepage...).
PASSTHROUGH_FIELDS = (
    "Maintainer", "Depends", "Pre-Depends", "Recommends", "Suggests",
    "Conflicts", "Breaks", "Provides", "Replaces", "Installed-Size",
    "Homepage", "Tag", "Priority",
)
MAX_VERSIONS_IN_PACKAGES = int(getattr(config, "PACKAGES_MAX_VERSIONS", 3))


def _extra_fields(deb_info):
    out = []
    for k in PASSTHROUGH_FIELDS:
        v = str(deb_info.get(k, "")).strip()
        if v:
            out.append((k, v))
    return out


def _apt_value(value):
    """
    Chuẩn hoá giá trị field APT: dòng 2+ PHẢI bắt đầu bằng 1 dấu cách,
    dòng trống → ' .'. Nếu không, Packages bị hỏng (APT/Cydia/Zebra từ chối).
    """
    lines = str(value).replace("\r", "").split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""
    first = lines[0].strip()
    rest = [(" " + l.strip()) if l.strip() else " ." for l in lines[1:]]
    return "\n".join([first] + rest)


def _first_line(text, limit=200):
    """Description của APT: dòng đầu = tóm tắt ngắn."""
    t = str(text or "").strip().split("\n")[0].strip()
    return t if len(t) <= limit else t[:limit].rsplit(" ", 1)[0] + "…"


def _markdown_description(text, max_chars=1000):
    """
    Giữ nguyên xuống dòng/markdown (khác utils.smart_truncate_description vốn
    ép mọi \\n thành dấu cách → mất bullet/đoạn văn). Cắt ở ranh giới đoạn/từ.
    """
    DEFAULT = "Được tổng hợp by Kyic Store."
    t = str(text or "").replace("\r", "").strip()
    if len(t) < 10:
        return DEFAULT
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    if max_chars and len(t) > max_chars:
        cut = t[:max_chars]
        cut = cut[:cut.rfind("\n")] if "\n" in cut[max_chars // 2:] else cut.rsplit(" ", 1)[0]
        t = cut.rstrip() + "…"
    return t


def get_version_note(tweak_title, ver, fallback=None):
    """Đọc ĐÚNG ghi chú của phiên bản `ver` (v{ver}.txt). Rỗng nếu chưa có."""
    note = _read_file(os.path.join(config.TWEAK_DESC_DIR, tweak_title, f"v{ver}.txt"))
    if note:
        return note
    return "" if fallback is None else fallback


def _sidecar_note(deb_dir, safe_filename, ver):
    """Ghi chú đặt cạnh file .deb: <tên>.txt / v<ver>.txt / <ver>.txt / <tên>.md"""
    if not deb_dir:
        return ""
    for name in (f"{safe_filename}.txt", f"v{ver}.txt", f"{ver}.txt", f"{safe_filename}.md"):
        t = _read_file(os.path.join(deb_dir, name))
        if len(t) > 5:
            return t
    return ""


def _commit_note(rel_path):
    """Commit message gần nhất của file .deb (khi upload qua web/commit tay). Lọc rác."""
    repo = os.getenv("GITHUB_REPOSITORY", "")
    if not repo or not rel_path:
        return ""
    try:
        import github as _gh
        msg = _gh.get_file_commit_message(repo, f"repo/{rel_path}".replace("//", "/"))
    except Exception:
        return ""
    msg = (msg or "").strip()
    return "" if (len(msg) < 8 or _NOISE_COMMIT.match(msg)) else msg


def resolve_release_note(tweak_title, ver, safe_filename, cloud_body="", deb_dir=None, rel_path=None):
    """
    Chọn nguồn "Có gì mới" theo thứ tự ưu tiên rồi LƯU vào v{ver}.txt (bền vững,
    không mất kể cả khi clean_commit_run_logs reset lịch sử commit):

      Cloud .deb : GitHub Release (title + body)  >  v{ver}.txt đã có
      Local .deb : file ghi chú cạnh .deb  >  v{ver}.txt đã có  >  commit message
    """
    ver_file = os.path.join(config.TWEAK_DESC_DIR, tweak_title, f"v{ver}.txt")
    existing = _read_file(ver_file)
    note = ""
    if cloud_body and len(cloud_body.strip()) > 10:
        note = cloud_body.strip()
    else:
        note = _sidecar_note(deb_dir, safe_filename, ver) or existing or _commit_note(rel_path)
    if note and len(note) > 5 and note != existing:
        if _save_desc_file(ver_file, note):
            logger.info(f"💾 Lưu changelog v{ver}: {ver_file}")
    return note or existing


def build_web_depiction_html(path, name, ver, author, description, history_md, icon, banner=""):
    """
    Trang HTML tĩnh cho field `Depiction:` — Cydia / Installer / Zebra (bản cũ)
    KHÔNG đọc SileoDepiction nên cần trang web thường.
    """
    esc = _html.escape
    page = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(name)}</title>
<style>
:root{{color-scheme:light dark;--bg:#fff;--fg:#1c1c1e;--mut:#6e6e73;--card:#f2f2f7;--ac:#f77686}}
@media(prefers-color-scheme:dark){{:root{{--bg:#000;--fg:#f2f2f7;--mut:#98989d;--card:#1c1c1e}}}}
body{{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,Helvetica,Arial,sans-serif}}
.h{{display:flex;gap:12px;align-items:center;margin-bottom:14px}}
.h img{{width:56px;height:56px;border-radius:13px}}
h1{{font-size:20px;margin:0}} .m{{color:var(--mut);font-size:13px}}
.c{{background:var(--card);border-radius:12px;padding:12px 14px;margin:12px 0;white-space:pre-wrap;word-break:break-word}}
h2{{font-size:13px;text-transform:uppercase;color:var(--mut);margin:18px 0 4px}}
</style></head><body>
<div class="h"><img src="{esc(icon)}" alt=""><div><h1>{esc(name)}</h1>
<div class="m">v{esc(str(ver))} · {esc(str(author))}</div></div></div>
<h2>Mô tả</h2><div class="c">{esc(description)}</div>
<h2>Có gì mới</h2><div class="c">{esc(history_md)}</div>
</body></html>"""
    return _save_desc_file(path, page)


def write_release_file(archs_seen):
    """
    Cập nhật `Release`: giữ nguyên Origin/Label/Suite/... đã có, nhưng
    - Architectures = hợp (cũ ∪ thực tế trong Packages)  → thêm iphoneos-arm64e
    - Date = hiện tại (để Sileo/Cydia nhận ra index mới)
    - MD5Sum/SHA256 cho Packages, .gz, .bz2, .xz (APT chuẩn)
    """
    rel_path = os.path.join(config.REPO_OUTPUT_DIR, "Release")
    keep = {}
    order = []
    for line in _read_file(rel_path).split("\n"):
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            k = k.strip()
            if k in ("MD5Sum", "SHA1", "SHA256", "Date"):
                continue
            keep[k] = v.strip(); order.append(k)
    defaults = {"Origin": config.REPO_NAME, "Label": config.REPO_NAME, "Suite": "stable",
                "Version": "1.0", "Codename": "ios", "Components": "main",
                "Description": f"Kho tài nguyên của {config.REPO_NAME}."}
    for k, v in defaults.items():
        if k not in keep:
            keep[k] = v; order.append(k)
    archs = set(keep.get("Architectures", "").split()) | set(archs_seen)
    keep["Architectures"] = " ".join(sorted(archs))
    if "Architectures" not in order:
        order.append("Architectures")

    files = [f for f in ("Packages", "Packages.gz", "Packages.bz2", "Packages.xz")
             if os.path.exists(os.path.join(config.REPO_OUTPUT_DIR, f))]

    def _render(date_str):
        out = [f"{k}: {keep[k]}" for k in order] + [f"Date: {date_str}"]
        for label, algo in (("MD5Sum", hashlib.md5), ("SHA256", hashlib.sha256)):
            out.append(f"{label}:")
            for f in files:
                data = open(os.path.join(config.REPO_OUTPUT_DIR, f), "rb").read()
                out.append(f" {algo(data).hexdigest()} {len(data):>8} {f}")
        return "\n".join(out) + "\n"

    # 🔑 Chỉ cập nhật Date khi NỘI DUNG thật sự đổi (Packages/kiến trúc/hash).
    # Nếu không, mỗi lần chạy đều tạo thay đổi giả → commit + Pages build vô ích.
    old = open(rel_path, encoding="utf-8").read() if os.path.exists(rel_path) else ""
    m = re.search(r"^Date: (.*)$", old, re.M)
    if m and _render(m.group(1)).strip() == old.strip():
        return
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S UTC")
    with open(rel_path, "w", encoding="utf-8") as fh:
        fh.write(_render(now))


def get_tweak_assets(tweak_name, deb_info):
    """Lấy icon/banner/video/screenshots từ control field, fallback local, fallback default."""
    exts = ['.png', '.jpg', '.jpeg', '.webp']
    match_variants = [
        clean_string_for_match(tweak_name),
        clean_string_for_match(deb_info.get("Package", "")),
        clean_string_for_match(deb_info.get("Package", "").split('.')[-1])
    ]
    base_variant = match_variants[0] or "default"

    def icon_url(fname):
        return f"{config.RAW_URL.rstrip('/')}/{config.ICON_DIR_NAME.strip('/')}/{fname}"

    def image_url(fname):
        return f"{config.RAW_URL.rstrip('/')}/{config.IMG_DIR_NAME.strip('/')}/{tweak_name}/{fname}"

    local_icons = os.listdir(config.ICON_DIR) if os.path.exists(config.ICON_DIR) else []
    tweak_img_dir = config.get_tweak_images_dir(tweak_name)
    local_images = os.listdir(tweak_img_dir) if os.path.exists(tweak_img_dir) else []

    icon, banner, video, screens = None, None, None, []

    # Từ control field
    remote_icon = deb_info.get('Icon') or deb_info.get('icon')
    if remote_icon and str(remote_icon).startswith("http"):
        if utils.download_resource_to_local(remote_icon, os.path.join(config.ICON_DIR, f"{base_variant}.jpg")):
            icon = icon_url(f"{base_variant}.jpg")

    remote_banner = deb_info.get('Banner') or deb_info.get('banner')
    if remote_banner and str(remote_banner).startswith("http"):
        os.makedirs(tweak_img_dir, exist_ok=True)
        if utils.download_resource_to_local(remote_banner, os.path.join(tweak_img_dir, f"{base_variant}_banner.jpg")):
            banner = image_url(f"{base_variant}_banner.jpg")

    remote_video = deb_info.get('Video') or deb_info.get('video')
    if remote_video and str(remote_video).startswith("http"):
        os.makedirs(tweak_img_dir, exist_ok=True)
        if utils.download_resource_to_local(remote_video, os.path.join(tweak_img_dir, f"{base_variant}.mp4")):
            video = image_url(f"{base_variant}.mp4")

    raw_screens = (
        deb_info.get('Screenshots') or deb_info.get('screenshots')
        or deb_info.get('Screenshot') or deb_info.get('screenshot')
    )
    if raw_screens:
        urls_list = []
        if isinstance(raw_screens, list):
            urls_list = raw_screens
        elif isinstance(raw_screens, str):
            if raw_screens.startswith('['):
                try:
                    urls_list = json.loads(raw_screens)
                except Exception:
                    urls_list = [u.strip() for u in raw_screens.strip('[]').split(',') if u]
            else:
                urls_list = [u.strip() for u in raw_screens.split(',') if u]
        os.makedirs(tweak_img_dir, exist_ok=True)
        for idx, scr in enumerate(urls_list, start=1):
            if str(scr).startswith("http"):
                if utils.download_resource_to_local(scr, os.path.join(tweak_img_dir, f"{base_variant}_{idx}.jpg")):
                    screens.append(image_url(f"{base_variant}_{idx}.jpg"))

    # Fallback local
    if not icon:
        for v in match_variants:
            if not v:
                continue
            m = next((f for f in local_icons if clean_string_for_match(f.rsplit('.', 1)[0]) == v and any(f.lower().endswith(e) for e in exts)), None)
            if m:
                icon = icon_url(m); break

    if not banner:
        for v in match_variants:
            if not v:
                continue
            m = next((f for f in local_images if clean_string_for_match(f.rsplit('.', 1)[0]) in [f"{v}banner", f"{v}_banner"] and any(f.lower().endswith(e) for e in exts)), None)
            if m:
                banner = image_url(m); break

    if not video:
        for v in match_variants:
            if not v:
                continue
            m = next((f for f in local_images if clean_string_for_match(f) == f"{v}.mp4"), None)
            if m:
                video = image_url(m); break

    if not screens:
        for i in range(1, 16):
            m = next((f for f in local_images if clean_string_for_match(f.rsplit('.', 1)[0]) in [f"{base_variant}_{i}", f"{base_variant}{i}"] and any(f.lower().endswith(e) for e in exts)), None)
            if m:
                screens.append(image_url(m))

    if not icon: icon = config.SOURCE_LOGO
    if not banner: banner = config.DEFAULT_BANNER
    if not video: video = config.DEFAULT_VIDEO
    if not screens: screens = utils.get_default_screens()

    return {
        "icon": utils.clean_github_url(icon),
        "banner": utils.clean_github_url(banner),
        "video": utils.clean_github_url(video),
        "screenshots": [utils.clean_github_url(s) for s in screens if s]
    }


def build_sileo_depiction_json(safe_filename, tweak_name, version, description, assets, author, deb_info, privacy_list):
    """Tạo file depiction JSON cho Sileo (1 file riêng mỗi version+arch)."""
    section = deb_info.get("Section", "Tweaks")

    # Mô tả sản phẩm: từ control file, fallback default.txt
    default_file = os.path.join(config.TWEAK_DESC_DIR, tweak_name, "default.txt")
    if description and len(str(description).strip()) > 5:
        final_description = description.strip()
    elif os.path.exists(default_file):
        final_description = _read_file(default_file) or description
    else:
        final_description = description

    # Lịch sử phiên bản: từ v*.txt (release notes)
    changelog_markdown = config.get_tweak_changelog_history(tweak_name, version)

    target_folder, json_filename = config.get_depiction_path_by_filename(section, tweak_name, safe_filename)
    os.makedirs(target_folder, exist_ok=True)
    file_path = os.path.join(target_folder, json_filename)

    privacy_text = ", ".join(privacy_list) if privacy_list else "Không yêu cầu quyền đặc biệt"
    clean_desc = _markdown_description(final_description, max_chars=1000)
    latest_note = get_version_note(tweak_name, version)
    whats_new_views = []
    if latest_note:
        whats_new_views = [
            {"class": "DepictionSubheaderView", "title": f"Có gì mới ở v{version}", "useBoldText": True},
            {"class": "DepictionMarkdownView", "useSpacing": True, "markdown": _markdown_description(latest_note, 600)},
            {"class": "DepictionSpacerView", "spacing": 8},
        ]
    sileo_screenshots = [{"accessibilityText": f"Screenshot{i}", "url": str(s)} for i, s in enumerate(assets["screenshots"]) if s]

    depiction_data = {
        "minVersion": "0.1",
        "headerImage": assets["banner"],
        "class": "DepictionTabView",
        "tintColor": "#F77686",
        "tabs": [
            {
                "class": "DepictionStackView",
                "tabname": "Details",
                "views": [
                    {"class": "DepictionSubheaderView", "useBottomMargin": False, "title": str(tweak_name), "useBoldText": True},
                    {"class": "DepictionMarkdownView", "useSpacing": True, "markdown": clean_desc},
                    {"class": "DepictionSpacerView", "spacing": 8},
                    *whats_new_views,
                    {"class": "DepictionScreenshotsView", "screenshots": sileo_screenshots, "itemSize": "{160, 275.41333333333336}", "itemCornerRadius": 6},
                    {"class": "DepictionSeparatorView"},
                    {"class": "DepictionSpacerView", "spacing": 8},
                    {"class": "DepictionTableTextView", "title": "Developer", "text": str(author)},
                    {"class": "DepictionTableTextView", "title": "Yêu cầu quyền", "text": privacy_text},
                    {"class": "DepictionSpacerView", "spacing": 8}
                ]
            },
            {
                "class": "DepictionStackView",
                "tabname": "Changelog",
                "views": [
                    {"class": "DepictionTableTextView", "title": f"Version {version}", "text": "Lịch sử cập nhật"},
                    {"class": "DepictionMarkdownView", "useSpacing": True, "markdown": changelog_markdown}
                ]
            },
            {
                "class": "DepictionStackView",
                "tabname": "Support",
                "views": [
                    {"class": "DepictionSubheaderView", "title": "KÊNH HỖ TRỢ CHÍNH THỨC", "useBoldText": True},
                    {"class": "DepictionTableButtonView", "title": "📢 Telegram Channel", "action": "https://t.me/+uhoygGN-1Gc4NzZl"},
                    {"class": "DepictionTableButtonView", "title": "💬 Telegram Group", "action": "https://t.me/kyicchat"},
                    {"class": "DepictionTableButtonView", "title": "🎮 Discord Server", "action": "https://discord.gg/qUXBQFYa"},
                    {"class": "DepictionSeparatorView"},
                    {"class": "DepictionTableButtonView", "title": "☕ Ủng hộ qua PayPal", "action": "https://www.paypal.me/225668"}
                ]
            }
        ]
    }

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(depiction_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"❌ Lỗi ghi depiction {safe_filename}: {e}")
        return None

    return file_path


def _save_desc_for_tweak(tweak_title, deb_info, ver, release_note=""):
    """
    Lưu 2 file mô tả cho tweak:
    - default.txt : mô tả sản phẩm từ control file (chỉ ghi lần đầu)
    - v{ver}.txt  : release note phiên bản từ GitHub Release body
    """
    desc_dir = os.path.join(config.TWEAK_DESC_DIR, tweak_title)
    control_desc = deb_info.get("Description", "").strip()

    default_file = os.path.join(desc_dir, "default.txt")
    if control_desc and len(control_desc) > 5 and not os.path.exists(default_file):
        if _save_desc_file(default_file, control_desc):
            logger.info(f"💾 Lưu mô tả sản phẩm: {default_file}")

    if release_note and len(release_note) > 10:
        ver_file = os.path.join(desc_dir, f"v{ver}.txt")
        if _save_desc_file(ver_file, release_note):
            logger.info(f"💾 Lưu changelog: {ver_file}")


def run_sileo_engine(release_assets, system_db):
    """Xử lý .deb cloud + local, tạo Packages, Packages.bz2 và debs.json."""
    if "tweaks" not in system_db:
        system_db["tweaks"] = {}

    tweaks_map = defaultdict(list)
    processed_safenames = set()
    processed_tweaks_titles = []

    # ── Cloud .deb ────────────────────────────────────────────────────
    for asset in (release_assets if isinstance(release_assets, list) else []):
        f_name = asset.get("name", "")
        f_url  = asset.get("url", "")
        sz     = asset.get("size", 0)
        if not f_name.endswith(".deb") or not f_url:
            continue

        safe_filename = f_name.rsplit('.', 1)[0]
        if safe_filename in processed_safenames:
            continue
        processed_safenames.add(safe_filename)

        parts  = safe_filename.split('_')
        raw_id = parts[0] if parts else safe_filename
        ver    = parts[1] if len(parts) > 1 else "1.0"
        arch   = parts[2] if len(parts) > 2 else "iphoneos-arm"

        logger.info(f"-> Cloud Tweak: {raw_id} [{arch}]")
        md5, sha1, sha256 = calculate_hashes_from_url(f_url)

        deb_info = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".deb", delete=False) as tmp:
                temp_path = tmp.name
            req = urllib.request.Request(f_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                with open(temp_path, 'wb') as f:
                    f.write(resp.read())
            deb_info = extract_deb_control_data(temp_path)
            os.remove(temp_path)
        except Exception as e:
            logger.warning(f"⚠️ Không đọc được control [{raw_id}]: {e}")

        if not deb_info:
            deb_info = {
                "Package": f"com.kyic.{clean_string_for_match(raw_id)}",
                "Name": raw_id, "Version": ver,
                "Description": f"Tweak {raw_id} từ Kyic Store.",
                "Author": "Kyic Store", "Section": "Tweaks", "Architecture": arch
            }

        tweak_title = resolve_display_name(deb_info, raw_id)
        processed_tweaks_titles.append(tweak_title)

        # 🔑 Dùng Version trong control (tên file kiểu pkg_227_1.7.6_arch làm `ver` sai)
        deb_ver = str(deb_info.get("Version") or ver)
        release_note = resolve_release_note(
            tweak_title, deb_ver, safe_filename, cloud_body=asset.get("body", ""))
        _save_desc_for_tweak(tweak_title, deb_info, deb_ver)

        system_db["tweaks"][f_url] = deb_info
        assets = get_tweak_assets(tweak_title, deb_info)
        tweaks_map[(deb_info["Package"], deb_info["Architecture"], deb_info["Version"])].append({
            "name": deb_info["Name"], "ver": deb_info["Version"],
            "bid": deb_info["Package"], "arch": deb_info["Architecture"],
            "dl": f_url, "sz": sz,
            "date": asset.get("date") or _now_iso8601_z(),
            "desc": deb_info["Description"],
            "release_note": release_note,
            "author": deb_info["Author"], "icon": assets["icon"],
            "banner": assets["banner"], "video": assets["video"],
            "screenshots": assets["screenshots"],
            "permissions": utils.format_permissions(deb_info.get('Permissions', {})),
            "tweak_name": tweak_title, "safe_file": safe_filename,
            "section": deb_info["Section"], "is_cloud": True,
            "md5": md5, "sha1": sha1, "sha256": sha256,
            "assets": assets, "deb_info": deb_info, "extra": _extra_fields(deb_info)
        })

    # ── Local .deb ────────────────────────────────────────────────────
    if os.path.exists(config.DEBS_INPUT_DIR):
        for entry in sorted(os.listdir(config.DEBS_INPUT_DIR)):
            if entry.startswith('.') or entry == 'desc':
                continue
            entry_path = os.path.join(config.DEBS_INPUT_DIR, entry)
            deb_files = []

            if os.path.isfile(entry_path) and entry.endswith(".deb"):
                deb_files.append((entry_path, entry, extract_tweak_name_from_filename(entry)))
            elif os.path.isdir(entry_path):
                for f_name in sorted(os.listdir(entry_path)):
                    if f_name.endswith(".deb"):
                        deb_files.append((os.path.join(entry_path, f_name), f_name, entry))

            for path, f_name, tweak_title in deb_files:
                safe_filename = f_name.rsplit('.', 1)[0]
                if safe_filename in processed_safenames:
                    continue
                processed_safenames.add(safe_filename)

                md5, sha1, sha256 = calculate_hashes_from_local(path)
                relative_path = os.path.relpath(path, config.REPO_OUTPUT_DIR).replace("\\", "/")
                f_url = f"{config.BASE_URL}{relative_path}"
                deb_info = extract_deb_control_data(path)

                if tweak_title == extract_tweak_name_from_filename(f_name):
                    tweak_title = resolve_display_name(deb_info, tweak_title)

                logger.info(f"-> Local Tweak: {deb_info['Name']} [{tweak_title}/{deb_info['Architecture']}/v{deb_info['Version']}]")
                processed_tweaks_titles.append(deb_info['Name'])

                # "Có gì mới" cho .deb local: file ghi chú cạnh .deb > v{ver}.txt > commit message
                local_release_note = resolve_release_note(
                    tweak_title, deb_info['Version'], safe_filename,
                    deb_dir=os.path.dirname(path), rel_path=relative_path)
                _save_desc_for_tweak(tweak_title, deb_info, deb_info['Version'])

                system_db["tweaks"][f_url] = deb_info
                assets = get_tweak_assets(tweak_title, deb_info)
                tweaks_map[(deb_info["Package"], deb_info["Architecture"], deb_info["Version"])].append({
                    "name": deb_info["Name"], "ver": deb_info["Version"],
                    "bid": deb_info["Package"], "arch": deb_info["Architecture"],
                    "dl": relative_path, "sz": int(os.path.getsize(path)),
                    "date": _file_mtime_iso8601_z(path),
                    "desc": deb_info["Description"],
                    "release_note": local_release_note,
                    "author": deb_info["Author"], "icon": assets["icon"],
                    "banner": assets["banner"], "video": assets["video"],
                    "screenshots": assets["screenshots"],
                    "permissions": utils.format_permissions(deb_info.get('Permissions', {})),
                    "tweak_name": tweak_title, "safe_file": safe_filename,
                    "section": deb_info["Section"], "is_cloud": False,
                    "md5": md5, "sha1": sha1, "sha256": sha256,
                    "assets": assets, "deb_info": deb_info, "extra": _extra_fields(deb_info)
                })

    # ── Depiction (sinh SAU khi mọi v*.txt đã được ghi → changelog luôn đủ) ──
    for _key, _vs in tweaks_map.items():
        for v in _vs:
            build_sileo_depiction_json(
                v["safe_file"], v["tweak_name"], v["ver"], v["desc"], v["assets"],
                v["author"], v["deb_info"], v["permissions"])

    # ── Packages ──────────────────────────────────────────────────────
    # APT cho phép liệt kê NHIỀU phiên bản của cùng Package+Architecture trong
    # 1 file Packages (Sileo/Cydia/Zebra đều hiện "phiên bản khác" để hạ cấp).
    # Giữ MAX_VERSIONS_IN_PACKAGES bản mới nhất mỗi (Package, Arch).
    latest_per_arch = {}
    versions_by_arch = defaultdict(list)
    for bid, arch, ver in tweaks_map.keys():
        versions_by_arch[(bid, arch)].append(ver)
    for k, vers in versions_by_arch.items():
        vers.sort(key=utils.parse_version_tuple, reverse=True)
        latest_per_arch[k] = vers[0]
    keep_versions = {k: set(v[:max(1, MAX_VERSIONS_IN_PACKAGES)]) for k, v in versions_by_arch.items()}

    section_map = {
        "Tweaks": "tweaks", "Themes": "themes", "Addons": "addons",
        "System": "system", "Tools": "tools"
    }
    metadata_url_base = config.DEPICTION_DIR_NAME.replace("repo/", "").strip("/")
    final_packages = ""
    archs_seen = set()

    def _pk_sort(k):
        return (k[0], k[1], tuple(-x for x in utils.parse_version_tuple(k[2])))

    for key in sorted(tweaks_map.keys(), key=_pk_sort):
        bid, arch, ver = key
        if ver not in keep_versions.get((bid, arch), set()):
            logger.info(f"⏭️  Bỏ qua {bid} v{ver} [{arch}] (quá giới hạn {MAX_VERSIONS_IN_PACKAGES} bản)")
            continue
        for v in tweaks_map[key]:
            subdir = section_map.get(v["section"], "tweaks")
            base = f"{config.BASE_URL}{metadata_url_base}/{subdir}/{v['tweak_name']}/{v['safe_file']}"
            depiction_url = base + ".json"
            web_url = base + ".html"
            # Trang web cho Cydia (Depiction:)
            web_dir = os.path.join(config.DEPICTION_DIR, subdir, v["tweak_name"])
            build_web_depiction_html(
                os.path.join(web_dir, f"{v['safe_file']}.html"),
                v["name"], v["ver"], v["author"],
                _markdown_description(v["desc"], 2000),
                config.get_tweak_changelog_history(v["tweak_name"], v["ver"], limit=15),
                v["icon"])
            archs_seen.add(v["arch"])
            fields = [
                ("Package", v["bid"]), ("Name", v["name"]), ("Version", v["ver"]),
                ("Architecture", v["arch"]), ("Filename", v["dl"]), ("Size", v["sz"]),
                ("MD5sum", v["md5"]), ("SHA1", v["sha1"]), ("SHA256", v["sha256"]),
                ("Author", v["author"]),
            ]
            fields += [(k, val) for k, val in v.get("extra", []) if k != "Description"]
            fields += [
                ("Description", v["desc"]), ("Section", v["section"]), ("Icon", v["icon"]),
                ("Depiction", web_url), ("SileoDepiction", depiction_url),
            ]
            final_packages += "".join(f"{k}: {_apt_value(val)}\n" for k, val in fields) + "\n"

    packages_path = os.path.join(config.REPO_OUTPUT_DIR, "Packages")
    with open(packages_path, "w", encoding="utf-8") as f:
        f.write(final_packages)

    raw_pk = final_packages.encode("utf-8")
    for fname, opener in (("Packages.bz2", lambda p: bz2.BZ2File(p, "wb")),
                          ("Packages.gz",  lambda p: gzip.GzipFile(p, "wb", mtime=0)),
                          ("Packages.xz",  lambda p: lzma.LZMAFile(p, "wb"))):
        try:
            with opener(os.path.join(config.REPO_OUTPUT_DIR, fname)) as f_out:
                f_out.write(raw_pk)
        except Exception as e:
            logger.error(f"❌ Lỗi nén {fname}: {e}")

    write_release_file(archs_seen)

    # ⚠️ Cảnh báo kiến trúc: máy rootful (iphoneos-arm) KHÔNG thấy gói chỉ có arm64
    arch_map = defaultdict(set)
    for (bid, arch) in versions_by_arch:
        arch_map[bid].add(arch)
    for bid, archs in sorted(arch_map.items()):
        if "iphoneos-arm" not in archs:
            logger.warning(f"⚠️ {bid} chỉ có {sorted(archs)} → máy rootful (iphoneos-arm) sẽ KHÔNG thấy trên Sileo/Cydia")

    # ── debs.json ────────────────────────────────────────────────────
    # Gom tất cả phiên bản theo bundle ID, không lọc bỏ bản cũ
    sileo_tweaks_by_bundle = {}

    for key in sorted(tweaks_map.keys(), key=lambda k: utils.parse_version_tuple(k[2])):
        bid, arch, ver = key
        for v in tweaks_map[key]:
            tweak_title = v["tweak_name"]

            # Khởi tạo entry lần đầu gặp bundle này
            if bid not in sileo_tweaks_by_bundle:
                product_description = v["desc"]
                default_file = os.path.join(config.TWEAK_DESC_DIR, tweak_title, "default.txt")
                if (not product_description or len(str(product_description).strip()) <= 5) and os.path.exists(default_file):
                    product_description = _read_file(default_file) or product_description

                sileo_tweaks_by_bundle[bid] = {
                    "name": v["name"],
                    "bundle": bid,
                    "version": v["ver"],        # sẽ được cập nhật lên bản mới nhất bên dưới
                    "date": v["date"],
                    "section": v["section"],
                    "author": v["author"],
                    "icon": v["icon"],
                    "size": v["sz"],
                    "downloadURL": v["dl"],
                    "description": product_description,
                    "tweak_name": tweak_title,
                    "screenshotURLs": v["screenshots"],
                    "videoURL": v["video"],
                    "appPermissions": v["permissions"],
                    "versions": []
                }

            entry = sileo_tweaks_by_bundle[bid]

            # Thêm phiên bản này vào danh sách versions (tránh trùng theo cả version + arch)
            v_arch = v["arch"]
            existing_keys = {(vv["version"], vv["architecture"]) for vv in entry["versions"]}
            if (ver, v_arch) not in existing_keys:
                release_note = get_version_note(tweak_title, ver)   # ĐÚNG note của version này
                entry["versions"].append({
                    "version": ver,
                    "date": v["date"],
                    "downloadURL": v["dl"],
                    "size": v["sz"],
                    "architecture": v_arch,
                    "md5": v["md5"],
                    "sha1": v["sha1"],
                    "sha256": v["sha256"],
                    "releaseNote": release_note
                })

            # Cập nhật fields chính lên bản mới nhất của đúng arch này
            latest_ver = latest_per_arch.get((bid, v_arch))
            if ver == latest_ver:
                entry["version"]        = ver
                entry["date"]           = v["date"]
                entry["downloadURL"]    = v["dl"]
                entry["size"]           = v["sz"]
                entry["icon"]           = v["icon"]
                entry["screenshotURLs"] = v["screenshots"]
                entry["videoURL"]       = v["video"]
                entry["appPermissions"] = v["permissions"]
                # 🔑 Mô tả sản phẩm lấy từ bản MỚI NHẤT (trước đây lấy bản cũ nhất)
                _d = v["desc"]
                _df = os.path.join(config.TWEAK_DESC_DIR, tweak_title, "default.txt")
                if (not _d or len(str(_d).strip()) <= 5) and os.path.exists(_df):
                    _d = _read_file(_df) or _d
                entry["description"] = _d

    # Sort versions giảm dần (mới nhất trên đầu) cho từng bundle
    for entry in sileo_tweaks_by_bundle.values():
        entry["versions"].sort(
            key=lambda vv: utils.parse_version_tuple(vv["version"]),
            reverse=True
        )
        # Gắn changelog đầy đủ dựa trên toàn bộ danh sách phiên bản đã có
        tweak_title = entry["tweak_name"]
        latest = entry["versions"][0]["version"] if entry["versions"] else entry["version"]
        entry["changelog"] = config.get_tweak_changelog_history(tweak_title, latest, limit=50)

    # 🔑 FIX: Chuẩn hoá output theo ĐÚNG cấu trúc Feather apps.json /
    # dylibs.json — root: name/identifier/iconURL/apps/news; mỗi entry:
    # name/bundleIdentifier/developerName/subtitle/localizedDescription/
    # iconURL/tintColor/version/versionDate/size/downloadURL/versions[]/
    # screenshotURLs/videoURL/appPermissions. Trước đây debs.json (sileo.json)
    # dùng cấu trúc riêng ("tweaks": [...]) không đồng bộ với 2 nguồn còn lại,
    # khiến việc thêm debs.json làm 1 "nguồn" (source) bị khác định dạng.
    final_debs = []
    for bid, entry in sileo_tweaks_by_bundle.items():
        final_debs.append({
            "name": entry["name"],
            "bundleIdentifier": bid,
            "developerName": entry["author"],
            "subtitle": "Tweak Sideload",
            "localizedDescription": entry["description"],
            "iconURL": entry["icon"],
            "tintColor": config.TINT_COLOR,
            "version": entry["version"],
            "versionDate": entry["date"],
            "size": entry["size"],
            "downloadURL": entry["downloadURL"],
            "versions": [
                {
                    "version": v["version"],
                    "date": v["date"],
                    "size": v["size"],
                    "downloadURL": v["downloadURL"],
                    "localizedDescription": v["releaseNote"] or f"Cập nhật lên v{v['version']}.",
                    "architecture": v["architecture"],
                    "md5": v["md5"],
                    "sha1": v["sha1"],
                    "sha256": v["sha256"]
                }
                for v in entry["versions"]
            ],
            "screenshotURLs": entry["screenshotURLs"],
            "videoURL": entry["videoURL"],
            "appPermissions": entry["appPermissions"]
        })

    final_debs.sort(key=lambda x: x['name'].lower())

    output_json = {
        "name": config.REPO_NAME,
        "identifier": config.SOURCE_IDENTIFIER,
        "iconURL": config.SOURCE_LOGO,
        "apps": final_debs,
        "news": []
    }

    json_output_path = os.path.join(config.REPO_OUTPUT_DIR, 'debs.json')
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(output_json, f, indent=2, ensure_ascii=False)

    logger.info(f"✅ debs.json: {len(final_debs)} tweaks → {json_output_path}")
    return processed_tweaks_titles
