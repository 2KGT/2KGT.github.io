# .github/scripts/core/sileo_engine.py
import os
import json
import subprocess
import bz2
from collections import defaultdict
import sys
import hashlib
import re
import urllib.request
import logging
import logger

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from . import utils

def calculate_hashes_from_url(url):
    """Tải tạm file Cloud và tính các loại hash để xác thực"""
    try:
        temp_path = "temp_hash.deb"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response, open(temp_path, 'wb') as f:
            f.write(response.read())
            
        with open(temp_path, "rb") as f:
            data = f.read()
            md5 = hashlib.md5(data).hexdigest()
            sha1 = hashlib.sha1(data).hexdigest()
            sha256 = hashlib.sha256(data).hexdigest()
        
        if os.path.exists(temp_path): 
            os.remove(temp_path)
        return md5, sha1, sha256
    except Exception as e:
        print(f"⚠️ Lỗi tính hash file cloud: {e}")
        return "0"*32, "0"*40, "0"*64

def extract_deb_control_data(path):
    """Sử dụng dpkg-deb để bốc thông tin trực tiếp từ control của file .deb (Có chống nghẽn Timeout)"""
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
        msg_err = f"⚠️ Treo quá lâu khi đọc: {f_name} (Đã bỏ qua)"
        print(msg_err)
        logger.log_step(current_step="sileo", status="running", live_log=msg_err)
    except Exception as e:
        print(f"❌ Lỗi đọc file .deb bằng dpkg-deb: {e}")
        
    if not info.get("Package"): 
        info["Package"] = f"com.kyic.{f_name.split('_')[0].lower()}"
    if not info.get("Name"): 
        info["Name"] = f_name.split('_')[0]
    
    if "Section" in info and info["Section"]:
        clean_section = info["Section"].strip().capitalize()
        if clean_section.lower() in ["tweak", "tweaks", "patched"]: clean_section = "Tweaks"
        elif clean_section.lower() in ["theme", "themes"]: clean_section = "Themes"
        elif clean_section.lower() in ["addon", "addons"]: clean_section = "Addons"
        elif clean_section.lower() in ["system", "utilities"]: clean_section = "System"
        info["Section"] = clean_section
    else:
        info["Section"] = "Tweaks"
        
    return info

def clean_string_for_match(text):
    if not text:
        return ""
    return re.sub(r'[^a-z0-9]', '', text.lower())

def get_tweak_assets(tweak_name, deb_info):
    exts = ['.png', '.jpg', '.jpeg', '.webp']
    match_variants = [
        clean_string_for_match(tweak_name),
        clean_string_for_match(deb_info.get("Package", "")),
        clean_string_for_match(deb_info.get("Package", "").split('.')[-1])
    ]
    base_variant = match_variants[0] or "default"
    
    local_icons = os.listdir(config.ICON_DIR) if os.path.exists(config.ICON_DIR) else []
    local_images = os.listdir(config.IMG_DIR) if os.path.exists(config.IMG_DIR) else []
    
    def build_asset_url(dir_name, file_name):
        base = config.RAW_URL.rstrip('/')
        sub_dir = dir_name.strip('/')
        return f"{base}/{sub_dir}/{file_name}"

    icon_url, banner_url, video_url, screens = None, None, None, []

    remote_icon = deb_info.get('Icon') or deb_info.get('icon')
    if remote_icon and str(remote_icon).startswith("http"):
        logger.log_step(current_step="sileo", status="running", live_log=f"📥 Đang tải tài nguyên -> {tweak_name}_icon.jpg")
        if utils.download_resource_to_local(remote_icon, os.path.join(config.ICON_DIR, f"{base_variant}.jpg")):
            icon_url = build_asset_url(config.ICON_DIR_NAME, f"{base_variant}.jpg")

    remote_banner = deb_info.get('Banner') or deb_info.get('banner')
    if remote_banner and str(remote_banner).startswith("http"):
        logger.log_step(current_step="sileo", status="running", live_log=f"📥 Đang tải tài nguyên -> {tweak_name}_banner.jpg")
        if utils.download_resource_to_local(remote_banner, os.path.join(config.IMG_DIR, f"{base_variant}_banner.jpg")):
            banner_url = build_asset_url(config.IMG_DIR_NAME, f"{base_variant}_banner.jpg")

    remote_video = deb_info.get('Video') or deb_info.get('video')
    if remote_video and str(remote_video).startswith("http"):
        if utils.download_resource_to_local(remote_video, os.path.join(config.IMG_DIR, f"{base_variant}.mp4")):
            video_url = build_asset_url(config.IMG_DIR_NAME, f"{base_variant}.mp4")

    raw_screens_data = deb_info.get('Screenshots') or deb_info.get('screenshots') or deb_info.get('Screenshot') or deb_info.get('screenshot')
    if raw_screens_data:
        urls_list = []
        if isinstance(raw_screens_data, list): urls_list = raw_screens_data
        elif isinstance(raw_screens_data, str):
            if raw_screens_data.startswith('[') and raw_screens_data.endswith(']'):
                try: urls_list = json.loads(raw_screens_data)
                except: urls_list = [u.strip() for u in raw_screens_data.strip('[]').split(',') if u]
            else: urls_list = [u.strip() for u in raw_screens_data.split(',') if u]
        
        idx = 1
        for scr_url in urls_list:
            if str(scr_url).startswith("http"):
                logger.log_step(current_step="sileo", status="running", live_log=f"📥 Đang tải tài nguyên -> {tweak_name}_screen_{idx}.jpg")
                if utils.download_resource_to_local(scr_url, os.path.join(config.IMG_DIR, f"{base_variant}_{idx}.jpg")):
                    screens.append(build_asset_url(config.IMG_DIR_NAME, f"{base_variant}_{idx}.jpg"))
                    idx += 1

    if not icon_url:
        for variant in match_variants:
            if not variant: continue
            matched = next((f for f in local_icons if clean_string_for_match(f.rsplit('.', 1)[0]) == variant and any(f.lower().endswith(e) for e in exts)), None)
            if matched:
                icon_url = build_asset_url(config.ICON_DIR_NAME, matched)
                break

    if not banner_url:
        for variant in match_variants:
            if not variant: continue
            matched = next((f for f in local_images if clean_string_for_match(f.rsplit('.', 1)[0]) in [f"{variant}banner", f"{variant}_banner"] and any(f.lower().endswith(e) for e in exts)), None)
            if matched:
                banner_url = build_asset_url(config.IMG_DIR_NAME, matched)
                break

    if not video_url:
        for variant in match_variants:
            if not variant: continue
            matched = next((f for f in local_images if clean_string_for_match(f) == f"{variant}.mp4"), None)
            if matched:
                video_url = build_asset_url(config.IMG_DIR_NAME, matched)
                break

    if not screens:
        for i in range(1, 16):
            matched = next((f for f in local_images if clean_string_for_match(f.rsplit('.', 1)[0]) in [f"{base_variant}_{i}", f"{base_variant}{i}"] and any(f.lower().endswith(e) for e in exts)), None)
            if matched: screens.append(build_asset_url(config.IMG_DIR_NAME, matched))

    # Gán tài nguyên fallback chuẩn xác 100% theo cấu trúc cục bộ mới
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
    target_folder = config.DEPICTION_DIR
    os.makedirs(target_folder, exist_ok=True)
    file_path = os.path.join(target_folder, f"{safe_filename}.json")
    
    privacy_text = ", ".join(privacy_list) if privacy_list else "Không yêu cầu quyền đặc biệt"
    clean_desc = utils.smart_truncate_description(description, max_chars=1000)
    
    sileo_screenshots = []
    for idx, s in enumerate(assets["screenshots"]):
        if s:
            sileo_screenshots.append({
                "accessibilityText": f"Screenshot{idx}",
                "url": str(s)
            })

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
                    {"class": "DepictionTableTextView", "title": f"Version {version}", "text": "Cập nhật mới nhất"},
                    {"class": "DepictionMarkdownView", "markdown": f"- Đồng bộ hóa thành công phiên bản v{version} lên hệ thống Kyic Premium Store.\n- Tối ưu hóa cấu trúc dữ liệu phẳng đám mây kết hợp local."}
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

    with open(file_path, 'w', encoding='utf-8') as f: 
        json.dump(depiction_data, f, indent=2, ensure_ascii=False)

def run_sileo_engine(release_assets, system_db):
    # 🌟 An toàn: Đảm bảo trường khóa "tweaks" luôn được định hình sẵn trong cache DB phòng lỗi KeyError
    if "tweaks" not in system_db: 
        system_db["tweaks"] = {}
        
    tweaks_map = defaultdict(list)
    processed_safenames = set()
    processed_tweaks_titles = []

    # Xử lý Cloud
    deb_cloud_list = release_assets if isinstance(release_assets, list) else []
    for asset in deb_cloud_list:
        f_name = asset.get("name", "")
        f_url = asset.get("url", "")
        sz = asset.get("size", 0)
        if not f_name.endswith(".deb"): continue
        safe_filename = f_name.rsplit('.', 1)[0]
        processed_safenames.add(safe_filename)
        
        parts = safe_filename.split('_')
        tweak_title = parts[0] if len(parts) > 0 else safe_filename
        ver = parts[1] if len(parts) > 1 else "1.0"
        arch = parts[2] if len(parts) > 2 else "iphoneos-arm"
        bid = f"com.kyic.{clean_string_for_match(tweak_title)}"
        
        print(f"-> Đang quét Cloud Tweak: {tweak_title}", flush=True)
        processed_tweaks_titles.append(tweak_title)
        
        md5, sha1, sha256 = calculate_hashes_from_url(f_url)
        
        deb_info = {"Package": bid, "Name": tweak_title, "Version": ver, "Description": f"Tweak {tweak_title} từ Kyic Store.", "Author": "Kyic Store", "Section": "Tweaks", "Architecture": arch}
        system_db["tweaks"][f_url] = deb_info
        assets = get_tweak_assets(tweak_title, deb_info)
        build_sileo_depiction_json(safe_filename, tweak_title, ver, deb_info["Description"], assets, deb_info["Author"], deb_info, [])
        tweaks_map[(bid, arch)].append({"name": tweak_title, "ver": str(ver), "bid": bid, "arch": arch, "dl": f_url, "sz": sz, "desc": deb_info["Description"], "author": deb_info["Author"], "icon": assets["icon"], "safe_file": safe_filename, "section": deb_info["Section"], "is_cloud": True, "md5": md5, "sha1": sha1, "sha256": sha256})

    # Xử lý Local
    if os.path.exists(config.DEBS_INPUT_DIR):
        for root, dirs, files in os.walk(config.DEBS_INPUT_DIR):
            for f_name in files:
                if f_name.endswith(".deb"):
                    safe_filename = f_name.rsplit('.', 1)[0]
                    if safe_filename in processed_safenames: continue
                    path = os.path.join(root, f_name)
                    
                    with open(path, "rb") as f_deb:
                        bytes_data = f_deb.read()
                        md5 = hashlib.md5(bytes_data).hexdigest()
                        sha1 = hashlib.sha1(bytes_data).hexdigest()
                        sha256 = hashlib.sha256(bytes_data).hexdigest()
                        
                    relative_path = os.path.relpath(path, config.REPO_OUTPUT_DIR).replace("\\", "/")
                    f_url = f"{config.BASE_URL}{relative_path}"
                    deb_info = extract_deb_control_data(path)
                    
                    print(f"-> Đang quét Local Tweak: {deb_info['Name']}", flush=True)
                    processed_tweaks_titles.append(deb_info['Name'])
                    
                    system_db["tweaks"][f_url] = deb_info
                    
                    assets = get_tweak_assets(deb_info["Name"], deb_info)
                    build_sileo_depiction_json(safe_filename, deb_info["Name"], deb_info["Version"], deb_info["Description"], assets, deb_info["Author"], deb_info, utils.format_permissions(deb_info.get('Permissions', {})))
                    
                    tweaks_map[(deb_info["Package"], deb_info["Architecture"])].append({"name": deb_info["Name"], "ver": deb_info["Version"], "bid": deb_info["Package"], "arch": deb_info["Architecture"], "dl": relative_path, "sz": int(os.path.getsize(path)), "desc": deb_info["Description"], "author": deb_info["Author"], "icon": assets["icon"], "safe_file": safe_filename, "section": deb_info["Section"], "is_cloud": False, "md5": md5, "sha1": sha1, "sha256": sha256})

    # Đồng bộ đầu ra Packages
    final_packages = ""
    for key in sorted(tweaks_map.keys()):
        for v_item in tweaks_map[key]:
            clean_dir_url = config.DEPICTION_DIR_NAME.replace("repo/", "").strip("/")
            json_depiction_url = f"{config.BASE_URL}{clean_dir_url}/{v_item['safe_file']}.json"
            
            final_packages += f"Package: {v_item['bid']}\nName: {v_item['name']}\nVersion: {v_item['ver']}\nArchitecture: {v_item['arch']}\nFilename: {v_item['dl']}\nSize: {v_item['sz']}\nMD5sum: {v_item['md5']}\nSHA1: {v_item['sha1']}\nSHA256: {v_item['sha256']}\nAuthor: {v_item['author']}\nDescription: {v_item['desc']}\nSection: {v_item['section']}\nIcon: {v_item['icon']}\nSileoDepiction: {json_depiction_url}\n\n"

    with open(os.path.join(config.REPO_OUTPUT_DIR, "Packages"), "w", encoding="utf-8") as f: f.write(final_packages)
    try:
        with open(os.path.join(config.REPO_OUTPUT_DIR, "Packages"), 'rb') as f_in:
            with bz2.BZ2File(os.path.join(config.REPO_OUTPUT_DIR, "Packages.bz2"), 'wb') as f_out: f_out.write(f_in.read())
    except: pass

    return processed_tweaks_titles
