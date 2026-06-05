# .github/scripts/gemini.py

import os
import logging
import logger
import json
import urllib.request
import requests  # 🌟 BỔ SUNG: Import để hàm send_final_report không bị crash
import re
import time
import datetime
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

def scan_repo_inventory(repo_path='../../'):
    """Quét và phân loại tài nguyên trong repo"""
    inv = {"json": 0, "yml": 0, "py": 0, "img": 0}
    img_exts = {'.png', '.jpg', '.jpeg', '.gif', '.svg'}
    for root, dirs, files in os.walk(repo_path):
        if '.git' in dirs: dirs.remove('.git')
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext == '.json': inv["json"] += 1
            elif ext in ['.yml', '.yaml']: inv["yml"] += 1
            elif ext == '.py': inv["py"] += 1
            elif ext in img_exts: inv["img"] += 1
    return inv

def ask_gemini_ai(prompt, retries=2):
    """Hàm bốc câu thoại từ Gemini với cơ chế Retry"""
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        return "Hệ thống đã được dọn dẹp sạch sẽ, kiểm tra key cấu hình ⚙️"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for _ in range(retries):
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode('utf-8'))
                    ai_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                    return re.sub(r'^[`"\']+|[`"\']+$', '', ai_text).strip()
        except Exception:
            time.sleep(1)
            continue
    return "Hệ thống đã đồng bộ hóa thành công ✨"

def process_and_dispatch_env(system_db, old_apps, old_tweaks, total_apps, total_apps_size, total_tweaks, total_tweaks_size):
    event_name = (os.getenv("GITHUB_EVENT_NAME") or "push").lower()
    is_manual = (event_name in ["workflow_dispatch", "release"])
    
    new_apps = set(system_db.get("apps", {}).keys()) - old_apps
    new_tweaks = set(system_db.get("tweaks", {}).keys()) - old_tweaks
    
    change_logs = []
    for url in new_apps:
        app = system_db["apps"].get(url)
        if app: change_logs.append(f"🔹 {app.get('name')} (v{app.get('ver')})")
    for url in new_tweaks:
        tweak = system_db["tweaks"].get(url)
        if tweak: change_logs.append(f"🔸 {tweak.get('Name') or tweak.get('name', 'Tweak')}")

    smart_desc = ", ".join(change_logs) if change_logs else "Cập nhật lại hệ thống"

    # Thời gian và cấu trúc
    now = datetime.datetime.now()
    thu = ["Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy", "Chủ nhật"]
    current_time_str = f"{now.strftime('%H:%M')} {thu[now.weekday()]} {now.strftime('%d/%m/%Y')}"
    
    inv = scan_repo_inventory()
    structure_str = f"IMG: {inv['img']}, JSON: {inv['json']}, PY: {inv['py']}, YML: {inv['yml']}"
    
    # Logic AI thông minh, không gắn cứng
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
    
    ai_description = ask_gemini_ai(prompt)

    # Cấu trúc hiển thị Telegram
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

    # Giới hạn smart_desc để không làm vỡ khung tin nhắn Telegram
    if len(smart_desc) > 120:
        smart_desc = smart_desc[:117] + "..."

    # Ghi vào GITHUB_ENV
    github_env = os.getenv('GITHUB_ENV')
    if github_env:
        with open(github_env, 'a', encoding='utf-8') as f:
            f.write(f"repo_describe<<EOF\n{smart_desc}\nEOF\n")
            f.write(f"AI_DESC<<EOF\n{ai_description}\nEOF\n")

    return bai_viet_telegram

# Hàm gửi tin nhắn độc lập
def send_final_report(message):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Lỗi gửi báo cáo độc lập: {e}")
