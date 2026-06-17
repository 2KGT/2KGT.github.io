# .github/scripts/gemini.py
import os
import json
import urllib.request
import urllib.error
import re
import time
import datetime
import sys
import logging

# FIX: Bỏ import requests — dùng urllib thuần nhất quán với toàn bộ codebase
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import config

logger = logging.getLogger(__name__)


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
    """
    Gọi Gemini API với cơ chế retry.

    FIX 1: Không dùng response.status để kiểm tra — urlopen đã raise HTTPError
    nếu status không phải 2xx, nên kiểm tra status là thừa và có thể bỏ sót lỗi.
    FIX 2: Truy cập an toàn vào cấu trúc JSON trả về — tránh KeyError nếu
    Gemini trả về response thiếu field (ví dụ bị chặn bởi safety filter).
    FIX 3: Phân biệt HTTPError (quota, key sai) với lỗi mạng — không retry
    khi gặp lỗi 400/403 vì retry sẽ không giải quyết được.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        logger.warning("⚠️ Thiếu GEMINI_API_KEY, bỏ qua gọi AI.")
        return ""

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={gemini_key}"
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

        # FIX 3: Không retry lỗi client (4xx) — retry chỉ có ý nghĩa với lỗi server/mạng
        except urllib.error.HTTPError as e:
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


# FIX: Bỏ hàm send_final_report — chức năng này đã được xử lý tập trung
# trong main.py bằng send_telegram(). Giữ 2 nơi gửi Telegram gây trùng lặp
# và khó kiểm soát token/chat_id.
