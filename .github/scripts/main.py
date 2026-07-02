# .github/scripts/main.py
"""
main.py — Điều phối logic pipeline chính. Không xử lý data, không gửi thông báo trực tiếp.
"""

import os
import sys
import logging

import config
import data
import notify
import github
from core import feather_engine, sileo_engine, dylib_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


def main():
    logger.info("🎬 Khởi chạy hệ thống tự động hóa Kyic storage...")

    # 1. Nạp database
    feather_db, sileo_db, dylib_db = data.load_databases()
    feather_db.setdefault("apps", {})
    sileo_db.setdefault("tweaks", {})
    dylib_db.setdefault("dylibs", {})

    # 2. Quét GitHub Releases
    raw_assets  = github.get_release_assets()
    total_ipa   = len(raw_assets.get("ipa", []))
    total_deb   = len(raw_assets.get("deb", []))
    total_dylib = len(raw_assets.get("dylib", []))
    logger.info(f"📊 Quét đám mây: {total_ipa} IPA, {total_deb} DEB, {total_dylib} DYLIB.")
    # 3. Feather Engine — xử lý IPA
    logger.info("📂 Feather Engine...")
    processed_apps = feather_engine.run_feather_engine(raw_assets.get("ipa", []), feather_db)
    logger.info(f"📱 Apps: {', '.join(processed_apps) if processed_apps else 'Không có mới'}")
    # 4. Sileo Engine — xử lý DEB
    logger.info("⚙️ Sileo Engine...")
    processed_tweaks = sileo_engine.run_sileo_engine(raw_assets.get("deb", []), sileo_db)
    logger.info(f"📦 Tweaks: {', '.join(processed_tweaks) if processed_tweaks else 'Không có mới'}")

    # 5. Dylib Engine — xử lý DYLIB
    logger.info("📚 Dylib Engine...")
    dylib_engine.run_dylib_engine(raw_assets.get("dylib", []), sileo_db)
    logger.info("📚 Dylibs hoàn tất.")
    # 6. Lưu database + thống kê + commit message
    data.save_databases(feather_db, sileo_db, dylib_db)

    # 6b. Quét bảo mật toàn diện trước khi commit
    scan_result = data.scan_all(virustotal=True)
    if not scan_result["clean"]:
        logger.warning(f"🛡️ {scan_result['summary']}")
        for threat in scan_result["threats"][:10]:
            logger.warning(f"   {threat}")
    else:
        logger.info(f"🛡️ {scan_result['summary']}")
    stats = data.calculate_repo_statistics(raw_assets)
    data.save_commit_message(stats[0], stats[2])

    # 7. Thông báo Telegram — phân loại theo trigger
    event = os.getenv("GITHUB_EVENT_NAME", "push").lower()
    if event == "release":
        notify.notify_release_from_env()
    else:
        notify.notify_sync(processed_apps, processed_tweaks, stats)

    logger.info("🏁 [SUCCESS] Hoàn thành toàn bộ quy trình!")


if __name__ == "__main__":
    main()
