# .github/scripts/gemini.py
import os
import json
import urllib.request
import re
import sys
import random
import datetime

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

def scan_repo_inventory(repo_path='../../'):
    """Quét và phân loại tài nguyên trong repo (Inventory)"""
    inv = {"json": 0, "yml": 0, "py": 0, "img": 0}
    img_exts = {'.png', '.jpg', '.jpeg', '.gif', '.svg'}
    
    # Duyệt qua các tệp trong repo, loại trừ thư mục .git
    for root, dirs, files in os.walk(repo_path):
        if '.git' in dirs: dirs.remove('.git')
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext == '.json': inv["json"] += 1
            elif ext in ['.yml', '.yaml']: inv["yml"] += 1
            elif ext == '.py': inv["py"] += 1
            elif ext in img_exts: inv["img"] += 1
    return inv

def ask_gemini_ai(prompt):
    """Hàm bốc câu thoại trực tiếp từ trí tuệ nhân tạo Gemini"""
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        return "Anh yêu ơi! Hệ thống đã được em dọn dẹp sạch sẽ, honey có muốn kiểm tra gì không! ❤️"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status == 200:
                result = json.loads(response.read().decode('utf-8'))
                ai_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                ai_text = re.sub(r'^[`"\']+|[`"\']+$', '', ai_text).strip()
                return " ".join(ai_text.split())
    except Exception:
        pass
    return "Anh yêu ơi! Hệ thống đã được em dọn dẹp sạch sẽ, honey có muốn kiểm tra gì không! ❤️"

def process_and_dispatch_env(system_db, old_apps, old_tweaks, total_apps, total_apps_size, total_tweaks, total_tweaks_size):
    """Xử lý phân tích dữ liệu và đóng gói bảng tin"""
    event_raw = os.getenv("GITHUB_EVENT_NAME") or "push"
    event_name = str(event_raw).strip().lower()
    
    is_manual = (event_name == "workflow_dispatch")
    is_release = (event_name == "release")

    new_apps_detected = set(system_db.get("apps", {}).keys()) - old_apps
    new_tweaks_detected = set(system_db.get("tweaks", {}).keys()) - old_tweaks
    
    change_logs = []
    if is_manual or is_release:
        for url in new_apps_detected:
            app_info = system_db["apps"].get(url)
            if app_info: change_logs.append(f"🔹 {app_info.get('name')} (v{app_info.get('ver')})")
        for url in new_tweaks_detected:
            tweak_info = system_db["tweaks"].get(url)
            if tweak_info:
                tweak_name = tweak_info.get('Name') or tweak_info.get('name', 'Tweak')
                change_logs.append(f"🔸 {tweak_name}")

    smart_desc = ", ".join(change_logs) if change_logs else "Cập nhật lại hệ thống"

    # AI Description logic
    if is_manual or is_release:
        prompt = f"Hãy viết 1 câu thông báo ngắn đóng vai người yêu {'quyến rũ' if smart_desc == 'Cập nhật lại hệ thống' else 'đáng yêu nịnh nọt'} báo cáo hệ thống. Nội dung: {smart_desc}. Chỉ xuất duy nhất lời thoại."
        ai_description = ask_gemini_ai(prompt)
    else:
        ai_description = "Hệ thống tự động ghi nhận có cập nhật mới nè! ✨🎁"

    # Lấy thông số thời gian và cấu trúc repo
    now = datetime.datetime.now()
    thu_dict = {0: "Thứ hai", 1: "Thứ ba", 2: "Thứ tư", 3: "Thứ năm", 4: "Thứ sáu", 5: "Thứ bảy", 6: "Chủ nhật"}
    current_time_str = f"{now.strftime('%H:%M')} {thu_dict[now.weekday()]} {now.strftime('%d/%m/%Y')}"
    
    inv = scan_repo_inventory()
    structure_str = f"📄 JSON: {inv['json']} | 🖼 Img: {inv['img']} | ⚙️ YML: {inv['yml']} | 🐍 PY: {inv['py']}"

    # CẤU TRÚC BÀI VIẾT TELEGRAM
       # 1. Quét và sắp xếp theo thứ tự A-Z (Img, JSON, PY, YML)
    inv = scan_repo_inventory()
    
    # Sắp xếp theo tên để đảm bảo logic hiển thị A-Z
    structure_str = (
        f"   • Img: {inv['img']}  • JSON: {inv['json']}\n"
        f"   • PY: {inv['py']}  • YML: {inv['yml']}"
    )

    # 2. Cấu trúc bài viết đã tinh gọn, bỏ hết icon thừa
    bai_viet_telegram = (
        f"🔄 <b>ĐỒNG BỘ HỆ THỐNG REPO</b>\n"
        f"──────────────────\n"
        f"⏰ <b>Time</b>: {current_time_str}\n"
        f"📱 <b>Apps</b>: {total_apps} | {total_apps_size}\n"
        f"📦 <b>Tweaks</b>: {total_tweaks} | {total_tweaks_size}\n"
        f"🏗 <b>Structure</b>:\n"
        f"{structure_str}\n"
        f"📊 <b>Status</b>: Bảo trì hoàn tất\n"
        f"📝 <b>Describe</b>: {smart_desc}\n"
        f"──────────────────\n"
        f"💬 <b>Notes</b>: {ai_description}\n"
        f"──────────────────\n"
        f"Hệ thống đã kiểm tra và đồng bộ hoàn tất."
    )

    github_env = os.getenv('GITHUB_ENV')
    if github_env:
        try:
            with open(github_env, 'a', encoding='utf-8') as env_file:
                env_file.write(f"total_apps={total_apps}\n")
                env_file.write(f"total_apps_size={total_apps_size}\n")
                env_file.write(f"total_tweaks={total_tweaks}\n")
                env_file.write(f"total_tweaks_size={total_tweaks_size}\n")
                env_file.write(f"repo_describe<<EOF\n{smart_desc}\nEOF\n")
                env_file.write(f"AI_DESC<<EOF\n{ai_description}\nEOF\n")
        except Exception:
            pass

    return bai_viet_telegram
