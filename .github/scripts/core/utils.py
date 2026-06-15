# .github/scripts/core/utils.py
import re
import os
import sys
import urllib.request

# Khắc phục đường dẫn hệ thống để nạp cấu hình chính xác
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

import config

def clean_text(text):
    """Làm sạch khoảng trắng thừa trong chuỗi văn bản"""
    if not text: return ""
    return re.sub(r'\s+', ' ', str(text)).strip()

def smart_truncate_description(text, max_chars=None):
    """
    Xử lý mô tả ứng dụng thông minh.
    Giữ nguyên nội dung nếu đã có chi tiết, chỉ áp dụng mặc định khi dữ liệu rỗng.
    """
    if not text:
        return "Ứng dụng Premium phiên bản ổn định, mượt mờ, mở khóa đầy đủ tính năng cao cấp từ Kyic Store."
    
    clean = re.sub(r'[\r\n\t]+', ' ', str(text))
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    # Chỉ áp dụng chuỗi mặc định nếu nội dung quá ngắn hoặc là nội dung rác/tự động cũ
    if len(clean) < 10 or "từ Kyic Store" in clean or "cung cấp bởi" in clean:
        # Nếu đã có nội dung dài (ví dụ từ file .txt), hãy tôn trọng nó
        if len(clean) > 20: 
            return clean
        return "Ứng dụng Premium phiên bản ổn định, mượt mờ, mở khóa đầy đủ tính năng cao cấp từ Kyic Store."
    
    return clean

def format_permissions(raw_data):
    """Phân tích cấu trúc quyền hạn (Permissions) an toàn từ file cấu hình của App"""
    formatted_dict = {}
    if not raw_data: return formatted_dict
    try:
        if isinstance(raw_data, dict):
            for k, v in raw_data.items():
                clean_k = clean_text(k)
                clean_v = clean_text(v)
                if clean_k:
                    if not clean_v: clean_v = f"Ứng dụng yêu cầu quyền truy cập {clean_k}."
                    formatted_dict[clean_k] = clean_v
        elif isinstance(raw_data, list):
            for item in raw_data:
                if isinstance(item, dict):
                    for k, v in item.items():
                        clean_k = clean_text(k)
                        clean_v = clean_text(v) if v else f"Ứng dụng yêu cầu quyền truy cập {clean_k}."
                        if clean_k: formatted_dict[clean_k] = clean_v
                elif isinstance(item, str):
                    clean_item = clean_text(item)
                    if clean_item:
                        display_name = config.PERM_MAPPING.get(clean_item, clean_item)
                        formatted_dict[display_name] = f"Ứng dụng yêu cầu quyền truy cập {display_name}."
    except Exception as e:
        print(f"⚠️ Lỗi xử lý cấu trúc quyền hạn: {e}", flush=True)
    return formatted_dict

def clean_github_url(url):
    """Chuyển đổi các liên kết GitHub Blob thông thường sang định dạng liên kết tải tệp thô (Raw URL)"""
    if not url or not isinstance(url, str): return ""
    if "github.com" in url and "/blob/" in url:
        url = url.split("?")[0].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    if "github.com" in url and url.endswith("?raw=true"):
        url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/").replace("?raw=true", "")
    return url

def download_resource_to_local(url, target_path):
    """Tải tài nguyên từ xa về máy ảo lưu trữ có xử lý tệp tạm độc lập"""
    if not url or not isinstance(url, str) or not url.startswith("http"): 
        return False
    
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    temp_path = target_path + ".tmp"
    
    try:
        print(f"📥 Đang tải: {os.path.basename(target_path)}", flush=True)
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            with open(temp_path, 'wb') as f:
                f.write(response.read())
        
        if os.path.exists(temp_path):
            os.replace(temp_path, target_path)
            return True
    except Exception as e:
        if os.path.exists(temp_path): 
            try: os.remove(temp_path)
            except: pass
        print(f"❌ Thất bại khi tải file {os.path.basename(target_path)}: {e}", flush=True)
    return False

def get_default_assets(asset_name):
    return f"{config.RAW_URL.rstrip('/')}/depictions/default/{asset_name}.png"

def get_default_screens():
    return config.get_default_screenshots()

