# .github/scripts/core/utils.py
import re
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

import config

def clean_text(text):
    if not text: return ""
    return re.sub(r'\s+', ' ', str(text)).strip()

def smart_truncate_description(text, max_chars=None):
    if not text:
        return "Ứng dụng Premium phiên bản ổn định, mượt mà, mở khóa đầy đủ tính năng cao cấp từ Kyic Store."
    clean = re.sub(r'[\r\n\t]+', ' ', str(text))
    clean = re.sub(r'\s+', ' ', clean).strip()
    if len(clean) < 10 or "từ Kyic Store" in clean or "cung cấp bởi" in clean:
        return "Ứng dụng Premium phiên bản ổn định, mượt mà, mở khóa đầy đủ tính năng cao cấp từ Kyic Store."
    return clean

def format_permissions(raw_data):
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
        print(f"⚠️ Lỗi parse permissions: {e}")
    return formatted_dict

def clean_github_url(url):
    if not url or not isinstance(url, str): return ""
    if "github.com" in url and "/blob/" in url:
        url = url.split("?")[0].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    if "github.com" in url and url.endswith("?raw=true"):
        url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/").replace("?raw=true", "")
    return url

def download_resource_to_local(url, target_path):
    if not url or not isinstance(url, str) or not url.startswith("http"): return False
    if os.path.exists(target_path) and os.path.getsize(target_path) > 0: return True 
    try:
        print(f"📥 Đang tải tài nguyên về local -> {os.path.basename(target_path)}")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'})
        with urllib.request.urlopen(req, timeout=20) as response:
            with open(target_path, 'wb') as f: f.write(response.read())
        return True
    except Exception as e:
        print(f"⚠️ Không thể tải file từ {url}. Lỗi: {e}")
        return False

def get_default_screens():
    screens = []
    if os.path.exists(config.IMG_DIR):
        all_imgs = sorted(os.listdir(config.IMG_DIR))
        for f in all_imgs:
            if f.lower().startswith("kyic") and not any(x in f.lower() for x in ["banner", "logo"]):
                if any(f.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp', '.mp4']):
                    screens.append(f"{config.RAW_URL}{config.IMG_DIR_NAME}/{f}")
    return screens if screens else [config.SOURCE_LOGO]
