# .github/scripts/core/dylib_engine.py
import os
import json
import logging
import hashlib
import tempfile
import urllib.request
import datetime
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from . import utils

logger = logging.getLogger(__name__)

# ... [Giữ nguyên hàm calculate_hashes_from_url và calculate_hashes_from_local] ...
def calculate_hashes_from_url(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        md5, sha1, sha256 = hashlib.md5(), hashlib.sha1(), hashlib.sha256()
        with tempfile.NamedTemporaryFile(suffix=".dylib", delete=False) as tmp:
            with urllib.request.urlopen(req, timeout=30) as response:
                while chunk := response.read(65536):
                    tmp.write(chunk)
                    md5.update(chunk); sha1.update(chunk); sha256.update(chunk)
            temp_path = tmp.name
        os.remove(temp_path)
        return md5.hexdigest(), sha1.hexdigest(), sha256.hexdigest()
    except Exception as e:
        logger.error(f"⚠️ Lỗi hash cloud dylib: {e}")
        return "0"*32, "0"*40, "0"*64

def calculate_hashes_from_local(path):
    md5, sha1, sha256 = hashlib.md5(), hashlib.sha1(), hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            md5.update(chunk); sha1.update(chunk); sha256.update(chunk)
    return md5.hexdigest(), sha1.hexdigest(), sha256.hexdigest()

def run_dylib_engine(release_assets, system_db):
    dylibs_data = []
    tweak_lookup = {
        utils.clean_string_for_match(info.get("Name", "")): info 
        for info in system_db.get("tweaks", {}).values()
    }

    # 1 & 2. Thu thập dữ liệu
    # ... (Giữ nguyên logic thu thập Local và Cloud của bạn) ...
    # (Thu thập vào dylibs_data như cũ)
    
    # 3. Xử lý Output kép
    # A. Ghi file cho Feather/Sileo (Gốc)
    with open(config.DYLIBS_DATABASE, 'w', encoding='utf-8') as f:
        json.dump({"dylibs": dylibs_data, "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}, f, indent=2, ensure_ascii=False)

    # B. Ghi file cho Web (Gom nhóm Bundle)
    grouped_data = {}
    for entry in dylibs_data:
        bundle = entry['bundle']
        if bundle not in grouped_data:
            grouped_data[bundle] = entry.copy()
            grouped_data[bundle]['versions'] = []
            grouped_data[bundle]['icon'] = entry.get("icon", f"{config.RAW_URL}repo/depictions/icons/{bundle}.png")
        
        grouped_data[bundle]['versions'].append({"ver": entry.get("version", "1.0"), "url": entry.get("downloadURL")})

    web_json_path = config.DYLIBS_DATABASE.replace(".json", "_web.json")
    with open(web_json_path, 'w', encoding='utf-8') as f:
        json.dump({"dylibs": list(grouped_data.values())}, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ Đã tạo {config.DYLIBS_DATABASE} và {web_json_path}")

def _create_dylib_entry(filename, deb_info, is_cloud, url=None, hashes=None, size=0):
    md5, sha1, sha256 = hashes or ("0"*32, "0"*40, "0"*64)
    base_info = {
        "filename": filename,
        "md5": md5, "sha1": sha1, "sha256": sha256,
        "size": size,
        "downloadURL": url if is_cloud else f"{config.BASE_URL}dylibs/{filename}"
    }
    
    if deb_info:
        base_info.update({
            "name": deb_info.get("Name"),
            "bundle": deb_info.get("Package"),
            "version": deb_info.get("Version"),
            "author": deb_info.get("Author"),
            "description": deb_info.get("Description"),
            "icon": deb_info.get("Icon", f"{config.RAW_URL}repo/depictions/icons/{deb_info.get('Package')}.png")
        })
    else:
        name = filename.rsplit('.', 1)[0]
        bundle = f"com.kyic.{utils.clean_string_for_match(name)}"
        base_info.update({
            "name": name,
            "bundle": bundle,
            "version": "1.0",
            "author": "Kyic Store",
            "description": "Thư viện mở rộng từ Kyic Store.",
            "icon": f"{config.RAW_URL}repo/depictions/icons/{bundle}.png"
        })
    return base_info
    return base_info
