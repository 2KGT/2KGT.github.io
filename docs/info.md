# 📂 CẤU TRÚC HỆ THỐNG
⏱️ *Cập nhật tự động lúc: 21/06/2026 02:10:34 (Giờ Hà Nội)*

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
│   │   ├── config.py
│   │   ├── 📂 core/
│   │   │   ├── __init__.py
│   │   │   ├── dylib_engine.py
│   │   │   ├── feather_engine.py
│   │   │   ├── sileo_engine.py
│   │   │   └── utils.py
│   │   ├── gemini.py
│   │   ├── github.py
│   │   ├── logs.py
│   │   ├── main.py
│   │   └── views.py
│   └── 📂 workflows/
│       ├── Auto-sync-feather-sileo.yml
│       ├── Auto-sync-generate-info.yml
│       ├── Clean-commit-run-logs.yml
│       └── Clean-theos-stubborn.yml
├── .gitignore
├── .nojekyll
├── 📂 FAQs/
│   ├── FAQ.md
│   └── FAQ_EN.md
├── LICENSE
├── README.md
├── cliff.toml
├── index.html
└── 📂 repo/
    ├── Packages
    ├── Packages.bz2
    ├── README.md
    ├── Release
    ├── 📂 apps/
    │   ├── 📂 AllSign/
    │   │   ├── .gitkeep
    │   │   └── [ 📊 Số lượng: 📱 Apps iOS .ipa: 1 file ]
    │   ├── 📂 ESign/
    │   │   ├── .gitkeep
    │   │   └── [ 📊 Số lượng: 📱 Apps iOS .ipa: 1 file ]
    │   ├── 📂 Feather/
    │   │   ├── .gitkeep
    │   │   └── [ 📊 Số lượng: 📱 Apps iOS .ipa: 1 file ]
    │   ├── 📂 GBox/
    │   │   └── .gitkeep
    │   ├── 📂 LCSign/
    │   │   ├── .gitkeep
    │   │   └── [ 📊 Số lượng: 📱 Apps iOS .ipa: 1 file ]
    │   ├── 📂 Lithium/
    │   │   └── .gitkeep
    │   ├── 📂 MuteOTA/
    │   │   ├── .gitkeep
    │   │   └── [ 📊 Số lượng: 📱 Apps iOS .ipa: 1 file ]
    │   ├── 📂 Pocket/
    │   │   ├── .gitkeep
    │   │   └── [ 📊 Số lượng: 📱 Apps iOS .ipa: 1 file ]
    │   ├── 📂 PostBox/
    │   │   └── .gitkeep
    │   └── 📂 Zebra/
    │       └── .gitkeep
    ├── apps.html
    ├── 📂 data/
    │   ├── 📂 default/
    │   │   ├── .gitkeep
    │   │   ├── Kyic_video.mp4
    │   │   └── [ 📊 Số lượng: 📸 Ảnh JPEG: 8 file, 🖼️ Ảnh PNG: 4 file ]
    │   ├── 📂 desc/
    │   │   ├── 📂 apps/
    │   │   │   ├── 📂 BiliBili/
    │   │   │   │   └── v2.70.0.txt
    │   │   │   ├── 📂 DLiPA/
    │   │   │   │   └── v1.3.txt
    │   │   │   ├── 📂 Facebook/
    │   │   │   │   ├── v519.0.0.txt
    │   │   │   │   ├── v538.1.0.txt
    │   │   │   │   ├── v551.1.0.txt
    │   │   │   │   └── v565.0.0.txt
    │   │   │   ├── 📂 Instagram/
    │   │   │   │   ├── v419.0.0.txt
    │   │   │   │   └── v433.0.0.txt
    │   │   │   ├── 📂 LCSign/
    │   │   │   │   ├── v1.1.6.txt
    │   │   │   │   └── v1.1.txt
    │   │   │   ├── 📂 MuteOTA/
    │   │   │   │   └── v1.2.txt
    │   │   │   ├── 📂 Phim4K/
    │   │   │   │   ├── v2.2.2.txt
    │   │   │   │   └── v2.3.1.txt
    │   │   │   ├── 📂 SPAMSMS/
    │   │   │   │   └── v1.0.0.txt
    │   │   │   ├── 📂 Stay/
    │   │   │   │   ├── v2.9.18.txt
    │   │   │   │   └── v2.9.20.txt
    │   │   │   ├── 📂 Telegram/
    │   │   │   │   ├── v12.6.3.txt
    │   │   │   │   └── v12.8.txt
    │   │   │   ├── 📂 Turrit/
    │   │   │   │   ├── v1.4.6.txt
    │   │   │   │   ├── v1.4.7.txt
    │   │   │   │   └── v1.4.8.txt
    │   │   │   ├── 📂 UnKeySign/
    │   │   │   │   └── v1.1.8.txt
    │   │   │   ├── 📂 YouTube/
    │   │   │   │   ├── v21.16.2.txt
    │   │   │   │   ├── v21.17.3.txt
    │   │   │   │   ├── v21.22.3.txt
    │   │   │   │   └── v21.24.3.txt
    │   │   │   └── 📂 Zebra/
    │   │   │       └── v1.1.28.txt
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
    │   │   │   │   │   └── v433.0.0.txt
    │   │   │   │   ├── 📂 LCSign/
    │   │   │   │   │   ├── v1.1.6.txt
    │   │   │   │   │   └── v1.1.txt
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
    │   │   │   │   │   └── v1.4.8.txt
    │   │   │   │   ├── 📂 UnKeySign/
    │   │   │   │   │   └── v1.1.8.txt
    │   │   │   │   ├── 📂 YouTube/
    │   │   │   │   │   ├── v21.16.2.txt
    │   │   │   │   │   ├── v21.17.3.txt
    │   │   │   │   │   ├── v21.22.3.txt
    │   │   │   │   │   └── v21.24.3.txt
    │   │   │   │   ├── 📂 Zebra/
    │   │   │   │   │   └── v1.1.28.txt
    │   │   │   │   └── 📂 全能签/
    │   │   │   └── 📂 tweaks/
    │   │   │       ├── 📂 Lead/
    │   │   │       ├── 📂 TGExtra/
    │   │   │       ├── 📂 YoutubeX/
    │   │   │       ├── 📂 cc18/
    │   │   │       ├── 📂 ccappicon/
    │   │   │       ├── 📂 fastlock/
    │   │   │       ├── 📂 flow/
    │   │   │       ├── 📂 glow/
    │   │   │       ├── 📂 infuseplus/
    │   │   │       ├── 📂 noytpremium/
    │   │   │       ├── 📂 oledkeyboard/
    │   │   │       ├── 📂 orwellvk/
    │   │   │       ├── 📂 tweach/
    │   │   │       ├── 📂 twlegacy/
    │   │   │       ├── 📂 yougroupsettings/
    │   │   │       ├── 📂 youmod/
    │   │   │       ├── 📂 youmute/
    │   │   │       ├── 📂 youpip/
    │   │   │       ├── 📂 youspeed/
    │   │   │       ├── 📂 youtubefix/
    │   │   │       ├── 📂 yt-native-share/
    │   │   │       ├── 📂 ytmu/
    │   │   │       ├── 📂 ytplus/
    │   │   │       ├── 📂 ytuhd/
    │   │   │       ├── 📂 ytunshorts/
    │   │   │       └── 📂 ytvideooverlay/
    │   │   ├── 📂 tweaks/
    │   │   │   ├── 📂 Lead/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 9 file ]
    │   │   │   ├── 📂 TGExtra/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 3 file ]
    │   │   │   ├── 📂 YoutubeX/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
    │   │   │   ├── 📂 cc18/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 3 file ]
    │   │   │   ├── 📂 ccappicon/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 3 file ]
    │   │   │   ├── 📂 fastlock/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 9 file ]
    │   │   │   ├── 📂 flow/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 3 file ]
    │   │   │   ├── 📂 glow/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 18 file ]
    │   │   │   ├── 📂 infuseplus/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 18 file ]
    │   │   │   ├── 📂 noytpremium/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
    │   │   │   ├── 📂 oledkeyboard/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 3 file ]
    │   │   │   ├── 📂 orwellvk/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 6 file ]
    │   │   │   ├── 📂 tweach/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 12 file ]
    │   │   │   ├── 📂 twlegacy/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 3 file ]
    │   │   │   ├── 📂 yougroupsettings/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
    │   │   │   ├── 📂 youmod/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
    │   │   │   ├── 📂 youmute/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
    │   │   │   ├── 📂 youpip/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 2 file ]
    │   │   │   ├── 📂 youspeed/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 3 file ]
    │   │   │   ├── 📂 youtubefix/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
    │   │   │   ├── 📂 yt-native-share/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 3 file ]
    │   │   │   ├── 📂 ytmu/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 9 file ]
    │   │   │   ├── 📂 ytplus/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 18 file ]
    │   │   │   ├── 📂 ytuhd/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 2 file ]
    │   │   │   ├── 📂 ytunshorts/
    │   │   │   │   └── [ 📊 Số lượng: ⚙️ Config .json: 1 file ]
    │   │   │   └── 📂 ytvideooverlay/
    │   │   │       └── [ 📊 Số lượng: ⚙️ Config .json: 3 file ]
    │   │   └── 📂 wiki/
    │   │       └── [ 📊 Số lượng: ⚙️ Config .json: 3 file ]
    │   ├── 📂 icons/
    │   │   └── [ 📊 Số lượng: 📸 Ảnh JPG: 18 file, 🖼️ Ảnh PNG: 17 file ]
    │   └── 📂 images/
    │       ├── 📂 AutoAC/
    │       │   └── .gitkeep
    │       ├── 📂 AutoAC 2/
    │       │   ├── .gitkeep
    │       │   └── [ 📊 Số lượng: 🖼️ Ảnh PNG: 3 file ]
    │       ├── 📂 DLiPA/
    │       │   ├── .gitkeep
    │       │   └── [ 📊 Số lượng: 🖼️ Ảnh PNG: 5 file ]
    │       ├── 📂 Facebook/
    │       │   └── [ 📊 Số lượng: 📸 Ảnh JPG: 11 file ]
    │       ├── 📂 Feather/
    │       │   ├── .gitkeep
    │       │   └── [ 📊 Số lượng: 🖼️ Ảnh PNG: 4 file ]
    │       ├── 📂 Instagram/
    │       │   └── [ 📊 Số lượng: 📸 Ảnh JPG: 7 file ]
    │       ├── 📂 Lead/
    │       │   ├── .gitkeep
    │       │   └── [ 📊 Số lượng: 📸 Ảnh JPG: 1 file ]
    │       ├── 📂 Stay/
    │       │   └── [ 📊 Số lượng: 📸 Ảnh JPG: 5 file ]
    │       ├── 📂 TGEXtra/
    │       │   ├── .gitkeep
    │       │   └── [ 📊 Số lượng: 📸 Ảnh JPG: 1 file ]
    │       ├── 📂 Telegram/
    │       │   └── [ 📊 Số lượng: 📸 Ảnh JPG: 8 file ]
    │       ├── 📂 Turrit/
    │       │   └── [ 📊 Số lượng: 📸 Ảnh JPG: 9 file ]
    │       ├── 📂 YouTube/
    │       │   ├── .gitkeep
    │       │   └── [ 📊 Số lượng: 📸 Ảnh JPG: 6 file ]
    │       └── 📂 ytplus/
    │           ├── .gitkeep
    │           └── [ 📊 Số lượng: 📸 Ảnh JPG: 8 file, 🖼️ Ảnh PNG: 1 file ]
    ├── 📂 debs/
    │   ├── 📂 Lead/
    │   │   ├── .gitkeep
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 9 file ]
    │   ├── 📂 TGExtra/
    │   │   ├── .gitkeep
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 3 file ]
    │   ├── 📂 YoutubeX/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 1 file ]
    │   ├── 📂 cc18/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 3 file ]
    │   ├── 📂 ccappicon/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 3 file ]
    │   ├── 📂 fastlock/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 9 file ]
    │   ├── 📂 flow/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 3 file ]
    │   ├── 📂 glow/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 18 file ]
    │   ├── 📂 infuseplus/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 18 file ]
    │   ├── 📂 noytpremium/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 1 file ]
    │   ├── 📂 oledkeyboard/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 3 file ]
    │   ├── 📂 orwellvk/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 6 file ]
    │   ├── 📂 tweach/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 12 file ]
    │   ├── 📂 twlegacy/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 3 file ]
    │   ├── 📂 yougroupsettings/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 1 file ]
    │   ├── 📂 youmod/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 1 file ]
    │   ├── 📂 youmute/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 1 file ]
    │   ├── 📂 youpip/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 2 file ]
    │   ├── 📂 youspeed/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 3 file ]
    │   ├── 📂 youtubefix/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 1 file ]
    │   ├── 📂 yt-native-share/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 3 file ]
    │   ├── 📂 ytmu/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 9 file ]
    │   ├── 📂 ytplus/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 18 file ]
    │   ├── 📂 ytuhd/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 2 file ]
    │   ├── 📂 ytunshorts/
    │   │   └── [ 📊 Số lượng: 📦 Package .deb: 1 file ]
    │   └── 📂 ytvideooverlay/
    │       └── [ 📊 Số lượng: 📦 Package .deb: 3 file ]
    ├── 📂 depictions/
    │   ├── 📂 default/
    │   ├── 📂 icons/
    │   ├── 📂 images/
    │   └── 📂 metadata/
    ├── 📂 dylibs/
    │   ├── .gitkeep
    │   └── 📂 Lead/
    │       └── .gitkeep
    ├── dylibs.html
    ├── index.html
    ├── tweaks.html
    └── [ 📊 Số lượng: ⚙️ Config .json: 3 file, 🖼️ Ảnh PNG: 1 file ]
```
