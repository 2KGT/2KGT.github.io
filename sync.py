import os, json, sys, subprocess, urllib.parse, urllib.request, zipfile, plistlib, bz2, re, tarfile
from datetime import datetime
from collections import defaultdict

# ==========================================================================
# 📌 KHỐI I: CẤU HÌNH HỆ THỐNG GỐC (🔴 #H)
# ==========================================================================

# [Task H-1]: Khai báo các hằng số đường dẫn URL và siêu dữ liệu nguồn
BASE_URL = "https://2kgt.github.io/repo/"
RAW_URL = "https://raw.githubusercontent.com/2KGT/repo/main/"

REPO_NAME = "Kyic Premium Store"
SOURCE_IDENTIFIER = "com.kyic.premium"
FEATHER_DATABASE = "metadata/wikiipa.json" 

# [Task H-2]: Định nghĩa các phân vùng thư mục hệ thống
ICON_DIR = "icons"
IMG_DIR = "depictions/images"
DEPICTION_DIR = "depictions"

SOURCE_LOGO = f"{RAW_URL}{ICON_DIR}/Kyic.png"
DEFAULT_BANNER = f"{RAW_URL}{IMG_DIR}/Kyic_banner.png"
DEFAULT_VIDEO = f"{RAW_URL}{IMG_DIR}/Kyic.mp4"

# [Task H-3]: Bộ quét không giới hạn, tự động gom toàn bộ ảnh chụp màn hình đạt chuẩn Kyic(n).png
DEFAULT_SCREENS = []
if os.path.exists(IMG_DIR):
    all_imgs = sorted(os.listdir(IMG_DIR))
    for f in all_imgs:
        if f.startswith("Kyic") and not any(x in f.lower() for x in ["banner", "logo"]):
            if any(f.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp']):
                DEFAULT_SCREENS.append(f"{RAW_URL}{IMG_DIR}/{f}")

if not DEFAULT_SCREENS:
    DEFAULT_SCREENS = [SOURCE_LOGO]

NEWS_DONATE_IMAGE = f"{BASE_URL}{IMG_DIR}/donate.png"
NEWS_ABOUT_IMAGE = f"{BASE_URL}{IMG_DIR}/about.png"

# [Task H-4]: Khởi tạo tự động các thư mục vật lý trên phân vùng lưu trữ nếu chưa tồn tại
for d in ["apps", "debs", "metadata", DEPICTION_DIR, ICON_DIR, IMG_DIR]: 
    os.makedirs(d, exist_ok=True)

# [Task H-5]: Định nghĩa hàm làm sạch URL bộ nhớ đệm của GitHub
def clean_github_url(url):
    if not url: return url
    if "github.com" in url and "blob" in url and not url.endswith("?raw=true"):
        return url + "?raw=true"
    return url

# [Task H-6]: Thiết lập bảng ánh xạ ngôn ngữ bản dịch quyền truy cập iOS
PERM_MAPPING = {
    "NSCameraUsageDescription": "Máy ảnh", "NSMicrophoneUsageDescription": "Micro",
    "NSPhotoLibraryUsageDescription": "Thư viện ảnh", "NSPhotoLibraryAddUsageDescription": "Ghi vào Thư viện ảnh",
    "NSLocationWhenInUseUsageDescription": "Vị trí khi dùng ứng dụng", "NSLocationAlwaysAndWhenInUseUsageDescription": "Vị trí mọi lúc",
    "NSLocationAlwaysUsageDescription": "Vị trí chạy ngầm", "NSContactsUsageDescription": "Danh bạ",
    "NSCalendarsUsageDescription": "Lịch", "NSRemindersUsageDescription": "Nhắc nhở",
    "NSBluetoothAlwaysUsageDescription": "Kết nối Bluetooth", "NSBluetoothPeripheralUsageDescription": "Thiết bị ngoại vi Bluetooth",
    "NSFaceIDUsageDescription": "Face ID / Touch ID", "NSUserTrackingUsageDescription": "Theo dõi quảng cáo",
    "NSLocalNetworkUsageDescription": "Mạng cục bộ"
}

# [Task H-7]: Gọi API GitHub để cào danh sách gói cài đặt từ Releases
def fetch_github_release_assets():
    repo_full = os.getenv('GITHUB_REPOSITORY')
    assets_list = []
    if not repo_full: return assets_list
    try:
        api_url = f"https://api.github.com/repos/{repo_full}/releases"
        req = urllib.request.Request(api_url, headers={'Authorization': f'token {os.getenv("GITHUB_TOKEN")}'})
        with urllib.request.urlopen(req) as response:
            releases = json.loads(response.read().decode())
            for rel in releases:
                for asset in rel.get('assets', []):
                    assets_list.append({"name": asset['name'], "url": asset['browser_download_url'], "size": int(asset['size']), "date": rel.get('published_at')})
    except: pass
    return assets_list

# ==========================================================================
# 📌 KHỐI II: LỘ TRÌNH FEATHER (🟣 #F)
# ==========================================================================

# [Task F-1]: Trích xuất luồng nhị phân file Info.plist từ IPA để lấy BundleID, Version và quyền truy cập
def extract_ipa_permissions_and_data(path):
    version, bid = "1.0", "com.kyic.unknown"
    permissions = []
    try:
        with zipfile.ZipFile(path, 'r') as z:
            plist_path = next((f for f in z.namelist() if re.match(r'^Payload/[^/]+\.app/Info\.plist$', f)), None)
            if plist_path:
                with z.open(plist_path) as f:
                    plist = plistlib.load(f)
                    version = plist.get('CFBundleShortVersionString') or plist.get('CFBundleVersion', '1.0')
                    bid = plist.get('CFBundleIdentifier', 'com.kyic.app')
                    for plist_key, display_name in PERM_MAPPING.items():
                        if plist_key in plist:
                            reason = plist.get(plist_key) or f"Ứng dụng yêu cầu quyền truy cập {display_name}."
                            permissions.append({"name": display_name, "text": str(reason)})
    except: pass
    return version, bid, permissions

# [Task F-2]: Đồng bộ thông tin từ iTunes API (App Store) lấy mô tả, icon và ảnh chụp màn hình gốc
def get_itunes_info(bundle_id):
    mapping_table = {"com.kyic.youtube": "com.google.ios.youtube", "com.kyic.tiktok": "com.zhiliaoapp.musically", "com.kyic.facebook": "com.facebook.Facebook", "com.kyic.spotify": "com.spotify.client"}
    target_id = mapping_table.get(bundle_id.lower(), bundle_id)
    try:
        url = f"https://itunes.apple.com/lookup?bundleId={target_id}&country=VN&lang=vi_vn"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data['resultCount'] > 0:
                res = data['results'][0]
                raw_screens = res.get('screenshotUrls', []) or res.get('ipadScreenshotUrls', [])
                clean_screens = list(set([clean_github_url(re.sub(r'\.(png|webp|gif|jpg|jpeg)[^/]*$', '.jpg', u)) for u in raw_screens]))
                raw_icon = res.get('artworkUrl512') or res.get('artworkUrl100')
                clean_icon = clean_github_url(re.sub(r'\.(png|webp|gif|jpg|jpeg)[^/]*$', '.jpg', raw_icon)) if raw_icon else None
                return {"icon": clean_icon, "banner": clean_screens[0] if clean_screens else None, "screenshots": clean_screens, "desc": res.get('description', ""), "privacy_url": res.get('privacyPolicyUrl'), "is_store": True}
    except: pass
    return None

# [Task F-3]: Quét tài nguyên cục bộ dự phòng trong thư mục icons/ và depictions/images/
def get_local_assets_ipa(name):
    exts = ['.png', '.jpg', '.jpeg']
    icon_url = next((f"{BASE_URL}{ICON_DIR}/{name}{e}" for e in exts if os.path.exists(f"{ICON_DIR}/{name}{e}")), None)
    screens = [f"{BASE_URL}{IMG_DIR}/{name}_{i}{e}" for i in range(1, 7) for e in exts if os.path.exists(f"{IMG_DIR}/{name}_{i}{e}")]
    banner_url = next((f"{BASE_URL}{IMG_DIR}/{name}_banner{e}" for e in exts if os.path.exists(f"{IMG_DIR}/{name}_banner{e}")), None)
    return {"icon": clean_github_url(icon_url), "banner": clean_github_url(banner_url), "screenshots": [clean_github_url(s) for s in screens]}

# [Task F-4]: Khởi tạo cấu trúc báo cáo bảo mật và quyền riêng tư tự động
def generate_privacy_report(app_name, is_store_app, app_permissions):
    if is_store_app:
        return [
            {"title": "Dữ Liệu Được Dùng Để Theo Dõi Bạn", "description": "Dữ liệu sau đây có thể được sử dụng để theo dõi bạn trên các ứng dụng và trang web do các công ty khác sở hữu:", "items": ["Mã Định Danh", "Dữ Liệu Sử Dụng", "Thông Tin Thiết Bị"]},
            {"title": "Dữ Liệu Liên Kết Với Bạn", "description": f"Dữ liệu sau đây có thể được thu thập và liên kết trực tiếp với danh tính của bạn khi dùng {app_name}:", "items": ["Thông Tin Liên Hệ", "Nội Dung Người Dùng", "Lịch Sử Tìm Kiếm", "Mã Định Danh", "Dữ Liệu Sử Dụng"]}
        ]
    else:
        collected_items = [perm["name"] for perm in app_permissions] or ["Dữ Liệu Sử Dụng"]
        return [{"title": "Dữ Liệu Được Ứng Dụng Thu Thập", "description": f"Nhà phát triển ứng dụng {app_name} cho biết quy trình bảo mật của ứng dụng có thể bao gồm việc xử lý dữ liệu như mô tả bên dưới:", "items": collected_items}]

def run_feather_engine(release_assets):
    print("▶️ Khởi chạy Feather Engine...")
    
    # [Task F-5]: Đọc bộ nhớ đệm cơ sở dữ liệu Feather (metadata/wikiipa.json) để tối ưu tốc độ
    feather_db = {"apps": {}}
    if os.path.exists(FEATHER_DATABASE):
        try:
            with open(FEATHER_DATABASE, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                if "apps" in old_data: feather_db["apps"] = old_data["apps"]
                elif isinstance(old_data, dict): feather_db["apps"] = old_data
        except: pass

    apps_map = defaultdict(list)
    apps_perms_map = {}
    apps_store_status_map = {}
    apps_privacy_url_map = {}

    if os.path.exists("apps"):
        for f_name in os.listdir("apps"):
            if f_name.endswith(".ipa"):
                path = os.path.join("apps", f_name)
                f_url = f"{BASE_URL}{path}"
                clean_name = f_name.rsplit('.', 1)[0].split('_', 1)[0]
                
                if f_url in feather_db["apps"] and isinstance(feather_db["apps"][f_url], dict):
                    cache = feather_db["apps"][f_url]
                    bid, ver, perms, p_url, is_store = cache.get('bid'), cache.get('ver'), cache.get('permissions', []), cache.get('privacy_url'), cache.get('is_store', False)
                else:
                    ver, bid, perms = extract_ipa_permissions_and_data(path)
                    local = get_local_assets_ipa(clean_name)
                    info = get_itunes_info(bid)
                    p_url, is_store = (info['privacy_url'], True) if info else (None, False)
                    icon = info['icon'] if info and info['icon'] else (local['icon'] or SOURCE_LOGO)
                    banner = info['banner'] if info and info['banner'] else (local['banner'] or DEFAULT_BANNER)
                    screens = info['screenshots'] if info and info['screenshots'] else (local['screenshots'] or DEFAULT_SCREENS)
                    desc = info['desc'] if info else f"Ứng dụng {clean_name} từ Kyic Store."
                    
                    feather_db["apps"][f_url] = {"bid": bid, "ver": str(ver), "name": clean_name, "icon": icon, "banner": banner, "screenshots": screens, "desc": desc, "permissions": perms, "privacy_url": p_url, "is_store": is_store}

                apps_perms_map[bid], apps_privacy_url_map[bid], apps_store_status_map[bid] = perms, p_url, is_store
                apps_map[bid].append({"name": clean_name, "ver": str(ver), "bid": bid, "dl": f_url, "sz": int(os.path.getsize(path)), "date": "Local"})

    for asset in release_assets:
        f_name = asset["name"]
        if f_name.endswith(".ipa"):
            f_url = asset["url"]
            clean_name = f_name.rsplit('.', 1)[0].split('_', 1)[0]

            if f_url in feather_db["apps"] and isinstance(feather_db["apps"][f_url], dict):
                cache = feather_db["apps"][f_url]
                bid, ver, perms, p_url, is_store = cache.get('bid'), cache.get('ver'), cache.get('permissions', []), cache.get('privacy_url'), cache.get('is_store', False)
            else:
                temp_path = f"temp_{f_name}"; urllib.request.urlretrieve(f_url, temp_path)
                ver, bid, perms = extract_ipa_permissions_and_data(temp_path)
                if os.path.exists(temp_path): os.remove(temp_path)

                local = get_local_assets_ipa(clean_name)
                info = get_itunes_info(bid)
                p_url, is_store = (info['privacy_url'], True) if info else (None, False)
                icon = info['icon'] if info and info['icon'] else (local['icon'] or SOURCE_LOGO)
                banner = info['banner'] if info and info['banner'] else (local['banner'] or DEFAULT_BANNER)
                screens = info['screenshots'] if info and info['screenshots'] else (local['screenshots'] or DEFAULT_SCREENS)
                desc = info['desc'] if info else f"Ứng dụng {clean_name} từ Kyic Store."
                
                feather_db["apps"][f_url] = {"bid": bid, "ver": str(ver), "name": clean_name, "icon": icon, "banner": banner, "screenshots": screens, "desc": desc, "permissions": perms, "privacy_url": p_url, "is_store": is_store}

            apps_perms_map[bid], apps_privacy_url_map[bid], apps_store_status_map[bid] = perms, p_url, is_store
            if not any(x['dl'] == f_url for x in apps_map[bid]):
                apps_map[bid].append({"name": clean_name, "ver": str(ver), "bid": bid, "dl": f_url, "sz": asset["size"], "date": asset["date"]})

    # [Task F-6]: Tổng hợp mảng danh sách ứng dụng kèm sắp xếp phiên bản mới nhất lên đầu
    final_apps = []
    
    # [Task F-7]: Nhúng tài nguyên bảng tin tức (news) cố định cho mục Donate và About
    final_news = [
        {"title": "Donate", "identifier": "feather-donate", "caption": "Nếu bạn yêu thích kho ứng dụng Kyic Premium Store, hãy cân nhắc quyên góp ủng hộ cho chúng tôi!", "tintColor": "848ef9", "imageURL": clean_github_url(NEWS_DONATE_IMAGE), "date": "2026-05-19", "url": "https://www.paypal.me/225668", "notify": False},
        {"title": "About", "identifier": "feather-about", "caption": "Chào mừng bạn đến với Kyic Premium Store! Kho chia sẻ ứng dụng iOS Premium và Tweak nâng cao cài đặt trực tiếp qua Feather.", "tintColor": "8A28F7", "imageURL": clean_github_url(NEWS_ABOUT_IMAGE), "url": "https://github.com/2KGT/repo/blob/main/README.md", "date": "2026-05-19", "notify": True}
    ]

    sorted_bids = sorted(apps_map.keys(), key=lambda b: apps_map[b][0]['name'].lower())
    for bid in sorted_bids:
        versions = apps_map[bid]
        versions.sort(key=lambda x: x['ver'], reverse=True) 
        latest = versions[0]
        matched_data = next((v for k, v in feather_db["apps"].items() if v.get('bid') == bid), {})
        
        date_str = latest['date'] if latest['date'] != "Local" else datetime.utcnow().isoformat() + "Z"
        app_item = {
            "name": latest['name'], "bundleIdentifier": bid, "developerName": "Kyic Store", "iconURL": clean_github_url(matched_data.get('icon', SOURCE_LOGO)), "localizedDescription": matched_data.get('desc', ""), "subtitle": "Phiên bản Premium", "tintColor": "#848ef9",
            "versions": [{"version": v['ver'], "date": v['date'] if v['date'] != "Local" else date_str, "size": v['sz'], "downloadURL": v['dl']} for v in versions],
            "appPermissions": apps_perms_map.get(bid, []), "screenshotURLs": [clean_github_url(s) for s in matched_data.get('screenshots', DEFAULT_SCREENS)], "version": latest['ver'], "versionDate": date_str, "size": latest['sz'], "downloadURL": latest['dl']
        }
        app_item["appPrivacy"] = generate_privacy_report(latest['name'], apps_store_status_map.get(bid, False), apps_perms_map.get(bid, []))
        if apps_privacy_url_map.get(bid): app_item["privacyPolicyURL"] = apps_privacy_url_map.get(bid)
        final_apps.append(app_item)

    # [Task F-8]: Xuất file cấu hình tổng hợp cuối cùng ra tệp apps.json và cập nhật tệp cache
    with open('apps.json', 'w', encoding='utf-8') as f: json.dump({"name": REPO_NAME, "identifier": SOURCE_IDENTIFIER, "iconURL": clean_github_url(SOURCE_LOGO), "apps": final_apps, "news": final_news}, f, indent=2, ensure_ascii=False)
    
    with open(FEATHER_DATABASE, 'w', encoding='utf-8') as f: json.dump(feather_db, f, indent=2, ensure_ascii=False)
    print("✅ Lộ trình Feather (#F) hoàn tất!")


# ==========================================================================
# 📌 KHỐI III: LỘ TRÌNH SILEO NÂNG CẤP CHUYÊN SÂU (🔵 #S)
# ==========================================================================

# [Task S-1]: Thực hiện lệnh hệ thống ar và tar để bung file control của DEB lấy thông số cấu hình Tweak
def extract_deb_control_data(path):
    info = {
        "Package": "", "Name": "", "Version": "1.0", 
        "Description": "Một tweak tuyệt vời từ Kyic Store.", 
        "Author": "Kyic Store", "Section": "Tweaks"
    }
    try:
        with open(path, 'rb') as f:
            cmd = f"ar -x {path} control.tar.xz control.tar.gz control.tar.zst control.tar 2>/dev/null"
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
        tar_file = next((f for f in ["control.tar.xz", "control.tar.gz", "control.tar.zst", "control.tar"] if os.path.exists(f)), None)
        if tar_file:
            with tarfile.open(tar_file) as tar:
                control_file = next((m for m in tar.getmembers() if "./control" in m.name or "control" in m.name), None)
                if control_file:
                    f_content = tar.extractfile(control_file).read().decode('utf-8', errors='ignore')
                    for line in f_content.split('\n'):
                        if ':' in line:
                            k, v = line.split(':', 1)
                            k, v = k.strip(), v.strip()
                            info[k] = v
            os.remove(tar_file)
    except: pass
    
    if not info["Package"]: info["Package"] = f"com.kyic.{os.path.basename(path).split('_')[0].lower()}"
    if not info["Name"]: info["Name"] = os.path.basename(path).split('_')[0]
    return info

# [Task S-2]: Định vị ảnh đại diện, ảnh banner thương hiệu và tập hợp chuỗi ảnh chụp màn hình cho từng Tweak
def get_tweak_assets(tweak_name, deb_info):
    exts = ['.png', '.jpg', '.jpeg']
    safe_asset_name = tweak_name.replace(" ", "")
    icon_url = deb_info.get('Icon') or deb_info.get('icon') or next((f"{BASE_URL}{ICON_DIR}/{safe_asset_name}{e}" for e in exts if os.path.exists(f"{ICON_DIR}/{safe_asset_name}{e}")), clean_github_url(SOURCE_LOGO))
    banner_url = deb_info.get('Banner') or deb_info.get('banner') or next((f"{BASE_URL}{IMG_DIR}/{safe_asset_name}_banner{e}" for e in exts if os.path.exists(f"{IMG_DIR}/{safe_asset_name}_banner{e}")), clean_github_url(DEFAULT_BANNER))
    video_url = deb_info.get('Video') or deb_info.get('video') or (f"{BASE_URL}{IMG_DIR}/{safe_asset_name}.mp4" if os.path.exists(f"{IMG_DIR}/{safe_asset_name}.mp4") else clean_github_url(DEFAULT_VIDEO))
    
    screens = []
    ctrl_screens = deb_info.get('Screenshots') or deb_info.get('screenshots') or deb_info.get('Screenshot')
    if ctrl_screens:
        screens = [s.strip() for s in re.split(r'[,\s]+', ctrl_screens) if s.strip()]
    if not screens:
        screens = [f"{BASE_URL}{IMG_DIR}/{safe_asset_name}_{i}{e}" for i in range(1, 15) for e in exts if os.path.exists(f"{IMG_DIR}/{safe_asset_name}_{i}{e}")]
    if not screens: 
        screens = [clean_github_url(s) for s in DEFAULT_SCREENS]
    else:
        screens = [clean_github_url(s) for s in screens]
        
    return {"icon": clean_github_url(icon_url), "banner": clean_github_url(banner_url), "video": clean_github_url(video_url), "screenshots": screens}

# [Task S-3]: Khởi tạo cấu trúc phân tầng JSON kết xuất đồ họa ba tab cho từng Tweak vào thư mục depictions/
def build_sileo_depiction_json(package_id, tweak_name, version, description, assets, author, deb_info):
    file_path = os.path.join(DEPICTION_DIR, f"{tweak_name}.json")
    changelog_text = deb_info.get('Changes') or deb_info.get('Changelog') or deb_info.get('changes') or "Cập nhật và tối ưu hóa cấu trúc gói cài đặt hệ thống nhằm tương thích tốt nhất với Sileo."
    dev_name = deb_info.get('Developer') or author
    
    depiction_data = {
        "minVersion": "0.1",
        "class": "SileoRootDepiction",
        "headerImage": assets["banner"],
        "tintColor": "#848ef9",
        "tabs": [
            {
                "tabname": "Giới Thiệu",
                "class": "SileoListViewDepiction",
                "views": [
                    {
                        "class": "SileoMarkdownDepiction",
                        "markdown": f"### {tweak_name}\n\n{description}\n\nPhát triển bởi **{dev_name}**.",
                        "useBoldText": True
                    },
                    {
                        "class": "SileoScreenshotsDepiction",
                        "screenshots": [{"url": s, "accessibilityText": "Screenshot"} for s in assets["screenshots"]],
                        "itemCornerRadius": 8,
                        "itemSize": "{160, 346}"
                    }
                ]
            },
            {
                "tabname": "Nhật Ký",
                "class": "SileoListViewDepiction",
                "views": [
                    {
                        "class": "SileoMarkdownDepiction",
                        "markdown": f"#### Lịch sử cập nhật (Phiên bản {version})\n\n{changelog_text}",
                        "useBoldText": False
                    },
                    {
                        "class": "SileoSpacerDepiction",
                        "spacing": 15
                    },
                    {
                        "class": "SileoTableLayoutDepiction",
                        "title": "Thông số kỹ thuật",
                        "rows": [
                            ["Nhà phát triển", dev_name],
                            ["Phiên bản", str(version)],
                            ["Định danh", package_id],
                            ["Phân mục", deb_info.get('Section', 'Tweaks')]
                        ]
                    }
                ]
            },
            {
                "tabname": "Hỗ Trợ",
                "class": "SileoListViewDepiction",
                "views": [
                    {
                        "class": "SileoMarkdownDepiction",
                        "markdown": "Mọi yêu cầu hỗ trợ hoặc báo lỗi về Tweak này, vui lòng liên hệ trực tiếp qua các kênh chính thức của Kyic Premium Store dưới đây.",
                        "useBoldText": False
                    },
                    {
                        "class": "SileoSpacerDepiction",
                        "spacing": 10
                    },
                    {
                        "class": "SileoHeaderDepiction",
                        "title": "Liên hệ nhà phát triển"
                    },
                    {
                        "class": "SileoControlCenterButtonDepiction",
                        "title": "Ghé thăm GitHub Repo",
                        "action": "https://github.com/2KGT/repo"
                    },
                    {
                        "class": "SileoControlCenterButtonDepiction",
                        "title": "Kênh Hỗ Trợ Kyic",
                        "action": "https://2kgt.github.io/repo/"
                    }
                ]
            }
        ]
    }
    with open(file_path, 'w', encoding='utf-8') as f: 
        json.dump(depiction_data, f, indent=2, ensure_ascii=False)

# [Task S-4]: Tạo dựng file cấu hình kiến trúc giao diện trang chủ đại diện nguồn sileo.json
def generate_sileo_main_repo_json():
    print("✨ Đang khởi tạo giao diện đại diện (Main Repo Depiction) cho Sileo...")
    sileo_main_data = {
        "minVersion": "0.1",
        "class": "SileoRootDepiction",
        "headerImage": DEFAULT_BANNER,
        "tintColor": "#848ef9",
        "tabs": [
            {
                "tabname": "Cửa Hàng",
                "class": "SileoListViewDepiction",
                "views": [
                    {
                        "class": "SileoMarkdownDepiction",
                        "markdown": f"## {REPO_NAME} ✨\nChào mừng bạn đã đến với kho tiện ích nâng cao hệ thống. Mọi tài nguyên cấu hình đều được đồng bộ tự động hóa an toàn.",
                        "useMargins": True
                    },
                    {
                        "class": "SileoControlCenterButtonDepiction",
                        "title": "ℹ️ Giới thiệu về Kyic Premium",
                        "action": "https://github.com/2KGT/repo/blob/main/README.md"
                    },
                    {
                        "class": "SileoSpacerDepiction",
                        "spacing": 10
                    },
                    {
                        "class": "SileoControlCenterButtonDepiction",
                        "title": "❤️ Tặng Kyic ly cà phê (Donate qua Paypal/MoMo)",
                        "action": "https://www.paypal.me/225668"
                    }
                ]
            }
        ]
    }
    with open("sileo.json", "w", encoding="utf-8") as f:
        json.dump(sileo_main_data, f, indent=2, ensure_ascii=False)

def run_sileo_engine(release_assets):
    print("▶️ Khởi chạy Sileo Engine nâng cấp...")
    tweaks_map = defaultdict(list)

    # [Task S-5]: Quét tuần tự toàn bộ các gói DEB cục bộ và DEB từ GitHub Release để gộp chung cơ sở dữ liệu
    if os.path.exists("debs"):
        for f_name in os.listdir("debs"):
            if f_name.endswith(".deb"):
                path = os.path.join("debs", f_name)
                deb_info = extract_deb_control_data(path)
                bid, tweak_title, ver, desc, author = deb_info["Package"], deb_info["Name"], deb_info["Version"], deb_info["Description"], deb_info["Author"]
                assets = get_tweak_assets(tweak_title, deb_info)
                
                build_sileo_depiction_json(bid, tweak_title, ver, desc, assets, author, deb_info)
                tweaks_map[bid].append({"name": tweak_title, "ver": str(ver), "bid": bid, "dl": f"{BASE_URL}{path}", "sz": int(os.path.getsize(path)), "desc": desc, "author": author, "icon": assets["icon"]})

    for asset in release_assets:
        f_name = asset["name"]
        if f_name.endswith(".deb"):
            f_url = asset["url"]
            temp_path = f"temp_{f_name}"; urllib.request.urlretrieve(f_url, temp_path)
            deb_info = extract_deb_control_data(temp_path)
            if os.path.exists(temp_path): os.remove(temp_path)

            bid, tweak_title, ver, desc, author = deb_info["Package"], deb_info["Name"], deb_info["Version"], deb_info["Description"], deb_info["Author"]
            assets = get_tweak_assets(tweak_title, deb_info)
            
            build_sileo_depiction_json(bid, tweak_title, ver, desc, assets, author, deb_info)
            if not any(x['dl'] == f_url for x in tweaks_map[bid]):
                tweaks_map[bid].append({"name": tweak_title, "ver": str(ver), "bid": bid, "dl": f_url, "sz": asset["size"], "desc": desc, "author": author, "icon": assets["icon"]})

    # [Task S-6]: Sắp xếp danh sách gói cài đặt theo thứ tự bảng chữ cái alphabet của tên Tweak
    final_packages = ""
    sorted_bids = sorted(tweaks_map.keys(), key=lambda b: tweaks_map[b][0]['name'].lower())
    
    for bid in sorted_bids:
        versions = tweaks_map[bid]
        versions.sort(key=lambda x: x['ver']) 

        for v_item in versions:
            original_filename = v_item['name']
            
            final_packages += f"Package: {bid}\n"
            final_packages += f"Name: {v_item['name']}\n"
            final_packages += f"Version: {v_item['ver']}\n"
            final_packages += f"Architecture: iphoneos-arm\n"
            final_packages += f"Filename: {v_item['dl'].replace(BASE_URL, '')}\n"
            final_packages += f"Size: {v_item['sz']}\n"
            final_packages += f"Author: {v_item['author']}\n"
            final_packages += f"Description: {v_item['desc']}\n"
            final_packages += f"Icon: {v_item['icon']}\n"
            final_packages += f"SileoDepiction: {BASE_URL}{DEPICTION_DIR}/{original_filename}.json\n\n"

    # [Task S-7]: Biến dịch và đóng gói toàn bộ thuộc tính kỹ thuật vào tệp phân phối cốt lõi Packages
    with open("Packages", "w", encoding="utf-8") as f: f.write(final_packages)
    
    generate_sileo_main_repo_json()
    print("✅ Lộ trình Sileo (#S) hoàn tất với bộ cào chuyên sâu!")

# ==========================================================================
# 📌 KHỐI IV: TIẾN TRÌNH ĐIỀU TỐC TỔNG HỢP GỐC (🟡 #M)
# ==========================================================================

# [Task M-1]: Khởi tạo và ghi đè file định danh hệ thống Release ở thư mục gốc
# [Task M-2]: Bơm con trỏ ánh xạ SileoDepiction vào file Release để kích hoạt giao diện Store
def update_release_file_for_sileo():
    print("✍️  Cập nhật file Release liên kết giao diện đại diện nguồn...")
    
    # Tự động lấy từ đầu tiên của chuỗi REPO_NAME làm Label viết tắt để hiển thị ngoài danh sách nguồn Sileo
    short_label = REPO_NAME.split()[0] if REPO_NAME else "Kyic"
    
    release_content = (
        f"Origin: {REPO_NAME}\n"
        f"Label: {short_label}\n"
        f"Suite: stable\n"
        f"Version: 1.0\n"
        f"Codename: ios\n"
        f"Architectures: iphoneos-arm iphoneos-arm64\n"
        f"Components: main\n"
        f"Description: Kho tài nguyên ứng dụng và tiện ích nâng cao của {REPO_NAME}.\n"
        f"SileoDepiction: {BASE_URL}sileo.json\n"
    )
    with open("Release", "w", encoding="utf-8") as f:
        f.write(release_content)

# [Task M-3]: Thiết lập hàm điều tốc trung tâm main() để quản lý thứ tự kích hoạt của các Engine phụ
def main():
    print("⚙️  Bắt đầu tiến trình làm mới Kho ứng dụng Kyic Store...")
    
    # [Task M-4]: Kích hoạt nạp tài nguyên đầu vào từ GitHub Assets, đẩy qua lộ trình Feather rồi đến Sileo
    release_assets = fetch_github_release_assets()
    
    run_feather_engine(release_assets)
    run_sileo_engine(release_assets)
    
    update_release_file_for_sileo()
    
    # [Task M-5]: Xuất thông báo trạng thái đồng bộ hóa thành công lên bảng điều khiển kết thúc tiến trình
    print("\n🚀 [Hoàn Tất] Toàn bộ mã nguồn đã đồng bộ thành công!")

if __name__ == "__main__":
    main()