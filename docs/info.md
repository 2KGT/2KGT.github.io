# 📂 CẤU TRÚC HỆ THỐNG
⏱️ *Cập nhật tự động lúc: 11/07/2026 14:49:06 (Giờ Hà Nội)*

```text
🗺️ Root/
├── .commit_msg
├── .gitattributes
├── 📂 .github/
│   ├── 📂 ISSUE_TEMPLATE/
│   │   ├── config.yml
│   │   ├── en_bug_report.yml
│   │   ├── en_feature_request.yml
│   │   ├── vi_bug.yml
│   │   └── vi_feature.yml
│   ├── 📂 scripts/
│   │   ├── ._sync.py
│   │   ├── clean.py
│   │   ├── config.py
│   │   ├── 📂 core/
│   │   │   ├── __init__.py
│   │   │   ├── dylib_engine.py
│   │   │   ├── feather_engine.py
│   │   │   ├── sileo_engine.py
│   │   │   └── utils.py
│   │   ├── data.py
│   │   ├── gemini.py
│   │   ├── github.py
│   │   ├── logs.py
│   │   ├── main.py
│   │   ├── notify.py
│   │   └── views.py
│   └── 📂 workflows/
│       └── Auto-sync-feather-sileo.yml
├── .gitignore
├── .nojekyll
├── 📂 FAQs/
│   ├── FAQ.md
│   └── FAQ_EN.md
├── LICENSE
├── README.md
├── cliff.toml
├── index.html
├── 📂 repo/
│   ├── Packages
│   ├── Packages.bz2
│   ├── README.md
│   ├── Release
│   ├── 📂 apps/
│   │   ├── 📂 AllSign/
│   │   │   ├── .gitkeep
│   │   │   └── [ 📊 Số lượng: 📱 Apps iOS .ipa: 1 file ]
│   │   ├── 📂 ESign/
│   │   │   ├── .gitkeep
│   │   │   └── [ 📊 Số lượng: 📱 Apps iOS .ipa: 1 file ]
│   │   ├── 📂 Feather/
│   │   │   ├── .gitkeep
│   │   │   └── [ 📊 Số lượng: 📱 Apps iOS .ipa: 1 file ]
│   │   ├── 📂 GBox/
│   │   │   └── .gitkeep
│   │   ├── 📂 LCSign/
│   │   │   ├── .gitkeep
│   │   │   └── [ 📊 Số lượng: 📱 Apps iOS .ipa: 1 file ]
│   │   ├── 📂 Lithium/
│   │   │   └── .gitkeep
│   │   ├── 📂 MuteOTA/
│   │   │   ├── .gitkeep
│   │   │   └── [ 📊 Số lượng: 📱 Apps iOS .ipa: 1 file ]
│   │   ├── 📂 Pocket/
│   │   │   ├── .gitkeep
│   │   │   └── [ 📊 Số lượng: 📱 Apps iOS .ipa: 1 file ]
│   │   ├── 📂 PostBox/
│   │   │   └── .gitkeep
│   │   └── 📂 Zebra/
│   │       └── .gitkeep
│   ├── 📂 data/
│   │   ├── 📂 default/
│   │   │   ├── .gitkeep
│   │   │   ├── Kyic_banner.webp
│   │   │   ├── Kyic_video.mp4
│   │   │   └── [ 📊 Số lượng: 📸 Ảnh JPEG: 8 file, 🖼️ Ảnh PNG: 4 file ]
│   │   ├── 📂 desc/
│   │   │   ├── 📂 apps/
│   │   │   │   ├── 📂 BiliBili/
│   │   │   │   │   └── v2.70.0.txt
│   │   │   │   ├── 📂 DLiPA/
│   │   │   │   │   └── v1.3.txt
│   │   │   │   ├── 📂 ESign/
│   │   │   │   ├── 📂 Facebook/
│   │   │   │   │   ├── v519.0.0.txt
│   │   │   │   │   ├── v538.1.0.txt
│   │   │   │   │   ├── v551.1.0.txt
│   │   │   │   │   └── v565.0.0.txt
│   │   │   │   ├── 📂 Feather/
│   │   │   │   ├── 📂 Instagram/
│   │   │   │   │   ├── v419.0.0.txt
│   │   │   │   │   ├── v433.0.0.txt
│   │   │   │   │   └── v435.1.0.txt
│   │   │   │   ├── 📂 LCSign/
│   │   │   │   │   ├── v1.1.6.txt
│   │   │   │   │   ├── v1.1.txt
│   │   │   │   │   └── v1.2.txt
│   │   │   │   ├── 📂 LCSign-1/
│   │   │   │   │   └── v1.2.txt
│   │   │   │   ├── 📂 MuteOTA/
│   │   │   │   │   └── v1.2.txt
│   │   │   │   ├── 📂 Phim4K/
│   │   │   │   │   ├── v2.2.2.txt
│   │   │   │   │   └── v2.3.1.txt
│   │   │   │   ├── 📂 Pocket/
│   │   │   │   ├── 📂 SPAMSMS/
│   │   │   │   │   └── v1.0.0.txt
│   │   │   │   ├── 📂 Stay/
│   │   │   │   │   ├── v2.9.18.txt
│   │   │   │   │   └── v2.9.20.txt
│   │   │   │   ├── 📂 Telegram/
│   │   │   │   │   ├── v12.6.3.txt
│   │   │   │   │   └── v12.8.txt
│   │   │   │   ├── 📂 Turrit/
│   │   │   │   │   ├── v1.4.6.txt
│   │   │   │   │   ├── v1.4.7.txt
│   │   │   │   │   ├── v1.4.8.txt
│   │   │   │   │   ├── v1.4.9.txt
│   │   │   │   │   └── v1.5.0.txt
│   │   │   │   ├── 📂 UnKeySign/
│   │   │   │   │   └── v1.1.8.txt
│   │   │   │   ├── 📂 YouTube/
│   │   │   │   │   ├── v21.16.2.txt
│   │   │   │   │   ├── v21.17.3.txt
│   │   │   │   │   ├── v21.22.3.txt
│   │   │   │   │   ├── v21.24.3.txt
│   │   │   │   │   └── v21.25.5.txt
│   │   │   │   ├── 📂 Zebra/
│   │   │   │   │   └── v1.1.28.txt
│   │   │   │   └── 📂 全能签/
│   │   │   ├── 📂 dylibs/
│   │   │   │   ├── 📂 AutoRevenuecat/
│   │   │   │   │   ├── v1.3.1.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 3 file ]
│   │   │   │   ├── 📂 Autocat/
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 3 file ]
│   │   │   │   ├── 📂 DLTwitter/
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   │   ├── 📂 FbStorySeen/
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   │   ├── 📂 FixIpa/
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   │   ├── 📂 Ghi âm tắt màn/
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   │   ├── 📂 Lead/
│   │   │   │   │   ├── v1.3.3.txt
│   │   │   │   │   ├── v1.4.2.txt
│   │   │   │   │   ├── v1.4.3.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 3 file ]
│   │   │   │   ├── 📂 LoadControl/
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   │   ├── 📂 SideloadFixerLol/
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   │   ├── 📂 SideloadKeychainFix/
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   │   ├── 📂 Sideloadbypass1/
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   │   ├── 📂 Sideloadbypass2/
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   │   ├── 📂 TWIGalaxy/
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   │   ├── 📂 TwitDate/
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   │   └── 📂 XLogin/
│   │   │   │       └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   ├── 📂 tweaks/
│   │   │   │   ├── 📂 BHTwitter/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   │   ├── 📂 Lead/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   ├── v1.4.3.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 10 file ]
│   │   │   │   ├── 📂 NFB/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 2 file ]
│   │   │   │   ├── 📂 NoYTPremium/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   │   ├── 📂 TGExtra/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 3 file ]
│   │   │   │   ├── 📂 YTUnShorts/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   │   ├── 📂 YTVideoOverlay/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   │   ├── 📂 YouGroupSettings/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   │   ├── 📂 YouMute/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   │   ├── 📂 YouSpeed/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   │   ├── 📂 YouTube Fix/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   │   ├── 📂 YouTube X/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   │   ├── 📂 bilibili/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   │   ├── 📂 cc18/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 3 file ]
│   │   │   │   ├── 📂 ccappicon/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 3 file ]
│   │   │   │   ├── 📂 fastlock/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 9 file ]
│   │   │   │   ├── 📂 flow/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 3 file ]
│   │   │   │   ├── 📂 glow/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 18 file ]
│   │   │   │   ├── 📂 infuseplus/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 18 file ]
│   │   │   │   ├── 📂 oledkeyboard/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 3 file ]
│   │   │   │   ├── 📂 orwellvk/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 6 file ]
│   │   │   │   ├── 📂 tweach/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 12 file ]
│   │   │   │   ├── 📂 twlegacy/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 3 file ]
│   │   │   │   ├── 📂 youmod/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
│   │   │   │   ├── 📂 youpip/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 2 file ]
│   │   │   │   ├── 📂 youspeed/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 2 file ]
│   │   │   │   ├── 📂 yt-native-share/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 3 file ]
│   │   │   │   ├── 📂 ytmu/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 9 file ]
│   │   │   │   ├── 📂 ytplus/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 18 file ]
│   │   │   │   ├── 📂 ytuhd/
│   │   │   │   │   ├── default.txt
│   │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 2 file ]
│   │   │   │   └── 📂 ytvideooverlay/
│   │   │   │       ├── default.txt
│   │   │   │       └── [ 📊 Số lượng: ⚙️ Config .json: 2 file ]
│   │   │   └── 📂 wiki/
│   │   │       └── [ 📊 Số lượng: ⚙️ Config .json: 3 file ]
│   │   ├── 📂 icons/
│   │   │   └── [ 📊 Số lượng: 📸 Ảnh JPG: 18 file, 🖼️ Ảnh PNG: 17 file ]
│   │   └── 📂 images/
│   │       ├── 📂 AutoAC/
│   │       │   ├── .gitkeep
│   │       │   └── [ 📊 Số lượng: 🖼️ Ảnh PNG: 3 file ]
│   │       ├── 📂 DLiPA/
│   │       │   ├── .gitkeep
│   │       │   └── [ 📊 Số lượng: 🖼️ Ảnh PNG: 5 file ]
│   │       ├── 📂 Facebook/
│   │       │   └── [ 📊 Số lượng: 📸 Ảnh JPG: 11 file ]
│   │       ├── 📂 Feather/
│   │       │   ├── .gitkeep
│   │       │   └── [ 📊 Số lượng: 🖼️ Ảnh PNG: 4 file ]
│   │       ├── 📂 Instagram/
│   │       │   └── [ 📊 Số lượng: 📸 Ảnh JPG: 9 file ]
│   │       ├── 📂 Lead/
│   │       │   ├── .gitkeep
│   │       │   └── [ 📊 Số lượng: 📸 Ảnh JPG: 1 file ]
│   │       ├── 📂 Stay/
│   │       │   └── [ 📊 Số lượng: 📸 Ảnh JPG: 5 file ]
│   │       ├── 📂 TGEXtra/
│   │       │   ├── .gitkeep
│   │       │   └── [ 📊 Số lượng: 📸 Ảnh JPG: 1 file ]
│   │       ├── 📂 Telegram/
│   │       │   └── [ 📊 Số lượng: 📸 Ảnh JPG: 8 file ]
│   │       ├── 📂 Turrit/
│   │       │   └── [ 📊 Số lượng: 📸 Ảnh JPG: 9 file ]
│   │       ├── 📂 YouTube/
│   │       │   ├── .gitkeep
│   │       │   └── [ 📊 Số lượng: 📸 Ảnh JPG: 6 file ]
│   │       └── 📂 ytplus/
│   │           ├── .gitkeep
│   │           └── [ 📊 Số lượng: 📸 Ảnh JPG: 8 file, 🖼️ Ảnh PNG: 1 file ]
│   ├── 📂 debs/
│   │   ├── 📂 BHTwitter/
│   │   │   ├── .gitkeep
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 1 file ]
│   │   ├── 📂 Lead/
│   │   │   ├── .gitkeep
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 9 file ]
│   │   ├── 📂 NFB/
│   │   │   ├── .gitkepp
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 1 file ]
│   │   ├── 📂 TGExtra/
│   │   │   ├── .gitkeep
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 3 file ]
│   │   ├── 📂 YoutubeX/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 1 file ]
│   │   ├── 📂 bilibili/
│   │   │   ├── .gitkeep
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 1 file ]
│   │   ├── 📂 cc18/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 3 file ]
│   │   ├── 📂 ccappicon/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 3 file ]
│   │   ├── 📂 fastlock/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 9 file ]
│   │   ├── 📂 flow/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 3 file ]
│   │   ├── 📂 glow/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 18 file ]
│   │   ├── 📂 infuseplus/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 18 file ]
│   │   ├── 📂 noytpremium/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 1 file ]
│   │   ├── 📂 oledkeyboard/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 3 file ]
│   │   ├── 📂 orwellvk/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 6 file ]
│   │   ├── 📂 tweach/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 12 file ]
│   │   ├── 📂 twlegacy/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 3 file ]
│   │   ├── 📂 yougroupsettings/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 1 file ]
│   │   ├── 📂 youmod/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 1 file ]
│   │   ├── 📂 youmute/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 1 file ]
│   │   ├── 📂 youpip/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 2 file ]
│   │   ├── 📂 youspeed/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 3 file ]
│   │   ├── 📂 youtubefix/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 1 file ]
│   │   ├── 📂 yt-native-share/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 3 file ]
│   │   ├── 📂 ytmu/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 9 file ]
│   │   ├── 📂 ytplus/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 18 file ]
│   │   ├── 📂 ytuhd/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 2 file ]
│   │   ├── 📂 ytunshorts/
│   │   │   └── [ 📊 Số lượng: 📦 Package .deb: 1 file ]
│   │   └── 📂 ytvideooverlay/
│   │       └── [ 📊 Số lượng: 📦 Package .deb: 3 file ]
│   ├── 📂 dylibs/
│   │   ├── .gitkeep
│   │   ├── 📂 FbStorySeen/
│   │   │   ├── .gitkeep
│   │   │   └── FbStorySeen.dylib
│   │   ├── 📂 Ghi âm tắt màn/
│   │   │   ├── .gitkeep
│   │   │   └── Ghi âm tắt màn.dylib
│   │   ├── 📂 SideloadFix/
│   │   │   ├── .gitkeep
│   │   │   ├── FixIpa.dylib
│   │   │   ├── LoadControl.dylib
│   │   │   ├── Sideloadbypass1.dylib
│   │   │   ├── Sideloadbypass2.dylib
│   │   │   ├── sideloadFixerLol.dylib
│   │   │   └── sideloadKeychainFix.dylib
│   │   ├── 📂 X-Plugins/
│   │   │   ├── .gitkeep
│   │   │   ├── DLTwitter.dylib
│   │   │   ├── TWIGalaxy.dylib
│   │   │   └── TwitDate.dylib
│   │   ├── 📂 XLogin/
│   │   │   ├── .gitkeep
│   │   │   └── XLogin.dylib
│   │   └── 📂 autoCat/
│   │       ├── .gitkeep
│   │       ├── com.kyic.autocat_1.3.1_iphoneos-arm.dylib
│   │       ├── com.kyic.autocat_1.3.1_iphoneos-arm64.dylib
│   │       └── com.kyic.autocat_1.3.1_iphoneos-arm64e.dylib
│   ├── 📂 html/
│   │   ├── .gitkeep
│   │   ├── apps.html
│   │   ├── auth.html
│   │   ├── checkout-cancel.html
│   │   ├── checkout-success.html
│   │   ├── dashboard.html
│   │   ├── debs.html
│   │   ├── dylibs.html
│   │   ├── index.html
│   │   ├── shop.html
│   │   └── sign.html
│   ├── index.html
│   └── [ 📊 Số lượng: ⚙️ Config .json: 3 file, 🖼️ Ảnh PNG: 1 file ]
└── 📂 supabase/
    ├── .gitkeep
    └── 📂 functions/
        ├── .gitkeep
        ├── 📂 create-order/
        │   ├── .gitkeep
        │   └── index.ts
        ├── 📂 issue-license/
        │   ├── .gitkeep
        │   └── index.ts
        └── 📂 udid-capture/
            ├── .gitkeep
            └── index.ts
```
