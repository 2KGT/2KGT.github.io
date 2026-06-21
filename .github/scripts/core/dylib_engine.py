# .github/scripts/core/dylib_engine.py
import os
import sys
import json
import logging
import hashlib
import re
import time
import datetime
import inspect
import config

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from . import utils
from collections import defaultdict
logger = logging.getLogger(__name__)


def clean_string_for_match(text):
    if not text:
        return ""
    return re.sub(r'[^a-z0-9]', '', text.lower())


def calculate_hashes_from_local(path):
    """Tính hash chuẩn cho file .dylib cục bộ (streaming tránh tràn RAM)"""
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                md5.update(chunk)
                sha1.update(chunk)
                sha256.update(chunk)
    except Exception as e:
        logger.error(f"⚠️ Lỗi tính hash dylib [{path}]: {e}")
        return "0" * 32, "0" * 40, "0" * 64
    return md5.hexdigest(), sha1.hexdigest(), sha256.hexdigest()


def parse_dylib_filename(filename):
    """
    Phân tách tên file .dylib để lấy các trường nhận diện:
    Ví dụ: com.kyic.glow_1.3.1_iphoneos-arm.dylib
    -> id_or_name: com.kyic.glow, ver: 1.3.1, arch: iphoneos-arm
    """
    name_no_ext = filename.rsplit('.', 1)[0]
    parts = name_no_ext.split('_')
    
    id_or_name = parts[0] if len(parts) > 0 else name_no_ext
    ver = parts[1] if len(parts) > 1 else None
    arch = parts[2] if len(parts) > 2 else None
    
    return id_or_name, ver, arch


def resolve_display_name(deb_match, fallback_id):
    """
    FIX: Suy ra "tên đẹp" cho dylib, đồng bộ logic với sileo_engine.py.

    Thứ tự ưu tiên:
    1. Field 'Name' từ deb_match (dữ liệu DEB đã đối chiếu được) — nếu
       hợp lệ và KHÔNG phải là bundle ID trá hình (Name == Package).
    2. Fallback: lấy đoạn cuối cùng của bundle ID/tên file dylib
       (com.w3ltyyy.lead → lead → Lead), viết hoa chữ cái đầu.

    Không tự early-return name rỗng/None — luôn rơi xuống fallback.
    """
    def _looks_like_bundle_id(s):
        # com.x.y kiểu domain ngược — nhiều dấu chấm + toàn chữ thường/số
        return bool(re.match(r'^[a-z0-9]+(\.[a-z0-9]+){2,}$', s.strip()))

    name = (deb_match or {}).get("Name", "")
    name = name.strip() if isinstance(name, str) else ""

    if name and not _looks_like_bundle_id(name):
        return name

    base = fallback_id.strip().split('.')[-1] if fallback_id else fallback_id
    base = base or fallback_id or "tweak"
    return base[:1].upper() + base[1:] if base else base


def find_matching_deb_data(f_name, system_db):
    """
    Thuật toán khớp mật mã cải tiến: Đối chiếu chuẩn xác theo Tên hoặc Package ID
    từ dữ liệu deb (sileo_engine) lưu trong system_db["tweaks"]
    """
    id_or_name, dylib_ver, dylib_arch = parse_dylib_filename(f_name)
    
    # Tìm kiếm các biến thể để tăng tỷ lệ khớp (Glow, com.kyic.glow)
    clean_dylib_id = clean_string_for_match(id_or_name)
    clean_dylib_base = clean_string_for_match(id_or_name.split('.')[-1])
    
    best_match = None
    tweaks_dict = system_db.get("tweaks", {})
    
    for key, deb_info in tweaks_dict.items():
        deb_pkg = deb_info.get("Package", "")
        deb_name = deb_info.get("Name", "")
        deb_ver = deb_info.get("Version", "")
        deb_arch = deb_info.get("Architecture", "")
        
        clean_deb_pkg = clean_string_for_match(deb_pkg)
        clean_deb_pkg_base = clean_string_for_match(deb_pkg.split('.')[-1])
        clean_deb_name = clean_string_for_match(deb_name)
        
        # Kiểm tra khớp chéo đa điều kiện
        if (clean_dylib_id == clean_deb_pkg or 
            clean_dylib_base in [clean_deb_pkg_base, clean_deb_name]):
            
            # Ưu tiên số 1: Khớp hoàn hảo cả kiến trúc và phiên bản
            if dylib_ver == deb_ver and dylib_arch == deb_arch:
                return deb_info
            # Ưu tiên số 2: Khớp phiên bản
            if dylib_ver == deb_ver:
                best_match = deb_info
            # Ưu tiên số 3: Fallback lấy dữ liệu trùng tên gần nhất
            elif not best_match:
                best_match = deb_info
                
    return best_match


def run_dylib_engine(release_assets, system_db):
    """
    🌟 PHÂN HỆ XỬ LÝ DYLIBS: 
    Đối chiếu tên file .dylib -> Khớp lấy thông tin từ DEB -> Đổ qua utils nắn khung -> Xuất dữ liệu vào wiki và repo
    """
    logger.info("🚀 Khởi chạy phân hệ xử lý dữ liệu dylibs chuyên sâu...")
    
    processed_dylibs_titles = []
    wiki_dylibs_data = {}  # Lưu trữ dữ liệu thô chi tiết đầy đủ thuộc tính cho wikidylibs.json
    dylibs_list_data = []  # Lưu dữ liệu danh mục rút gọn sau khi nắn khung cho dylibs.json
    
    # Xác định thư mục chứa file dylib thực tế từ config
    dylibs_input_dir = getattr(config, "DYLIBS_INPUT_DIR", os.path.join(config.REPO_OUTPUT_DIR, "dylibs"))
    
    if not os.path.exists(dylibs_input_dir):
        logger.warning(f"⚠️ Không tìm thấy thư mục chứa dylibs tại: {dylibs_input_dir}")
        return processed_dylibs_titles

    # Quét tất cả các file .dylib thực tế hiện có trong thư mục
    dylib_files = [f for f in sorted(os.listdir(dylibs_input_dir)) if f.endswith('.dylib') and not f.startswith('.')]

    for f_name in dylib_files:
        path = os.path.join(dylibs_input_dir, f_name)
        id_or_name, dylib_ver, dylib_arch = parse_dylib_filename(f_name)
        
        # 1. Khớp mật mã để lấy thông tin toàn vẹn từ cấu trúc DEB đã chạy trước đó
        deb_match = find_matching_deb_data(f_name, system_db)
        
        # Tính toán dung lượng và mã hash của tệp dylib thực tế
        md5, sha1, sha256 = calculate_hashes_from_local(path)
        file_size = int(os.path.getsize(path))
        relative_path = os.path.relpath(path, config.REPO_OUTPUT_DIR).replace("\\", "/")
        download_url = f"{config.BASE_URL.rstrip('/')}/{relative_path.lstrip('/')}"
        
        # Định hình dữ liệu cơ sở dựa trên việc đối chiếu kết quả
        # FIX: dùng resolve_display_name() để tên đẹp nhất quán với
        # sileo_engine.py — tránh hiển thị bundle ID thô (com.w3ltyyy.lead)
        # khi deb_match["Name"] vô tình trùng bundle ID, và viết hoa chữ
        # đầu khi phải fallback về đoạn cuối id_or_name.
        if deb_match:
            name = resolve_display_name(deb_match, id_or_name)
            bundle = deb_match.get("Package", id_or_name)
            version = dylib_ver if dylib_ver else deb_match.get("Version", "1.0")
            architecture = dylib_arch if dylib_arch else deb_match.get("Architecture", "iphoneos-arm64")
            section = deb_match.get("Section", "Tweaks")
            author = deb_match.get("Author", "Kyic Store")
            description = deb_match.get("Description", "Tinh chỉnh cấu trúc dylib.")
        else:
            name = resolve_display_name(None, id_or_name)
            bundle = id_or_name if '.' in id_or_name else f"com.kyic.{id_or_name.lower()}"
            version = dylib_ver if dylib_ver else "1.0"
            architecture = dylib_arch if dylib_arch else "iphoneos-arm64"
            section = "Tweaks"
            author = "Kyic Store"
            description = "Tinh chỉnh dylib độc lập (Không có gói DEB đối chiếu)."

        # Đồng bộ hóa Icon xử lý qua utils hoặc config
        clean_base = clean_string_for_match(name)
        icon_url = f"{config.RAW_URL.rstrip('/')}/{config.ICON_DIR_NAME.strip('/')}/{clean_base}.jpg"
        icon_url = utils.clean_github_url(icon_url)
        if not icon_url or "default" in icon_url:
            icon_url = config.SOURCE_LOGO

        # 2. Lưu vào Cấu trúc wikidylibs_data (Đã sửa lỗi nạp thiếu dữ liệu)
        wiki_dylibs_data[download_url] = {
            "Package": bundle,
            "Name": name,
            "Version": version,
            "Architecture": architecture,
            "Section": section,
            "Author": author,
            "Description": description,
            "Icon": icon_url,
            "Size": file_size,
            "MD5": md5,
            "SHA1": sha1,
            "SHA256": sha256,
            "Dylib_File": f_name
        }

        # 3. Đổ dữ liệu qua utils để nắn khung dọn dẹp chuỗi trước khi nạp vào dylibs.json
        final_name = str(name)
        final_version = str(version)
        processed_dylibs_titles.append(final_name)

        dylibs_list_data.append({
            "name": final_name,
            "bundle": bundle,
            "version": final_version,
            "architecture": architecture,
            "section": section,
            "author": author,
            "icon": icon_url,
            "size": file_size,
            "downloadURL": download_url,
            "md5": md5,
            "sha256": sha256
        })

    # Thời gian tạo bản dựng
    gen_time = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # 4. FIX ĐƯỜNG DẪN: Xuất file wikidylibs.json ra thẳng thư mục WIKI thay vì REPO_OUTPUT_DIR
    wiki_dir_path = getattr(config, "WIKI_DIR", os.path.join(os.path.dirname(config.REPO_OUTPUT_DIR), "wiki"))
    os.makedirs(wiki_dir_path, exist_ok=True)
    
    wiki_output_path = os.path.join(wiki_dir_path, 'wikidylibs.json')
    try:
        with open(wiki_output_path, 'w', encoding='utf-8') as f:
            json.dump({"dylibs_db": wiki_options_db_format(wiki_dylibs_data), "generated_at": gen_time}, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Đã xuất cấu trúc nguồn vào thư mục wiki: {wiki_output_path}")
    except Exception as e:
        logger.error(f"❌ Lỗi ghi tệp wikidylibs.json vào wiki: {e}")

    # 5. Kết xuất file cấu trúc dylibs.json ra thẳng root repo output
    dylibs_output_path = os.path.join(config.REPO_OUTPUT_DIR, 'dylibs.json')
    output_json = {
        "dylibs": dylibs_list_data,
        "generated_at": gen_time,
        "total": len(dylibs_list_data)
    }
    try:
        with open(dylibs_output_path, 'w', encoding='utf-8') as f:
            json.dump(output_json, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Đã kết xuất dylibs.json hoàn chỉnh tại repo root: {dylibs_output_path}")
    except Exception as e:
        logger.error(f"❌ Lỗi ghi tệp dylibs.json: {e}")

    return processed_dylibs_titles


def wiki_options_db_format(data_dict):
    """Hàm phụ trợ dọn dẹp hoặc sắp xếp lại dict giống wkidebs.json"""
    return {k: v for k, v in sorted(data_dict.items(), key=lambda item: item[1].get("Name", ""))}
