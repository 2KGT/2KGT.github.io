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
import config

logger = logging.getLogger(__name__)
from collections import defaultdict
from . import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def calculate_hashes_from_url(url):
    """Tải tạm file cloud, tính MD5/SHA1/SHA256 bằng streaming."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        md5, sha1, sha256 = hashlib.md5(), hashlib.sha1(), hashlib.sha256()
        with tempfile.NamedTemporaryFile(suffix=".deb", delete=False) as tmp:
            temp_path = tmp.name
            with urllib.request.urlopen(req, timeout=30) as resp:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    tmp.write(chunk)
                    md5.update(chunk); sha1.update(chunk); sha256.update(chunk)
        os.remove(temp_path)
        return md5.hexdigest(), sha1.hexdigest(), sha256.hexdigest()
    except Exception as e:
        logger.error(f"⚠️ Lỗi tính hash cloud [{url}]: {e}")
        return "0" * 32, "0" * 40, "0" * 64


def calculate_hashes_from_local(path):
    """Tính MD5/SHA1/SHA256 file local bằng streaming."""
    md5, sha1, sha256 = hashlib.md5(), hashlib.sha1(), hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                md5.update(chunk); sha1.update(chunk); sha256.update(chunk)
    except Exception as e:
        logger.error(f"⚠️ Lỗi tính hash local [{path}]: {e}")
        return "0" * 32, "0" * 40, "0" * 64
    return md5.hexdigest(), sha1.hexdigest(), sha256.hexdigest()


def extract_deb_control_data(path):
    """Đọc control fields từ file .deb bằng dpkg-deb."""
    info = {
        "Package": "", "Name": "", "Version": "1.0",
        "Description": "Một tweak tuyệt vời từ Kyic Store.",
        "Author": "Kyic Store", "Section": "Tweaks", "Architecture": "iphoneos-arm"
    }
    f_name = os.path.basename(path)
    try:
        result = subprocess.run(
            ['dpkg-deb', '-f', path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, errors='ignore', timeout=5
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
        logger.warning(f"⚠️ Timeout khi đọc: {f_name}")
    except Exception as e:
        logger.error(f"❌ Lỗi đọc .deb: {e}")

    if not info.get("Package"):
        info["Package"] = f"com.kyic.{f_name.split('_')[0].lower()}"
    if not info.get("Name"):
        info["Name"] = f_name.split('_')[0]

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
    """Lấy tên tweak từ filename: cc18_0.0.3_iphoneos-arm.deb → cc18."""
    name_no_ext = filename.rsplit('.', 1)[0]
    tweak_name = name_no_ext.split('_')[0]
    return tweak_name if tweak_name else name_no_ext


def resolve_display_name(deb_info, fallback_id):
    """
    Ưu tiên field Name từ control file. Bỏ qua nếu Name trùng với bundle ID
    (com.x.y) — fallback về đoạn cuối bundle ID, viết hoa chữ đầu.
    """
    def _is_bundle_id(s):
        return bool(re.match(r'^[a-z0-9]+(\.[a-z0-9]+){2,}$', s.strip()))

    name = (deb_info or {}).get("Name", "")
    name = name.strip() if isinstance(name, str) else ""
    if name and not _is_bundle_id(name):
        return name

    base = fallback_id.strip().split('.')[-1] if fallback_id else fallback_id
    base = base or fallback_id or "tweak"
    return base[:1].upper() + base[1:] if base else base


def _save_desc_file(path, content):
    """Ghi file text, tạo thư mục nếu cần. Trả về True nếu thành công."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.warning(f"⚠️ Không ghi được {path}: {e}")
        return False


def _read_file(path):
    """Đọc file text, trả về chuỗi hoặc rỗng nếu lỗi."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return ""


def get_tweak_assets(tweak_name, deb_info):
    """Lấy icon/banner/video/screenshots từ control field, fallback local, fallback default."""
    exts = ['.png', '.jpg', '.jpeg', '.webp']
    match_variants = [
        clean_string_for_match(tweak_name),
        clean_string_for_match(deb_info.get("Package", "")),
        clean_string_for_match(deb_info.get("Package", "").split('.')[-1])
    ]
    base_variant = match_variants[0] or "default"

    def icon_url(fname):
        return f"{config.RAW_URL.rstrip('/')}/{config.ICON_DIR_NAME.strip('/')}/{fname}"

    def image_url(fname):
        return f"{config.RAW_URL.rstrip('/')}/{config.IMG_DIR_NAME.strip('/')}/{tweak_name}/{fname}"

    local_icons = os.listdir(config.ICON_DIR) if os.path.exists(config.ICON_DIR) else []
    tweak_img_dir = config.get_tweak_images_dir(tweak_name)
    local_images = os.listdir(tweak_img_dir) if os.path.exists(tweak_img_dir) else []

    icon, banner, video, screens = None, None, None, []

    # Từ control field
    remote_icon = deb_info.get('Icon') or deb_info.get('icon')
    if remote_icon and str(remote_icon).startswith("http"):
        if utils.download_resource_to_local(remote_icon, os.path.join(config.ICON_DIR, f"{base_variant}.jpg")):
            icon = icon_url(f"{base_variant}.jpg")

    remote_banner = deb_info.get('Banner') or deb_info.get('banner')
    if remote_banner and str(remote_banner).startswith("http"):
        os.makedirs(tweak_img_dir, exist_ok=True)
        if utils.download_resource_to_local(remote_banner, os.path.join(tweak_img_dir, f"{base_variant}_banner.jpg")):
            banner = image_url(f"{base_variant}_banner.jpg")

    remote_video = deb_info.get('Video') or deb_info.get('video')
    if remote_video and str(remote_video).startswith("http"):
        os.makedirs(tweak_img_dir, exist_ok=True)
        if utils.download_resource_to_local(remote_video, os.path.join(tweak_img_dir, f"{base_variant}.mp4")):
            video = image_url(f"{base_variant}.mp4")

    raw_screens = (
        deb_info.get('Screenshots') or deb_info.get('screenshots')
        or deb_info.get('Screenshot') or deb_info.get('screenshot')
    )
    if raw_screens:
        urls_list = []
        if isinstance(raw_screens, list):
            urls_list = raw_screens
        elif isinstance(raw_screens, str):
            if raw_screens.startswith('['):
                try:
                    urls_list = json.loads(raw_screens)
                except Exception:
                    urls_list = [u.strip() for u in raw_screens.strip('[]').split(',') if u]
            else:
                urls_list = [u.strip() for u in raw_screens.split(',') if u]
        os.makedirs(tweak_img_dir, exist_ok=True)
        for idx, scr in enumerate(urls_list, start=1):
            if str(scr).startswith("http"):
                if utils.download_resource_to_local(scr, os.path.join(tweak_img_dir, f"{base_variant}_{idx}.jpg")):
                    screens.append(image_url(f"{base_variant}_{idx}.jpg"))

    # Fallback local
    if not icon:
        for v in match_variants:
            if not v:
                continue
            m = next((f for f in local_icons if clean_string_for_match(f.rsplit('.', 1)[0]) == v and any(f.lower().endswith(e) for e in exts)), None)
            if m:
                icon = icon_url(m); break

    if not banner:
        for v in match_variants:
            if not v:
                continue
            m = next((f for f in local_images if clean_string_for_match(f.rsplit('.', 1)[0]) in [f"{v}banner", f"{v}_banner"] and any(f.lower().endswith(e) for e in exts)), None)
            if m:
                banner = image_url(m); break

    if not video:
        for v in match_variants:
            if not v:
                continue
            m = next((f for f in local_images if clean_string_for_match(f) == f"{v}.mp4"), None)
            if m:
                video = image_url(m); break

    if not screens:
        for i in range(1, 16):
            m = next((f for f in local_images if clean_string_for_match(f.rsplit('.', 1)[0]) in [f"{base_variant}_{i}", f"{base_variant}{i}"] and any(f.lower().endswith(e) for e in exts)), None)
            if m:
                screens.append(image_url(m))

    if not icon: icon = config.SOURCE_LOGO
    if not banner: banner = config.DEFAULT_BANNER
    if not video: video = config.DEFAULT_VIDEO
    if not screens: screens = utils.get_default_screens()

    return {
        "icon": utils.clean_github_url(icon),
        "banner": utils.clean_github_url(banner),
        "video": utils.clean_github_url(video),
        "screenshots": [utils.clean_github_url(s) for s in screens if s]
    }


def build_sileo_depiction_json(safe_filename, tweak_name, version, description, assets, author, deb_info, privacy_list):
    """Tạo file depiction JSON cho Sileo (1 file riêng mỗi version+arch)."""
    section = deb_info.get("Section", "Tweaks")

    # Mô tả sản phẩm: từ control file, fallback default.txt
    default_file = os.path.join(config.TWEAK_DESC_DIR, tweak_name, "default.txt")
    if description and len(str(description).strip()) > 5:
        final_description = description.strip()
    elif os.path.exists(default_file):
        final_description = _read_file(default_file) or description
    else:
        final_description = description

    # Lịch sử phiên bản: từ v*.txt (release notes)
    changelog_markdown = config.get_tweak_changelog_history(tweak_name, version)

    target_folder, json_filename = config.get_depiction_path_by_filename(section, tweak_name, safe_filename)
    os.makedirs(target_folder, exist_ok=True)
    file_path = os.path.join(target_folder, json_filename)

    privacy_text = ", ".join(privacy_list) if privacy_list else "Không yêu cầu quyền đặc biệt"
    clean_desc = utils.smart_truncate_description(final_description, max_chars=1000)
    sileo_screenshots = [{"accessibilityText": f"Screenshot{i}", "url": str(s)} for i, s in enumerate(assets["screenshots"]) if s]

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
        logger.error(f"❌ Lỗi ghi depiction {safe_filename}: {e}")
        return None

    return file_path


def _save_desc_for_tweak(tweak_title, deb_info, ver, release_note=""):
    """
    Lưu 2 file mô tả cho tweak:
    - default.txt : mô tả sản phẩm từ control file (chỉ ghi lần đầu)
    - v{ver}.txt  : release note phiên bản từ GitHub Release body
    """
    desc_dir = os.path.join(config.TWEAK_DESC_DIR, tweak_title)
    control_desc = deb_info.get("Description", "").strip()

    default_file = os.path.join(desc_dir, "default.txt")
    if control_desc and len(control_desc) > 5 and not os.path.exists(default_file):
        if _save_desc_file(default_file, control_desc):
            logger.info(f"💾 Lưu mô tả sản phẩm: {default_file}")

    if release_note and len(release_note) > 10:
        ver_file = os.path.join(desc_dir, f"v{ver}.txt")
        if _save_desc_file(ver_file, release_note):
            logger.info(f"💾 Lưu changelog: {ver_file}")


def run_sileo_engine(release_assets, system_db):
    """Xử lý .deb cloud + local, tạo Packages, Packages.bz2 và sileo.json."""
    if "tweaks" not in system_db:
        system_db["tweaks"] = {}

    tweaks_map = defaultdict(list)
    processed_safenames = set()
    processed_tweaks_titles = []

    # ── Cloud .deb ────────────────────────────────────────────────────
    for asset in (release_assets if isinstance(release_assets, list) else []):
        f_name = asset.get("name", "")
        f_url  = asset.get("url", "")
        sz     = asset.get("size", 0)
        if not f_name.endswith(".deb") or not f_url:
            continue

        safe_filename = f_name.rsplit('.', 1)[0]
        if safe_filename in processed_safenames:
            continue
        processed_safenames.add(safe_filename)

        parts  = safe_filename.split('_')
        raw_id = parts[0] if parts else safe_filename
        ver    = parts[1] if len(parts) > 1 else "1.0"
        arch   = parts[2] if len(parts) > 2 else "iphoneos-arm"

        logger.info(f"-> Cloud Tweak: {raw_id} [{arch}]")
        md5, sha1, sha256 = calculate_hashes_from_url(f_url)

        deb_info = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".deb", delete=False) as tmp:
                temp_path = tmp.name
            req = urllib.request.Request(f_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                with open(temp_path, 'wb') as f:
                    f.write(resp.read())
            deb_info = extract_deb_control_data(temp_path)
            os.remove(temp_path)
        except Exception as e:
            logger.warning(f"⚠️ Không đọc được control [{raw_id}]: {e}")

        if not deb_info:
            deb_info = {
                "Package": f"com.kyic.{clean_string_for_match(raw_id)}",
                "Name": raw_id, "Version": ver,
                "Description": f"Tweak {raw_id} từ Kyic Store.",
                "Author": "Kyic Store", "Section": "Tweaks", "Architecture": arch
            }

        tweak_title = resolve_display_name(deb_info, raw_id)
        processed_tweaks_titles.append(tweak_title)

        release_note = asset.get("body", "").strip()
        _save_desc_for_tweak(tweak_title, deb_info, ver, release_note)

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
            "dl": f_url, "sz": sz,
            "desc": deb_info["Description"],
            "release_note": release_note,
            "author": deb_info["Author"], "icon": assets["icon"],
            "tweak_name": tweak_title, "safe_file": safe_filename,
            "section": deb_info["Section"], "is_cloud": True,
            "md5": md5, "sha1": sha1, "sha256": sha256
        })

    # ── Local .deb ────────────────────────────────────────────────────
    if os.path.exists(config.DEBS_INPUT_DIR):
        for entry in sorted(os.listdir(config.DEBS_INPUT_DIR)):
            if entry.startswith('.') or entry == 'desc':
                continue
            entry_path = os.path.join(config.DEBS_INPUT_DIR, entry)
            deb_files = []

            if os.path.isfile(entry_path) and entry.endswith(".deb"):
                deb_files.append((entry_path, entry, extract_tweak_name_from_filename(entry)))
            elif os.path.isdir(entry_path):
                for f_name in sorted(os.listdir(entry_path)):
                    if f_name.endswith(".deb"):
                        deb_files.append((os.path.join(entry_path, f_name), f_name, entry))

            for path, f_name, tweak_title in deb_files:
                safe_filename = f_name.rsplit('.', 1)[0]
                if safe_filename in processed_safenames:
                    continue
                processed_safenames.add(safe_filename)

                md5, sha1, sha256 = calculate_hashes_from_local(path)
                relative_path = os.path.relpath(path, config.REPO_OUTPUT_DIR).replace("\\", "/")
                f_url = f"{config.BASE_URL}{relative_path}"
                deb_info = extract_deb_control_data(path)

                if tweak_title == extract_tweak_name_from_filename(f_name):
                    tweak_title = resolve_display_name(deb_info, tweak_title)

                logger.info(f"-> Local Tweak: {deb_info['Name']} [{tweak_title}/{deb_info['Architecture']}/v{deb_info['Version']}]")
                processed_tweaks_titles.append(deb_info['Name'])

                # Release note cho local: đọc từ v{ver}.txt nếu đã lưu trước
                local_release_note = _read_file(os.path.join(config.TWEAK_DESC_DIR, tweak_title, f"v{deb_info['Version']}.txt"))
                _save_desc_for_tweak(tweak_title, deb_info, deb_info['Version'])

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
                    "desc": deb_info["Description"],
                    "release_note": local_release_note,
                    "author": deb_info["Author"], "icon": assets["icon"],
                    "tweak_name": tweak_title, "safe_file": safe_filename,
                    "section": deb_info["Section"], "is_cloud": False,
                    "md5": md5, "sha1": sha1, "sha256": sha256
                })

    # ── Packages ──────────────────────────────────────────────────────
    # Mỗi (Package, Architecture) chỉ quảng bá bản mới nhất trong Packages.
    latest_per_arch = {}
    for bid, arch, ver in tweaks_map.keys():
        arch_key = (bid, arch)
        if arch_key not in latest_per_arch or utils.parse_version_tuple(ver) > utils.parse_version_tuple(latest_per_arch[arch_key]):
            latest_per_arch[arch_key] = ver

    section_map = {
        "Tweaks": "tweaks", "Themes": "themes", "Addons": "addons",
        "System": "system", "Tools": "tools"
    }
    metadata_url_base = config.DEPICTION_DIR_NAME.replace("repo/", "").strip("/")
    final_packages = ""

    for key in sorted(tweaks_map.keys()):
        bid, arch, ver = key
        if ver != latest_per_arch.get((bid, arch)):
            logger.info(f"⏭️  Bỏ qua {bid} v{ver} [{arch}] (có bản mới hơn)")
            continue
        for v in tweaks_map[key]:
            subdir = section_map.get(v["section"], "tweaks")
            depiction_url = f"{config.BASE_URL}{metadata_url_base}/{subdir}/{v['tweak_name']}/{v['safe_file']}.json"
            final_packages += (
                f"Package: {v['bid']}\nName: {v['name']}\nVersion: {v['ver']}\n"
                f"Architecture: {v['arch']}\nFilename: {v['dl']}\nSize: {v['sz']}\n"
                f"MD5sum: {v['md5']}\nSHA1: {v['sha1']}\nSHA256: {v['sha256']}\n"
                f"Author: {v['author']}\nDescription: {v['desc']}\n"
                f"Section: {v['section']}\nIcon: {v['icon']}\n"
                f"SileoDepiction: {depiction_url}\n\n"
            )

    packages_path = os.path.join(config.REPO_OUTPUT_DIR, "Packages")
    with open(packages_path, "w", encoding="utf-8") as f:
        f.write(final_packages)

    try:
        with open(packages_path, 'rb') as f_in:
            with bz2.BZ2File(os.path.join(config.REPO_OUTPUT_DIR, "Packages.bz2"), 'wb') as f_out:
                f_out.write(f_in.read())
    except Exception as e:
        logger.error(f"❌ Lỗi nén Packages.bz2: {e}")

    # ── sileo.json ────────────────────────────────────────────────────
    # Gom tất cả phiên bản theo bundle ID, không lọc bỏ bản cũ
    sileo_tweaks_by_bundle = {}

    for key in sorted(tweaks_map.keys(), key=lambda k: utils.parse_version_tuple(k[2])):
        bid, arch, ver = key
        for v in tweaks_map[key]:
            tweak_title = v["tweak_name"]

            # Khởi tạo entry lần đầu gặp bundle này
            if bid not in sileo_tweaks_by_bundle:
                product_description = v["desc"]
                default_file = os.path.join(config.TWEAK_DESC_DIR, tweak_title, "default.txt")
                if (not product_description or len(str(product_description).strip()) <= 5) and os.path.exists(default_file):
                    product_description = _read_file(default_file) or product_description

                sileo_tweaks_by_bundle[bid] = {
                    "name": v["name"],
                    "bundle": bid,
                    "version": v["ver"],        # sẽ được cập nhật lên bản mới nhất bên dưới
                    "section": v["section"],
                    "author": v["author"],
                    "icon": v["icon"],
                    "size": v["sz"],
                    "downloadURL": v["dl"],
                    "description": product_description,
                    "tweak_name": tweak_title,
                    "versions": []
                }

            entry = sileo_tweaks_by_bundle[bid]

            # Thêm phiên bản này vào danh sách versions (tránh trùng)
            existing_vers = {vv["version"] for vv in entry["versions"]}
            if ver not in existing_vers:
                release_note = config.get_tweak_changelog_history(tweak_title, ver, limit=1)
                entry["versions"].append({
                    "version": ver,
                    "downloadURL": v["dl"],
                    "size": v["sz"],
                    "architecture": arch,
                    "md5": v["md5"],
                    "sha1": v["sha1"],
                    "sha256": v["sha256"],
                    "releaseNote": release_note
                })

            # Cập nhật fields chính lên bản mới nhất
            latest_ver = latest_per_arch.get((bid, arch))
            if ver == latest_ver:
                entry["version"]     = ver
                entry["downloadURL"] = v["dl"]
                entry["size"]        = v["sz"]
                entry["icon"]        = v["icon"]

    # Sort versions giảm dần (mới nhất trên đầu) cho từng bundle
    for entry in sileo_tweaks_by_bundle.values():
        entry["versions"].sort(
            key=lambda vv: utils.parse_version_tuple(vv["version"]),
            reverse=True
        )
        # Gắn changelog đầy đủ dựa trên toàn bộ danh sách phiên bản đã có
        tweak_title = entry["tweak_name"]
        latest = entry["versions"][0]["version"] if entry["versions"] else entry["version"]
        entry["changelog"] = config.get_tweak_changelog_history(tweak_title, latest, limit=50)

    sileo_data = sorted(sileo_tweaks_by_bundle.values(), key=lambda x: x["name"])
    output_json = {
        "tweaks": sileo_data,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    json_output_path = os.path.join(config.REPO_OUTPUT_DIR, 'sileo.json')
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(output_json, f, indent=2, ensure_ascii=False)

    logger.info(f"✅ sileo.json: {len(sileo_data)} tweaks → {json_output_path}")
    return processed_tweaks_titles
