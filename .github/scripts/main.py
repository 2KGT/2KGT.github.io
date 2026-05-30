# .github/scripts/main.py
import os
import sys
import json
import re
import requests

# Khắc phục đường dẫn để nhận diện thư mục scripts/ làm gốc
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import config
import gemini
import fetch_github
import logger  # Bộ log Telegram

# Gọi chung các module từ gói core/ cùng cấp
from core import feather_engine
from core import sileo_engine

# ==========================================
# KHÂU 1: NẠP CƠ SỞ DỮ LIỆU ĐỆM (CACHE DB)
# ==========================================
def load_system_database():
    """Tự động nạp cơ sở dữ liệu wikiipa.json"""
    db_path = config.FEATHER_DATABASE
    if os.path.exists(db_path):
        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "apps" not in data: data["apps"] = {}
                if "tweaks" not in data: data["tweaks"] = {}
                return data
        except Exception as e:
            logger.warn(f"Không thể đọc file database cũ, khởi tạo mới. Lỗi: {e}")
    return {"apps": {}, "tweaks": {}}

# ==========================================
# KHÂU 4: BỘ TÍNH TOÁN THỐNG KÊ & TỔNG HỢP DỮ LIỆU
# ==========================================
def calculate_repo_statistics():
    """Đo đạc và tính toán dung lượng thực tế từ các file thành phẩm json/Packages"""
    logger.info("📊 Khâu 4: Đang tiến hành bộ tính toán thống kê khối lượng...")
    
    # Thống kê Apps từ file apps.json thành phẩm
    apps_json_path = os.path.join(config.REPO_OUTPUT_DIR, 'apps.json')
    try:
        with open(apps_json_path, 'r', encoding='utf-8') as f:
            apps_data = json.load(f)
            total_apps = len(apps_data.get("apps", []))
            apps_size_bytes = sum(int(app.get("size", 0)) for app in apps_data.get("apps", []))
            total_apps_size = f"{apps_size_bytes / (1024 * 1024):.2f} MB" if apps_size_bytes > 0 else "0 MB"
    except Exception as e:
        logger.warn(f"Chưa có apps.json: {e}")
        total_apps, total_apps_size = 0, "0 MB"

    # Thống kê Tweaks từ file Packages thành phẩm
    try:
        with open(os.path.join(config.REPO_OUTPUT_DIR, "Packages"), "r", encoding="utf-8") as f:
            content = f.read()
            total_tweaks = content.count("Package:")
            sizes = re.findall(r'^Size:\s*(\d+)', content, re.MULTILINE)
            tweaks_size_bytes = sum(int(s) for s in sizes)
            total_tweaks_size = f"{tweaks_size_bytes / (1024 * 1024):.2f} MB" if tweaks_size_bytes > 0 else "0 MB"
    except Exception as e:
        total_tweaks, total_tweaks_size = 0, "0 MB"

    return total_apps, total_apps_size, total_tweaks, total_tweaks_size


# ==========================================
# ĐẦU NÃO ĐIỀU PHỐI CHÍNH (PIPELINE)
# ==========================================
def main():
    logger.success("🚀 Khởi động Pipeline tự động hóa tích hợp core/...")
    
    # Bước 1: Khởi tạo dữ liệu nền và lưu trạng thái cũ để so sánh
    system_db = load_system_database()
    old_apps = set(system_db.get("apps", {}).keys())
    old_tweaks = set(system_db.get("tweaks", {}).keys())
    
    # Bước 2: Def cào tất cả dữ liệu thô từ Cloud
    logger.info("📡 Khâu 2: Thu thập toàn bộ tài nguyên từ GitHub Releases Cloud...")
    raw_assets = fetch_github.get_release_assets()
    
    # Bước 3: Phân loại dữ liệu và chạy xử lý cho từng đối tượng tương ứng
    logger.info("⚙️ Khâu 3: Phân loại dữ liệu và kích hoạt các lõi Engine...")
    
    # 3.1 Chuyển dữ liệu IPA sang cho Feather xử lý tạo cấu trúc phẳng
    try:
        feather_engine.run_feather_engine(raw_assets.get("ipa", []), system_db)
    except Exception as e:
        logger.error(f"Lỗi tại Feather Engine: {e}")
        
    # 3.2 Chuyển dữ liệu DEB sang cho Sileo xử lý tạo Packages/Depictions
    try:
        sileo_engine.run_sileo_engine(raw_assets.get("deb", []), system_db)
    except Exception as e:
        logger.error(f"Lỗi tại Sileo Engine: {e}")

    # Bước 4 & 5: Đưa qua bộ tính toán thống kê và cập nhật bộ đệm JSON cục bộ
    total_apps, total_apps_size, total_tweaks, total_tweaks_size = calculate_repo_statistics()
    
    try:
        with open(config.FEATHER_DATABASE, 'w', encoding='utf-8') as f: 
            json.dump(system_db, f, indent=2, ensure_ascii=False)
        logger.success("💾 Khâu 5: Đã cập nhật và lưu bộ đệm hệ thống (wikiipa.json)!")
    except Exception as e:
        logger.error(f"Không thể ghi file database cache: {e}")
        
    # Bước 6: Khâu sau cùng - Chuyển tiếp dữ liệu tổng hợp cho AI Gemini biên soạn bản tin
    logger.ai("🤖 Khâu 6: Chuyển giao dữ liệu tổng hợp cho AI Gemini...")
    noi_dung_gui = gemini.process_and_dispatch_env(
        system_db, old_apps, old_tweaks,
        total_apps, total_apps_size, total_tweaks, total_tweaks_size
    )
    
    # Kết thúc tiến trình, gửi thông báo chốt hạ tới nhóm hỗ trợ Telegram
    print("[SUCCESS] 🏁 Pipeline hoàn thành chu trình xuất sắc!")
    logger.maintenance_heartbeat()
    logger.clear_live_logs()

    # Bắn thông báo cuối cùng lên Telegram kèm nút bấm
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_CHANNEL")
    URL_NGUON = "https://2kgt.github.io/" 

    if TOKEN and CHAT_ID and noi_dung_gui:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            payload = {
                "chat_id": CHAT_ID,
                "text": noi_dung_gui,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "reply_markup": {
                    "inline_keyboard": [[{"text": "🌐 Thêm Nguồn Kyic", "url": URL_NGUON}]]
                }
            }
            requests.post(url, json=payload, timeout=15)
        except Exception as e:
            print(f"⚠️ Thất bại khi gửi bảng thông báo chốt hạ: {e}")

if __name__ == "__main__":
    main()
