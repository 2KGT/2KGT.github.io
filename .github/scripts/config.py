# .github/scripts/config.py
import os
import logging  # Đã thêm: Khai báo thư viện log tiêu chuẩn của Python
import logger   # Giữ nguyên: Module logger cục bộ (Telegram/Custom log) của anh

CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if "scripts" in CURRENT_SCRIPT_DIR.lower():
    REPO_ROOT = os.path.dirname(os.path.dirname(CURRENT_SCRIPT_DIR)) if ".github" in CURRENT_SCRIPT_DIR.lower() else os.path.dirname(CURRENT_SCRIPT_DIR)
else:
    REPO_ROOT = CURRENT_SCRIPT_DIR

# --- Đường dẫn và URL ---
BASE_URL = "https://2kgt.github.io/repo/"
RAW_URL = "https://raw.githubusercontent.com/2KGT/repo/main/"
REPO_NAME = "Kyic Premium Store"
SOURCE_IDENTIFIER = "com.kyic.premium"

ICON_DIR_NAME = "repo/depictions/icons"
IMG_DIR_NAME = "repo/depictions/images"
DEPICTION_DIR_NAME = "repo/depictions/metadata"

ICON_DIR = os.path.join(REPO_ROOT, ICON_DIR_NAME)
IMG_DIR = os.path.join(REPO_ROOT, IMG_DIR_NAME)
DEPICTION_DIR = os.path.join(REPO_ROOT, DEPICTION_DIR_NAME)

FEATHER_DATABASE = os.path.join(DEPICTION_DIR, "wikiipa.json")
APPS_INPUT_DIR = os.path.join(REPO_ROOT, "repo/apps")
DEBS_INPUT_DIR = os.path.join(REPO_ROOT, "repo/debs")
REPO_OUTPUT_DIR = os.path.join(REPO_ROOT, "repo")

# --- Tài nguyên mặc định ---
SOURCE_LOGO = f"{RAW_URL}{ICON_DIR_NAME}/Kyic.png"
DEFAULT_BANNER = f"{RAW_URL}{IMG_DIR_NAME}/Kyic_banner.png"
DEFAULT_VIDEO = f"{RAW_URL}{IMG_DIR_NAME}/Kyic.mp4"
NEWS_DONATE_IMAGE = f"{RAW_URL}{IMG_DIR_NAME}/donate.png"
NEWS_ABOUT_IMAGE = f"{RAW_URL}{IMG_DIR_NAME}/about.png"

# --- Quyền hệ thống iOS ---
PERM_MAPPING = {
    "NSCameraUsageDescription": "Máy ảnh", 
    "NSMicrophoneUsageDescription": "Micro",
    "NSPhotoLibraryUsageDescription": "Thư viện ảnh", 
    "NSPhotoLibraryAddUsageDescription": "Ghi vào Thư viện ảnh",
    "NSLocationWhenInUseUsageDescription": "Vị trí khi dùng ứng dụng", 
    "NSLocationAlwaysAndWhenInUseUsageDescription": "Vị trí mọi lúc",
    "NSLocationAlwaysUsageDescription": "Vị trí chạy ngầm", 
    "NSContactsUsageDescription": "Danh bạ",
    "NSCalendarsUsageDescription": "Lịch", 
    "NSRemindersUsageDescription": "Nhắc nhở",
    "NSBluetoothAlwaysUsageDescription": "Kết nối Bluetooth", 
    "NSBluetoothPeripheralUsageDescription": "Thiết bị ngoại vi Bluetooth",
    "NSFaceIDUsageDescription": "Face ID / Touch ID", 
    "NSUserTrackingUsageDescription": "Theo dõi quảng cáo",
    "NSLocalNetworkUsageDescription": "Mạng cục bộ"
}

# --- Cấu hình logger hệ thống Python ---
logging.basicConfig(level=logging.INFO)
# Đổi tên thành sys_logger để tránh xung đột với module logger cục bộ ở dòng số 3
sys_logger = logging.getLogger(__name__)

# --- Tạo thư mục tự động và in Log (Đã gộp tối ưu) ---
for d in [APPS_INPUT_DIR, DEBS_INPUT_DIR, DEPICTION_DIR, ICON_DIR, IMG_DIR, REPO_OUTPUT_DIR]: 
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)
        sys_logger.info(f"Đã tạo thư mục thành công: {d}")
