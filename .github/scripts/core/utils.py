# .github/scripts/core/utils.py
import re
import os
import sys
import urllib.request
import logging
import datetime
import inspect
import config

# Logger chuẩn thay vì print trần
logger = logging.getLogger(__name__)

# Khắc phục đường dẫn hệ thống để nạp cấu hình chính xác
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

def clean_text(text):
    """Làm sạch khoảng trắng thừa trong chuỗi văn bản"""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', str(text)).strip()


def parse_version_tuple(ver_str):
    """Chuyển chuỗi version thành tuple số để sort chính xác: '10.2.1' → (10, 2, 1)"""
    try:
        return tuple(int(x) for x in str(ver_str).split('.'))
    except Exception:
        return (0,)


def smart_truncate_description(text, max_chars=None):
    """
    Xử lý mô tả ứng dụng thông minh.
    Giữ nguyên nội dung nếu đã có chi tiết, chỉ áp dụng mặc định khi dữ liệu rỗng.

    FIX: Tách rõ 3 nhánh logic thay vì lồng nhau gây mâu thuẫn:
      1. Rỗng / quá ngắn (< 10 ký tự)  → trả về chuỗi mặc định
      2. Chứa chuỗi rác cũ             → trả về chuỗi mặc định
      3. Còn lại                        → trả về nội dung đã làm sạch
    """
    DEFAULT = "Ứng dụng Premium phiên bản ổn định, mượt mà, mở khóa đầy đủ tính năng cao cấp từ Kyic Store."

    if not text:
        return DEFAULT

    clean = re.sub(r'[\r\n\t]+', ' ', str(text))
    clean = re.sub(r'\s+', ' ', clean).strip()

    # Nhánh 1: Quá ngắn để có ý nghĩa
    if len(clean) < 10:
        return DEFAULT

    # Nhánh 2: Chứa chuỗi rác/tự động cũ
    STALE_MARKERS = ["từ Kyic Store", "cung cấp bởi"]
    if any(marker in clean for marker in STALE_MARKERS):
        return DEFAULT

    # Nhánh 3: Nội dung hợp lệ — áp dụng giới hạn ký tự nếu có
    if max_chars and len(clean) > max_chars:
        # Cắt tại ranh giới từ, không cắt giữa chừng
        truncated = clean[:max_chars].rsplit(' ', 1)[0]
        return truncated + "…"

    return clean


def format_permissions(raw_data):
    """Phân tích cấu trúc quyền hạn (Permissions) an toàn từ file cấu hình của App"""
    formatted_dict = {}
    if not raw_data:
        return formatted_dict
    try:
        if isinstance(raw_data, dict):
            for k, v in raw_data.items():
                clean_k = clean_text(k)
                clean_v = clean_text(v)
                if clean_k:
                    if not clean_v:
                        clean_v = f"Ứng dụng yêu cầu quyền truy cập {clean_k}."
                    formatted_dict[clean_k] = clean_v

        elif isinstance(raw_data, list):
            for item in raw_data:
                if isinstance(item, dict):
                    for k, v in item.items():
                        clean_k = clean_text(k)
                        clean_v = clean_text(v) if v else f"Ứng dụng yêu cầu quyền truy cập {clean_k}."
                        if clean_k:
                            formatted_dict[clean_k] = clean_v
                elif isinstance(item, str):
                    clean_item = clean_text(item)
                    if clean_item:
                        display_name = config.PERM_MAPPING.get(clean_item, clean_item)
                        formatted_dict[display_name] = f"Ứng dụng yêu cầu quyền truy cập {display_name}."

    except Exception as e:
        logger.warning(f"⚠️ Lỗi xử lý cấu trúc quyền hạn: {e}")

    return formatted_dict


def clean_github_url(url):
    """
    Chuyển đổi các liên kết GitHub Blob thông thường sang định dạng Raw URL.

    FIX: Xử lý tuần tự một lần thay vì áp dụng hai nhánh if độc lập
    có thể biến đổi URL hai lần không cần thiết.
    """
    if not url or not isinstance(url, str):
        return ""

    # Chuẩn hóa: bỏ query string trước khi xử lý
    clean = url.split("?")[0].rstrip()

    if "github.com" in clean and "/blob/" in clean:
        clean = (
            clean
            .replace("github.com", "raw.githubusercontent.com")
            .replace("/blob/", "/")
        )

    return clean


def download_resource_to_local(url, target_path):
    """
    Tải tài nguyên từ xa về máy ảo lưu trữ, có xử lý file tạm độc lập.

    FIX: Kiểm tra kích thước file sau khi tải — tránh lưu file rỗng (0 bytes)
    khi server trả về response hợp lệ nhưng không có nội dung.
    """
    if not url or not isinstance(url, str) or not url.startswith("http"):
        return False

    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    temp_path = target_path + ".tmp"

    try:
        logger.info(f"📥 Đang tải: {os.path.basename(target_path)}")
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            with open(temp_path, 'wb') as f:
                f.write(response.read())

        # FIX: Từ chối file rỗng
        if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
            logger.warning(f"⚠️ File tải về rỗng (0 bytes), bỏ qua: {os.path.basename(target_path)}")
            try:
                os.remove(temp_path)
            except Exception:
                pass
            return False

        os.replace(temp_path, target_path)
        return True

    except Exception as e:
        logger.error(f"❌ Thất bại khi tải file {os.path.basename(target_path)}: {e}")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return False


def get_default_assets(asset_name):
    return f"{config.RAW_URL.rstrip('/')}/data/default/{asset_name}.png"


def get_default_screens():
    return config.get_default_screenshots()
    
    
def clean_string_for_match(text):
    """Chuẩn hóa chuỗi để so khớp tên tweak/file"""
    if not text:
        return ""
    # Chuyển thành chữ thường và xóa khoảng trắng dư thừa
    return str(text).lower().strip()
