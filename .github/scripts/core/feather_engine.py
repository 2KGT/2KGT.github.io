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


# ─────────────────────────────────────────────
# FIX: parse_version_tuple dùng chung từ utils.py
# (tránh duplicate logic giữa feather_engine và sileo_engine)
# ─────────────────────────────────────────────


def get_optimized_description(clean_name, version, release_note=None):
    """Logic thông minh: GitHub Note > File local > Mặc định"""
    # FIX: Dùng config.DESC_DIR thay vì tự ghép đường dẫn thủ công
    # Đảm bảo lưu đúng vào main(root)/repo/depictions/metadata/desc/apps/<AppName>/
    app_desc_dir = os.path.join(config.DESC_DIR, clean_name)
    os.makedirs(app_desc_dir, exist_ok=True)
    version_file = os.path.join(app_desc_dir, f"v{version}.txt")
    default_file = os.path.join(app_desc_dir, "default.txt")

    if release_note and len(release_note.strip()) > 10:
        if not os.path.exists(version_file):
            with open(version_file, 'w', encoding='utf-8') as f:
                f.write(release_note.strip())
        return release_note.strip()

    if os.path.exists(version_file):
        with open(version_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    if os.path.exists(default_file):
        with open(default_file, 'r', encoding='utf-8') as f:
            return f.read().strip()

    return f"Cập nhật phiên bản Premium v{version} từ Kyic Store."


def extract_ipa_permissions_and_data(path):
    """Giải nén tệp IPA tạm thời để bốc tách Info.plist lấy thông tin quyền hạn và Bundle ID"""
    version, bid, min_os, build_ver = "1.0", "com.kyic.unknown", "12.0", "1"
    permissions = {}
    try:
        with zipfile.ZipFile(path, 'r') as z:
            plist_path = next(
                (f for f in z.namelist() if re.match(r'^Payload/[^/]+\.app/Info\.plist$', f)),
                None
            )
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
    except Exception as e:
        # FIX 2: Không nuốt exception âm thầm
        print(f"⚠️ Lỗi đọc IPA {path}: {e}", flush=True)
    return str(version), str(bid), permissions, str(min_os), str(build_ver)


def get_itunes_info(bundle_id):
    """Tra cứu dữ liệu ứng dụng trên App Store Việt Nam theo Bundle ID"""
    if not bundle_id or bundle_id == "com.kyic.unknown":
        return None
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
    except Exception as e:
        # FIX 2: Log lỗi iTunes thay vì bỏ qua
        print(f"⚠️ Lỗi tra cứu iTunes [{bundle_id}]: {e}", flush=True)
    return None


def get_local_assets_ipa(name):
    """Quét và lấy liên kết tài nguyên ảnh cục bộ trong kho bãi nếu có sẵn"""
    exts = ['.png', '.jpg', '.jpeg', '.webp']

    def build_asset_url(dir_name, file_name):
        return f"{config.RAW_URL.rstrip('/')}/{dir_name.strip('/')}/{file_name}"

    icon_url = next(
        (build_asset_url(config.ICON_DIR_NAME, f"{name}{e}")
         for e in exts if os.path.exists(os.path.join(config.ICON_DIR, f"{name}{e}"))),
        None
    )
    
    # FIX: Banner lấy từ images/<AppName>/ (subfolder, không phẳng)
    app_img_dir = config.get_app_images_dir(name)
    banner_url = next(
        (build_asset_url(config.IMG_DIR_NAME, f"{name}/{name}_banner{e}")
         for e in exts if os.path.exists(os.path.join(app_img_dir, f"{name}_banner{e}"))),
        None
    )

    # FIX: Screenshots lấy từ images/<AppName>/
    screens = []
    i = 1
    while True:
        found = False
        for e in exts:
            file_path = os.path.join(app_img_dir, f"{name}_{i}{e}")
            if os.path.exists(file_path):
                screens.append(build_asset_url(config.IMG_DIR_NAME, f"{name}/{name}_{i}{e}"))
                found = True
                break
        if not found:
            break
        i += 1

    return {"icon": icon_url, "banner": banner_url, "screenshots": screens}


def _download_ipa_safe(url, temp_path):
    """
    FIX 3: Tải IPA có timeout + try/except thay vì urlretrieve trần
    Trả về True nếu thành công, False nếu thất bại
    """
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)'}
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            with open(temp_path, 'wb') as f:
                f.write(response.read())

        # FIX: Kiểm tra file tải về không rỗng
        if os.path.getsize(temp_path) == 0:
            print(f"⚠️ File tải về rỗng (0 bytes): {url}", flush=True)
            os.remove(temp_path)
            return False

        return True
    except Exception as e:
        print(f"❌ Lỗi tải IPA [{url}]: {e}", flush=True)
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return False


def _get_local_file_date(path):
    """
    FIX 4: Lấy ngày sửa file local thay vì trả về chuỗi "Local"
    Trả về ISO 8601 UTC timestamp
    """
    try:
        mtime = os.path.getmtime(path)
        return datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_feather_engine(release_assets, feather_db):
    """🌟 PHÂN HỆ XỬ LÝ CHÍNH: Quét tài nguyên IPA và đóng gói cấu trúc Feather JSON"""
    if "apps" not in feather_db:
        feather_db["apps"] = {}

    apps_map = defaultdict(list)

    def build_asset_url(dir_name, file_name):
        return f"{config.RAW_URL.rstrip('/')}/{dir_name.strip('/')}/{file_name}"

    to_process = []
    processed_names = []

    # Thu thập IPA từ thư mục local (hỗ trợ cấu trúc nested: repo/apps/AppName/AppName.ipa)
    if os.path.exists(config.APPS_INPUT_DIR):
        # FIX: Quét từng thư mục app con, sau đó quét .ipa bên trong
        for entry in os.listdir(config.APPS_INPUT_DIR):
            # Bỏ qua thư mục đặc biệt
            if entry.startswith('.') or entry == 'desc':
                continue
            
            entry_path = os.path.join(config.APPS_INPUT_DIR, entry)
            
            # Nếu là file (cũ) → xử lý như trước
            if os.path.isfile(entry_path) and entry.endswith(".ipa"):
                full_path = entry_path
                to_process.append({
                    "name": entry,
                    "url": f"{config.BASE_URL}apps/{entry}",
                    "path": full_path,
                    "is_cloud": False,
                    "date": _get_local_file_date(full_path)
                })
            # Nếu là folder (mới) → quét .ipa bên trong
            elif os.path.isdir(entry_path):
                for f in os.listdir(entry_path):
                    if f.endswith(".ipa"):
                        full_path = os.path.join(entry_path, f)
                        to_process.append({
                            "name": f,
                            "url": f"{config.BASE_URL}apps/{entry}/{f}",
                            "path": full_path,
                            "is_cloud": False,
                            "date": _get_local_file_date(full_path)
                        })

    # Thu thập IPA từ GitHub Releases
    for asset in release_assets:
        if asset["name"].endswith(".ipa"):
            to_process.append({
                "name": asset["name"],
                "url": asset["url"],
                "is_cloud": True,
                "size": asset["size"],
                "date": asset["date"],
                "note": asset.get("body")
            })

    for item in to_process:
        f_name, f_url = item["name"], item["url"]
        # FIX: Extract app name từ IPA filename một cách đúng đắn
        # Logic: Telegram.1.0.ipa hoặc Telegram_1.0.ipa → "Telegram"
        # 1. Bỏ extension .ipa
        name_no_ext = f_name.rsplit('.', 1)[0]
        # 2. Tách bằng '_' hoặc '.' để lấy phần đầu (tên app thực)
        # Tìm ký tự đầu tiên là '_' hoặc '.', lấy phần trước đó
        clean_name = re.split(r'[_.]', name_no_ext)[0]
        # 3. Fallback nếu rỗng (không nên xảy ra)
        if not clean_name:
            clean_name = name_no_ext
        
        curr_size = item.get("size") if item.get("is_cloud") else os.path.getsize(item["path"])

        print(f"-> Đang xử lý IPA: {f_name}", flush=True)
        processed_names.append(clean_name)

        cached = feather_db["apps"].get(f_url)

        # FIX: Kiểm tra cache đầy đủ field trước khi dùng
        required_fields = {"bid", "ver", "size", "icon", "banner", "screenshots", "desc", "permissions", "minOS", "buildVersion"}
        cache_valid = (
            cached is not None
            and cached.get("size") == curr_size
            and required_fields.issubset(cached.keys())
        )

        if cache_valid:
            data = cached
            apps_map[data['bid']].append({
                "name": clean_name, "ver": data['ver'], "bid": data['bid'],
                "dl": f_url, "sz": curr_size, "date": item.get("date"),
                "minOS": data['minOS'], "buildVersion": data['buildVersion'],
                "note": item.get("note")
            })
        else:
            if item["is_cloud"]:
                temp_path = os.path.join(config.REPO_ROOT, f"temp_{f_name}")
                print(f"📸 Đang tải và phân tích cấu trúc IPA từ đám mây: {clean_name}", flush=True)
                # FIX 3: Dùng hàm tải an toàn có timeout
                if not _download_ipa_safe(f_url, temp_path):
                    print(f"⚠️ Bỏ qua {f_name} do lỗi tải file.", flush=True)
                    continue
                ver, bid, perms, min_os, build_ver = extract_ipa_permissions_and_data(temp_path)
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            else:
                ver, bid, perms, min_os, build_ver = extract_ipa_permissions_and_data(item["path"])

            info = get_itunes_info(bid)
            local = get_local_assets_ipa(clean_name)

            # Đồng bộ Icon
            icon = local['icon']
            if not icon and info and info.get('icon'):
                path = os.path.join(config.ICON_DIR, f"{clean_name}.jpg")
                if utils.download_resource_to_local(info['icon'], path):
                    icon = build_asset_url(config.ICON_DIR_NAME, f"{clean_name}.jpg")
            if not icon:
                icon = config.SOURCE_LOGO

            # Đồng bộ Banner — FIX: lưu vào images/<AppName>/
            banner = local['banner']
            if not banner and info and info.get('banner'):
                app_img_dir = config.get_app_images_dir(clean_name)
                os.makedirs(app_img_dir, exist_ok=True)
                path = os.path.join(app_img_dir, f"{clean_name}_banner.jpg")
                if utils.download_resource_to_local(info['banner'], path):
                    banner = build_asset_url(config.IMG_DIR_NAME, f"{clean_name}/{clean_name}_banner.jpg")
            if not banner:
                banner = config.DEFAULT_BANNER

            # Đồng bộ Screenshots — FIX: lưu vào images/<AppName>/
            screens = local['screenshots']
            if not screens and info and info.get('screenshots'):
                app_img_dir = config.get_app_images_dir(clean_name)
                os.makedirs(app_img_dir, exist_ok=True)
                dl_screens = []
                for idx, url in enumerate(info['screenshots']):
                    path = os.path.join(app_img_dir, f"{clean_name}_{idx + 1}.jpg")
                    if utils.download_resource_to_local(url, path):
                        dl_screens.append(build_asset_url(config.IMG_DIR_NAME, f"{clean_name}/{clean_name}_{idx + 1}.jpg"))
                if dl_screens:
                    screens = dl_screens
            if not screens:
                screens = utils.get_default_screens()

            desc = (info['desc'] if info else None) or f"Ứng dụng {clean_name} từ Kyic Store."

            feather_db["apps"][f_url] = {
                "bid": str(bid), "ver": str(ver), "name": clean_name,
                "size": curr_size, "icon": icon, "banner": banner,
                "screenshots": screens, "desc": desc,
                "permissions": perms, "minOS": min_os, "buildVersion": build_ver
            }
            apps_map[bid].append({
                "name": clean_name, "ver": str(ver), "bid": str(bid),
                "dl": f_url, "sz": curr_size, "date": item.get("date"),
                "minOS": min_os, "buildVersion": build_ver, "note": item.get("note")
            })

    final_apps = []
    for bid, versions in apps_map.items():
        # FIX 1: Deduplicate theo version trước khi sort
        seen_versions = {}
        for v in versions:
            ver_key = str(v['ver'])
            # Ưu tiên giữ bản cloud (có date thực) hơn bản local nếu trùng version
            if ver_key not in seen_versions or v.get('dl', '').startswith('http'):
                seen_versions[ver_key] = v
        unique_versions = list(seen_versions.values())

        # FIX 1: Sort theo tuple số, không theo string
        unique_versions.sort(key=lambda x: utils.parse_version_tuple(x['ver']), reverse=True)

        latest = unique_versions[0]
        data = feather_db["apps"].get(latest['dl'])

        if not data:
            print(f"⚠️ Không tìm thấy cache cho {latest['dl']}, bỏ qua.", flush=True)
            continue

        v_date = latest['date'] or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # FIX: Tách biến dùng chung thay vì lặp lại inline
        fallback_identifier = final_apps[0]['bundleIdentifier'] if final_apps else config.SOURCE_IDENTIFIER

        app_item = {
            "name": str(latest['name']),
            "bundleIdentifier": str(bid),
            "developerName": "Kyic Store",
            "subtitle": "Phiên bản Premium",
            "localizedDescription": utils.smart_truncate_description(data['desc']),
            "iconURL": utils.clean_github_url(data['icon']),
            "tintColor": config.TINT_COLOR,  # FIX: Đưa vào config, không hardcode
            "version": str(latest['ver']),
            "versionDate": v_date,
            "size": int(latest['sz']),
            "downloadURL": str(latest['dl']),
            "versions": [
                {
                    "version": v['ver'],
                    "date": v['date'],
                    "size": v['sz'],
                    "downloadURL": v['dl'],
                    "localizedDescription": get_optimized_description(v['name'], v['ver'], v.get('note'))
                }
                for v in unique_versions
            ],
            "screenshotURLs": [utils.clean_github_url(s) for s in data['screenshots']],
            "videoURL": utils.clean_github_url(config.DEFAULT_VIDEO),
            "appPermissions": utils.format_permissions(data['permissions'])
        }
        final_apps.append(app_item)

    final_apps.sort(key=lambda x: x['name'].lower())

    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    first_bid = final_apps[0]['bundleIdentifier'] if final_apps else config.SOURCE_IDENTIFIER

    news_list = [
        {
            "title": "Donate",
            "identifier": "feather-donate",
            "caption": "Ủng hộ Kyic Store!",
            "date": today,
            "imageURL": utils.clean_github_url(config.NEWS_DONATE_IMAGE),
            "url": "https://www.paypal.me/225668",
            "appIdentifier": first_bid
        },
        {
            "title": "About",
            "identifier": "feather-about",
            "caption": "Chào mừng!",
            "date": today,
            "imageURL": utils.clean_github_url(config.NEWS_ABOUT_IMAGE),
            "url": "https://github.com/2KGT/repo/blob/main/README.md",
            "appIdentifier": first_bid
        }
    ]

    if final_apps:
        latest_app = final_apps[0]
        news_list.insert(0, {
            "title": f"App mới: {latest_app['name']}",
            "identifier": f"new-{latest_app['bundleIdentifier']}",
            "caption": f"Phiên bản {latest_app['version']} đã sẵn sàng.",
            "date": today,
            "imageURL": latest_app['iconURL'],
            "url": "https://github.com/2KGT/repo/blob/main/README.md",
            "appIdentifier": latest_app['bundleIdentifier']
        })

    output_json = {
        "name": config.REPO_NAME,
        "identifier": config.SOURCE_IDENTIFIER,
        "iconURL": utils.clean_github_url(config.SOURCE_LOGO),
        "apps": final_apps,
        "news": news_list
    }

    with open(os.path.join(config.REPO_OUTPUT_DIR, 'apps.json'), 'w', encoding='utf-8') as f:
        json.dump(output_json, f, indent=2, ensure_ascii=False)

    return processed_names

