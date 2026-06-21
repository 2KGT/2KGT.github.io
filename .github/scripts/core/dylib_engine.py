# .github/scripts/core/dylib_engine.py
import os
import sys
import json
import logging
import hashlib
import re
import datetime
from urllib.parse import urlparse
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
    """
    def _looks_like_bundle_id(s):
        return bool(re.match(r'^[a-z0-9]+(\.[a-z0-9]+){2,}$', s.strip()))

    name = (deb_match or {}).get("Name", "")
    name = name.strip() if isinstance(name, str) else ""

    if name and not _looks_like_bundle_id(name):
        return name

    base = fallback_id.strip().split('.')[-1] if fallback_id else fallback_id
    base = base or fallback_id or "tweak"
    return base[:1].upper() + base[1:] if base else base


def _extract_deb_filename(dict_key):
    """
    Lấy tên tệp .deb gốc từ 1 record trong system_db["tweaks"].

    ĐỐI CHIẾU THỰC TẾ với sileo_engine.py: `system_db["tweaks"][f_url] =
    deb_info` — value (deb_info) chỉ là control data thuần (Package/Name/
    Version/Architecture/Description/...), KHÔNG có field "Filename" nào.
    Tên tệp .deb thật ra nằm ở chính KEY của dict (f_url): với .deb cloud,
    f_url = asset["url"] (link release asset, có thể kèm query string
    token); với .deb local, f_url = BASE_URL + relative_path (kết thúc
    bằng đúng tên tệp). Nên lấy basename từ phần path của key, bỏ qua
    query string (?...) nếu có.
    """
    if not dict_key:
        return ""
    path_part = urlparse(str(dict_key)).path or str(dict_key)
    return os.path.basename(path_part)


def find_matching_deb_data(f_name, system_db):
    """
    🔑 CHÌA KHÓA ĐỐI CHIẾU (đơn giản hoá): tên tệp .dylib và tên tệp
    .deb tương ứng về cơ bản GIỐNG HOÀN TOÀN, chỉ khác phần đuôi mở
    rộng. Ví dụ:
        com.kyic.glow_1.3.1_iphoneos-arm.deb
        com.kyic.glow_1.3.1_iphoneos-arm.dylib
    => Chỉ cần so khớp toàn bộ tên tệp (bỏ đuôi, đã chuẩn hoá) là đủ
    xác định chính xác gói .deb tương ứng — không cần suy luận
    id/version/arch riêng lẻ như trước.

    Nếu không tìm thấy khớp tuyệt đối (vd dylib bị đổi tên thủ công),
    rơi xuống thuật toán dò theo Package/Name cũ làm phương án dự phòng.
    """
    dylib_base = clean_string_for_match(f_name.rsplit('.', 1)[0])
    tweaks_dict = system_db.get("tweaks", {})

    # 1) Khớp CHÍNH: toàn bộ tên tệp (chỉ khác đuôi .deb/.dylib)
    for key, deb_info in tweaks_dict.items():
        deb_filename = _extract_deb_filename(key)
        deb_base = clean_string_for_match(os.path.splitext(deb_filename)[0])
        if deb_base and deb_base == dylib_base:
            return deb_info

    # 2) Dự phòng: thuật toán cũ — khớp theo Package ID / tên rút gọn
    return _fallback_fuzzy_match_deb(f_name, tweaks_dict)


def _fallback_fuzzy_match_deb(f_name, tweaks_dict):
    """Phương án dự phòng khi không khớp được nguyên tên tệp."""
    id_or_name, dylib_ver, dylib_arch = parse_dylib_filename(f_name)

    clean_dylib_id = clean_string_for_match(id_or_name)
    clean_dylib_base = clean_string_for_match(id_or_name.split('.')[-1])

    best_match = None
    for key, deb_info in tweaks_dict.items():
        deb_pkg = deb_info.get("Package", "")
        deb_name = deb_info.get("Name", "")
        deb_ver = deb_info.get("Version", "")
        deb_arch = deb_info.get("Architecture", "")

        clean_deb_pkg = clean_string_for_match(deb_pkg)
        clean_deb_pkg_base = clean_string_for_match(deb_pkg.split('.')[-1])
        clean_deb_name = clean_string_for_match(deb_name)

        if (clean_dylib_id == clean_deb_pkg or
                clean_dylib_base in [clean_deb_pkg_base, clean_deb_name]):

            if dylib_ver == deb_ver and dylib_arch == deb_arch:
                return deb_info
            if dylib_ver == deb_ver:
                best_match = deb_info
            elif not best_match:
                best_match = deb_info

    return best_match


def get_dylib_assets(dylib_name, deb_match):
    """
    FIX MỚI: Lấy đầy đủ asset (icon/banner/screenshots) cho dylib —
    cùng tinh thần get_tweak_assets() của sileo_engine.py, vì dylib
    sideload độc lập qua TrollFools/SideStore cần hiển thị đẹp trên
    web giống Feather, không chỉ icon đơn thuần.

    Thứ tự ưu tiên:
    1. Control field khai báo trong deb_match (Icon/Banner/Screenshots)
       nếu dylib đối chiếu khớp được với 1 gói .deb đã xử lý trước đó.
    2. Quét thư mục local đã tải/upload sẵn:
       repo/data/icons/<base>.*  và  repo/data/images/<dylib_name>/*
    3. Asset mặc định của repo (SOURCE_LOGO / DEFAULT_BANNER / default screens).
    """
    exts = ['.png', '.jpg', '.jpeg', '.webp']
    base_variant = clean_string_for_match(dylib_name) or "default"

    def build_icon_url(file_name):
        return f"{config.RAW_URL.rstrip('/')}/{config.ICON_DIR_NAME.strip('/')}/{file_name}"

    def build_image_url(file_name):
        return f"{config.RAW_URL.rstrip('/')}/{config.IMG_DIR_NAME.strip('/')}/{dylib_name}/{file_name}"

    local_icons = os.listdir(config.ICON_DIR) if os.path.exists(config.ICON_DIR) else []
    dylib_img_dir = config.get_dylib_images_dir(dylib_name)
    local_images = os.listdir(dylib_img_dir) if os.path.exists(dylib_img_dir) else []

    icon_url, banner_url, screens = None, None, []

    if deb_match:
        remote_icon = deb_match.get('Icon') or deb_match.get('icon')
        if remote_icon and str(remote_icon).startswith("http"):
            if utils.download_resource_to_local(remote_icon, os.path.join(config.ICON_DIR, f"{base_variant}.jpg")):
                icon_url = build_icon_url(f"{base_variant}.jpg")

        remote_banner = deb_match.get('Banner') or deb_match.get('banner')
        if remote_banner and str(remote_banner).startswith("http"):
            os.makedirs(dylib_img_dir, exist_ok=True)
            if utils.download_resource_to_local(remote_banner, os.path.join(dylib_img_dir, f"{base_variant}_banner.jpg")):
                banner_url = build_image_url(f"{base_variant}_banner.jpg")

        raw_screens_data = (
            deb_match.get('Screenshots') or deb_match.get('screenshots')
            or deb_match.get('Screenshot') or deb_match.get('screenshot')
        )
        if raw_screens_data:
            urls_list = []
            if isinstance(raw_screens_data, list):
                urls_list = raw_screens_data
            elif isinstance(raw_screens_data, str):
                if raw_screens_data.startswith('[') and raw_screens_data.endswith(']'):
                    try:
                        urls_list = json.loads(raw_screens_data)
                    except Exception:
                        urls_list = [u.strip() for u in raw_screens_data.strip('[]').split(',') if u]
                else:
                    urls_list = [u.strip() for u in raw_screens_data.split(',') if u]

            os.makedirs(dylib_img_dir, exist_ok=True)
            for idx, scr_url in enumerate(urls_list, start=1):
                if str(scr_url).startswith("http"):
                    if utils.download_resource_to_local(scr_url, os.path.join(dylib_img_dir, f"{base_variant}_{idx}.jpg")):
                        screens.append(build_image_url(f"{base_variant}_{idx}.jpg"))

    # ── Fallback: tìm trong thư mục local đã tải/upload sẵn ──
    if not icon_url:
        matched = next(
            (f for f in local_icons
             if clean_string_for_match(f.rsplit('.', 1)[0]) == base_variant
             and any(f.lower().endswith(e) for e in exts)),
            None
        )
        if matched:
            icon_url = build_icon_url(matched)

    if not banner_url:
        matched = next(
            (f for f in local_images
             if clean_string_for_match(f.rsplit('.', 1)[0]) in [f"{base_variant}banner", f"{base_variant}_banner"]
             and any(f.lower().endswith(e) for e in exts)),
            None
        )
        if matched:
            banner_url = build_image_url(matched)

    if not screens:
        for i in range(1, 16):
            matched = next(
                (f for f in local_images
                 if clean_string_for_match(f.rsplit('.', 1)[0]) in [f"{base_variant}_{i}", f"{base_variant}{i}"]
                 and any(f.lower().endswith(e) for e in exts)),
                None
            )
            if matched:
                screens.append(build_image_url(matched))

    if not icon_url:
        icon_url = config.SOURCE_LOGO
    if not banner_url:
        banner_url = config.DEFAULT_BANNER
    if not screens:
        screens = utils.get_default_screens()

    return {
        "icon": utils.clean_github_url(icon_url),
        "banner": utils.clean_github_url(banner_url),
        "screenshots": [utils.clean_github_url(s) for s in screens if s]
    }


def build_dylib_depiction_json(safe_filename, dylib_name, version, description, assets, author, bundle, architecture, extra):
    """
    FIX MỚI: Depiction JSON riêng từng version+arch cho dylib — KHÔNG
    dùng format DepictionTabView của Sileo (dylib không qua APT/Sileo),
    mà dùng cấu trúc key-value đơn giản giống phong cách Feather, để
    dylib.html trên web tự đọc và hiển thị trực tiếp.

    Cấu trúc: repo/data/desc/dylibs/<DylibName>/<safe_filename>.json
    """
    optimized_desc = config.get_optimized_dylib_description(dylib_name, version)
    final_description = optimized_desc if optimized_desc else description
    changelog_markdown = config.get_dylib_changelog_history(dylib_name, version)

    target_folder, json_filename = config.get_dylib_depiction_path(dylib_name, safe_filename)
    os.makedirs(target_folder, exist_ok=True)
    file_path = os.path.join(target_folder, json_filename)

    clean_desc = utils.smart_truncate_description(final_description, max_chars=1000)

    depiction_data = {
        "name": str(dylib_name),
        "bundle": str(bundle),
        "version": str(version),
        "architecture": str(architecture),
        "author": str(author),
        "description": clean_desc,
        "changelog": changelog_markdown,
        "icon": assets["icon"],
        "banner": assets["banner"],
        "screenshots": assets["screenshots"],
        "size": extra.get("size", 0),
        "md5": extra.get("md5", ""),
        "sha1": extra.get("sha1", ""),
        "sha256": extra.get("sha256", ""),
        "downloadURL": extra.get("downloadURL", ""),
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(depiction_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"❌ Lỗi ghi depiction JSON cho dylib {safe_filename}: {e}")
        return None

    # FIX: URL public trỏ tới file depiction vừa ghi — dùng cho field
    # "depictionURL" trong dylibs.json để web fetch chi tiết từng bản.
    rel = os.path.relpath(file_path, config.REPO_OUTPUT_DIR).replace("\\", "/")
    return f"{config.BASE_URL.rstrip('/')}/{rel.lstrip('/')}"


def run_dylib_engine(release_assets, system_db):
    """
    🌟 PHÂN HỆ XỬ LÝ DYLIBS (kiến trúc Feather + nội dung kiểu Sileo):

    - Quét .dylib cục bộ (repo/dylibs/).
    - Đối chiếu với system_db["tweaks"] (do sileo_engine xử lý trước đó
      trong main.py) để lấy Name/Author/Icon/Description đẹp — giống deb.
    - Gom theo bundle để xuất "versions[]" như apps.json của Feather.
    - Mỗi version+arch có file changelog .txt riêng + depiction .json
      riêng tại repo/data/desc/dylibs/<Name>/ — không version nào đè
      version khác.
    """
    logger.info("🚀 Khởi chạy phân hệ xử lý dữ liệu dylibs chuyên sâu...")

    processed_dylibs_titles = []
    wiki_dylibs_data = {}     # cache thô đầy đủ thuộc tính cho wikidylibs.json
    dylibs_map = defaultdict(list)  # group theo bundle để dựng versions[]

    dylibs_input_dir = getattr(config, "DYLIBS_INPUT_DIR", os.path.join(config.REPO_OUTPUT_DIR, "dylibs"))

    if not os.path.exists(dylibs_input_dir):
        logger.warning(f"⚠️ Không tìm thấy thư mục chứa dylibs tại: {dylibs_input_dir}")
        return processed_dylibs_titles

    dylib_files = [f for f in sorted(os.listdir(dylibs_input_dir)) if f.endswith('.dylib') and not f.startswith('.')]

    for f_name in dylib_files:
        path = os.path.join(dylibs_input_dir, f_name)
        safe_filename = f_name.rsplit('.', 1)[0]
        id_or_name, dylib_ver, dylib_arch = parse_dylib_filename(f_name)

        # 1. Đối chiếu để lấy thông tin đẹp từ DEB đã xử lý trước đó (nếu có)
        deb_match = find_matching_deb_data(f_name, system_db)

        md5, sha1, sha256 = calculate_hashes_from_local(path)
        file_size = int(os.path.getsize(path))
        relative_path = os.path.relpath(path, config.REPO_OUTPUT_DIR).replace("\\", "/")
        download_url = f"{config.BASE_URL.rstrip('/')}/{relative_path.lstrip('/')}"

        # FIX: tên đẹp — ưu tiên Name từ deb_match, fallback đoạn cuối bundle ID
        dylib_name = resolve_display_name(deb_match, id_or_name)

        version = dylib_ver if dylib_ver else (deb_match.get("Version") if deb_match else "1.0")
        architecture = dylib_arch if dylib_arch else (deb_match.get("Architecture") if deb_match else "iphoneos-arm64")
        bundle = deb_match.get("Package", id_or_name) if deb_match else (
            id_or_name if '.' in id_or_name else f"com.kyic.{id_or_name.lower()}"
        )
        author = deb_match.get("Author", "Kyic Store") if deb_match else "Kyic Store"
        section = deb_match.get("Section", "Tweaks") if deb_match else "Tweaks"
        raw_description = deb_match.get("Description") if deb_match else None
        if not raw_description:
            raw_description = "Tinh chỉnh cấu trúc dylib." if deb_match else "Tinh chỉnh dylib độc lập (Không có gói DEB đối chiếu)."

        logger.info(f"-> Đang quét Dylib: {dylib_name} [{architecture}/v{version}]")
        processed_dylibs_titles.append(dylib_name)

        # 2. FIX MỚI: Lưu changelog v{version}.txt riêng cho dylib — ưu
        # tiên Description từ deb_match làm nội dung (nếu chưa có file
        # sẵn từ trước), giống cơ chế release_note của sileo_engine.
        dylib_desc_dir = os.path.join(config.DYLIB_DESC_DIR, dylib_name)
        version_file = os.path.join(dylib_desc_dir, f"v{version}.txt")
        if raw_description and len(str(raw_description).strip()) > 10 and not os.path.exists(version_file):
            os.makedirs(dylib_desc_dir, exist_ok=True)
            try:
                with open(version_file, 'w', encoding='utf-8') as f:
                    f.write(str(raw_description).strip())
                logger.info(f"💾 Lưu changelog dylib: {version_file}")
            except Exception as e:
                logger.warning(f"⚠️ Không lưu changelog cho dylib {dylib_name} v{version}: {e}")

        # 3. FIX MỚI: Đầy đủ asset (icon/banner/screenshots) — cần cho
        # sideload qua TrollFools/SideStore hiển thị đẹp trên web.
        assets = get_dylib_assets(dylib_name, deb_match)

        # 4. FIX MỚI: Depiction JSON riêng từng version+arch
        depiction_url = build_dylib_depiction_json(
            safe_filename, dylib_name, version, raw_description, assets, author, bundle, architecture,
            extra={"size": file_size, "md5": md5, "sha1": sha1, "sha256": sha256, "downloadURL": download_url}
        )

        # 5. Cache thô đầy đủ thuộc tính — giữ wikidylibs.json để tránh
        # tính lại hash mỗi lần chạy (như cơ chế cache của feather/sileo)
        wiki_dylibs_data[download_url] = {
            "Package": bundle, "Name": dylib_name, "Version": version,
            "Architecture": architecture, "Section": section, "Author": author,
            "Description": raw_description, "Icon": assets["icon"], "Banner": assets["banner"],
            "Screenshots": assets["screenshots"], "Size": file_size,
            "MD5": md5, "SHA1": sha1, "SHA256": sha256, "Dylib_File": f_name
        }

        dylibs_map[bundle].append({
            "name": dylib_name, "ver": str(version), "bundle": bundle,
            "architecture": architecture, "size": file_size,
            "downloadURL": download_url, "md5": md5, "sha256": sha256,
            "author": author, "icon": assets["icon"], "banner": assets["banner"],
            "screenshots": assets["screenshots"], "depictionURL": depiction_url,
            "safe_file": safe_filename,
            "description": config.get_optimized_dylib_description(dylib_name, version)
        })

    # 6. FIX MỚI: Xuất dylibs.json theo cấu trúc giống apps.json của
    # Feather — group theo bundle, mỗi entry có "versions[]" đầy đủ,
    # nhưng nội dung (name/author/icon/description) lấy theo style sileo.
    final_dylibs = []
    for bundle, versions in dylibs_map.items():
        unique_versions = sorted(versions, key=lambda v: utils.parse_version_tuple(v['ver']), reverse=True)
        latest = unique_versions[0]

        final_dylibs.append({
            "name": latest['name'],
            "bundleIdentifier": bundle,
            "developerName": latest['author'],
            "subtitle": "Dylib Sideload",
            "localizedDescription": latest['description'],
            "iconURL": latest['icon'],
            "tintColor": config.TINT_COLOR,
            "version": latest['ver'],
            "architecture": latest['architecture'],
            "size": latest['size'],
            "downloadURL": latest['downloadURL'],
            "depictionURL": latest['depictionURL'],
            "versions": [
                {
                    "version": v['ver'],
                    "architecture": v['architecture'],
                    "size": v['size'],
                    "downloadURL": v['downloadURL'],
                    "depictionURL": v['depictionURL'],
                    "localizedDescription": v['description']
                }
                for v in unique_versions
            ],
            "screenshotURLs": latest['screenshots'],
            "bannerURL": latest['banner']
        })

    final_dylibs.sort(key=lambda x: x['name'].lower())

    gen_time = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # 7. Xuất wikidylibs.json (cache thô) vào thư mục wiki
    wiki_dir_path = getattr(config, "WIKI_DIR", os.path.join(os.path.dirname(config.REPO_OUTPUT_DIR), "wiki"))
    os.makedirs(wiki_dir_path, exist_ok=True)
    wiki_output_path = os.path.join(wiki_dir_path, 'wikidylibs.json')
    try:
        with open(wiki_output_path, 'w', encoding='utf-8') as f:
            json.dump({"dylibs_db": wiki_options_db_format(wiki_dylibs_data), "generated_at": gen_time}, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Đã xuất cấu trúc nguồn vào thư mục wiki: {wiki_output_path}")
    except Exception as e:
        logger.error(f"❌ Lỗi ghi tệp wikidylibs.json vào wiki: {e}")

    # 8. Xuất dylibs.json hoàn chỉnh ra repo root (nguồn cho dylib.html)
    dylibs_output_path = os.path.join(config.REPO_OUTPUT_DIR, 'dylibs.json')
    output_json = {
        "name": config.REPO_NAME,
        "identifier": config.SOURCE_IDENTIFIER,
        "dylibs": final_dylibs,
        "generated_at": gen_time,
        "total": len(final_dylibs)
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
