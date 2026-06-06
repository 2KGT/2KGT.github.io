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
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def scan_repo_inventory(repo_path='.'):
    """Quét và phân loại tài nguyên tại Root của repo"""
    inv = {"json": 0, "yml": 0, "py": 0, "img": 0}
    img_exts = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'}
    if not os.path.exists(repo_path):
        return inv
        
    for root, dirs, files in os.walk(repo_path):
        # Tối ưu hóa: Bỏ qua các thư mục hệ thống ngay từ vòng lặp duyệt để tăng tốc
        dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', '.github')]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext == '.json': inv["json"] += 1
            elif ext in ('.yml', '.yaml'): inv["yml"] += 1
            elif ext == '.py': inv["py"] += 1
            elif ext in img_exts: inv["img"] += 1
    return inv

def ask_gemini_ai(prompt, retries=2):
    """Hàm lấy câu thoại từ Gemini với cơ chế Retry"""
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        return "Hệ thống hoạt động ổn định, tiến trình tự động hoàn tất ⚙️"

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
                    # Loại bỏ các dấu nháy thừa ở đầu/cuối chuỗi do AI phản hồi
                    return re.sub(r'^[`"\']+|[`"\']+$', '', ai_text).strip()
        except Exception as e:
            print(f"⚠️ Thử lại gọi API Gemini lần {i+1} thất bại: {e}")
            time.sleep(1.5)
            continue
    return "Hệ thống đã đồng bộ hóa dữ liệu thành công ✨"

def get_file_size_display(file_path):
    """Tính dung lượng file trả về chuỗi định dạng dễ đọc"""
    if os.path.exists(file_path):
        size_bytes = os.path.getsize(file_path)
        if size_bytes >= 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        return f"{size_bytes / 1024:.2f} KB"
    return "0 KB"

def generate_update_summary(processed_apps, processed_tweaks):
    """🌟 HÀM ĐỒNG BỘ CHÍNH: Tạo nội dung thông báo tổng hợp"""
    event_name = (os.getenv("GITHUB_EVENT_NAME") or "push").lower()
    is_manual = (event_name in ["workflow_dispatch", "release"])
    
    # 1. Đếm số lượng tệp thực tế
    total_apps = 0
    if os.path.exists(config.APPS_INPUT_DIR):
        total_apps = len([f for f in os.listdir(config.APPS_INPUT_DIR) if f.endswith('.ipa')])
        
    total_tweaks = 0
    if os.path.exists(config.DEBS_INPUT_DIR):
        for root, dirs, files in os.walk(config.DEBS_INPUT_DIR):
            total_tweaks += len([f for f in files if f.endswith('.deb')])

    # 2. Lấy dung lượng tệp cơ sở dữ liệu đầu ra
    apps_json_path = os.path.join(config.REPO_OUTPUT_DIR, 'apps.json')
    packages_path = os.path.join(config.REPO_OUTPUT_DIR, 'Packages')
    
    total_apps_size = get_file_size_display(apps_json_path) if total_apps > 0 else "0 MB"
    total_tweaks_size = get_file_size_display(packages_path) if total_tweaks > 0 else "0 KB"

    # 3. Tổng hợp danh sách thay đổi thực tế (Cần Escape HTML để tránh lỗi Telegram hiển thị)
    change_logs = []
    if processed_apps:
        for app in processed_apps: change_logs.append(f"🔹 {escape_html(app)}")
    if processed_tweaks:
        for tweak in processed_tweaks: change_logs.append(f"🔸 {escape_html(tweak)}")

    smart_desc = ", ".join(change_logs) if change_logs else "Tối ưu hóa &amp; Đồng bộ định kỳ"

    # 4. Tính toán thời gian chạy hệ thống (Fix lệch múi giờ +7 từ UTC của GitHub)
    now_utc = datetime.datetime.utcnow()
    now_ict = now_utc + datetime.timedelta(hours=7)
    thu = ["Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy", "Chủ nhật"]
    current_time_str = f"{now_ict.strftime('%H:%M')} {thu[now_ict.weekday()]} {now_ict.strftime('%d/%m/%Y')}"
    
    # 5. Quét cấu trúc tài nguyên kho bãi hiện tại
    inv = scan_repo_inventory('.')
    structure_str = f"IMG: {inv['img']}, JSON: {inv['json']}, PY: {inv['py']}, YML: {inv['yml']}"
    
    # 6. Gọi AI tạo lời bình luận thông minh ngắn gọn
    event_type = "Manual/Control" if is_manual else "Auto/Monitoring"
    data_metrics = f"Apps: {total_apps}, Tweaks: {total_tweaks}, Structure: {structure_str}"
    
    prompt = f"""
    Bạn là AI quản trị hệ thống của Kyic.
    Ngữ cảnh: {event_type} | Thay đổi: {smart_desc} | Dữ liệu: {data_metrics}.
    Nhiệm vụ:
    - Nếu Manual: Viết như một chỉ huy, khẳng định sự kiểm soát và tính ổn định.
    - Nếu Auto: Viết như hệ thống giám sát, nhấn mạnh sự mượt mà và tối ưu.
    - TUYỆT ĐỐI không dùng câu văn mẫu, không nịnh nọt.
    - Sử dụng thuật ngữ công nghệ, chuyên nghiệp, súc tích (dưới 30 từ).
    - Kết thúc bằng 1 icon độc nhất phù hợp. Chỉ trả về lời thoại.
    """
    
    ai_description = escape_html(ask_gemini_ai(prompt))

    # 7. Xây dựng khung giao diện bài viết Telegram HTML chuẩn chỉnh
    bai_viet_telegram = (
        f"🔄 <b>ĐỒNG BỘ HỆ THỐNG REPO</b>\n"
        f"──────────────────\n"
        f"⏰ <b>Time</b>: {current_time_str}\n"
        f"📱 <b>Apps</b>: {total_apps} | {total_apps_size}\n"
        f"📦 <b>Tweaks</b>: {total_tweaks} | {total_tweaks_size}\n"
        f"🏗 <b>More</b>: {structure_str}\n"
        f"📊 <b>Status</b>: Bảo trì hoàn tất\n"
        f"📝 <b>Describe</b>: {smart_desc}\n"
        f"──────────────────\n"
        f"<b>Notes</b>: {ai_description}\n"
        f"──────────────────\n"
    )

    # Khống chế độ dài chuỗi describe phục vụ ghi xuất GitHub Actions Env (Không làm ảnh hưởng telegram)
    github_desc = smart_desc
    if len(github_desc) > 120:
        github_desc = github_desc[:117] + "..."

    # Ghi xuất dự phòng vào GITHUB_ENV
    github_env = os.getenv('GITHUB_ENV')
    if github_env:
        try:
            with open(github_env, 'a', encoding='utf-8') as f:
                f.write(f"repo_describe<<EOF\n{github_desc}\nEOF\n")
                f.write(f"AI_DESC<<EOF\n{ai_description}\nEOF\n")
        except Exception as e:
            print(f"⚠️ Không ghi được vào GITHUB_ENV: {e}")

    return bai_viet_telegram

def send_final_report(message):
    """Hàm gửi tin nhắn độc lập lên Telegram bằng thư viện requests có xử lý ngoại lệ nghiêm ngặt"""
    token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("❌ Thất bại: Thiếu cấu hình TELEGRAM_TOKEN hoặc TELEGRAM_CHAT_ID trong Secrets!")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    try:
        res = requests.post(url, json=payload, timeout=12)
        # Ép buộc ném ra ngoại lệ nếu HTTP Status Code >= 400
        res.raise_for_status()
        print("🚀 [Telegram] Báo cáo tổng hợp đã được gửi thành công.")
    except requests.exceptions.HTTPError as http_err:
        print(f"❌ Lỗi HTTP từ Telegram API: {http_err}")
        if res.status_code == 400:
            print("👉 Gợi ý: Kiểm tra lại cú pháp thẻ HTML hoặc các ký tự đặc biệt chưa được đóng.")
        print(f"Chi tiết phản hồi từ Telegram: {res.text}")
    except Exception as e:
        print(f"❌ Lỗi kết nối không xác định khi gửi Telegram: {e}")
