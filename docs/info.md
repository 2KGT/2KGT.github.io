# 📂 CẤU TRÚC HỆ THỐNG
⏱️ *Cập nhật tự động lúc: 02/06/2026 07:09:20 (ICT)*

```text
🗺️ Root/
├── .gitattributes
├── 📂 .github/
│   ├── 📂 ISSUE_TEMPLATE/
│   │   ├── config.yml
│   │   ├── en_bug_report.yml
│   │   ├── en_feature_request.yml
│   │   ├── vi_bug.yml
│   │   └── vi_feature.yml
│   ├── 📂 scripts/
│   │   ├── config.py
│   │   ├── 📂 core/
│   │   │   ├── __init__.py
│   │   │   ├── feather_engine.py
│   │   │   ├── sileo_engine.py
│   │   │   └── utils.py
│   │   ├── fetch_github.py
│   │   ├── gemini.py
│   │   ├── logger.py
│   │   ├── main.py
│   │   └── sync.py
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
├── 📂 docs/
│   ├── CHANGELOG.md
│   ├── SECURITY.md
│   ├── SUPPORT.md
│   └── info.md
├── generate_tree.py
├── index.html
└── 📂 repo/
    ├── Packages
    ├── Packages.bz2
    ├── README.md
    ├── Release
    ├── 📂 apps/
    │   ├── 📂 desc/
    │   │   ├── BiliBili.txt
    │   │   ├── ESign.txt
    │   │   ├── Feather.txt
    │   │   ├── GBox.txt
    │   │   ├── Instagram.txt
    │   │   ├── LCSign.txt
    │   │   ├── Lithium.txt
    │   │   ├── MuteOTA.txt
    │   │   ├── Phim.4K.txt
    │   │   ├── Stay.txt
    │   │   ├── Telegram.txt
    │   │   ├── Turrit.txt
    │   │   ├── UnKeySign.txt
    │   │   ├── YouTube.txt
    │   │   ├── Zebra.txt
    │   │   └── 全能签.txt
    │   └── [ 📊 Tóm tắt tài nguyên: 📱 Ứng dụng iOS .ipa: 13 file ]
    ├── 📂 debs/
    │   ├── 📂 YoutubeX/
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📦 Gói tinh chỉnh .deb: 1 file ]
    │   ├── 📂 cc18/
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📦 Gói tinh chỉnh .deb: 3 file ]
    │   ├── 📂 ccappicon/
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📦 Gói tinh chỉnh .deb: 3 file ]
    │   ├── 📂 fastlock/
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📦 Gói tinh chỉnh .deb: 9 file ]
    │   ├── 📂 flow/
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📦 Gói tinh chỉnh .deb: 3 file ]
    │   ├── 📂 glow/
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📦 Gói tinh chỉnh .deb: 18 file ]
    │   ├── 📂 infuseplus/
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📦 Gói tinh chỉnh .deb: 18 file ]
    │   ├── 📂 noytpremium/
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📦 Gói tinh chỉnh .deb: 1 file ]
    │   ├── 📂 oledkeyboard/
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📦 Gói tinh chỉnh .deb: 3 file ]
    │   ├── 📂 orwellvk/
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📦 Gói tinh chỉnh .deb: 6 file ]
    │   ├── 📂 tweach/
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📦 Gói tinh chỉnh .deb: 12 file ]
    │   ├── 📂 twlegacy/
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📦 Gói tinh chỉnh .deb: 3 file ]
    │   ├── 📂 yougroupsettings/
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📦 Gói tinh chỉnh .deb: 1 file ]
    │   ├── 📂 youmod/
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📦 Gói tinh chỉnh .deb: 1 file ]
    │   ├── 📂 youmute/
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📦 Gói tinh chỉnh .deb: 1 file ]
    │   ├── 📂 youspeed/
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📦 Gói tinh chỉnh .deb: 1 file ]
    │   ├── 📂 youtubefix/
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📦 Gói tinh chỉnh .deb: 1 file ]
    │   ├── 📂 yt-native-share/
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📦 Gói tinh chỉnh .deb: 3 file ]
    │   ├── 📂 ytmu/
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📦 Gói tinh chỉnh .deb: 9 file ]
    │   ├── 📂 ytplus/
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📦 Gói tinh chỉnh .deb: 18 file ]
    │   ├── 📂 ytunshorts/
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📦 Gói tinh chỉnh .deb: 1 file ]
    │   └── 📂 ytvideooverlay/
    │       └── [ 📊 Tóm tắt tài nguyên: 📦 Gói tinh chỉnh .deb: 1 file ]
    ├── 📂 depictions/
    │   ├── 📂 icons/
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📸 Ảnh JPG: 11 file, 🖼️ Ảnh PNG: 23 file ]
    │   ├── 📂 images/
    │   │   ├── Kyic.webm
    │   │   ├── Kyic_banner.mov
    │   │   └── [ 📊 Tóm tắt tài nguyên: 📸 Ảnh JPG: 44 file, 🖼️ Ảnh PNG: 12 file ]
    │   └── 📂 metadata/
    │       └── [ 📊 Tóm tắt tài nguyên: ⚙️ Cấu hình .json: 119 file ]
    └── [ 📊 Tóm tắt tài nguyên: ⚙️ Cấu hình .json: 2 file, 🖼️ Ảnh PNG: 1 file ]
```
