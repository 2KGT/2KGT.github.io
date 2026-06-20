# .github/scripts/config.py
import os
import sys
import re
import logging
import inspect
import datetime

# Logger chuẩn
sys_logger = logging.getLogger(__name__)

# --- Cấu hình đường dẫn ---
CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if "scripts" in CURRENT_SCRIPT_DIR.lower():
    REPO_ROOT = os.path.dirname(os.path.dirname(CURRENT_SCRIPT_DIR)) if ".github" in CURRENT_SCRIPT_DIR.lower() else os.path.dirname(CURRENT_SCRIPT_DIR)
else:
    REPO_ROOT = CURRENT_SCRIPT_DIR

# --- HÀM GHI FILE AN TOÀN (Cốt lõi của hệ thống Audit) ---
def safe_write_file(filepath, content, mode='w'):
    """
    Ghi dữ liệu vào file và tự động ghi log audit để theo dõi thủ phạm thay đổi.
    """
    # Đảm bảo thư mục cha tồn tại
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # Ghi nội dung vào file
    with open(filepath, mode, encoding='utf-8') as f:
        f.write(content)
    
    # Ghi log audit
    try:
        # Lấy thông tin file nào gọi hàm này
        caller = inspect.stack()[1]
        origin = f"{os.path.basename(caller.filename)}:{caller.lineno}"
        log_path = os.path.join(REPO_ROOT, "repo/audit.log")
        timestamp = datetime.datetime.now().strftime("%H:%M %d/%m/%Y")
        
        with open(log_path, "a", encoding='utf-8') as f:
            f.write(f"{timestamp}|{os.path.basename(filepath)}|WRITE|{origin}\n")
    except Exception as e:
        sys_logger.error(f"⚠️ Lỗi ghi audit log: {e}")

# --- Đường dẫn và URL ---
BASE_URL = "https://2kgt.github.io/repo/"
RAW_URL = "https://raw.githubusercontent.com/2KGT/2KGT.github.io/main/"
REPO_NAME = "Kyic Premium Store"
SOURCE_IDENTIFIER = "com.kyic.premium"
# tintColor config 
TINT_COLOR = "848ef9"

ICON_DIR_NAME = "repo/data/icons"
IMG_DIR_NAME = "repo/data/images"
DEPICTION_DIR_NAME = "repo/data"
DEFAULT_DIR_NAME = "repo/data/default"

ICON_DIR = os.path.join(REPO_ROOT, ICON_DIR_NAME)
IMG_DIR = os.path.join(REPO_ROOT, IMG_DIR_NAME)
DEPICTION_DIR = os.path.join(REPO_ROOT, DEPICTION_DIR_NAME)
DEFAULT_DIR = os.path.join(REPO_ROOT, DEFAULT_DIR_NAME)

# Cấu trúc thư mục: main(root)/repo/
APPS_INPUT_DIR = os.path.join(REPO_ROOT, "repo/apps")
DEBS_INPUT_DIR = os.path.join(REPO_ROOT, "repo/debs")
DYLIBS_INPUT_DIR = os.path.join(REPO_ROOT, "repo/dylibs")
REPO_OUTPUT_DIR = os.path.join(REPO_ROOT, "repo")

# --- Vùng lưu trữ "trí nhớ đầu vào" (Wiki Data) ---
# Cấu trúc: Gom wiki file database wiki/
# main(root)/repo/data/wiki/
WIKI_DIR = os.path.join(DEPICTION_DIR, "wiki")
FEATHER_DATABASE = os.path.join(WIKI_DIR, "wikiapps.json")
SILEO_DATABASE = os.path.join(WIKI_DIR, "wikidebs.json")
DYLIBS_DATABASE = os.path.join(WIKI_DIR, "wikidylibs.json")

# --- Vùng xắp xếp lưu trữ từ wiki thành "Sản phẩm cuối"
# Nơi các app Sileo/Feather đọc vào
APPS_JSON_PATH = os.path.join(REPO_ROOT, "repo/apps.json")
SILEO_JSON_PATH = os.path.join(REPO_ROOT, "repo/sileo.json")
DYLIBS_JSON_PATH = os.path.join(REPO_ROOT, "repo/dylibs.json")

# FIX: Chuyển desc vào gom cùng cụm data/ cho nhất quán
# Cấu trúc: main(root)/repo/data/desc/apps/<AppName>/v1.0.txt
# Cấu trúc: main(root)/repo/data/desc/tweaks/<TweakName>/v1.0.txt
DESC_DIR = os.path.join(DEPICTION_DIR, "desc", "apps")
TWEAK_DESC_DIR = os.path.join(DEPICTION_DIR, "desc", "tweaks")

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

def get_app_dir_by_name(app_name):
    """
    Lấy đường dẫn app theo app name.
    
    Cấu trúc: repo/apps/<app_name>/
    Ví dụ: repo/apps/Telegram/
    """
    return os.path.join(APPS_INPUT_DIR, app_name)


def get_tweak_dir_by_name(tweak_name):
    """
    FIX: Lấy đường dẫn tweak theo tweak name.
    
    Cấu trúc: repo/debs/<tweak_name>/
    Ví dụ: repo/debs/cc18/
    Gom tất cả phiên bản + architecture vào 1 folder
    """
    return os.path.join(DEBS_INPUT_DIR, tweak_name)


def get_depiction_dir_by_section(section):
    """Lấy thư mục depiction theo section: tweaks, themes, addons..."""
    section_map = {
        "Tweaks": "tweaks",
        "Themes": "themes",
        "Addons": "addons",
        "System": "system",
        "Tools": "tools"
    }
    subdir = section_map.get(section, "tweaks").lower()
    return os.path.join(DEPICTION_DIR, subdir)


def get_depiction_path_by_filename(section, tweak_name, safe_filename):
    """
    FIX: Lấy đường dẫn depiction lồng theo section/tweak_name, dùng
    safe_filename (tweak_ver_arch) làm tên file JSON — KHÔNG dùng chung
    1 file cho mọi version/arch để tránh xung đột đè dữ liệu.

    Cấu trúc: repo/data/<section>/<tweak_name>/<tweak_ver_arch>.json
    Ví dụ:
      repo/data/tweaks/glow/glow_1.3.1_iphoneos-arm.json
      repo/data/tweaks/glow/glow_1.3.1_iphoneos-arm64.json
      repo/data/tweaks/glow/glow_1.3.1_iphoneos-arm64e.json
      repo/data/tweaks/glow/glow_1.3.0_iphoneos-arm.json  (version cũ vẫn giữ riêng)

    ⭐ Lý do tách theo version+arch (không gộp theo bundle_id):
    - Mỗi .deb (arm/arm64/arm64e) build JSON độc lập, không ghi đè lẫn nhau
    - Khi có nhiều version cùng tồn tại trong repo/debs/<TweakName>/,
      mỗi version giữ JSON riêng — không version nào đè mất version khác
    - Packages mỗi entry (mỗi arch) trỏ SileoDepiction tới đúng file JSON
      của riêng nó — an toàn tuyệt đối, không xung đột

    Return: (target_folder, json_filename)
    """
    section_map = {
        "Tweaks": "tweaks",
        "Themes": "themes",
        "Addons": "addons",
        "System": "system",
        "Tools": "tools"
    }
    subdir = section_map.get(section, "tweaks").lower()
    tweak_dir = os.path.join(DEPICTION_DIR, subdir, tweak_name)
    json_filename = f"{safe_filename}.json"
    return tweak_dir, json_filename


def get_default_screenshots():
    """
    Tự động quét thư mục repo/data/default để lấy danh sách ảnh từ Kyic_1 đến Kyic_8.
    Nếu chạy trên Actions mà thư mục trống, hàm sẽ tự động sinh danh sách link chuẩn.
    """
    screens = []
    exts = ['.png', '.jpg', '.jpeg', '.webp']

    if os.path.exists(DEFAULT_DIR):
        try:
            all_files = sorted(os.listdir(DEFAULT_DIR))
            for f in all_files:
                if f.lower().startswith("kyic_") and any(f.lower().endswith(ext) for ext in exts):
                    if not any(x in f.lower() for x in ["banner", "logo", "video"]):
                        screens.append(f"{RAW_URL.rstrip('/')}/{DEFAULT_DIR_NAME.strip('/')}/{f}")
        except Exception as e:
            sys_logger.error(f"⚠️ Lỗi quét thư mục default: {e}")

    # Fallback: sinh cứng 8 link nếu quét cục bộ trống
    if not screens:
        for i in range(1, 9):
            screens.append(f"{RAW_URL.rstrip('/')}/{DEFAULT_DIR_NAME.strip('/')}/Kyic_{i}.jpeg")

    return screens


def get_optimized_tweak_description(tweak_name, version):
    """
    FIX: Logic thông minh lấy mô tả tweak theo phiên bản (giống IPA).
    
    Thứ tự ưu tiên:
    1. File v<version>.txt (ví dụ: v0.0.3.txt)
    2. File default.txt (mô tả mặc định)
    3. Chuỗi mặc định từ control data
    
    Cấu trúc: repo/data/desc/tweaks/<TweakName>/v<version>.txt
    Ví dụ: repo/data/desc/tweaks/cc18/v0.0.3.txt
    """
    tweak_desc_dir = os.path.join(TWEAK_DESC_DIR, tweak_name)
    os.makedirs(tweak_desc_dir, exist_ok=True)
    version_file = os.path.join(tweak_desc_dir, f"v{version}.txt")
    default_file = os.path.join(tweak_desc_dir, "default.txt")

    if os.path.exists(version_file):
        try:
            with open(version_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception:
            pass

    if os.path.exists(default_file):
        try:
            with open(default_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception:
            pass

    return f"Cập nhật phiên bản Tweak v{version} từ Kyic Store."


def get_tweak_changelog_history(tweak_name, current_version, limit=10):
    """
    FIX: Lấy lịch sử changelog NHIỀU phiên bản cho tweak — mô phỏng đúng
    tinh thần "Version History" mà Feather (IPA) đang có qua mảng `versions[]`.

    Vì Sileo/APT KHÔNG hỗ trợ mảng version trong Packages (mỗi Package +
    Architecture chỉ được liệt kê 1 lần theo chuẩn), lịch sử nhiều phiên bản
    được gộp thành 1 khối markdown hiển thị trong tab "Changelog" của
    depiction JSON — người dùng vẫn thấy đầy đủ "có gì mới" qua từng version.

    Đọc tất cả file v<version>.txt đã từng được tạo trong:
    repo/data/desc/tweaks/<TweakName>/
    Sort giảm dần theo version số (mới nhất trước), giới hạn `limit` bản
    gần nhất để tránh markdown quá dài.

    Return: chuỗi markdown, ví dụ:
        ### v1.3.1 (hiện tại)
        - Fix crash khi mở Control Center

        ### v1.3.0
        - Thêm hiệu ứng glow mới
    """
    tweak_desc_dir = os.path.join(TWEAK_DESC_DIR, tweak_name)
    if not os.path.exists(tweak_desc_dir):
        return f"### v{current_version}\nCập nhật phiên bản v{current_version} từ Kyic Store."

    version_entries = []
    try:
        for fname in os.listdir(tweak_desc_dir):
            match = re.match(r'^v(.+)\.txt$', fname)
            if not match:
                continue
            ver = match.group(1)
            fpath = os.path.join(tweak_desc_dir, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                if content:
                    version_entries.append((ver, content))
            except Exception:
                continue
    except Exception as e:
        sys_logger.error(f"⚠️ Lỗi quét changelog history cho {tweak_name}: {e}")

    if not version_entries:
        return f"### v{current_version}\nCập nhật phiên bản v{current_version} từ Kyic Store."

    def _ver_tuple(v):
        try:
            return tuple(int(x) for x in str(v).split('.'))
        except Exception:
            return (0,)

    # Sort giảm dần theo version số (mới nhất trước)
    version_entries.sort(key=lambda x: _ver_tuple(x[0]), reverse=True)
    version_entries = version_entries[:limit]

    blocks = []
    for ver, content in version_entries:
        label = f"### v{ver} (hiện tại)" if ver == str(current_version) else f"### v{ver}"
        blocks.append(f"{label}\n{content}")

    return "\n\n".join(blocks)


def get_app_images_dir(app_name):
    """
    FIX: Lấy thư mục images theo app name (giống tweak, nhất quán).
    
    Cấu trúc: repo/data/images/<app_name>/
    Ví dụ: repo/data/images/Telegram/
    - Telegram_banner.png
    - Telegram_1.png
    - Telegram_2.png
    """
    return os.path.join(IMG_DIR, app_name)


def get_tweak_images_dir(tweak_name):
    """
    FIX: Lấy thư mục images theo tweak name.
    
    Cấu trúc: repo/data/images/<tweak_name>/
    Ví dụ: repo/data/images/cc18/
    - cc18_banner.png
    - cc18_1.png
    - cc18_2.png
    """
    return os.path.join(IMG_DIR, tweak_name)


# --- Tạo thư mục tự động ---
for d in [APPS_INPUT_DIR, DEBS_INPUT_DIR, DYLIBS_INPUT_DIR, DESC_DIR, TWEAK_DESC_DIR, DEPICTION_DIR, WIKI_DIR, ICON_DIR, IMG_DIR, DEFAULT_DIR, REPO_OUTPUT_DIR]:
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)
        sys_logger.info(f"Đã tạo thư mục thành công: {d}")

