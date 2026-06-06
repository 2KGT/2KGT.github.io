# .github/scripts/main.py
import os
import sys
import time
import json
import re
import datetime
import requests

# Khắc phục đường dẫn gốc trước khi nạp các module nội bộ
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import config
import gemini
import fetch_github
from core import feather_engine, sileo_engine


def load_databases():
    """Nạp dữ liệu bộ nhớ đệm wikiipa.json và wikideb.json độc lập"""
    def read_db(path):
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Lỗi đọc database {path}: {e}", flush=True)
        return {}

    return read_db(config.FEATHER_DATABASE), read_db(config.SILEO_DATABASE)


def save_databases(feather_db, sileo_db):
    """Ghi đè dữ liệu cấu trúc vào 2 tệp DB thông qua file tạm an toàn"""
    def safe_write(path, data):
        tmp_path = f"{path}.tmp"
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, path)
        except Exception as e:
            print(f"❌ Lỗi ghi database {path}: {e}", flush=True)
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    safe_write(config.FEATHER_DATABASE, feather_db)
    safe_write(config.SILEO_DATABASE, sileo_db)


def calculate_repo_statistics():
    """Tính toán tổng số lượng và dung lượng của ứng dụng và tweaks"""
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
    """Lưu thông điệp đẩy lên Git ra ngoài thư mục gốc để né trigger path lặp vô tận"""
    msg = f"🚀 Auto Sync: {total_apps} apps, {total_tweaks} tweaks | {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"
    commit_file_path = os.path.join(config.REPO_ROOT, '.commit_msg')
    try:
        with open(commit_file_path, 'w', encoding='utf-8') as f:
            f.write(msg)
        print(f"📝 Đã tạo file commit_msg: {msg}", flush=True)
    except Exception as e:
        print(f"⚠️ Không thể lưu file commit_msg: {e}", flush=True)


def main():
    """🌟 PHÂN HỆ ĐIỀU PHỐI CHÍNH (Core Automation Engine)"""
    print("🎬 Khởi chạy hệ thống tự động hóa Kyic Premium Store...", flush=True)
    
    # 1. Khởi tạo bộ nhớ đệm database và quét file trên GitHub Releases
    feather_db, sileo_db = load_databases()
    if "apps" not in feather_db: feather_db["apps"] = {}
    if "tweaks" not in sileo_db: sileo_db["tweaks"] = {}
    
    raw_assets = fetch_github.get_release_assets()
    total_ipa = len(raw_assets.get("ipa", []))
    total_deb = len(raw_assets.get("deb", []))
    
    print(f"📊 Hệ thống quét đám mây: Tìm thấy {total_ipa} tệp IPA và {total_deb} tệp DEB.", flush=True)
    time.sleep(0.5)

    # 2. Xử lý luồng dữ liệu IPA (Feather Engine)
    print("📂 Đang nạp phân hệ Feather Engine...", flush=True)
    processed_apps = feather_engine.run_feather_engine(raw_assets.get("ipa", []), feather_db)
    if processed_apps:
        print(f"📱 Hoàn tất xử lý Apps: {', '.join(processed_apps)}", flush=True)
    else:
        print("📱 Không phát hiện App mới cần xử lý bổ sung.", flush=True)
    time.sleep(0.5)
    
    # 3. Xử lý luồng dữ liệu DEB (Sileo Engine)
    print("⚙️ Đang nạp phân hệ Sileo Engine...", flush=True)
    processed_tweaks = sileo_engine.run_sileo_engine(raw_assets.get("deb", []), sileo_db)
    if processed_tweaks:
        print(f"📦 Hoàn tất xử lý Tweaks: {', '.join(processed_tweaks)}", flush=True)
    else:
        print("📦 Không phát hiện Tweak mới cần xử lý bổ sung.", flush=True)
    time.sleep(0.5)
    
    # 4. Ghi dữ liệu đồng bộ database và tạo tên commit
    save_databases(feather_db, sileo_db)
    stats = calculate_repo_statistics()
    save_commit_message(stats[0], stats[2])
    
    # 5. Biên dịch thông báo tích hợp trí tuệ nhân tạo Gemini và đẩy lên Telegram Channel
    print("🤖 Đang kết nối trí tuệ nhân tạo Gemini dịch thuật và tóm tắt thay đổi...", flush=True)
    msg_summary = gemini.generate_update_summary(processed_apps, processed_tweaks)
    
    token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id, 
            "text": msg_summary, 
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "reply_markup": {
                "inline_keyboard": [[{"text": "🌐 Thêm Nguồn Kyic Store", "url": "https://2kgt.github.io/"}]]
            }
        }
        try:
            res = requests.post(url, json=payload, timeout=15)
            res.raise_for_status()
            print("🚀 [Telegram] Gửi tin nhắn thông báo cập nhật thành công.", flush=True)
        except Exception as e:
            print(f"❌ Lỗi gửi báo cáo Telegram: {e}", flush=True)
    else:
        print("⚠️ Bỏ qua gửi Telegram: Thiếu cấu hình TELEGRAM_TOKEN hoặc TELEGRAM_CHAT_ID.", flush=True)

    print("🏁 [SUCCESS] Toàn bộ quy trình đồng bộ kho ứng dụng đã hoàn thành!", flush=True)


if __name__ == "__main__":
    main()
