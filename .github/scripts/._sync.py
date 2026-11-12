# .github/scripts/sync.py
import gemini
import os
import json
import sys
import subprocess
import urllib.parse
import urllib.request
import zipfile
import plistlib
import bz2
import re
import tarfile
from datetime import datetime
from collections import defaultdict

# --- HÀM CHUẨN HÓA DỮ LIỆU FEATHER & VÁ LỖI PARSE ---
def clean_text(text):
    if not text: return ""
    return re.sub(r'\s+', ' ', str(text)).strip()

def smart_truncate_description(text, max_chars=150):
    """
    Cắt ngắn mô tả ngầm: Giới hạn khoảng 150 ký tự và cố gắng
    kết thúc đúng dấu câu để đủ câu đủ nghĩa, xóa sạch ký tự lạ phá JSON.
    """
    if not text: 
        return "Ứng dụng Premium được cung cấp bởi Kyic Store."
        
    # 1. Làm sạch tuyệt đối các ký tự xuống dòng, tab độc hại phá vỡ cấu trúc JSON
    clean = re.sub(r'[\r\n\t]+', ' ', str(text))
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    # Nếu chuỗi ngắn hơn giới hạn thì trả về luôn
    if len(clean) <= max_chars:
        return clean
        
    # 2. Cắt tạm thời ở giới hạn max_chars
    truncated = clean[:max_chars]
    
    # 3. Tìm dấu kết thúc câu (. ! ?) gần vị trí cắt nhất từ phải qua trái
    match = re.search(r'(.*[\.\!\?])', truncated)
    if match:
        return match.group(1).strip()
        
    # 4. Nếu không có dấu câu nào, cắt theo khoảng trắng gần nhất để tránh bị cụt chữ
    space_idx = truncated.rfind(' ')
    if space_idx != -1:
        return clean[:space_idx].strip() + "..."
        
    return truncated + "..."

def format_permissions(raw_data):
    """
    Chuẩn hóa danh sách quyền thành mảng các chuỗi tên Tiếng Việt phẳng.
    Bổ sung khối try-except để chống hoàn toàn lỗi parse data ngầm từ cache.
    """
    formatted_list = []
    if not raw_data:
        return formatted_list
        
    try:
        if isinstance(raw_data, dict):
            for k in raw_data.keys():
                clean_k = clean_text(k)
                if clean_k and clean_k not in formatted_list:
                    formatted_list.append(clean_k)
        elif isinstance(raw_data, list):
            for item in raw_data:
                if isinstance(item, dict):
                    k = clean_text(item.get('name', item.get('key', '')))
                    if not k and len(item) == 1:
                        k = clean_text(list(item.keys())[0])
                    if k and k not in formatted_list: formatted_list.append(k)
                elif isinstance(item, str):
                    k = clean_text(item)
                    if k and k not in formatted_list: formatted_list.append(k)
    except Exception as e:
        print(f"⚠️ Tránh được lỗi parse permissions nhờ try-except: {e}")
        
    return formatted_list

# ==========================================================================
# 📌 KHỐI I: CẤU HÌNH HỆ THỐNG GỐC (🔴 #H)
# ==========================================================================

CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

if "scripts" in CURRENT_SCRIPT_DIR.lower():
    if ".github" in CURRENT_SCRIPT_DIR.lower():
        REPO_ROOT = os.path.dirname(os.path.dirname(CURRENT_SCRIPT_DIR))
    else:
        REPO_ROOT = os.path.dirname(CURRENT_SCRIPT_DIR)
else:
    REPO_ROOT = CURRENT_SCRIPT_DIR

BASE_URL = "https://2kgt.github.io/repo/"  # Sửa đổi đảm bảo đi thẳng vào thư mục repo của github pages
RAW_URL = "https://raw.githubusercontent.com/2KGT/repo/main/"
REPO_NAME = "Kyic Premium Store"
SOURCE_IDENTIFIER = "com.kyic.premium"

ICON_DIR_NAME = "repo/depictions/icons"
IMG_DIR_NAME = "repo/depictions/images"
DEPICTION_DIR_NAME = "repo/depictions/metadata"

ICON_DIR = os.path.join(REPO_ROOT, ICON_DIR_NAME)
IMG_DIR = os.path.join(REPO_ROOT, IMG_DIR_NAME)
DEPICTION_DIR = os.path.join(REPO_ROOT, DEPICTION_DIR_NAME)

FEATHER_DATABASE = os.path.join(DEPICTION_DIR, "wikiipa.json")
APPS_INPUT_DIR = os.path.join(REPO_ROOT, "repo/apps")
DEBS_INPUT_DIR = os.path.join(REPO_ROOT, "repo/debs")
REPO_OUTPUT_DIR = os.path.join(REPO_ROOT, "repo")

SOURCE_LOGO = f"{RAW_URL}{ICON_DIR_NAME}/Kyic.png"
DEFAULT_BANNER = f"{RAW_URL}{IMG_DIR_NAME}/Kyic_banner.png"
DEFAULT_VIDEO = f"{RAW_URL}{IMG_DIR_NAME}/Kyic.mp4"

DEFAULT_SCREENS = []
if os.path.exists(IMG_DIR):
    all_imgs = sorted(os.listdir(IMG_DIR))
    for f in all_imgs:
        if f.lower().startswith("kyic") and not any(x in f.lower() for x in ["banner", "logo"]):
            if any(f.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp', '.mp4']):
                DEFAULT_SCREENS.append(f"{RAW_URL}{IMG_DIR_NAME}/{f}")

if not DEFAULT_SCREENS:
    DEFAULT_SCREENS = [SOURCE_LOGO]

NEWS_DONATE_IMAGE = f"{RAW_URL}{IMG_DIR_NAME}/donate.png"
NEWS_ABOUT_IMAGE = f"{RAW_URL}{IMG_DIR_NAME}/about.png"

for d in [APPS_INPUT_DIR, DEBS_INPUT_DIR, DEPICTION_DIR, ICON_DIR, IMG_DIR, REPO_OUTPUT_DIR]: 
    os.makedirs(d, exist_ok=True)

def clean_github_url(url):
    """ Tự động tối ưu hóa đường dẫn ảnh từ github dạng blob sang dạng raw xem trực tiếp """
    if not url or not isinstance(url, str): return ""
    if "github.com" in url and "/blob/" in url:
        url = url.split("?")[0]
        url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    if "github.com" in url and url.endswith("?raw=true"):
        url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/").replace("?raw=true", "")
    return url

def download_resource_to_local(url, target_path):
    if not url or not isinstance(url, str) or not url.startswith("http"):
        return False
    if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
        return True 
    try:
        print(f"📥 Đang tải tài nguyên về local -> {os.path.basename(target_path)}")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'})
        with urllib.request.urlopen(req, timeout=20) as response:
            with open(target_path, 'wb') as f:
                f.write(response.read())
        return True
    except Exception as e:
        print(f"⚠️ Không thể tải file từ {url}. Lỗi: {e}")
        return False

PERM_MAPPING = {
    "NSCameraUsageDescription": "Máy ảnh", 
    "NSMicrophoneUsageDescription": "Micro",
    "NSPhotoLibraryUsageDescription": "Thư viện ảnh", 
    "NSPhotoLibraryAddUsageDescription": "Ghi vào Thư viện ảnh",
    "NSLocationWhenInUseUsageDescription": "Vị trí khi dùng ứng dụng", 
    "NSLocationAlwaysAndWhenInUseUsageDescription": "Vị trí mọi lúc",
    "NSLocationAlwaysUsageDescription": "Vị trí chạy ngầm", 
    "NSContactsUsageDescription": "Danh bạ",
    "NSCalendarsUsageDescription": "Lịch", 
    "NSRemindersUsageDescription": "Nhắc nhở",
    "NSBluetoothAlwaysUsageDescription": "Kết nối Bluetooth", 
    "NSBluetoothPeripheralUsageDescription": "Thiết Thiết bị ngoại vi Bluetooth",
    "NSFaceIDUsageDescription": "Face ID / Touch ID", 
    "NSUserTrackingUsageDescription": "Theo dõi quảng cáo",
    "NSLocalNetworkUsageDescription": "Mạng cục bộ"
}

def fetch_github_release_assets():
    print("🌐 Đang quét tài nguyên ứng dụng từ GitHub Release Cloud...")
    assets_list = []
    repository = os.getenv("GITHUB_REPOSITORY") or "2KGT/repo"
    token = os.getenv("GITHUB_TOKEN")
    url = f"https://api.github.com/repos/{repository}/releases"
    try:
        req = urllib.request.Request(url)
        if token:
            req.add_header("Authorization", f"token {token}")
        req.add_header("User-Agent", "Mozilla/5.0")
        
        with urllib.request.urlopen(req, timeout=15) as response:
            releases = json.loads(response.read().decode('utf-8'))
            for release in releases:
                if release.get("draft"): continue
                release_date = release.get("published_at") or release.get("created_at")
                for asset in release.get("assets", []):
                    name = asset.get("name", "")
                    if name.endswith(".ipa"):
                        assets_list.append({
                            "name": name, "url": asset.get("browser_download_url"),
                            "size": asset.get("size", 0), "date": release_date
                        })
        print(f"📦 Tìm thấy {len(assets_list)} tệp tin ứng dụng .ipa trên GitHub Release Cloud!")
    except Exception as e:
        print(f"⚠️ Không thể quét dữ liệu ứng dụng từ GitHub Release Cloud. Lỗi: {e}")
    return assets_list


# ==========================================================================
# 📌 KHỐI II: HỆ THỐNG FEATHER (🟣 #F)
# ==========================================================================

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
                    for plist_key, display_name in PERM_MAPPING.items():
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
    icon_url = next((f"{RAW_URL}{ICON_DIR_NAME}/{name}{e}" for e in exts if os.path.exists(os.path.join(ICON_DIR, f"{name}{e}"))), None)
    banner_url = next((f"{RAW_URL}{IMG_DIR_NAME}/{name}_banner{e}" for e in exts if os.path.exists(os.path.join(IMG_DIR, f"{name}_banner{e}"))), None)
    video_url = f"{RAW_URL}{IMG_DIR_NAME}/{name}.mp4" if os.path.exists(os.path.join(IMG_DIR, f"{name}.mp4")) else None

    screens = []
    for i in range(1, 15):
        for e in exts:
            if os.path.exists(os.path.join(IMG_DIR, f"{name}_{i}{e}")):
                screens.append(f"{RAW_URL}{IMG_DIR_NAME}/{name}_{i}{e}")
                break
            elif os.path.exists(os.path.join(IMG_DIR, f"{name}{i}{e}")):
                screens.append(f"{RAW_URL}{IMG_DIR_NAME}/{name}{i}{e}")
                break
                
    return {"icon": icon_url, "banner": banner_url, "screenshots": screens, "video": video_url}

def run_feather_engine(release_assets, system_db):
    print("▶️ Khởi chạy Feather Engine (Chuẩn hoá cấu trúc phẳng)...")
    apps_map = defaultdict(list)

    if os.path.exists(APPS_INPUT_DIR):
        for f_name in os.listdir(APPS_INPUT_DIR):
            if f_name.endswith(".ipa"):
                path = os.path.join(APPS_INPUT_DIR, f_name)
                f_url = f"{BASE_URL}apps/{f_name}"
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
                        if download_resource_to_local(info['icon'], os.path.join(ICON_DIR, f"{clean_name}.jpg")):
                            icon = f"{RAW_URL}{ICON_DIR_NAME}/{clean_name}.jpg"
                    if not icon: icon = SOURCE_LOGO

                    banner = local['banner']
                    if not banner and info and info['banner']:
                        if download_resource_to_local(info['banner'], os.path.join(IMG_DIR, f"{clean_name}_banner.jpg")):
                            banner = f"{RAW_URL}{IMG_DIR_NAME}/{clean_name}_banner.jpg"
                    if not banner: banner = DEFAULT_BANNER

                    screens = local['screenshots']
                    if not screens and info and info['screenshots']:
                        downloaded_screens = []
                        for idx, scr_url in enumerate(info['screenshots']):
                            target_scr_path = os.path.join(IMG_DIR, f"{clean_name}_{idx+1}.jpg")
                            if download_resource_to_local(scr_url, target_scr_path):
                                downloaded_screens.append(f"{RAW_URL}{IMG_DIR_NAME}/{clean_name}_{idx+1}.jpg")
                        if downloaded_screens: screens = downloaded_screens
                    if not screens: screens = DEFAULT_SCREENS

                    video = local['video'] if local['video'] else DEFAULT_VIDEO
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
                temp_path = os.path.join(REPO_ROOT, f"temp_{f_name}")
                try:
                    urllib.request.urlretrieve(f_url, temp_path)
                    ver, bid, perms, min_os, build_ver = extract_ipa_permissions_and_data(temp_path)
                except Exception as e:
                    print(f"⚠️ Lỗi phân tích tệp tạm từ Cloud {f_name}: {e}")
                    continue
                finally:
                    if os.path.exists(temp_path): os.remove(temp_path)

                local = get_local_assets_ipa(clean_name)
                info = get_itunes_info(bid)
                
                icon = local['icon']
                if not icon and info and info['icon']:
                    if download_resource_to_local(info['icon'], os.path.join(ICON_DIR, f"{clean_name}.jpg")):
                        icon = f"{RAW_URL}{ICON_DIR_NAME}/{clean_name}.jpg"
                if not icon: icon = SOURCE_LOGO

                banner = local['banner']
                if not banner and info and info['banner']:
                    if download_resource_to_local(info['banner'], os.path.join(IMG_DIR, f"{clean_name}_banner.jpg")):
                        banner = f"{RAW_URL}{IMG_DIR_NAME}/{clean_name}_banner.jpg"
                if not banner: banner = DEFAULT_BANNER

                screens = local['screenshots']
                if not screens and info and info['screenshots']:
                    downloaded_screens = []
                    for idx, scr_url in enumerate(info['screenshots']):
                        target_scr_path = os.path.join(IMG_DIR, f"{clean_name}_{idx+1}.jpg")
                        if download_resource_to_local(scr_url, target_scr_path):
                            downloaded_screens.append(f"{RAW_URL}{IMG_DIR_NAME}/{clean_name}_{idx+1}.jpg")
                    if downloaded_screens: screens = downloaded_screens
                if not screens: screens = DEFAULT_SCREENS

                video = local['video'] if local['video'] else DEFAULT_VIDEO
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
        raw_scr_urls = [clean_github_url(s) for s in matched_data.get('screenshots', DEFAULT_SCREENS) if s]
        
        formatted_versions = []
        for v in versions:
            v_date = str(v['date'] if v['date'] != "Local" else date_str)
            if "T" in v_date: v_date = v_date.split("T")[0]
            formatted_versions.append({
                "version": str(v['ver']), "date": v_date, "size": int(v['sz']), "downloadURL": str(v['dl']),
                "localizedDescription": f"Cập nhật phiên bản Premium v{v['ver']}."
            })
        
        feather_perms = format_permissions(matched_data.get('permissions', {}))
        
        app_item = {
            "name": str(latest['name']), 
            "bundleIdentifier": str(bid), 
            "developerName": "Kyic Store", 
            "subtitle": "Phiên bản Premium", 
            
            # 🔥 ĐÃ SỬA: Áp dụng hàm cắt ngắn ngầm đủ câu để bảo vệ cấu trúc JSON
            "localizedDescription": smart_truncate_description(matched_data.get('desc', "")), 
            
            "iconURL": clean_github_url(matched_data.get('icon', SOURCE_LOGO)), 
            "tintColor": "848ef9",
            "version": str(latest['ver']), 
            "versionDate": date_str, 
            "size": int(latest['sz']), 
            "downloadURL": str(latest['dl']),
            "versions": formatted_versions, 
            "screenshotURLs": raw_scr_urls, 
            "videoURL": clean_github_url(matched_data.get('video', DEFAULT_VIDEO)),
            
            # 🔥 ĐÃ TINH GIẢN: Đi theo chuẩn Quyền riêng tư (Privacy) duy nhất giống App Store
            "privacy": feather_perms if feather_perms else []
        }
        final_apps.append(app_item)

    first_app_id = featured_bids[0] if featured_bids else SOURCE_IDENTIFIER
    final_news = [
        {"title": "Donate", "identifier": "feather-donate", "caption": "Nếu bạn yêu thích kho ứng dụng Kyic Premium Store, hãy quyên góp ủng hộ cho chúng tôi!", "date": "2026-05-19", "tintColor": "848ef9", "imageURL": clean_github_url(NEWS_DONATE_IMAGE), "notify": False, "url": "https://www.paypal.me/225668", "appIdentifier": str(first_app_id)},
        {"title": "About", "identifier": "feather-about", "caption": "Chào mừng bạn đến với Kyic Premium Store!", "date": "2026-05-19", "tintColor": "8A28F7", "imageURL": clean_github_url(NEWS_ABOUT_IMAGE), "notify": True, "url": "https://github.com/2KGT/repo/blob/main/README.md", "appIdentifier": str(first_app_id)}
    ]

    output_json = {"name": REPO_NAME, "identifier": SOURCE_IDENTIFIER, "iconURL": clean_github_url(SOURCE_LOGO), "apps": final_apps, "news": final_news}
    with open(os.path.join(REPO_OUTPUT_DIR, 'apps.json'), 'w', encoding='utf-8') as f: 
        json.dump(output_json, f, indent=2, ensure_ascii=False)
    print("✅ Đã xuất tệp apps.json chuẩn hóa cấu trúc phẳng Feather hoàn toàn!")


# ==========================================================================
# 📌 KHỐI III: HỆ THỐNG SILEO (🔵 #S)
# ==========================================================================

def extract_deb_control_data(path):
    info = {"Package": "", "Name": "", "Version": "1.0", "Description": "Một tweak tuyệt vời từ Kyic Store.", "Author": "Kyic Store", "Section": "Tweaks", "Architecture": "iphoneos-arm"}
    try:
        working_dir = os.path.dirname(os.path.abspath(path))
        deb_name = os.path.basename(path)
        cmd = f'ar -x "{deb_name}" control.tar.xz control.tar.gz control.tar.zst control.tar 2>/dev/null'
        subprocess.run(cmd, shell=True, cwd=working_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
        tar_file = next((f for f in ["control.tar.xz", "control.tar.gz", "control.tar.zst", "control.tar"] if os.path.exists(os.path.join(working_dir, f))), None)
        if tar_file:
            full_tar_path = os.path.join(working_dir, tar_file)
            with tarfile.open(full_tar_path) as tar:
                control_file = next((m for m in tar.getmembers() if "control" in m.name.lower()), None)
                if control_file:
                    f_content = tar.extractfile(control_file).read().decode('utf-8', errors='ignore')
                    for line in f_content.split('\n'):
                        if ':' in line:
                            k, v = line.split(':', 1)
                            info[k.strip()] = v.strip()
            os.remove(full_tar_path)
    except: pass
    
    if not info["Package"]: info["Package"] = f"com.kyic.{os.path.basename(path).split('_')[0].lower()}"
    if not info["Name"]: info["Name"] = os.path.basename(path).split('_')[0]
    
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

def get_tweak_assets(tweak_name, deb_info):
    exts = ['.png', '.jpg', '.jpeg', '.webp']
    clean_search_name = tweak_name.replace(" ", "").lower()
    local_icons = os.listdir(ICON_DIR) if os.path.exists(ICON_DIR) else []
    local_images = os.listdir(IMG_DIR) if os.path.exists(IMG_DIR) else []
    
    matched_icon_file = next((f for f in local_icons if f.replace(" ", "").lower().startswith(clean_search_name) and any(f.endswith(e) for e in exts)), None)
    icon_url = None
    if matched_icon_file:
        icon_url = f"{RAW_URL}{ICON_DIR_NAME}/{matched_icon_file}"
    else:
        remote_icon = deb_info.get('Icon') or deb_info.get('icon')
        if remote_icon and remote_icon.startswith("http"):
            target_path = os.path.join(ICON_DIR, f"{clean_search_name}.jpg")
            if download_resource_to_local(remote_icon, target_path):
                icon_url = f"{RAW_URL}{ICON_DIR_NAME}/{clean_search_name}.jpg"
    if not icon_url: icon_url = clean_github_url(SOURCE_LOGO)
    
    matched_banner_file = next((f for f in local_images if f.replace(" ", "").lower().startswith(f"{clean_search_name}_banner") and any(f.endswith(e) for e in exts)), None)
    banner_url = None
    if matched_banner_file:
        banner_url = f"{RAW_URL}{IMG_DIR_NAME}/{matched_banner_file}"
    else:
        remote_banner = deb_info.get('Banner') or deb_info.get('banner')
        # 🔥 ĐÃ SỬA: Loại bỏ từ 'upgrade' lỗi cú pháp, thêm kiểm tra an toàn với 'and'
        if remote_banner and remote_banner.startswith("http"):
            target_path = os.path.join(IMG_DIR, f"{clean_search_name}_banner.jpg")
            if download_resource_to_local(remote_banner, target_path):
                banner_url = f"{RAW_URL}{IMG_DIR_NAME}/{clean_search_name}_banner.jpg"
    if not banner_url: banner_url = clean_github_url(DEFAULT_BANNER)
    
    matched_video_file = next((f_file for f_file in local_images if f_file.replace(" ", "").lower() == f"{clean_search_name}.mp4"), None)
    video_url = None
    if matched_video_file:
        video_url = f"{RAW_URL}{IMG_DIR_NAME}/{matched_video_file}"
    else:
        remote_video = deb_info.get('Video') or deb_info.get('video')
        if remote_video and remote_video.startswith("http"):
            target_path = os.path.join(IMG_DIR, f"{clean_search_name}.mp4")
            if download_resource_to_local(remote_video, target_path):
                video_url = f"{RAW_URL}{IMG_DIR_NAME}/{clean_search_name}.mp4"
    if not video_url: video_url = clean_github_url(DEFAULT_VIDEO)
    
    screens = []
    for i in range(1, 15):
        matched_scr = next((f for f in local_images if f.replace(" ", "").lower().startswith(f"{clean_search_name}_{i}") and any(f.endswith(e) for e in exts)), None)
        if matched_scr:
            screens.append(f"{RAW_URL}{IMG_DIR_NAME}/{matched_scr}")
            
    if not screens:
        raw_screens_data = deb_info.get('Screenshots') or deb_info.get('screenshots') or deb_info.get('Screenshot') or deb_info.get('screenshot')
        if raw_screens_data:
            urls_list = []
            if isinstance(raw_screens_data, list):
                urls_list = raw_screens_data
            elif isinstance(raw_screens_data, str):
                if raw_screens_data.startswith('[') and raw_screens_data.endswith(']'):
                    try: urls_list = json.loads(raw_screens_data)
                    except: urls_list = [u.strip() for u in raw_screens_data.strip('[]').split(',') if u]
                else:
                    urls_list = [u.strip() for u in raw_screens_data.split(',') if u]
            
            idx = 1
            for scr_url in urls_list:
                if scr_url.startswith("http"):
                    target_scr_path = os.path.join(IMG_DIR, f"{clean_search_name}_{idx}.jpg")
                    if download_resource_to_local(scr_url, target_scr_path):
                        screens.append(f"{RAW_URL}{IMG_DIR_NAME}/{clean_search_name}_{idx}.jpg")
                        idx += 1
                        
    if not screens: screens = [clean_github_url(s) for s in DEFAULT_SCREENS]
    return {"icon": clean_github_url(icon_url), "banner": clean_github_url(banner_url), "video": clean_github_url(video_url), "screenshots": screens}

def build_sileo_depiction_json(safe_filename, tweak_name, version, description, assets, author, deb_info, privacy_list):
    file_path = os.path.join(DEPICTION_DIR, f"{safe_filename}.json")
    
    # Chuẩn hóa danh sách quyền riêng tư thành văn bản phẳng chuyên nghiệp cho Sileo
    privacy_text = ", ".join(privacy_list) if privacy_list else "Không yêu cầu quyền đặc biệt"
    clean_desc = smart_truncate_description(description, max_chars=300)
    
    depiction_data = {
        "minVersion": "0.1", "class": "SileoRootDepiction", "headerImage": assets["banner"], "tintColor": "848ef9",
        "tabs": [
            {
                "tabname": "Giới Thiệu", "class": "SileoListViewDepiction",
                "views": [
                    {"class": "SileoDepictionVideoView", "videoURL": assets["video"], "autoplay": False, "loop": False, "cornerRadius": 8},
                    {"class": "SileoMarkdownDepiction", "markdown": f"### {tweak_name}\n\n{clean_desc}", "useBoldText": True, "useMargins": True},
                    
                    # 🔥 ĐÃ CẬP NHẬT: Thêm bảng Quyền riêng tư tiêu chuẩn App Store vào Sileo
                    {"class": "SileoTableTextFieldWithTitleView", "title": "QUYỀN RIÊNG TƯ ỨNG DỤNG"},
                    {"class": "SileoTableKeyValueView", "title": "Yêu cầu quyền", "value": privacy_text},
                    
                    {"class": "SileoScreenshotsDepiction", "screenshots": [{"url": str(s), "accessibilityText": "Screenshot"} for s in assets["screenshots"] if s], "itemCornerRadius": 8}
                ]
            }
        ]
    }
    with open(file_path, 'w', encoding='utf-8') as f: json.dump(depiction_data, f, indent=2, ensure_ascii=False)

def run_sileo_engine(release_assets, system_db):
    print("▶️ Khởi chạy Sileo Engine...")
    tweaks_map = defaultdict(list)
    if os.path.exists(DEBS_INPUT_DIR):
        for root, dirs, files in os.walk(DEBS_INPUT_DIR):
            for f_name in files:
                if f_name.endswith(".deb"):
                    path = os.path.join(root, f_name)
                    relative_path = os.path.relpath(path, REPO_OUTPUT_DIR).replace("\\", "/")
                    f_url = f"{BASE_URL}{relative_path}"
                    safe_filename = f_name.rsplit('.', 1)[0]
                    
                    if f_url in system_db["tweaks"] and isinstance(system_db["tweaks"][f_url], dict):
                        deb_info = system_db["tweaks"][f_url]
                    else:
                        deb_info = extract_deb_control_data(path)
                        system_db["tweaks"][f_url] = deb_info

                    bid, tweak_title, ver, desc, author = deb_info["Package"], deb_info["Name"], deb_info["Version"], deb_info["Description"], deb_info["Author"]
                    arch = deb_info["Architecture"]
                    section = deb_info.get("Section", "Tweaks")
                    
                    # Lấy danh sách quyền từ dữ liệu để đồng bộ hóa quyền riêng tư chuẩn App Store
                    privacy_list = format_permissions(deb_info.get('Permissions', deb_info.get('permissions', {})))
                    
                    assets = get_tweak_assets(tweak_title, deb_info)
                    build_sileo_depiction_json(safe_filename, tweak_title, ver, desc, assets, author, deb_info, privacy_list)
                    
                    tweaks_map[(bid, arch)].append({"name": tweak_title, "ver": str(ver), "bid": bid, "arch": arch, "dl": relative_path, "sz": int(os.path.getsize(path)), "desc": desc, "author": author, "icon": assets["icon"], "safe_file": safe_filename, "section": section})

    final_packages = ""
    for key in sorted(tweaks_map.keys()):
        for v_item in tweaks_map[key]:
            final_packages += f"Package: {v_item['bid']}\nName: {v_item['name']}\nVersion: {str(v_item['ver'])}\nArchitecture: {v_item['arch']}\nFilename: {v_item['dl']}\nSize: {v_item['sz']}\nAuthor: {v_item['author']}\nDescription: {v_item['desc']}\nSection: {v_item['section']}\nIcon: {v_item['icon']}\nSileoDepiction: {BASE_URL}depictions/metadata/{v_item['safe_file']}.json\n\n"

    with open(os.path.join(REPO_OUTPUT_DIR, "Packages"), "w", encoding="utf-8") as f: f.write(final_packages)
    try:
        with open(os.path.join(REPO_OUTPUT_DIR, "Packages"), 'rb') as f_in:
            with bz2.BZ2File(os.path.join(REPO_OUTPUT_DIR, "Packages.bz2"), 'wb') as f_out: f_out.write(f_in.read())
    except: pass

    sileo_main_data = {"minVersion": "0.1", "class": "SileoRootDepiction", "headerImage": DEFAULT_BANNER, "tintColor": "848ef9", "tabs": [{"tabname": "Cửa Hàng", "class": "SileoListViewDepiction", "views": [{"class": "SileoMarkdownDepiction", "markdown": f"## {REPO_NAME} ✨", "useMargins": True}]}]}
    with open(os.path.join(REPO_OUTPUT_DIR, "sileo.json"), "w", encoding="utf-8") as f: json.dump(sileo_main_data, f, indent=2, ensure_ascii=False)

    short_label = REPO_NAME.split()[0] if REPO_NAME else "Kyic"
    release_content = f"Origin: {REPO_NAME}\nLabel: {short_label}\nSuite: stable\nVersion: 1.0\nCodename: ios\nArchitectures: iphoneos-arm iphoneos-arm64\nComponents: main\nDescription: Kho tài nguyên ứng dụng của {REPO_NAME}.\nSileoDepiction: {BASE_URL}sileo.json\n"
    with open(os.path.join(REPO_OUTPUT_DIR, "Release"), "w", encoding="utf-8") as f: f.write(release_content)


# ==========================================================================
# 📌 KHỐI IV: TIẾN TRÌNH ĐIỀU TỐC TỔNG HỢP AI (🟡 #M)
# ==========================================================================

def main():
    # 1. Khởi tạo DB lấy từ gemini helper
    system_db = gemini.load_system_database()
    old_apps = set(system_db.get("apps", {}).keys())
    old_tweaks = set(system_db.get("tweaks", {}).keys())
    
    release_assets = fetch_github_release_assets()
    
    run_feather_engine(release_assets, system_db)
    run_sileo_engine(release_assets, system_db)
    
    with open(FEATHER_DATABASE, 'w', encoding='utf-8') as f: 
        json.dump(system_db, f, indent=2, ensure_ascii=False)
        
    # 2. 🔥 GỌI HÀM TÍCH HỢP: Đẩy hết số liệu, log và AI sang gemini xử lý
    gemini.process_and_dispatch_env(system_db, old_apps, old_tweaks)


if __name__ == "__main__":
    main()
