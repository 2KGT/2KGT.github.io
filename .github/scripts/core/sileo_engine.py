# .github/scripts/core/sileo_engine.py
import os
import json
import subprocess
import bz2
import sys
import hashlib
import re
import urllib.request
import logging
import tempfile
import datetime
import inspect
import config

logger = logging.getLogger(__name__)
from collections import defaultdict
from . import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─────────────────────────────────────────────────────────
# FIX 1: Dùng tempfile thay vì tên cố định
# Tránh xung đột khi chạy song song
# FIX 2: Tính hash bằng streaming — không đọc toàn bộ vào RAM
# ─────────────────────────────────────────────────────────
def calculate_hashes_from_url(url):
    """Tải tạm file Cloud và tính các loại hash để xác thực"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        md5 = hashlib.md5()
        sha1 = hashlib.sha1()
        sha256 = hashlib.sha256()

        with tempfile.NamedTemporaryFile(suffix=".deb", delete=False) as tmp:
            temp_path = tmp.name
            with urllib.request.urlopen(req, timeout=30) as response:
                while True:
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    tmp.write(chunk)
                    md5.update(chunk)
                    sha1.update(chunk)
                    sha256.update(chunk)

        os.remove(temp_path)
        return md5.hexdigest(), sha1.hexdigest(), sha256.hexdigest()

    except Exception as e:
        logger.error(f"⚠️ Lỗi tính hash file cloud [{url}]: {e}")
        return "0" * 32, "0" * 40, "0" * 64


def calculate_hashes_from_local(path):
    """
    FIX 2: Tính hash file local bằng streaming
    Tránh đọc toàn bộ file .deb lớn vào RAM một lần
    """
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
        logger.error(f"⚠️ Lỗi tính hash file local [{path}]: {e}")
        return "0" * 32, "0" * 40, "0" * 64
    return md5.hexdigest(), sha1.hexdigest(), sha256.hexdigest()


def extract_deb_control_data(path):
    """Sử dụng dpkg-deb để bốc thông tin trực tiếp từ control của file .deb"""
    info = {
        "Package": "",
        "Name": "",
        "Version": "1.0",
        "Description": "Một tweak tuyệt vời từ Kyic Store.",
        "Author": "Kyic Store",
        "Section": "Tweaks",
        "Architecture": "iphoneos-arm"
    }

    f_name = os.path.basename(path)
    try:
        result = subprocess.run(
            ['dpkg-deb', '-f', path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors='ignore',
            timeout=5
        )
        if result.returncode == 0 and result.stdout:
            current_key = None
            for line in result.stdout.split('\n'):
                if not line.strip():
                    continue
                if line.startswith(' ') or line.startswith('\t'):
                    if current_key and current_key in info:
                        info[current_key] += "\n" + line.strip()
                elif ':' in line:
                    k, v = line.split(':', 1)
                    current_key = k.strip()
                    info[current_key] = v.strip()
    except subprocess.TimeoutExpired:
        logger.warning(f"⚠️ Treo quá lâu khi đọc: {f_name} (Đã bỏ qua)")
    except Exception as e:
        logger.error(f"❌ Lỗi đọc file .deb bằng dpkg-deb: {e}")

    if not info.get("Package"):
        info["Package"] = f"com.kyic.{f_name.split('_')[0].lower()}"
    if not info.get("Name"):
        info["Name"] = f_name.split('_')[0]

    # Chuẩn hóa Section
    section_map = {
        "tweak": "Tweaks", "tweaks": "Tweaks", "patched": "Tweaks",
        "theme": "Themes", "themes": "Themes",
        "addon": "Addons", "addons": "Addons",
        "system": "System", "utilities": "System"
    }
    raw_section = info.get("Section", "").strip().lower()
    info["Section"] = section_map.get(raw_section, info.get("Section", "Tweaks").strip().capitalize()) or "Tweaks"

    return info


def clean_string_for_match(text):
    if not text:
        return ""
    return re.sub(r'[^a-z0-9]', '', text.lower())


def extract_tweak_name_from_filename(filename):
    """
    FIX: Extract tên tweak từ filename (dùng làm fallback khi DEB nằm
    trực tiếp trong repo/debs/ mà không có folder riêng - cấu trúc cũ).

    Ví dụ:
    - cc18_0.0.3_iphoneos-arm.deb → cc18
    - ccappicon_0.0.1_iphoneos-arm64.deb → ccappicon
    """
    name_no_ext = filename.rsplit('.', 1)[0]
    tweak_name = name_no_ext.split('_')[0]
    return tweak_name if tweak_name else name_no_ext


def get_tweak_assets(tweak_name, deb_info):
    """
    FIX: Ảnh (banner/video/screenshots) lấy TRỰC TIẾP từ control field
    bên trong file .deb (Icon/Banner/Video/Screenshots) — KHÔNG tra
    AppStore, vì DEB là tweak/bẻ khoá, không tồn tại trên AppStore.

    Ảnh tải về được gom theo thư mục tên tweak để quản lý tập trung:
    Cấu trúc: repo/depictions/images/<tweak_name>/
        - <tweak_name>_banner.jpg
        - <tweak_name>.mp4
        - <tweak_name>_1.jpg, <tweak_name>_2.jpg, ...

    Icon vẫn giữ chung trong repo/depictions/icons/ (icon thường dùng lại
    nhiều nơi — ví dụ icon hiển thị trên Packages, không cần tách folder).
    """
    exts = ['.png', '.jpg', '.jpeg', '.webp']
    match_variants = [
        clean_string_for_match(tweak_name),
        clean_string_for_match(deb_info.get("Package", "")),
        clean_string_for_match(deb_info.get("Package", "").split('.')[-1])
    ]
    base_variant = match_variants[0] or "default"

    def build_icon_url(file_name):
        return f"{config.RAW_URL.rstrip('/')}/{config.ICON_DIR_NAME.strip('/')}/{file_name}"

    def build_image_url(file_name):
        # FIX: ảnh gom theo thư mục tweak_name — nhất quán với cách tổ chức DEB/desc
        return f"{config.RAW_URL.rstrip('/')}/{config.IMG_DIR_NAME.strip('/')}/{tweak_name}/{file_name}"

    # FIX 3: Quét thư mục một lần, dùng lại cho toàn bộ hàm (không gọi os.listdir lặp lại)
    local_icons = os.listdir(config.ICON_DIR) if os.path.exists(config.ICON_DIR) else []
    tweak_img_dir = config.get_tweak_images_dir(tweak_name)
    local_images = os.listdir(tweak_img_dir) if os.path.exists(tweak_img_dir) else []

    icon_url, banner_url, video_url, screens = None, None, None, []

    # ── Ưu tiên tài nguyên khai báo trực tiếp trong control field của .deb ──
    remote_icon = deb_info.get('Icon') or deb_info.get('icon')
    if remote_icon and str(remote_icon).startswith("http"):
        logger.info(f"📥 Đang tải Icon của {tweak_name} (từ control .deb)")
        if utils.download_resource_to_local(remote_icon, os.path.join(config.ICON_DIR, f"{base_variant}.jpg")):
            icon_url = build_icon_url(f"{base_variant}.jpg")

    remote_banner = deb_info.get('Banner') or deb_info.get('banner')
    if remote_banner and str(remote_banner).startswith("http"):
        logger.info(f"📥 Đang tải Banner của {tweak_name} (từ control .deb)")
        os.makedirs(tweak_img_dir, exist_ok=True)
        if utils.download_resource_to_local(remote_banner, os.path.join(tweak_img_dir, f"{base_variant}_banner.jpg")):
            banner_url = build_image_url(f"{base_variant}_banner.jpg")

    remote_video = deb_info.get('Video') or deb_info.get('video')
    if remote_video and str(remote_video).startswith("http"):
        logger.info(f"📥 Đang tải Video của {tweak_name} (từ control .deb)")
        os.makedirs(tweak_img_dir, exist_ok=True)
        if utils.download_resource_to_local(remote_video, os.path.join(tweak_img_dir, f"{base_variant}.mp4")):
            video_url = build_image_url(f"{base_variant}.mp4")

    # Xử lý Screenshots khai báo trong control field (list hoặc chuỗi JSON/CSV)
    raw_screens_data = (
        deb_info.get('Screenshots') or deb_info.get('screenshots')
        or deb_info.get('Screenshot') or deb_info.get('screenshot')
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

        os.makedirs(tweak_img_dir, exist_ok=True)
        for idx, scr_url in enumerate(urls_list, start=1):
            if str(scr_url).startswith("http"):
                logger.info(f"📥 Đang tải Screenshot {idx} của {tweak_name} (từ control .deb)")
                if utils.download_resource_to_local(scr_url, os.path.join(tweak_img_dir, f"{base_variant}_{idx}.jpg")):
                    screens.append(build_image_url(f"{base_variant}_{idx}.jpg"))

    # ── Fallback: tìm trong thư mục local đã tải/upload sẵn ──
    if not icon_url:
        for variant in match_variants:
            if not variant:
                continue
            matched = next(
                (f for f in local_icons
                 if clean_string_for_match(f.rsplit('.', 1)[0]) == variant
                 and any(f.lower().endswith(e) for e in exts)),
                None
            )
            if matched:
                icon_url = build_icon_url(matched)
                break

    if not banner_url:
        for variant in match_variants:
            if not variant:
                continue
            matched = next(
                (f for f in local_images
                 if clean_string_for_match(f.rsplit('.', 1)[0]) in [f"{variant}banner", f"{variant}_banner"]
                 and any(f.lower().endswith(e) for e in exts)),
                None
            )
            if matched:
                banner_url = build_image_url(matched)
                break

    if not video_url:
        for variant in match_variants:
            if not variant:
                continue
            matched = next(
                (f for f in local_images
                 if clean_string_for_match(f) == f"{variant}.mp4"),
                None
            )
            if matched:
                video_url = build_image_url(matched)
                break

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

    # Gán tài nguyên mặc định khi không tìm được gì
    if not icon_url: icon_url = config.SOURCE_LOGO
    if not banner_url: banner_url = config.DEFAULT_BANNER
    if not video_url: video_url = config.DEFAULT_VIDEO
    if not screens: screens = utils.get_default_screens()

    return {
        "icon": utils.clean_github_url(icon_url),
        "banner": utils.clean_github_url(banner_url),
        "video": utils.clean_github_url(video_url),
        "screenshots": [utils.clean_github_url(s) for s in screens if s]
    }


def build_sileo_depiction_json(safe_filename, tweak_name, version, description, assets, author, deb_info, privacy_list):
    """
    FIX: Tên file JSON = safe_filename đầy đủ (tweak_ver_arch), KHÔNG dùng
    chung 1 file cho mọi version/arch — tránh xung đột đè dữ liệu khi:
    - Nhiều version cùng tồn tại (v1.3.0, v1.3.1...)
    - Nhiều architecture của cùng version (arm, arm64, arm64e)

    Cấu trúc: repo/depictions/metadata/<section>/<tweak_name>/<safe_filename>.json
    Ví dụ:    repo/depictions/metadata/tweaks/glow/glow_1.3.1_iphoneos-arm.json

    FIX: Mô tả ưu tiên lấy từ changelog (v<version>.txt / default.txt) tại
    repo/depictions/metadata/desc/tweaks/<tweak_name>/ — giống cơ chế IPA.
    """
    section = deb_info.get("Section", "Tweaks")

    optimized_desc = config.get_optimized_tweak_description(tweak_name, version)
    final_description = optimized_desc if optimized_desc else description

    # FIX: Lấy lịch sử changelog NHIỀU phiên bản thật (đọc từ v*.txt) —
    # giống tinh thần "Version History" của Feather, thay vì text cứng.
    changelog_markdown = config.get_tweak_changelog_history(tweak_name, version)

    target_folder, json_filename = config.get_depiction_path_by_filename(section, tweak_name, safe_filename)
    os.makedirs(target_folder, exist_ok=True)
    file_path = os.path.join(target_folder, json_filename)

    privacy_text = ", ".join(privacy_list) if privacy_list else "Không yêu cầu quyền đặc biệt"
    clean_desc = utils.smart_truncate_description(final_description, max_chars=1000)

    sileo_screenshots = [
        {"accessibilityText": f"Screenshot{idx}", "url": str(s)}
        for idx, s in enumerate(assets["screenshots"]) if s
    ]

    depiction_data = {
        "minVersion": "0.1",
        "headerImage": assets["banner"],
        "class": "DepictionTabView",
        "tintColor": "#F77686",
        "tabs": [
            {
                "class": "DepictionStackView",
                "tabname": "Details",
                "views": [
                    {"class": "DepictionSubheaderView", "useBottomMargin": False, "title": str(tweak_name), "useBoldText": True},
                    {"class": "DepictionMarkdownView", "useSpacing": True, "markdown": clean_desc},
                    {"class": "DepictionSpacerView", "spacing": 8},
                    {"class": "DepictionScreenshotsView", "screenshots": sileo_screenshots, "itemSize": "{160, 275.41333333333336}", "itemCornerRadius": 6},
                    {"class": "DepictionSeparatorView"},
                    {"class": "DepictionSpacerView", "spacing": 8},
                    {"class": "DepictionTableTextView", "title": "Developer", "text": str(author)},
                    {"class": "DepictionTableTextView", "title": "Yêu cầu quyền", "text": privacy_text},
                    {"class": "DepictionSpacerView", "spacing": 8}
                ]
            },
            {
                "class": "DepictionStackView",
                "tabname": "Changelog",
                "views": [
                    {"class": "DepictionTableTextView", "title": f"Version {version}", "text": "Lịch sử cập nhật"},
                    {"class": "DepictionMarkdownView", "useSpacing": True, "markdown": changelog_markdown}
                ]
            },
            {
                "class": "DepictionStackView",
                "tabname": "Support",
                "views": [
                    {"class": "DepictionSubheaderView", "title": "KÊNH HỖ TRỢ CHÍNH THỨC", "useBoldText": True},
                    {"class": "DepictionTableButtonView", "title": "📢 Telegram Channel", "action": "https://t.me/+uhoygGN-1Gc4NzZl"},
                    {"class": "DepictionTableButtonView", "title": "💬 Telegram Group", "action": "https://t.me/kyicchat"},
                    {"class": "DepictionTableButtonView", "title": "🎮 Discord Server", "action": "https://discord.gg/qUXBQFYa"},
                    {"class": "DepictionSeparatorView"},
                    {"class": "DepictionTableButtonView", "title": "☕ Ủng hộ qua PayPal", "action": "https://www.paypal.me/225668"}
                ]
            }
        ]
    }

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(depiction_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"❌ Lỗi ghi depiction JSON cho {safe_filename}: {e}")
        return None

    return file_path


def run_sileo_engine(release_assets, system_db):
    """🌟 PHÂN HỆ XỬ LÝ CHÍNH: Phân tích các gói Tweaks DEB và biên dịch kho dữ liệu Packages cho Sileo"""
    if "tweaks" not in system_db:
        system_db["tweaks"] = {}

    tweaks_map = defaultdict(list)
    processed_safenames = set()
    processed_tweaks_titles = []

    # ── Xử lý Cloud .deb ──────────────────────────────────────────
    deb_cloud_list = release_assets if isinstance(release_assets, list) else []
    for asset in deb_cloud_list:
        f_name = asset.get("name", "")
        f_url = asset.get("url", "")
        sz = asset.get("size", 0)
        if not f_name.endswith(".deb"):
            continue

        safe_filename = f_name.rsplit('.', 1)[0]
        if safe_filename in processed_safenames:
            continue
        processed_safenames.add(safe_filename)

        parts = safe_filename.split('_')
        tweak_title = parts[0] if parts else safe_filename
        ver = parts[1] if len(parts) > 1 else "1.0"
        arch = parts[2] if len(parts) > 2 else "iphoneos-arm"

        # FIX 4: Tải và đọc control data thực tế từ cloud .deb
        # thay vì tự đặt bid/info từ tên file
        logger.info(f"-> Đang quét Cloud Tweak: {tweak_title} [{arch}]")
        processed_tweaks_titles.append(tweak_title)

        # FIX MỚI: Lấy Release Note (body) từ GitHub Release — tương tự Feather
        # Lưu vào v{version}.txt để `get_optimized_tweak_description()` dùng
        release_note = asset.get("body", "")
        if release_note and len(release_note.strip()) > 10:
            tweak_desc_dir = os.path.join(config.TWEAK_DESC_DIR, tweak_title)
            os.makedirs(tweak_desc_dir, exist_ok=True)
            version_file = os.path.join(tweak_desc_dir, f"v{ver}.txt")
            try:
                with open(version_file, 'w', encoding='utf-8') as f:
                    f.write(release_note.strip())
                logger.info(f"💾 Lưu changelog: {version_file}")
            except Exception as e:
                logger.warning(f"⚠️ Không lưu changelog cho {tweak_title} v{ver}: {e}")

        md5, sha1, sha256 = calculate_hashes_from_url(f_url)

        deb_info = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".deb", delete=False) as tmp:
                temp_deb_path = tmp.name
            req = urllib.request.Request(f_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                with open(temp_deb_path, 'wb') as f:
                    f.write(response.read())
            deb_info = extract_deb_control_data(temp_deb_path)
            os.remove(temp_deb_path)
        except Exception as e:
            logger.warning(f"⚠️ Không đọc được control từ cloud .deb [{tweak_title}]: {e}")

        if not deb_info:
            bid = f"com.kyic.{clean_string_for_match(tweak_title)}"
            deb_info = {
                "Package": bid, "Name": tweak_title, "Version": ver,
                "Description": f"Tweak {tweak_title} từ Kyic Store.",
                "Author": "Kyic Store", "Section": "Tweaks", "Architecture": arch
            }

        system_db["tweaks"][f_url] = deb_info
        assets = get_tweak_assets(tweak_title, deb_info)
        build_sileo_depiction_json(
            safe_filename, tweak_title, deb_info["Version"],
            deb_info["Description"], assets, deb_info["Author"], deb_info,
            utils.format_permissions(deb_info.get('Permissions', {}))
        )
        tweaks_map[(deb_info["Package"], deb_info["Architecture"], deb_info["Version"])].append({
            "name": deb_info["Name"], "ver": deb_info["Version"],
            "bid": deb_info["Package"], "arch": deb_info["Architecture"],
            "dl": f_url, "sz": sz, "desc": deb_info["Description"],
            "author": deb_info["Author"], "icon": assets["icon"],
            "tweak_name": tweak_title, "safe_file": safe_filename,
            "section": deb_info["Section"], "is_cloud": True,
            "md5": md5, "sha1": sha1, "sha256": sha256
        })

    # ── Xử lý Local .deb (NESTED: repo/debs/<TweakName>/*.deb) ─────
    # FIX: Gom tất cả architecture (arm/arm64/arm64e) + version của
    # cùng 1 tweak vào folder riêng, thay vì để phẳng cùng cấp.
    if os.path.exists(config.DEBS_INPUT_DIR):
        for entry in sorted(os.listdir(config.DEBS_INPUT_DIR)):
            if entry.startswith('.') or entry == 'desc':
                continue

            entry_path = os.path.join(config.DEBS_INPUT_DIR, entry)
            deb_files = []

            # Backward-compat: vẫn hỗ trợ file .deb nằm trực tiếp (cấu trúc cũ)
            if os.path.isfile(entry_path) and entry.endswith(".deb"):
                deb_files.append((entry_path, entry, extract_tweak_name_from_filename(entry)))
            elif os.path.isdir(entry_path):
                # entry chính là tên tweak (tên folder) — ưu tiên dùng tên folder
                for f_name in sorted(os.listdir(entry_path)):
                    if f_name.endswith(".deb"):
                        deb_files.append((os.path.join(entry_path, f_name), f_name, entry))

            for path, f_name, tweak_title in deb_files:
                safe_filename = f_name.rsplit('.', 1)[0]
                if safe_filename in processed_safenames:
                    continue
                processed_safenames.add(safe_filename)

                # FIX 2: Hash streaming thay vì đọc toàn bộ vào RAM
                md5, sha1, sha256 = calculate_hashes_from_local(path)

                relative_path = os.path.relpath(path, config.REPO_OUTPUT_DIR).replace("\\", "/")
                f_url = f"{config.BASE_URL}{relative_path}"
                deb_info = extract_deb_control_data(path)

                logger.info(f"-> Đang quét Local Tweak: {deb_info['Name']} [{tweak_title}/{deb_info['Architecture']}/v{deb_info['Version']}]")
                processed_tweaks_titles.append(deb_info['Name'])

                system_db["tweaks"][f_url] = deb_info
                assets = get_tweak_assets(tweak_title, deb_info)
                build_sileo_depiction_json(
                    safe_filename, tweak_title, deb_info["Version"],
                    deb_info["Description"], assets, deb_info["Author"], deb_info,
                    utils.format_permissions(deb_info.get('Permissions', {}))
                )
                tweaks_map[(deb_info["Package"], deb_info["Architecture"], deb_info["Version"])].append({
                    "name": deb_info["Name"], "ver": deb_info["Version"],
                    "bid": deb_info["Package"], "arch": deb_info["Architecture"],
                    "dl": relative_path, "sz": int(os.path.getsize(path)),
                    "desc": deb_info["Description"], "author": deb_info["Author"],
                    "icon": assets["icon"], "tweak_name": tweak_title,
                    "safe_file": safe_filename, "section": deb_info["Section"],
                    "is_cloud": False, "md5": md5, "sha1": sha1, "sha256": sha256
                })

    # ── Ghi Packages ────────────────────────────────────────────
    # FIX QUAN TRỌNG: Chuẩn APT/Packages CHỈ cho phép 1 entry duy nhất
    # mỗi (Package, Architecture). Nếu admin để nhiều version cùng tồn
    # tại trong repo/debs/<TweakName>/ (ví dụ v1.3.0 và v1.3.1 cùng arm),
    # Packages chỉ liệt kê bản MỚI NHẤT — tránh vi phạm chuẩn APT khiến
    # Sileo xử lý không xác định (có thể chọn nhầm bản, hoặc lỗi).
    #
    # Các version cũ hơn vẫn giữ nguyên trên đĩa (.deb + JSON depiction
    # riêng tại metadata/tweaks/<TweakName>/<tweak_ver_arch>.json) để
    # tham khảo/tải thủ công, chỉ không được advertise lại trong Packages.
    latest_per_arch = {}
    for key in tweaks_map.keys():
        bid, arch, ver = key
        arch_key = (bid, arch)
        if arch_key not in latest_per_arch or utils.parse_version_tuple(ver) > utils.parse_version_tuple(latest_per_arch[arch_key]):
            latest_per_arch[arch_key] = ver

    final_packages = ""
    section_map = {
        "Tweaks": "tweaks", "Themes": "themes", "Addons": "addons",
        "System": "system", "Tools": "tools"
    }
    metadata_url_base = config.DEPICTION_DIR_NAME.replace("repo/", "").strip("/")

    for key in sorted(tweaks_map.keys()):
        bid, arch, ver = key
        # Bỏ qua version không phải bản mới nhất của (Package, Architecture) này
        if ver != latest_per_arch.get((bid, arch)):
            logger.info(f"⏭️  Bỏ qua v{ver} của {bid} [{arch}] trong Packages (đã có bản mới hơn {latest_per_arch.get((bid, arch))})")
            continue

        for v_item in tweaks_map[key]:
            # FIX: URL depiction JSON trỏ đúng file riêng theo tweak_ver_arch
            # (không bao giờ 2 entry khác version/arch trỏ chung 1 JSON)
            subdir = section_map.get(v_item["section"], "tweaks")
            json_depiction_url = (
                f"{config.BASE_URL}{metadata_url_base}/{subdir}/"
                f"{v_item['tweak_name']}/{v_item['safe_file']}.json"
            )
            final_packages += (
                f"Package: {v_item['bid']}\n"
                f"Name: {v_item['name']}\n"
                f"Version: {v_item['ver']}\n"
                f"Architecture: {v_item['arch']}\n"
                f"Filename: {v_item['dl']}\n"
                f"Size: {v_item['sz']}\n"
                f"MD5sum: {v_item['md5']}\n"
                f"SHA1: {v_item['sha1']}\n"
                f"SHA256: {v_item['sha256']}\n"
                f"Author: {v_item['author']}\n"
                f"Description: {v_item['desc']}\n"
                f"Section: {v_item['section']}\n"
                f"Icon: {v_item['icon']}\n"
                f"SileoDepiction: {json_depiction_url}\n\n"
            )

    packages_path = os.path.join(config.REPO_OUTPUT_DIR, "Packages")
    with open(packages_path, "w", encoding="utf-8") as f:
        f.write(final_packages)

    # FIX 5: Không nuốt lỗi bz2
    try:
        with open(packages_path, 'rb') as f_in:
            with bz2.BZ2File(os.path.join(config.REPO_OUTPUT_DIR, "Packages.bz2"), 'wb') as f_out:
                f_out.write(f_in.read())
    except Exception as e:
        logger.error(f"❌ Lỗi nén Packages.bz2: {e}")
    
    # Logic tạo tạo file ⁠sileo.json
    # 1. Tạo danh sách tweak cho sileo.json
    sileo_data = []
    for key in sorted(tweaks_map.keys()):
        bid, arch, ver = key
        # Chỉ lấy bản mới nhất để hiển thị
        if ver == latest_per_arch.get((bid, arch)):
            v_item = tweaks_map[key][0]
            sileo_data.append({
                "name": v_item["name"],
                "bundle": v_item["bid"],
                "version": v_item["ver"],
                "section": v_item["section"],
                "author": v_item["author"],
                "icon": v_item["icon"],
                "size": v_item["sz"],
                "downloadURL": v_item['dl'],
            })

    # 2. Đóng gói vào biến output_json
    output_json = {
        "tweaks": sileo_data,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    # 3. Ghi file JSON (nằm ngoài vòng lặp và trước lệnh return)
    json_output_path = os.path.join(config.REPO_OUTPUT_DIR, 'sileo.json')
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(output_json, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ Đã tạo sileo.json tại: {json_output_path}")

    return processed_tweaks_titles

    

