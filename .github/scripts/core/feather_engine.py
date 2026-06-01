# .github/scripts/feather_engine.py
import os
import json
import re
import zipfile
import plistlib
import urllib.request
from datetime import datetime
from collections import defaultdict
import sys
import logger

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from . import utils

def extract_ipa_permissions_and_data(path):
    version, bid, min_os, build_ver = "1.0", "com.kyic.unknown", "12.0", "1"
    permissions = {} 
    try:
        with zipfile.ZipFile(path, 'r') as z:
            plist_path = next((f for f in z.namelist() if re.match(r'^Payload/[^/]+\.app/Info\.plist$', f)), None)
            if plist_path:
                with z.open(plist_path) as f:
                    plist = plistlib.load(f)
                    version = plist.get('CFBundleShortVersionString') or plist.get('CFBundleVersion', '1.0')
                    build_ver = plist.get('CFBundleVersion') or "1"
                    bid = plist.get('CFBundleIdentifier', 'com.kyic.app')
                    min_os = plist.get('MinimumOSVersion') or "12.0"
                    for plist_key, display_name in config.PERM_MAPPING.items():
                        if plist_key in plist:
                            reason = plist.get(plist_key) or f"Ứng dụng yêu cầu quyền truy cập {display_name}."
                            permissions[display_name] = str(reason)
    except: pass
    return str(version), str(bid), permissions, str(min_os), str(build_ver)

def get_itunes_info(bundle_id):
    mapping_table = {"com.kyic.youtube": "com.google.ios.youtube", "com.kyic.tiktok": "com.zhiliaoapp.musically", "com.kyic.facebook": "com.facebook.Facebook", "com.spotify.client": "com.spotify.client"}
    target_id = mapping_table.get(bundle_id.lower(), bundle_id)
    try:
        url = f"https://itunes.apple.com/lookup?bundleId={target_id}&country=VN&lang=vi_vn"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data['resultCount'] > 0:
                res = data['results'][0]
                raw_screens = res.get('screenshotUrls', []) or res.get('ipadScreenshotUrls', [])
                clean_screens = list(set([re.sub(r'\.(png|webp|gif|jpg|jpeg)[^/]*$', '.jpg', u) for u in raw_screens if u]))
                raw_icon = res.get('artworkUrl512') or res.get('artworkUrl100')
                clean_icon = re.sub(r'\.(png|webp|gif|jpg|jpeg)[^/]*$', '.jpg', raw_icon) if raw_icon else None
                return {"icon": clean_icon, "banner": clean_screens[0] if clean_screens else None, "screenshots": clean_screens, "desc": res.get('description', ""), "privacy_url": res.get('privacyPolicyUrl'), "is_store": True}
    except: pass
    return None

def get_local_assets_ipa(name):
    exts = ['.png', '.jpg', '.jpeg', '.webp']
    
    def build_asset_url(dir_name, file_name):
        base = config.RAW_URL.rstrip('/')
        sub_dir = dir_name.strip('/')
        return f"{base}/{sub_dir}/{file_name}"

    icon_url = next((build_asset_url(config.ICON_DIR_NAME, f"{name}{e}") for e in exts if os.path.exists(os.path.join(config.ICON_DIR, f"{name}{e}"))), None)
    banner_url = next((build_asset_url(config.IMG_DIR_NAME, f"{name}_banner{e}") for e in exts if os.path.exists(os.path.join(config.IMG_DIR, f"{name}_banner{e}"))), None)
    video_url = build_asset_url(config.IMG_DIR_NAME, f"{name}.mp4") if os.path.exists(os.path.join(config.IMG_DIR, f"{name}.mp4")) else None
    
    screens = []
    for i in range(1, 15):
        for e in exts:
            if os.path.exists(os.path.join(config.IMG_DIR, f"{name}_{i}{e}")):
                screens.append(build_asset_url(config.IMG_DIR_NAME, f"{name}_{i}{e}"))
                break
            elif os.path.exists(os.path.join(config.IMG_DIR, f"{name}{i}{e}")):
                screens.append(build_asset_url(config.IMG_DIR_NAME, f"{name}{i}{e}"))
                break
    return {"icon": icon_url, "banner": banner_url, "screenshots": screens, "video": video_url}

def run_feather_engine(release_assets, system_db):
    print("▶️ Khởi chạy Feather Engine (Kiến trúc gói core/)...")
    apps_map = defaultdict(list)
    default_screens = utils.get_default_screens()

    def build_asset_url(dir_name, file_name):
        base = config.RAW_URL.rstrip('/')
        sub_dir = dir_name.strip('/')
        return f"{base}/{sub_dir}/{file_name}"

    if os.path.exists(config.APPS_INPUT_DIR):
        for f_name in os.listdir(config.APPS_INPUT_DIR):
            if f_name.endswith(".ipa"):
                path = os.path.join(config.APPS_INPUT_DIR, f_name)
                f_url = f"{config.BASE_URL}apps/{f_name}"
                clean_name = f_name.rsplit('.', 1)[0].split('_', 1)[0]
                
                if f_url in system_db["apps"] and isinstance(system_db["apps"][f_url], dict):
                    cache = system_db["apps"][f_url]
                    bid, ver = cache.get('bid'), cache.get('ver')
                    min_os, build_ver = cache.get('minOS', '12.0'), cache.get('buildVersion', '1')
                else:
                    ver, bid, perms, min_os, build_ver = extract_ipa_permissions_and_data(path)
                    local = get_local_assets_ipa(clean_name)
                    info = get_itunes_info(bid)
                    
                    icon = local['icon']
                    if not icon and info and info['icon']:
                        if utils.download_resource_to_local(info['icon'], os.path.join(config.ICON_DIR, f"{clean_name}.jpg")):
                            icon = build_asset_url(config.ICON_DIR_NAME, f"{clean_name}.jpg")
                    if not icon: icon = config.SOURCE_LOGO

                    banner = local['banner']
                    if not banner and info and info['banner']:
                        if utils.download_resource_to_local(info['banner'], os.path.join(config.IMG_DIR, f"{clean_name}_banner.jpg")):
                            banner = build_asset_url(config.IMG_DIR_NAME, f"{clean_name}_banner.jpg")
                    if not banner: banner = config.DEFAULT_BANNER

                    screens = local['screenshots']
                    if not screens and info and info['screenshots']:
                        downloaded_screens = []
                        for idx, scr_url in enumerate(info['screenshots']):
                            if utils.download_resource_to_local(scr_url, os.path.join(config.IMG_DIR, f"{clean_name}_{idx+1}.jpg")):
                                downloaded_screens.append(build_asset_url(config.IMG_DIR_NAME, f"{clean_name}_{idx+1}.jpg"))
                        if downloaded_screens: screens = downloaded_screens
                    if not screens: screens = default_screens

                    video = local['video'] if local['video'] else config.DEFAULT_VIDEO
                    desc = info['desc'] if info else f"Ứng dụng {clean_name} từ Kyic Store."
                    system_db["apps"][f_url] = {"bid": str(bid), "ver": str(ver), "name": clean_name, "icon": icon, "banner": banner, "screenshots": screens, "video": video, "desc": desc, "permissions": perms, "minOS": min_os, "buildVersion": build_ver}

                apps_map[bid].append({"name": clean_name, "ver": str(ver), "bid": str(bid), "dl": f_url, "sz": int(os.path.getsize(path)), "date": "Local", "minOS": min_os, "buildVersion": build_ver})

    for asset in release_assets:
        f_name = asset["name"]
        if f_name.endswith(".ipa"):
            f_url = asset["url"]
            clean_name = f_name.rsplit('.', 1)[0].split('_', 1)[0]

            if f_url in system_db["apps"] and isinstance(system_db["apps"][f_url], dict):
                cache = system_db["apps"][f_url]
                bid, ver = cache.get('bid'), cache.get('ver')
                min_os, build_ver = cache.get('minOS', '12.0'), cache.get('buildVersion', '1')
            else:
                temp_path = os.path.join(config.REPO_ROOT, f"temp_{f_name}")
                try:
                    urllib.request.urlretrieve(f_url, temp_path)
                    ver, bid, perms, min_os, build_ver = extract_ipa_permissions_and_data(temp_path)
                except Exception as e:
                    print(f"⚠️ Lỗi phân tích Cloud {f_name}: {e}")
                    continue
                finally:
                    if os.path.exists(temp_path): os.remove(temp_path)

                local = get_local_assets_ipa(clean_name)
                info = get_itunes_info(bid)
                
                icon = local['icon']
                if not icon and info and info['icon']:
                    if utils.download_resource_to_local(info['icon'], os.path.join(config.ICON_DIR, f"{clean_name}.jpg")):
                        icon = build_asset_url(config.ICON_DIR_NAME, f"{clean_name}.jpg")
                if not icon: icon = config.SOURCE_LOGO

                banner = local['banner']
                if not banner and info and info['banner']:
                    if utils.download_resource_to_local(info['banner'], os.path.join(config.IMG_DIR, f"{clean_name}_banner.jpg")):
                        banner = build_asset_url(config.IMG_DIR_NAME, f"{clean_name}_banner.jpg")
                if not banner: banner = config.DEFAULT_BANNER

                screens = local['screenshots']
                if not screens and info and info['screenshots']:
                    downloaded_screens = []
                    for idx, scr_url in enumerate(info['screenshots']):
                        if utils.download_resource_to_local(scr_url, os.path.join(config.IMG_DIR, f"{clean_name}_{idx+1}.jpg")):
                            downloaded_screens.append(build_asset_url(config.IMG_DIR_NAME, f"{clean_name}_{idx+1}.jpg"))
                    if downloaded_screens: screens = downloaded_screens
                if not screens: screens = default_screens

                video = local['video'] if local['video'] else config.DEFAULT_VIDEO
                desc = info['desc'] if info else f"Ứng dụng {clean_name} từ Kyic Store."
                system_db["apps"][f_url] = {"bid": str(bid), "ver": str(ver), "name": clean_name, "icon": icon, "banner": banner, "screenshots": screens, "video": video, "desc": desc, "permissions": perms, "minOS": min_os, "buildVersion": build_ver}

            if not any(x['dl'] == f_url for x in apps_map[bid]):
                apps_map[bid].append({"name": clean_name, "ver": str(ver), "bid": str(bid), "dl": f_url, "sz": asset["size"], "date": asset["date"], "minOS": min_os, "buildVersion": build_ver})

    final_apps = []
    featured_bids = []
    sorted_bids = sorted(apps_map.keys(), key=lambda b: apps_map[b][0]['name'].lower())
    
    for bid in sorted_bids:
        featured_bids.append(str(bid))
        versions = apps_map[bid]
        versions.sort(key=lambda x: str(x['ver']), reverse=True) 
        latest = versions[0]
        matched_data = next((v for k, v in system_db["apps"].items() if v.get('bid') == bid), {})
        
        date_str = latest['date'] if latest['date'] != "Local" else datetime.utcnow().isoformat() + "Z"
        raw_scr_urls = [utils.clean_github_url(s) for s in matched_data.get('screenshots', default_screens) if s]
        
        formatted_versions = []
        for v in versions:
            v_date = str(v['date'] if v['date'] != "Local" else date_str)
            if "T" in v_date: v_date = v_date.split("T")[0]
            formatted_versions.append({
                "version": str(v['ver']), "date": v_date, "size": int(v['sz']), "downloadURL": str(v['dl']),
                "localizedDescription": f"Cập nhật phiên bản Premium v{v['ver']}."
            })
        
        feather_perms = utils.format_permissions(matched_data.get('permissions', {}))
        
        app_item = {
            "name": str(latest['name']), "bundleIdentifier": str(bid), "developerName": "Kyic Store", "subtitle": "Phiên bản Premium", 
            "localizedDescription": utils.smart_truncate_description(matched_data.get('desc', "")), 
            "iconURL": utils.clean_github_url(matched_data.get('icon', config.SOURCE_LOGO)), "tintColor": "848ef9",
            "version": str(latest['ver']), "versionDate": date_str, "size": int(latest['sz']), "downloadURL": str(latest['dl']),
            "versions": formatted_versions, "screenshotURLs": raw_scr_urls, "videoURL": utils.clean_github_url(matched_data.get('video', config.DEFAULT_VIDEO)),
            "appPermissions": feather_perms
        }
        final_apps.append(app_item)

    first_app_id = featured_bids[0] if featured_bids else config.SOURCE_IDENTIFIER
    final_news = [
        {"title": "Donate", "identifier": "feather-donate", "caption": "Nếu bạn yêu thích kho ứng dụng Kyic Premium Store, hãy quyên góp ủng hộ cho chúng tôi!", "date": "2026-05-19", "tintColor": "848ef9", "imageURL": utils.clean_github_url(config.NEWS_DONATE_IMAGE), "notify": False, "url": "https://www.paypal.me/225668", "appIdentifier": str(first_app_id)},
        {"title": "About", "identifier": "feather-about", "caption": "Chào mừng bạn đến với Kyic Premium Store!", "date": "2026-05-19", "tintColor": "8A28F7", "imageURL": utils.clean_github_url(config.NEWS_ABOUT_IMAGE), "notify": True, "url": "https://github.com/2KGT/repo/blob/main/README.md", "appIdentifier": str(first_app_id)}
    ]

    output_json = {"name": config.REPO_NAME, "identifier": config.SOURCE_IDENTIFIER, "iconURL": utils.clean_github_url(config.SOURCE_LOGO), "apps": final_apps, "news": final_news}
    with open(os.path.join(config.REPO_OUTPUT_DIR, 'apps.json'), 'w', encoding='utf-8') as f: 
        json.dump(output_json, f, indent=2, ensure_ascii=False)
    print("✅ Đã xuất tệp apps.json cấu trúc phẳng thành công!")

