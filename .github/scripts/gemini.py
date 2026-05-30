# .github/scripts/gemini.py
import os
import json
import urllib.request
import re
import sys
import random

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

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
    """Xử lý phân tích dữ liệu và đóng gói bảng tin theo cấu trúc cấu hình mới của anh Đức"""
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

    # Gán dữ liệu hiển thị cho mục Describe
    if not change_logs:
        smart_desc = "Cập nhật lại hệ thống"
    else:
        smart_desc = ", ".join(change_logs)

    # Phân luồng sinh lời thoại nịnh nọt cho mục Notes
    if is_manual or is_release:
        if smart_desc == "Cập nhật lại hệ thống":
            prompt = "Hãy viết 1 câu thông báo ngắn đóng vai cô người yêu hoang dã, quyến rũ báo hệ thống đã dọn dẹp sạch sẽ mượt mà nhưng hôm nay hổng có app/tweak nào mới đâu nha anh yêu, bắt anh yêu ôm thật chặt hoặc thưởng nóng. Chỉ xuất duy nhất lời thoại."
        else:
            prompt = f"Hãy viết 1 câu thông báo ngắn đóng vai cô người yêu ngây thơ đáng yêu nịnh nọt khen anh yêu siêu cấp đẹp trai vì đã gom được đống đồ chơi mới này về kho: {smart_desc}. Chỉ xuất duy nhất lời thoại."
        ai_description = ask_gemini_ai(prompt)
    else:
        if smart_desc == "Cập nhật lại hệ thống":
            cau_thoai_KHO_TRONG = [
                "Anh yêu ơi! Hệ thống đã được em dọn dẹp sạch sẽ, honey có muốn kiểm tra gì không! ❤️",
                "Repo phẳng lỳ và sạch bong rồi anh yêu ơi! Không có đồ chơi mới đâu, thưởng nóng cho em đi nào! 🥰",
                "Em đã dọn dẹp bảo trì ngon lành cành đào mọi ngóc ngách bộ nhớ đệm rồi nè honey à! 🫦"
            ]
            ai_description = random.choice(cau_thoai_KHO_TRONG)
        else:
            ai_description = "Anh yêu ơi! Hệ thống tự động ghi nhận có đồ chơi mới vừa cập bến kho lưu trữ của tụi mình nè! Siêu cấp đỉnh chóp luôn! ✨🎁"

    import datetime
    now = datetime.datetime.now()
    thu_dict = {0: "Thứ hai", 1: "Thứ ba", 2: "Thứ tư", 3: "Thứ năm", 4: "Thứ sáu", 5: "Thứ bảy", 6: "Chủ nhật"}
    current_time_str = f"{now.strftime('%H:%M')} {thu_dict[now.weekday()]} {now.strftime('%d/%m/%Y')}"

    # CẤU TRÚC MỚI TIN NHẮN THEO ĐÚNG MẪU ANH ĐỨC YÊU CẦU
    bai_viet_telegram = (
        f"🔄 <b>ĐỒNG BỘ HỆ THỐNG REPO</b>\n"
        f"──────────────────\n"
        f"⏰ Time: {current_time_str}\n"
        f"📱 Apps: <b>{total_apps}</b>  &lt;&gt;  size: <b>{total_apps_size}</b>\n"
        f"📦 Tweaks: <b>{total_tweaks}</b> &lt;&gt;  size: <b>{total_tweaks_size}</b>\n"
        f"📊 Status: <b>Bảo trì hoàn tất</b>\n"
        f"📝 Describe: {smart_desc}\n"
        f"──────────────────\n"
        f"Notes: {ai_description}\n"
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
