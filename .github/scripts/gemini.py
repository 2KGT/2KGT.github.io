# .github/scripts/gemini.py
import os
import json
import urllib.request
import requests
import re
import time
import datetime
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import config

def escape_html(text):
    """Bảo vệ các ký tự đặc biệt, tránh làm vỡ định dạng HTML của Telegram"""
    if not text:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def scan_repo_inventory(repo_path='.'):
    """Quét sạch tài nguyên kho bãi, cho phép đi sâu vào các folder hệ thống như .github"""
    inv = {"json": 0, "yml": 0, "py": 0, "img": 0}
    img_exts = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'}
    if not os.path.exists(repo_path):
        return inv
        
    for root, dirs, files in os.walk(repo_path):
        # Chỉ loại bỏ .git lịch sử và node_modules để giữ hiệu năng, cho phép quét .github
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
    """Hàm lấy câu thoại từ Gemini với cơ chế Retry"""
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        return ""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for i in range(retries):
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode('utf-8'))
                    ai_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                    return re.sub(r'^[`"\']+|[`"\']+$', '', ai_text).strip()
        except Exception as e:
            print(f"⚠️ Thử lại gọi API Gemini lần {i+1} thất bại: {e}")
            time.sleep(1.5)
            continue
    return ""

def generate_update_summary(processed_apps, processed_tweaks, stats_data=None):
    """🌟 HÀM ĐỒNG BỘ CHÍNH: Tạo nội dung thông báo tổng hợp bằng AI"""
    event_name = (os.getenv("GITHUB_EVENT_NAME") or "push").lower()
    is_manual = (event_name in ["workflow_dispatch", "release"])
    
    # 1. Tiếp nhận số liệu thống kê chuẩn xác từ main.py truyền sang
    if stats_data and len(stats_data) == 4:
        total_apps, total_apps_size, total_tweaks, total_tweaks_size = stats_data
    else:
        total_apps = len(processed_apps) if processed_apps else 0
        total_tweaks = len(processed_tweaks) if processed_tweaks else 0
        total_apps_size = "Đã cập nhật"
        total_tweaks_size = "Đã cập nhật"

    # 2. Tạo danh sách text thô gom các ứng dụng/tiện ích đổi mới làm ngữ cảnh cho AI
    raw_logs = []
    if processed_apps:
        for app in processed_apps: raw_logs.append(f"App: {app}")
    if processed_tweaks:
        for tweak in processed_tweaks: raw_logs.append(f"Tweak: {tweak}")
    raw_desc = ", ".join(raw_logs) if raw_logs else "Tối ưu hóa hệ thống & Bảo trì định kỳ"

    # 3. Tính toán thời gian chạy hệ thống (Chuẩn Giờ Việt Nam +7)
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_ict = now_utc + datetime.timedelta(hours=7)
    thu = ["Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy", "Chủ nhật"]
    current_time_str = f"{now_ict.strftime('%H:%M')} {thu[now_ict.weekday()]} {now_ict.strftime('%d/%m/%Y')}"
    
    # 4. Quét cấu trúc tài nguyên thực tế tại kho bãi (Bao gồm .github)
    inv = scan_repo_inventory('.')
    structure_str = f"IMG: {inv['img']}, JSON: {inv['json']}, PY: {inv['py']}, YML: {inv['yml']}"
    
    # 5. Gọi AI đúc kết cấu trúc chuỗi kết quả
    event_type = "Hành động thủ công (Chỉ huy)" if is_manual else "Hệ thống tự động (Giám sát)"
    
    prompt = f"""
    Bạn là AI quản trị cao cấp của kho ứng dụng Kyic Store.
    Ngữ cảnh vận hành: {event_type}
    Tài nguyên vừa thay đổi: {raw_desc}
    Thống kê kho bãi hiện tại: Apps={total_apps}, Tweaks={total_tweaks}, Cấu trúc file={structure_str}

    Nhiệm vụ: Tạo ra đúng 2 đoạn văn bản ngắn, NGĂN CÁCH BIỂU DIỄN BẰNG KÝ TỰ GẠCH ĐỨNG '|' theo cấu trúc: [Đoạn_Describe] | [Đoạn_Notes]

    Yêu cầu nghiêm ngặt:
    1. [Đoạn_Describe]: Viết một câu tóm tắt tổng hợp các app/tweak vừa đổi mới hoặc nâng cấp bản vá một cách mượt mà. TUYỆT ĐỐI không liệt kê danh sách, không lặp lại từ ngữ, ngắn gọn dưới 2 dòng. (Ví dụ: Cập nhật loạt công cụ ký số ESign, GBox và đồng bộ các gói tiện ích mod nâng cấp cho YouTube, Facebook).
    2. [Đoạn_Notes]: Nhận xét vận hành ngắn dưới 15 từ. Nếu thủ công: khẳng định quyền kiểm soát hệ thống; Nếu tự động: nhấn mạnh tiến trình mượt mà tối ưu. Cuối câu kết thúc bằng đúng 1 emoji phù hợp.
    3. Phản hồi xuất ra phải tuân thủ nghiêm ngặt định dạng thô phân tách bằng dấu gạch đứng, không chứa các ký tự định dạng markdown bọc ngoài: Đoạn_Describe | Đoạn_Notes
    """
    
    ai_response = ask_gemini_ai(prompt)
    
    # Tách chuỗi kết quả phân tách, xử lý chống lỗi dữ liệu trả về vỡ định dạng
    if ai_response and "|" in ai_response:
        parts = ai_response.split("|")
        ai_describe = parts[0].strip()
        ai_notes = parts[1].strip()
    else:
        ai_describe = "Đồng bộ hóa thành công các bản cập nhật mới cho kho ứng dụng và tiện ích mod hệ thống."
        ai_notes = "Hệ thống đã đồng bộ hóa dữ liệu thành công ✨"

    # 6. Định dạng bảo vệ HTML Telegram
    telegram_desc = escape_html(ai_describe)
    telegram_ai_notes = escape_html(ai_notes)

    # Đóng gói giao diện cấu trúc báo cáo Telegram HTML công bố
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

    # 7. Xử lý đẩy dữ liệu sạch ra GITHUB_ENV
    github_desc = raw_desc[:117] + "..." if len(raw_desc) > 120 else raw_desc
    github_env = os.getenv('GITHUB_ENV')
    if github_env:
        try:
            with open(github_env, 'a', encoding='utf-8') as f:
                f.write(f"repo_describe<<EOF\n{github_desc}\nEOF\n")
                f.write(f"AI_DESC<<EOF\n{ai_notes}\nEOF\n")
        except Exception as e:
            print(f"⚠️ Không ghi được vào GITHUB_ENV: {e}")

    return bai_viet_telegram

def send_final_report(message):
    """Hàm gửi tin nhắn độc lập lên Telegram thông qua requests"""
    token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("❌ Thất bại: Thiếu cấu hình TELEGRAM_TOKEN!")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        res = requests.post(url, json=payload, timeout=12)
        res.raise_for_status()
        print("🚀 [Telegram] Báo cáo tổng hợp đã được gửi thành công.")
    except Exception as e:
        print(f"❌ Lỗi gửi Telegram độc lập: {e}")
