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

# FIX: Bỏ import requests — dùng urllib thuần nhất quán với toàn bộ codebase
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import config

logger = logging.getLogger(__name__)

# ==========================================
# CACHE TÊN MODEL KHẢ DỤNG (tự động dò qua ListModels)
# ==========================================
# Lý do: Google liên tục deprecate model (gemini-1.5-flash, gemini-2.0-flash...
# đã bị khai tử và trả 404). Thay vì hardcode 1 tên model cố định rồi lại dính
# 404 lần nữa trong tương lai, ta hỏi thẳng API "model nào đang dùng được"
# rồi chọn 1 model flash phù hợp. Cache lại để không gọi ListModels nhiều lần
# trong cùng 1 lần chạy script (chỉ gọi 1 lần đầu tiên cần dùng).
_CACHED_MODEL_NAME = None

# Thứ tự ưu tiên khi có nhiều model flash khả dụng: ưu tiên bản ổn định (GA),
# không có hậu tố preview/-latest/exp, vì các bản preview có thể bị tắt đột ngột.
_PREFERRED_ORDER_HINTS = ["flash-lite", "flash"]


def _list_available_models(gemini_key):
    """Gọi ListModels, trả về list tên model (đã bỏ tiền tố 'models/') hỗ trợ generateContent."""
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
    """Chọn model flash phù hợp nhất: ưu tiên bản GA, tránh preview/exp nếu có lựa chọn khác."""
    flash_models = [n for n in model_names if "flash" in n.lower() and "image" not in n.lower()]
    if not flash_models:
        # Không có model flash nào -> đành lấy model bất kỳ hỗ trợ generateContent
        return model_names[0] if model_names else None

    # Ưu tiên bản KHÔNG preview/exp trước
    stable = [n for n in flash_models if "preview" not in n.lower() and "exp" not in n.lower()]
    candidates = stable if stable else flash_models

    # Trong các ứng viên, ưu tiên theo gợi ý thứ tự (flash thường, không phải lite)
    for hint in reversed(_PREFERRED_ORDER_HINTS):
        for n in candidates:
            if hint in n.lower():
                return n

    return candidates[0]


def resolve_gemini_model(gemini_key):
    """
    Trả về tên model Gemini khả dụng cho API key hiện tại, có cache trong
    vòng đời script. Nếu ListModels lỗi (mất mạng, key sai...), fallback về
    alias 'gemini-flash-latest' — alias này do Google duy trì, tự trỏ sang
    bản mới nhất nên hiếm khi bị 404 vì model cũ bị khai tử.
    """
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
    """Bảo vệ các ký tự đặc biệt, tránh làm vỡ định dạng HTML của Telegram"""
    if not text:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def scan_repo_inventory(repo_path='.'):
    """Quét tài nguyên kho bãi, cho phép đi sâu vào các folder hệ thống như .github"""
    inv = {"json": 0, "yml": 0, "py": 0, "img": 0}
    img_exts = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'}
    if not os.path.exists(repo_path):
        return inv

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules')]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext == '.json':
                inv["json"] += 1
            elif ext in ('.yml', '.yaml'):
                inv["yml"] += 1
            elif ext == '.py':
                inv["py"] += 1
            elif ext in img_exts:
                inv["img"] += 1
    return inv


def ask_gemini_ai(prompt, retries=2):
    # LÀM SẠCH KEY: loại bỏ khoảng trắng và xuống dòng thừa
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip().replace("\n", "").replace("\r", "")

    if not gemini_key:
        logger.warning("⚠️ Thiếu GEMINI_API_KEY, bỏ qua gọi AI.")
        return ""

    model_name = resolve_gemini_model(gemini_key)

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:generateContent?key={gemini_key}"
    )
    headers = {"Content-Type": "application/json"}
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")

    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))

            # FIX 2: Truy cập an toàn — Gemini có thể trả về candidates rỗng
            candidates = result.get("candidates", [])
            if not candidates:
                logger.warning("⚠️ Gemini trả về candidates rỗng (có thể bị safety filter).")
                return ""

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                logger.warning("⚠️ Gemini trả về parts rỗng.")
                return ""

            ai_text = parts[0].get("text", "").strip()
            return re.sub(r'^[`"\']+|[`"\']+$', '', ai_text).strip()

        # FIX 3: Không retry lỗi client (4xx) — TRỪ lỗi 404 do tên model lỗi thời,
        # trường hợp đó thử xoá cache để dò lại model 1 lần rồi retry tiếp.
        except urllib.error.HTTPError as e:
            if e.code == 404:
                logger.warning(f"⚠️ Model '{model_name}' trả 404 (có thể đã bị deprecate). Dò lại model khả dụng...")
                global _CACHED_MODEL_NAME
                _CACHED_MODEL_NAME = None
                model_name = resolve_gemini_model(gemini_key)
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{model_name}:generateContent?key={gemini_key}"
                )
                # Không tính là 1 lần retry "thật", thử lại ngay với model mới
                continue
            if 400 <= e.code < 500:
                logger.error(f"❌ Lỗi Gemini API {e.code} (không retry): {e.reason}")
                return ""
            logger.warning(f"⚠️ Lỗi Gemini HTTP {e.code} lần {attempt}/{retries}: {e.reason}")

        except urllib.error.URLError as e:
            logger.warning(f"⚠️ Lỗi kết nối Gemini lần {attempt}/{retries}: {e.reason}")

        except Exception as e:
            logger.warning(f"⚠️ Lỗi không xác định Gemini lần {attempt}/{retries}: {e}")

        if attempt < retries:
            time.sleep(1.5)

    return ""


def generate_update_summary(processed_apps, processed_tweaks, stats_data=None):
    """🌟 HÀM ĐỒNG BỘ CHÍNH: Tạo nội dung thông báo tổng hợp bằng AI"""
    event_name = (os.getenv("GITHUB_EVENT_NAME") or "push").lower()
    is_manual = event_name in ["workflow_dispatch", "release"]

    # 1. Tiếp nhận số liệu thống kê từ main.py
    if stats_data and len(stats_data) == 4:
        total_apps, total_apps_size, total_tweaks, total_tweaks_size = stats_data
    else:
        total_apps = len(processed_apps) if processed_apps else 0
        total_tweaks = len(processed_tweaks) if processed_tweaks else 0
        total_apps_size = "Đã cập nhật"
        total_tweaks_size = "Đã cập nhật"

    # 2. Gom danh sách thay đổi làm ngữ cảnh cho AI
    raw_logs = []
    if processed_apps:
        raw_logs.extend([f"App: {a}" for a in processed_apps])
    if processed_tweaks:
        raw_logs.extend([f"Tweak: {t}" for t in processed_tweaks])
    raw_desc = ", ".join(raw_logs) if raw_logs else "Tối ưu hóa hệ thống & Bảo trì định kỳ"

    # 3. Thời gian Việt Nam UTC+7
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_ict = now_utc + datetime.timedelta(hours=7)
    thu = ["Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy", "Chủ nhật"]
    current_time_str = f"{now_ict.strftime('%H:%M')} {thu[now_ict.weekday()]} {now_ict.strftime('%d/%m/%Y')}"

    # 4. Quét cấu trúc tài nguyên kho bãi
    inv = scan_repo_inventory('.')
    structure_str = f"IMG: {inv['img']}, JSON: {inv['json']}, PY: {inv['py']}, YML: {inv['yml']}"

    # 5. Gọi Gemini sinh nội dung
    event_type = "Hành động thủ công (Chỉ huy)" if is_manual else "Hệ thống tự động (Giám sát)"

    prompt = f"""
Bạn là AI quản trị cao cấp của kho ứng dụng Kyic Store.
Ngữ cảnh vận hành: {event_type}
Tài nguyên vừa thay đổi: {raw_desc}
Thống kê kho bãi hiện tại: Apps={total_apps}, Tweaks={total_tweaks}, Cấu trúc file={structure_str}

Nhiệm vụ: Tạo ra đúng 2 đoạn văn bản ngắn, NGĂN CÁCH BIỂU DIỄN BẰNG KÝ TỰ GẠCH ĐỨNG '|' theo cấu trúc: [Đoạn_Describe] | [Đoạn_Notes]

Yêu cầu nghiêm ngặt:
1. [Đoạn_Describe]: Viết một câu tóm tắt tổng hợp các app/tweak vừa đổi mới hoặc nâng cấp bản vá một cách mượt mà. TUYỆT ĐỐI không liệt kê danh sách, không lặp lại từ ngữ, ngắn gọn dưới 2 dòng.
2. [Đoạn_Notes]: Nhận xét vận hành ngắn dưới 15 từ. Nếu thủ công: khẳng định quyền kiểm soát hệ thống; Nếu tự động: nhấn mạnh tiến trình mượt mà tối ưu. Cuối câu kết thúc bằng đúng 1 emoji phù hợp.
3. Phản hồi xuất ra phải tuân thủ nghiêm ngặt định dạng thô phân tách bằng dấu gạch đứng, không chứa các ký tự định dạng markdown bọc ngoài: Đoạn_Describe | Đoạn_Notes
"""

    ai_response = ask_gemini_ai(prompt)

    # FIX: Lấy phần đầu tiên làm describe, ghép phần còn lại thành notes
    # Tránh mất nội dung nếu AI trả về chuỗi có nhiều hơn 1 dấu '|'
    if ai_response and "|" in ai_response:
        parts = ai_response.split("|", maxsplit=1)
        ai_describe = parts[0].strip()
        ai_notes = parts[1].strip()
    else:
        ai_describe = "Đồng bộ hóa thành công các bản cập nhật mới cho kho ứng dụng và mod tiện ích hệ thống."
        ai_notes = "Hệ thống đã đồng bộ hóa dữ liệu thành công ✨"

    # 6. Escape HTML cho Telegram
    telegram_desc = escape_html(ai_describe)
    telegram_ai_notes = escape_html(ai_notes)

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
        f"<b>Notes</b>: {telegram_ai_notes}\n"
        f"──────────────────\n"
    )

    # 7. Ghi vào GITHUB_ENV
    # FIX: Cắt raw_desc đúng tại 117 ký tự, không phải kiểm tra > 120 rồi cắt 117
    github_desc = raw_desc[:117] + "..." if len(raw_desc) > 117 else raw_desc
    github_env = os.getenv('GITHUB_ENV')
    if github_env:
        try:
            with open(github_env, 'a', encoding='utf-8') as f:
                f.write(f"repo_describe<<EOF\n{github_desc}\nEOF\n")
                f.write(f"AI_DESC<<EOF\n{ai_notes}\nEOF\n")
        except Exception as e:
            logger.warning(f"⚠️ Không ghi được vào GITHUB_ENV: {e}")

    return bai_viet_telegram
