# .github/scripts/gemini.py
import os
import sys
import json
import urllib.request
import urllib.error
import re
import time
import datetime
import logging

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import config
import data as _data

logger = logging.getLogger(__name__)

_CACHED_MODEL_NAME = None
_PREFERRED_ORDER_HINTS = ["flash-lite", "flash"]


def _list_available_models(gemini_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode("utf-8"))
    names = []
    for m in data.get("models", []):
        methods = m.get("supportedGenerationMethods", [])
        if "generateContent" in methods:
            name = m.get("name", "")
            if name.startswith("models/"):
                name = name[len("models/"):]
            if name:
                names.append(name)
    return names


def _pick_best_flash_model(model_names):
    flash_models = [n for n in model_names if "flash" in n.lower() and "image" not in n.lower()]
    if not flash_models:
        return model_names[0] if model_names else None
    stable = [n for n in flash_models if "preview" not in n.lower() and "exp" not in n.lower()]
    candidates = stable if stable else flash_models
    for hint in reversed(_PREFERRED_ORDER_HINTS):
        for n in candidates:
            if hint in n.lower():
                return n
    return candidates[0]


def resolve_gemini_model(gemini_key):
    global _CACHED_MODEL_NAME
    if _CACHED_MODEL_NAME:
        return _CACHED_MODEL_NAME
    fallback = "gemini-flash-latest"
    try:
        models = _list_available_models(gemini_key)
        best = _pick_best_flash_model(models)
        _CACHED_MODEL_NAME = best or fallback
    except Exception as e:
        logger.warning(f"⚠️ Không lấy được danh sách model Gemini ({e}), dùng fallback '{fallback}'.")
        _CACHED_MODEL_NAME = fallback
    logger.info(f"🤖 Đang dùng model Gemini: {_CACHED_MODEL_NAME}")
    return _CACHED_MODEL_NAME


def escape_html(text):
    if not text:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ask_gemini_ai(prompt, retries=2):
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip().replace("\n", "").replace("\r", "")
    if not gemini_key:
        logger.warning("⚠️ Thiếu GEMINI_API_KEY, bỏ qua gọi AI.")
        return ""

    model_name = resolve_gemini_model(gemini_key)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
    headers = {"Content-Type": "application/json"}
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")

    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))

            candidates = result.get("candidates", [])
            if not candidates:
                logger.warning("⚠️ Gemini trả về candidates rỗng.")
                return ""
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                logger.warning("⚠️ Gemini trả về parts rỗng.")
                return ""
            ai_text = parts[0].get("text", "").strip()
            return re.sub(r'^[`"\']+|[`"\']+$', '', ai_text).strip()

        except urllib.error.HTTPError as e:
            if e.code == 404:
                logger.warning(f"⚠️ Model '{model_name}' trả 404, dò lại model...")
                global _CACHED_MODEL_NAME
                _CACHED_MODEL_NAME = None
                model_name = resolve_gemini_model(gemini_key)
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
                continue
            if 400 <= e.code < 500:
                logger.error(f"❌ Lỗi Gemini API {e.code}: {e.reason}")
                return ""
            logger.warning(f"⚠️ Lỗi Gemini HTTP {e.code} lần {attempt}/{retries}: {e.reason}")
        except urllib.error.URLError as e:
            logger.warning(f"⚠️ Lỗi kết nối Gemini lần {attempt}/{retries}: {e.reason}")
        except Exception as e:
            logger.warning(f"⚠️ Lỗi Gemini lần {attempt}/{retries}: {e}")

        if attempt < retries:
            time.sleep(1.5)

    return ""


def generate_update_summary(processed_apps, processed_tweaks, stats_data=None):
    event_name = (os.getenv("GITHUB_EVENT_NAME") or "push").lower()
    is_manual = event_name in ["workflow_dispatch", "release"]

    if stats_data and len(stats_data) == 4:
        total_apps, total_apps_size, total_tweaks, total_tweaks_size = stats_data
    else:
        total_apps = len(processed_apps) if processed_apps else 0
        total_tweaks = len(processed_tweaks) if processed_tweaks else 0
        total_apps_size = "Đã cập nhật"
        total_tweaks_size = "Đã cập nhật"

    raw_logs = []
    if processed_apps:
        raw_logs.extend([f"App: {a}" for a in processed_apps])
    if processed_tweaks:
        raw_logs.extend([f"Tweak: {t}" for t in processed_tweaks])
    raw_desc = ", ".join(raw_logs) if raw_logs else "Tối ưu hóa hệ thống & Bảo trì định kỳ"

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_ict = now_utc + datetime.timedelta(hours=7)
    thu = ["Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy", "Chủ nhật"]
    current_time_str = f"{now_ict.strftime('%H:%M')} {thu[now_ict.weekday()]} {now_ict.strftime('%d/%m/%Y')}"

    # ✅ Smart format: Chỉ tổng count, không chi tiết loại ảnh
    try:
        inv = _data.scan_repo_inventory('.')
    except Exception as e:
        logger.warning(f"⚠️ scan_repo_inventory lỗi: {e}")
        inv = {}
    
    if not inv:
        inv = {"json": 0, "png": 0, "jpg": 0, "jpeg": 0, "gif": 0, "svg": 0, "webp": 0, "ipa": 0, "deb": 0, "dylib": 0, "so": 0}
    
    total_img = sum([inv.get(x, 0) for x in ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp']])
    total_yml = inv.get('yml', 0) + inv.get('yaml', 0)  # ✅ Tính tổng YML + YAML
    total_pkg = sum([inv.get(x, 0) for x in ['ipa', 'deb', 'dylib', 'so']])
    
    pkg_detail = f"DEB:{inv.get('deb', 0)} IPA:{inv.get('ipa', 0)}"
    if inv.get('dylib', 0) > 0:
        pkg_detail += f" DYLIB:{inv.get('dylib', 0)}"
    
    structure_str = f"IMG:{total_img} • JSON:{inv.get('json', 0)} • YML:{total_yml} • PKG:{total_pkg}({pkg_detail})"

    event_type = "Hành động thủ công (Chỉ huy)" if is_manual else "Hệ thống tự động (Giám sát)"
    prompt = f"""
Bạn là AI quản trị cao cấp của kho ứng dụng Kyic Store.
Ngữ cảnh vận hành: {event_type}
Tài nguyên vừa thay đổi: {raw_desc}
Thống kê kho bãi: Apps={total_apps}, Tweaks={total_tweaks}, {structure_str}

Nhiệm vụ: Tạo 2 đoạn ngắn cách nhau bằng '|': [Mô_tả] | [Nhận_xét]
1. Mô_tả: 1 câu tóm tắt thay đổi, không liệt kê, dưới 2 dòng
2. Nhận_xét: Dưới 15 từ, kết thúc 1 emoji
Format: Mô_tả | Nhận_xét (không markdown)
"""

    ai_response = ask_gemini_ai(prompt)
    if ai_response and "|" in ai_response:
        parts = ai_response.split("|", maxsplit=1)
        ai_describe = parts[0].strip()
        ai_notes = parts[1].strip()
    else:
        ai_describe = "Đồng bộ hóa thành công các bản cập nhật mới cho kho ứng dụng."
        ai_notes = "Hệ thống đã đồng bộ hóa dữ liệu thành công ✨"

    telegram_desc = escape_html(ai_describe)
    telegram_notes = escape_html(ai_notes)

    bai_viet_telegram = (
        f"🔄 <b>ĐỒNG BỘ HỆ THỐNG REPO</b>\n"
        f"──────────────────\n"
        f"⏰ <b>Time</b>: {current_time_str}\n"
        f"📱 <b>Apps</b>: {total_apps} | {total_apps_size}\n"
        f"📦 <b>Tweaks</b>: {total_tweaks} | {total_tweaks_size}\n"
        f"🏗 <b>More</b>: {structure_str}\n"
        f"📊 <b>Status</b>: Bảo trì hoàn tất\n"
        f"📝 <b>Describe</b>: {telegram_desc}\n"
        f"──────────────────\n"
        f"<b>Notes</b>: {telegram_notes}\n"
        f"──────────────────\n"
    )

    github_desc = raw_desc[:117] + "..." if len(raw_desc) > 117 else raw_desc
    github_env = os.getenv('GITHUB_ENV')
    if github_env:
        try:
            with open(github_env, 'a', encoding='utf-8') as f:
                f.write(f"repo_describe<<EOF\n{github_desc}\nEOF\n")
                f.write(f"AI_DESC<<EOF\n{ai_notes}\nEOF\n")
        except Exception as e:
            logger.warning(f"⚠️ Không ghi GITHUB_ENV: {e}")

    return bai_viet_telegram
