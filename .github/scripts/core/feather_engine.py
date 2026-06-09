# .github/scripts/core/feather_engine.py
import os
import json
import re
import zipfile
import plistlib
import urllib.request
import urllib.parse
import datetime
from collections import defaultdict
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from . import utils

def extract_ipa_permissions_and_data(path):
    """Giải nén tệp IPA tạm thời để bốc tách Info.plist lấy thông tin quyền hạn và Bundle ID"""
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
    """Tra cứu dữ liệu ứng dụng trên App Store Việt Nam theo Bundle ID"""
    if not bundle_id or bundle_id == "com.kyic.unknown": return None
    url = f"https://itunes.apple.com/lookup?bundleId={bundle_id}&country=VN&entity=software&lang=vi_vn"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
            if data.get('resultCount', 0) > 0:
                res = data['results'][0]
                return {
                    "icon": res.get('artworkUrl512'),
                    "banner": res.get('screenshotUrls', [None])[0],
                    "screenshots": res.get('screenshotUrls', []),
                    "desc": res.get('description', "")
                }
    except: pass
    return None

def get_local_assets_ipa(name):
    """Quét và lấy liên kết tài nguyên ảnh cục bộ trong kho bãi nếu có sẵn"""
    exts = ['.png', '.jpg', '.jpeg', '.webp']
    def build_asset_url(dir_name, file_name):
        return f"{config.RAW_URL.rstrip('/')}/{dir_name.strip('/')}/{file_name}"
    
    icon_url = next((build_asset_url(config.ICON_DIR_NAME, f"{name}{e}") for e in exts if os.path.exists(os.path.join(config.ICON_DIR, f"{name}{e}"))), None)
    banner_url = next((build_asset_url(config.IMG_DIR_NAME, f"{name}_banner{e}") for e in exts if os.path.exists(os.path.join(config.IMG_DIR, f"{name}_banner{e}"))), None)
    
    screens = []
    i = 1
    while True:
        found = False
        for e in exts:
            file_path = os.path.join(config.IMG_DIR, f"{name}_{i}{e}")
            if os.path.exists(file_path):
                screens.append(build_asset_url(config.IMG_DIR_NAME, f"{name}_{i}{e}"))
                found = True
                break
        if not found: break
        i += 1
    return {"icon": icon_url, "banner": banner_url, "screenshots": screens}

def run_feather_engine(release_assets, feather_db):
    """🌟 PHÂN HỆ XỬ LÝ CHÍNH: Quét tài nguyên IPA và đóng gói cấu trúc Feather JSON"""
    if "apps" not in feather_db: feather_db["apps"] = {}
    apps_map = defaultdict(list)
    def build_asset_url(dir_name, file_name): return f"{config.RAW_URL.rstrip('/')}/{dir_name.strip('/')}/{file_name}"

    to_process = []
    processed_names = []
    
    if os.path.exists(config.APPS_INPUT_DIR):
        for f in os.listdir(config.APPS_INPUT_DIR):
            if f.endswith(".ipa"):
                to_process.append({"name": f, "url": f"{config.BASE_URL}apps/{f}", "path": os.path.join(config.APPS_INPUT_DIR, f), "is_cloud": False})
    for asset in release_assets:
        if asset["name"].endswith(".ipa"):
            to_process.append({"name": asset["name"], "url": asset["url"], "is_cloud": True, "size": asset["size"], "date": asset["date"]})

    for item in to_process:
        f_name, f_url = item["name"], item["url"]
        clean_name = f_name.rsplit('.', 1)[0].split('_', 1)[0]
        curr_size = item.get("size") if item.get("is_cloud") else os.path.getsize(item["path"])
        
        print(f"-> Đang xử lý IPA: {f_name}", flush=True)
        processed_names.append(clean_name)
        
        # Đọc dữ liệu từ bộ nhớ đệm cache nếu tệp không có sự thay đổi dung lượng
        if f_url in feather_db["apps"] and feather_db["apps"][f_url].get("size") == curr_size:
            data = feather_db["apps"][f_url]
            bid, ver, min_os, build_ver = data['bid'], data['ver'], data['minOS'], data['buildVersion']
            perms = data.get('permissions', {})
        else:
            if item["is_cloud"]:
                temp_path = os.path.join(config.REPO_ROOT, f"temp_{f_name}")
                print(f"📸 Đang tải và phân tích cấu trúc IPA từ đám mây: {clean_name}", flush=True)
                urllib.request.urlretrieve(f_url, temp_path)
                ver, bid, perms, min_os, build_ver = extract_ipa_permissions_and_data(temp_path)
                try: os.remove(temp_path)
                except: pass
            else:
                ver, bid, perms, min_os, build_ver = extract_ipa_permissions_and_data(item["path"])
            
            info = get_itunes_info(bid)
            local = get_local_assets_ipa(clean_name)
            
            # Đồng bộ cấu hình Icon đại diện
            icon = local['icon']
            if not icon and info and info.get('icon'):
                path = os.path.join(config.ICON_DIR, f"{clean_name}.jpg")
                if utils.download_resource_to_local(info['icon'], path): icon = build_asset_url(config.ICON_DIR_NAME, f"{clean_name}.jpg")
            if not icon: icon = config.SOURCE_LOGO
            
            # Đồng bộ cấu hình Banner nền quảng bá
            banner = local['banner']
            if not banner and info and info.get('banner'):
                path = os.path.join(config.IMG_DIR, f"{clean_name}_banner.jpg")
                if utils.download_resource_to_local(info['banner'], path): banner = build_asset_url(config.IMG_DIR_NAME, f"{clean_name}_banner.jpg")
            if not banner: banner = config.DEFAULT_BANNER
            
            # Đồng bộ mảng hình ảnh mô tả thực tế (Screenshots)
            screens = local['screenshots']
            if not screens and info and info.get('screenshots'):
                dl_screens = []
                for idx, url in enumerate(info['screenshots']):
                    path = os.path.join(config.IMG_DIR, f"{clean_name}_{idx+1}.jpg")
                    if utils.download_resource_to_local(url, path): dl_screens.append(build_asset_url(config.IMG_DIR_NAME, f"{clean_name}_{idx+1}.jpg"))
                if dl_screens: screens = dl_screens
            if not screens: screens = utils.get_default_screens()
            
            desc = (info['desc'] if info else None) or f"Ứng dụng {clean_name} từ Kyic Store."
            feather_db["apps"][f_url] = {"bid": str(bid), "ver": str(ver), "name": clean_name, "size": curr_size, "icon": icon, "banner": banner, "screenshots": screens, "desc": desc, "permissions": perms, "minOS": min_os, "buildVersion": build_ver}

        apps_map[bid].append({"name": clean_name, "ver": str(ver), "bid": str(bid), "dl": f_url, "sz": curr_size, "date": item.get("date", "Local"), "minOS": min_os, "buildVersion": build_ver})

    final_apps = []
    for bid in apps_map:
        versions = sorted(apps_map[bid], key=lambda x: str(x['ver']), reverse=True)
        latest = versions[0]
        data = feather_db["apps"].get(latest['dl'])
        
        # Xử lý thời gian timezone-aware chuẩn ISO an toàn thay thế hàm cũ
        if latest['date'] != "Local":
            v_date = latest['date']
        else:
            v_date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        app_item = {
            "name": str(latest['name']), "bundleIdentifier": str(bid), "developerName": "Kyic Store",
            "subtitle": "Phiên bản Premium", "localizedDescription": utils.smart_truncate_description(data['desc']),
            "iconURL": utils.clean_github_url(data['icon']), "tintColor": "848ef9",
            "version": str(latest['ver']), "versionDate": v_date,
            "size": int(latest['sz']), "downloadURL": str(latest['dl']),
            "versions": [{"version": v['ver'], "date": v['date'] if v['date'] != "Local" else v_date, "size": v['sz'], "downloadURL": v['dl'], "localizedDescription": f"Cập nhật phiên bản Premium v{v['ver']}."} for v in versions],
            "screenshotURLs": [utils.clean_github_url(s) for s in data['screenshots']],
            "videoURL": utils.clean_github_url(config.DEFAULT_VIDEO), "appPermissions": utils.format_permissions(data['permissions'])
        }
        final_apps.append(app_item)
    
    final_apps.sort(key=lambda x: x['name'].lower())
    
    # Cấu hình mục tin tức (News) trên bảng điều khiển Feather
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    news_list = [
        {"title": "Donate", "identifier": "feather-donate", "caption": "Ủng hộ Kyic Store!", "date": today, "imageURL": utils.clean_github_url(config.NEWS_DONATE_IMAGE), "url": "https://www.paypal.me/225668", "appIdentifier": final_apps[0]['bundleIdentifier'] if final_apps else config.SOURCE_IDENTIFIER},
        {"title": "About", "identifier": "feather-about", "caption": "Chào mừng!", "date": today, "imageURL": utils.clean_github_url(config.NEWS_ABOUT_IMAGE), "url": "https://github.com/2KGT/repo/blob/main/README.md", "appIdentifier": final_apps[0]['bundleIdentifier'] if final_apps else config.SOURCE_IDENTIFIER}
    ]
    if final_apps:
        latest = final_apps[0]
        news_list.insert(0, {"title": f"App mới: {latest['name']}", "identifier": f"new-{latest['bundleIdentifier']}", "caption": f"Phiên bản {latest['version']} đã sẵn sàng.", "date": today, "imageURL": latest['iconURL'], "url": "https://github.com/2KGT/repo/blob/main/README.md", "appIdentifier": latest['bundleIdentifier']})

    output_json = {"name": config.REPO_NAME, "identifier": config.SOURCE_IDENTIFIER, "iconURL": utils.clean_github_url(config.SOURCE_LOGO), "apps": final_apps, "news": news_list}
    
    with open(os.path.join(config.REPO_OUTPUT_DIR, 'apps.json'), 'w', encoding='utf-8') as f:
        json.dump(output_json, f, indent=2, ensure_ascii=False)
        
    return processed_names
