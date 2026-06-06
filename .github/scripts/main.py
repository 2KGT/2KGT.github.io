# .github/scripts/main.py
import os
import sys
import time

# 1. Khắc phục đường dẫn gốc TRƯỚC khi import các module khác
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# 2. Import các thư viện hệ thống
import json
import re
import datetime
import requests
import logger

# 3. Import các module cục bộ trong project
import config
import gemini
import fetch_github
from core import feather_engine, sileo_engine


def load_databases():
    """Nạp riêng biệt wikiipa.json và wikideb.json"""
    def read_db(path):
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Lỗi đọc database {path}: {e}", flush=True)
        return {}

    return read_db(config.FEATHER_DATABASE), read_db(config.SILEO_DATABASE)


def save_databases(feather_db, sileo_db):
    """Ghi riêng biệt vào 2 file DB an toàn"""
    def safe_write(path, data):
        tmp_path = f"{path}.tmp"
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, path)
        except Exception as e:
            print(f"Lỗi ghi database {path}: {e}", flush=True)
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    safe_write(config.FEATHER_DATABASE, feather_db)
    safe_write(config.SILEO_DATABASE, sileo_db)


def calculate_repo_statistics():
    """Tính toán thống kê từ apps.json và Packages"""
    apps_json_path = os.path.join(config.REPO_OUTPUT_DIR, 'apps.json')
    total_apps, total_apps_size = 0, "0 MB"
    if os.path.exists(apps_json_path):
        try:
            with open(apps_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f).get("apps", [])
                total_apps = len(data)
                size = sum(int(app.get("size", 0)) for app in data)
                total_apps_size = f"{size / (1024 * 1024):.2f} MB"
        except: pass

    packages_path = os.path.join(config.REPO_OUTPUT_DIR, "Packages")
    total_tweaks, total_tweaks_size = 0, "0 MB"
    if os.path.exists(packages_path):
        try:
            with open(packages_path, "r", encoding="utf-8") as f:
                content = f.read()
                total_tweaks = content.count("Package:")
                sizes = re.findall(r'^Size:\s*(\d+)', content, re.MULTILINE)
                tweak_size = sum(int(s) for s in sizes)
                total_tweaks_size = f"{tweak_size / (1024 * 1024):.2f} MB"
        except: pass
            
    return total_apps, total_apps_size, total_tweaks, total_tweaks_size


def save_commit_message(total_apps, total_tweaks):
    msg = f"🚀 Auto Sync: {total_apps} apps, {total_tweaks} tweaks | {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"
    with open(os.path.join(CURRENT_DIR, '.commit_msg'), 'w', encoding='utf-8') as f:
        f.write(msg)


def main():
    print("🚀 Khởi động Pipeline (Dual-Database Mode)...", flush=True)
    logger.log_step(current_step="start", status="running", live_log="🚀 Khởi chạy Feather và Sileo Engine...")
    
    # 1. Load database và nạp dữ liệu tài nguyên
    feather_db, sileo_db = load_databases()
    if "apps" not in feather_db: feather_db["apps"] = {}
    if "tweaks" not in sileo_db: sileo_db["tweaks"] = {}
    
    raw_assets = fetch_github.get_release_assets()
    total_ipa = len(raw_assets.get("ipa", []))
    total_deb = len(raw_assets.get("deb", []))
    
    logger.log_step(current_step="start", status="running", live_log=f"📊 Tìm thấy {total_ipa} tệp IPA và {total_deb} tệp DEB.")
    time.sleep(0.5)

    # 2. Chạy phân hệ Feather Engine (Xử lý Apps)
    logger.log_step(current_step="feather", status="running", live_log="📂 Đang xử lý tài nguyên cho Feather...")
    processed_apps = feather_engine.run_feather_engine(raw_assets.get("ipa", []), feather_db)
    if processed_apps:
        apps_str = ", ".join(processed_apps)
        logger.log_step(current_step="feather", status="running", live_log=f"📱 Đã xử lý Apps: {apps_str}")
    else:
        logger.log_step(current_step="feather", status="running", live_log="📱 Không có App mới cần xử lý.")
    time.sleep(0.5)
    
    # 3. Chạy phân hệ Sileo Engine (Xử lý Tweaks)
    logger.log_step(current_step="sileo", status="running", live_log="⚙️ Đang xử lý tài nguyên cho Sileo...")
    processed_tweaks = sileo_engine.run_sileo_engine(raw_assets.get("deb", []), sileo_db)
    if processed_tweaks:
        tweaks_str = ", ".join(processed_tweaks)
        logger.log_step(current_step="sileo", status="running", live_log=f"📦 Đã xử lý Tweaks: {tweaks_str}")
    else:
        logger.log_step(current_step="sileo", status="running", live_log="📦 Không có Tweak mới cần xử lý.")
    time.sleep(0.5)
    
    # 4. Lưu lại dữ liệu cấu trúc
    save_databases(feather_db, sileo_db)
    stats = calculate_repo_statistics()
    save_commit_message(stats[0], stats[2])
    
    # 5. Gửi thông báo tổng kết tích hợp AI (Sử dụng danh sách thay đổi thực tế)
    logger.log_step(current_step="deploy", status="running", live_log="🤖 Gửi thông báo phân tích lên Telegram...")
    
    # Khởi tạo chuỗi giao diện từ bộ máy Gemini
    msg = gemini.generate_update_summary(processed_apps, processed_tweaks)
    
    token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id, 
            "text": msg, 
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "reply_markup": {"inline_keyboard": [[{"text": "🌐 Thêm Nguồn Kyic", "url": "https://2kgt.github.io/"}]]}
        }
        try:
            res = requests.post(url, json=payload, timeout=15)
            res.raise_for_status()
            print("🚀 [Telegram] Báo cáo tổng hợp đã được gửi thành công.")
        except Exception as e:
            print(f"❌ Lỗi gửi Telegram thông báo tổng từ main.py: {e}", flush=True)

    # 6. Chốt hạ tiến trình (Hàm logger.log_step giờ đã rỗng nên sẽ pass qua cực an toàn)
    logger.log_step(current_step="deploy", status="success", live_log="🏁 Toàn bộ hệ thống đồng bộ hoàn tất!")


if __name__ == "__main__":
    main()
