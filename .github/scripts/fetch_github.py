# .github/scripts/fetch_github.py
import json
import urllib.request
import os
import sys

# Khắc phục đường dẫn để import được config từ thư mục hiện tại
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import config

def get_release_assets():
    """
    Quét đám mây từ GitHub Releases của kho lưu trữ.
    Lọc và gom toàn bộ danh sách file .ipa và .deb hợp lệ.
    """
    ipa_assets = []
    deb_assets = []
    repository = os.getenv("GITHUB_REPOSITORY") or "2KGT/repo"
    token = os.getenv("GITHUB_TOKEN")
    url = f"https://api.github.com/repos/{repository}/releases"
    
    try:
        print(f"🔍 [FETCH CLOUD] Đang quét tài nguyên từ kho: {repository}...")
        req = urllib.request.Request(url)
        if token: 
            req.add_header("Authorization", f"token {token}")
        req.add_header("User-Agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15")
        
        with urllib.request.urlopen(req, timeout=15) as response:
            releases = json.loads(response.read().decode('utf-8'))
            for release in releases:
                if release.get("draft"): 
                    continue
                    
                release_date = release.get("published_at") or release.get("created_at")
                tag_name = release.get("tag_name", "")
                
                for asset in release.get("assets", []):
                    asset_name = asset.get("name", "")
                    download_url = asset.get("browser_download_url")
                    size = asset.get("size", 0)
                    
                    # 1. Gom file ứng dụng IPA
                    if asset_name.endswith(".ipa"):
                        ipa_assets.append({
                            "name": asset_name, 
                            "url": download_url, 
                            "size": size, 
                            "date": release_date
                        })
                    
                    # 2. 🔥 MỚI: Gom file tweak DEB từ Releases chính thức
                    elif asset_name.endswith(".deb"):
                        deb_assets.append({
                            "name": asset_name,
                            "url": download_url,
                            "size": size,
                            "tag": tag_name,
                            "date": release_date
                        })
                        
        print(f"📦 [FETCH CLOUD] Quét xong! Tìm thấy {len(ipa_assets)} tệp IPA và {len(deb_assets)} tệp DEB trên GitHub Releases.")
    except Exception as e:
        print(f"⚠️ [FETCH CLOUD] Không thể kết nối hoặc quét GitHub Release: {e}")
        
    # Trả về cả 2 mảng dữ liệu
    return {"ipa": ipa_assets, "deb": deb_assets}
