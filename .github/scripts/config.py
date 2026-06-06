# .github/scripts/config.py
import os
import sys

CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if "scripts" in CURRENT_SCRIPT_DIR.lower():
    REPO_ROOT = os.path.dirname(os.path.dirname(CURRENT_SCRIPT_DIR)) if ".github" in CURRENT_SCRIPT_DIR.lower() else os.path.dirname(CURRENT_SCRIPT_DIR)
else:
    REPO_ROOT = CURRENT_SCRIPT_DIR

# --- Đường dẫn và URL ---
# 🌟 Đã sửa chuẩn xác tên Repo GitHub thành 2KGT.github.io để sửa triệt để lỗi ảnh 404
BASE_URL = "https://2kgt.github.io/repo/"
RAW_URL = "https://raw.githubusercontent.com/2KGT/2KGT.github.io/main/"
REPO_NAME = "Kyic Premium Store"
SOURCE_IDENTIFIER = "com.kyic.premium"

ICON_DIR_NAME = "repo/depictions/icons"
IMG_DIR_NAME = "repo/depictions/images"
DEPICTION_DIR_NAME = "repo/depictions/metadata"
DEFAULT_DIR_NAME = "repo/depictions/default"

ICON_DIR = os.path.join(REPO_ROOT, ICON_DIR_NAME)
IMG_DIR = os.path.join(REPO_ROOT, IMG_DIR_NAME)
DEPICTION_DIR = os.path.join(REPO_ROOT, DEPICTION_DIR_NAME)
DEFAULT_DIR = os.path.join(REPO_ROOT, DEFAULT_DIR_NAME)

# --- Bộ não dữ liệu (Database) ---
FEATHER_DATABASE = os.path.join(DEPICTION_DIR, "wikiipa.json")
SILEO_DATABASE = os.path.join(DEPICTION_DIR, "wikideb.json")

APPS_INPUT_DIR = os.path.join(REPO_ROOT, "repo/apps")
DEBS_INPUT_DIR = os.path.join(REPO_ROOT, "repo/debs")
REPO_OUTPUT_DIR = os.path.join(REPO_ROOT, "repo")

# --- Tài nguyên mặc định ---
SOURCE_LOGO = f"{RAW_URL}{DEFAULT_DIR_NAME}/Kyic.png"
DEFAULT_BANNER = f"{RAW_URL}{DEFAULT_DIR_NAME}/Kyic_banner.png"
DEFAULT_VIDEO = f"{RAW_URL}{DEFAULT_DIR_NAME}/Kyic_video.mp4"
NEWS_DONATE_IMAGE = f"{RAW_URL}{DEFAULT_DIR_NAME}/donate.png"
NEWS_ABOUT_IMAGE = f"{RAW_URL}{DEFAULT_DIR_NAME}/about.png"

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
sys_logger = logging.getLogger(__name__)

# --- Hàm thông minh tự động quét hoặc sinh chuỗi ảnh chụp màn hình mặc định ---
def get_default_screenshots():
    """
    Tự động quét thư mục repo/depictions/default để lấy danh sách ảnh từ Kyic_1 đến Kyic_8.
    Nếu chạy trên Actions mà thư mục trống, hàm sẽ tự động sinh danh sách link chuẩn.
    """
    screens = []
    exts = ['.png', '.jpg', '.jpeg', '.webp']
    
    # Nếu tồn tại thư mục default cục bộ, tiến hành quét file thực tế
    if os.path.exists(DEFAULT_DIR):
        try:
            all_files = sorted(os.listdir(DEFAULT_DIR))
            for f in all_files:
                if f.lower().startswith("kyic_") and any(f.lower().endswith(ext) for ext in exts):
                    if not any(x in f.lower() for x in ["banner", "logo", "video"]):
                        screens.append(f"{RAW_URL.rstrip('/')}/{DEFAULT_DIR_NAME.strip('/')}/{f}")
        except Exception as e:
            sys_logger.error(f"⚠️ Lỗi quét thư mục default: {e}")

    # Cơ chế fallback dự phòng: Tự động gán cứng chuẩn xác 8 link ảnh nếu quét cục bộ bị trống
    if not screens:
        for i in range(1, 9):
            screens.append(f"{RAW_URL.rstrip('/')}/{DEFAULT_DIR_NAME.strip('/')}/Kyic_{i}.jpeg")
            
    return screens

# --- Tạo thư mục tự động ---
for d in [APPS_INPUT_DIR, DEBS_INPUT_DIR, DEPICTION_DIR, ICON_DIR, IMG_DIR, DEFAULT_DIR, REPO_OUTPUT_DIR]: 
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)
        sys_logger.info(f"Đã tạo thư mục thành công: {d}")
