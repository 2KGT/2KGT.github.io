# .github/scripts/main.py
import os
import sys
import time
import json
import re
import datetime
import logging
import urllib.request
import urllib.error

# Khắc phục đường dẫn gốc trước khi nạp các module nội bộ
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import config
import gemini
import github
from core import feather_engine, sileo_engine, dylib_engine

# FIX: Cấu hình logging tập trung thay vì print trần khắp nơi
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


def load_databases():
    """Nạp dữ liệu bộ nhớ đệm wikiipa.json, wikideb.json và wikidylib.json"""
    def read_db(path):
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ Lỗi đọc database {path}: {e}")
        return {}

    return (
        read_db(config.FEATHER_DATABASE), 
        read_db(config.SILEO_DATABASE), 
        read_db(config.DYLIBS_DATABASE)
    )

def save_databases(feather_db, sileo_db, dylib_db):
    """Ghi dữ liệu cấu trúc vào 3 tệp DB"""
    def safe_write(path, data):
        tmp_path = f"{path}.tmp"
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, path)
        except Exception as e:
            logger.error(f"❌ Lỗi ghi database {path}: {e}")

    safe_write(config.FEATHER_DATABASE, feather_db)
    safe_write(config.SILEO_DATABASE, sileo_db)
    safe_write(config.DYLIBS_DATABASE, dylib_db)

def calculate_repo_statistics(raw_assets):
    """Tính toán số lượng và tổng dung lượng tất cả tệp tin từ apps.json và Packages"""
    total_apps = 0
    apps_bytes = 0
    total_tweaks = 0
    tweaks_bytes = 0

    # 1. Thống kê Apps từ apps.json
    apps_json_path = os.path.join(config.REPO_OUTPUT_DIR, 'apps.json')
    if os.path.exists(apps_json_path):
        try:
            with open(apps_json_path, 'r', encoding='utf-8') as f:
                apps_data = json.load(f).get("apps", [])
                total_apps = len(apps_data)
                for app in apps_data:
                    ipa_files = app.get("versions", []) or app.get("files", [])
                    if isinstance(ipa_files, list) and ipa_files:
                        for ipa in ipa_files:
                            apps_bytes += int(ipa.get("size", 0))
                    else:
                        apps_bytes += int(app.get("size", 0))
        except Exception as e:
            logger.warning(f"⚠️ Lỗi phân tích cú pháp apps.json: {e}")

    # 2. Thống kê Tweaks từ Packages
    packages_path = os.path.join(config.REPO_OUTPUT_DIR, "Packages")
    if os.path.exists(packages_path):
        try:
            with open(packages_path, "r", encoding="utf-8") as f:
                content = f.read()
                total_tweaks = content.count("Package:")
                sizes = re.findall(r'^Size:\s*(\d+)', content, re.MULTILINE)
                for size_str in sizes:
                    tweaks_bytes += int(size_str)
        except Exception as e:
            logger.warning(f"⚠️ Lỗi phân tích cú pháp tệp Packages: {e}")

    def format_size(bytes_size):
        if bytes_size == 0:
            return "0 MB"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} GB"

    return total_apps, format_size(apps_bytes), total_tweaks, format_size(tweaks_bytes)


def save_commit_message(total_apps, total_tweaks):
    """Lưu thông điệp commit ra ngoài thư mục gốc để tránh trigger workflow lặp vô tận"""
    msg = (
        f"🚀 Auto Sync: {total_apps} apps, {total_tweaks} tweaks "
        f"| {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    commit_file_path = os.path.join(config.REPO_ROOT, '.commit_msg')
    try:
        with open(commit_file_path, 'w', encoding='utf-8') as f:
            f.write(msg)
        logger.info(f"📝 Đã tạo file commit_msg: {msg}")
    except Exception as e:
        logger.warning(f"⚠️ Không thể lưu file commit_msg: {e}")


def send_telegram(token, chat_id, text):
    """
    FIX: Thay thư viện requests bằng urllib thuần — loại bỏ dependency ngoài không cần thiết.
    requests không có trong stdlib, nếu môi trường GitHub Actions thiếu sẽ crash toàn bộ script.
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": {
            "inline_keyboard": [[
                {"text": "🌐 Thêm Nguồn Kyic Store", "url": "https://2kgt.github.io/"}
            ]]
        }
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode())
            if not result.get("ok"):
                logger.error(f"❌ Telegram API trả về lỗi: {result}")
                return False
        logger.info("🚀 [Telegram] Gửi tin nhắn thông báo cập nhật thành công.")
        return True

    # FIX: Phân biệt lỗi HTTP (sai token, chat_id...) với lỗi mạng
    except urllib.error.HTTPError as e:
        logger.error(f"❌ Lỗi HTTP Telegram {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        logger.error(f"❌ Lỗi kết nối Telegram: {e.reason}")
    except Exception as e:
        logger.error(f"❌ Lỗi gửi báo cáo Telegram: {e}")
    return False


def main():
    """🌟 PHÂN HỆ ĐIỀU PHỐI CHÍNH (Core Automation Engine)"""
    logger.info("🎬 Khởi chạy hệ thống tự động hóa Kyic Premium Store...")

    # 1. Nạp database và quét GitHub Releases
    feather_db, sileo_db, dylib_db = load_databases()
    feather_db.setdefault("apps", {})
    sileo_db.setdefault("tweaks", {})
    dylib_db.setdefault("dylibs", {})
    raw_assets = raw_assets = github.get_release_assets()
    total_ipa = len(raw_assets.get("ipa", []))
    total_deb = len(raw_assets.get("deb", []))
    total_dylib = len(raw_assets.get("dylib", []))
    logger.info(f"📊 Hệ thống quét đám mây: Tìm thấy {total_ipa} tệp IPA và {total_deb} tệp DEB và {total_dylib} tệp DYLIB.")
    time.sleep(0.5)

    # 2. Feather Engine — xử lý IPA
    logger.info("📂 Đang nạp phân hệ Feather Engine...")
    processed_apps = feather_engine.run_feather_engine(raw_assets.get("ipa", []), feather_db)
    if processed_apps:
        logger.info(f"📱 Hoàn tất xử lý Apps: {', '.join(processed_apps)}")
    else:
        logger.info("📱 Không phát hiện App mới cần xử lý bổ sung.")
    time.sleep(0.5)

    # 3. Sileo Engine — xử lý DEB
    logger.info("⚙️ Đang nạp phân hệ Sileo Engine...")
    processed_tweaks = sileo_engine.run_sileo_engine(raw_assets.get("deb", []), sileo_db)
    
    if processed_tweaks:
        logger.info(f"📦 Hoàn tất xử lý Tweaks: {', '.join(processed_tweaks)}")
    else:
        logger.info("📦 Không phát hiện Tweak mới cần xử lý bổ sung.")

    # 4. Dylib Engine — xử lý dylib
    logger.info("📚 Đang nạp phân hệ Dylib Engine...")
    dylib_engine.run_dylib_engine(raw_assets.get("dylib", []), sileo_db)
    logger.info("📚 Hoàn tất xử lý Dylibs.")
    
    time.sleep(0.5)

    # 5. Lưu database và tạo commit message
    save_databases(feather_db, sileo_db, dylib_db)
    stats = calculate_repo_statistics(raw_assets)
    save_commit_message(stats[0], stats[2])

    # 6. Tóm tắt bằng Gemini và gửi Telegram
    logger.info("🤖 Đang kết nối Gemini để tóm tắt thay đổi...")
    msg_summary = gemini.generate_update_summary(
        processed_apps=processed_apps,
        processed_tweaks=processed_tweaks,
        stats_data=stats
    )

    token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if token and chat_id:
        send_telegram(token, chat_id, msg_summary)
    else:
        logger.warning("⚠️ Bỏ qua gửi Telegram: Thiếu TELEGRAM_TOKEN hoặc TELEGRAM_CHAT_ID.")

    logger.info("🏁 [SUCCESS] Toàn bộ quy trình đồng bộ kho ứng dụng đã hoàn thành!")


if __name__ == "__main__":
    main()

