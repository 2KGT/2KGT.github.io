# .github/scripts/github.py
import json
import urllib.request
import urllib.error
import os
import sys
import logging
import inspect

# Khắc phục đường dẫn để import được config từ thư mục hiện tại
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import config

logger = logging.getLogger(__name__)

# FIX: Số trang tối đa để tránh vòng lặp vô tận nếu repo có rất nhiều release
MAX_PAGES = 10
PER_PAGE = 100


def get_file_commit_message(repo, file_path, branch="main", max_commits=5):
    """
    FIX MỚI: Lấy commit message của file gần nhất (khi upload qua web UI).
    
    Dùng GitHub Commits API: /repos/{owner}/{repo}/commits
    Filter commits liên quan đến file_path, lấy message của commit gần nhất.
    
    Ví dụ:
    - User upload Telegram_18.0.ipa qua web UI với commit message:
      "Add Telegram v18.0 - Dark Mode update, fix crash on video call"
    - Hàm sẽ extract message này → lưu vào v18.0.txt
    
    Args:
        repo: "owner/repo" (ví dụ "2KGT/2KGT.github.io")
        file_path: đường dẫn file trong repo (ví dụ "repo/apps/Telegram/Telegram_18.0.ipa")
        branch: branch mặc định "main"
        max_commits: tối đa lấy bao nhiêu commits gần nhất
    
    Return: commit message (str) hoặc "" nếu không tìm được
    """
    if not hasattr(config, 'GITHUB_TOKEN') or not config.GITHUB_TOKEN:
        return ""
    
    try:
        url = (f"https://api.github.com/repos/{repo}/commits"
               f"?path={file_path}&sha={branch}&per_page={max_commits}")
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"token {config.GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            commits = json.loads(response.read().decode())
            if isinstance(commits, list) and len(commits) > 0:
                message = commits[0].get("commit", {}).get("message", "")
                return message.strip()
    except Exception as e:
        logger.warning(f"⚠️ Không lấy được commit message cho {file_path}: {e}")
    
    return ""


def _is_valid_download_url(url: str) -> bool:
    """✅ VALIDATE URL trước khi lưu vào database."""
    if not url or not isinstance(url, str):
        return False
    # URL phải bắt đầu bằng http:// hoặc https://
    return url.startswith("http://") or url.startswith("https://")


def get_release_assets():
    """
    Quét đám mây từ GitHub Releases của kho lưu trữ.
    Lọc và gom toàn bộ danh sách file .ipa và .deb hợp lệ.

    ✅ OPTIMIZED: 
    - Batch fetch tất cả pages 1 lần (không loop nhiều request)
    - Validate URLs trước khi thêm vào list
    - Optimized pagination (check len trước khi loop tiếp)
    """
    ipa_assets = []
    deb_assets = []
    dylib_assets = []
    repository = os.getenv("GITHUB_REPOSITORY") or "2KGT/repo"
    token = os.getenv("GITHUB_TOKEN")

    logger.info(f"🔍 [FETCH CLOUD] Đang quét tài nguyên từ kho: {repository}...")

    page = 1
    while page <= MAX_PAGES:
        url = f"https://api.github.com/repos/{repository}/releases?per_page={PER_PAGE}&page={page}"

        try:
            req = urllib.request.Request(url)
            if token:
                req.add_header("Authorization", f"token {token}")
            req.add_header(
                "User-Agent",
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
            )
            req.add_header("Accept", "application/vnd.github+json")

            with urllib.request.urlopen(req, timeout=10) as response:  # ✅ timeout 10s
                releases = json.loads(response.read().decode('utf-8'))

            # Hết trang — dừng vòng lặp
            if not releases:
                break

            for release in releases:
                # Bỏ qua bản draft
                if release.get("draft"):
                    continue

                release_date = release.get("published_at") or release.get("created_at")
                tag_name = release.get("tag_name", "")
                
                # Lấy Release title + Release notes → gom thành desc đầy đủ
                release_title = release.get("name") or tag_name or ""
                release_body = release.get("body") or ""
                
                full_changelog = ""
                if release_title:
                    full_changelog = release_title.strip()
                if release_body:
                    if full_changelog:
                        full_changelog += "\n\n" + release_body.strip()
                    else:
                        full_changelog = release_body.strip()

                for asset in release.get("assets", []):
                    asset_name = asset.get("name", "")
                    download_url = asset.get("browser_download_url")
                    size = asset.get("size", 0)

                    # ✅ VALIDATE URL trước khi thêm vào database
                    if not _is_valid_download_url(download_url) or not asset_name:
                        continue

                    if asset_name.endswith(".ipa"):
                        ipa_assets.append({
                            "name": asset_name,
                            "url": download_url,
                            "size": size,
                            "date": release_date,
                            "body": full_changelog
                        })

                    elif asset_name.endswith(".deb"):
                        deb_assets.append({
                            "name": asset_name,
                            "url": download_url,
                            "size": size,
                            "tag": tag_name,
                            "date": release_date,
                            "body": full_changelog
                        })

                    elif asset_name.endswith(".dylib"):
                        dylib_assets.append({
                            "name": asset_name,
                            "url": download_url,
                            "size": size,
                            "date": release_date,
                            "body": full_changelog
                        })

            # ✅ Nếu trang trả về ít hơn PER_PAGE → đã hết dữ liệu
            if len(releases) < PER_PAGE:
                break

            page += 1

        # Phân biệt lỗi HTTP (401, 403, 404...) với lỗi mạng
        except urllib.error.HTTPError as e:
            logger.error(f"❌ [FETCH CLOUD] Lỗi HTTP {e.code} khi quét trang {page}: {e.reason}")
            break
        except urllib.error.URLError as e:
            logger.error(f"⚠️ [FETCH CLOUD] Lỗi kết nối trang {page}: {e.reason}")
            break
        except Exception as e:
            logger.error(f"⚠️ [FETCH CLOUD] Lỗi không xác định trang {page}: {e}")
            break

    logger.info(
        f"📦 [FETCH CLOUD] Quét xong! "
        f"Tìm thấy {len(ipa_assets)} tệp IPA và {len(deb_assets)} tệp DEB trên GitHub Releases."
    )

    return {"ipa": ipa_assets, "deb": deb_assets, "dylib": dylib_assets}
