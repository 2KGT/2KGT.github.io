// ==UserScript==
// @name         Father Script Manager (With Dock Logic)
// @namespace    https://github.com/2KGT/2KGT.github.io
// @version      2.0
// @description  Quản lý tập trung, bật/tắt các script con trực tiếp qua Dock UI giao diện tiện lợi.
// @author       2KGT
// @match        *://*/*
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_registerMenuCommand
// @run-at       document-start
// ==/UserScript==

(function() {
    'use strict';

    // ==========================================
    // 1. CẤU HÌNH DỮ LIỆU CÁC SCRIPT CON (Đã update link)
    // ==========================================
    const subScripts = [
        {
            id: "abpvn_adsblock",
            name: "🛡️ ABPVN AdsBlock",
            url: "https://raw.githubusercontent.com/2KGT/2KGT.github.io/refs/heads/main/repo/js/ABPVN%20AdsBlock.user.js",
            matches: ["*://*/*"] // Chạy mọi nơi
        },
        {
            id: "yt_autotranslate",
            name: "📺 YouTube Auto-translate",
            url: "https://raw.githubusercontent.com/2KGT/2KGT.github.io/refs/heads/main/repo/js/ACT.YouTube.DM.Auto-translate.user.js",
            matches: ["*://*.youtube.com/*"] // Chỉ chạy ở YouTube
        },
        {
            id: "adguard_extra",
            name: "🧩 AdGuard Extra",
            url: "https://raw.githubusercontent.com/2KGT/2KGT.github.io/refs/heads/main/repo/js/AdGuard%20Extra.user.js",
            matches: ["*://*/*"]
        },
        {
            id: "adguard_popup",
            name: "🚫 AdGuard Popup Blocker",
            url: "https://raw.githubusercontent.com/2KGT/2KGT.github.io/refs/heads/main/repo/js/AdGuard%20Popup%20Blocker.user.js",
            matches: ["*://*/*"]
        },
        {
            id: "auto_trans_vi",
            name: "🇻🇳 Dịch sang Tiếng Việt",
            url: "https://raw.githubusercontent.com/2KGT/2KGT.github.io/refs/heads/main/repo/js/auto%20translate%20vi_user.js",
            matches: ["*://*/*"]
        },
        {
            id: "img_grid_lister",
            name: "🖼️ Image Grid Lister",
            url: "https://raw.githubusercontent.com/2KGT/2KGT.github.io/refs/heads/main/repo/js/image-grid-lister_user.js",
            matches: ["*://*/*"]
        },
        {
            id: "open_inapp",
            name: "📲 Mở App khi bấm link",
            url: "https://raw.githubusercontent.com/2KGT/2KGT.github.io/refs/heads/main/repo/js/open%20inapp.user.js",
            matches: ["*://*/*"]
        }
    ];

    // ==========================================
    // 2. LOGIC KIỂM TRA ĐIỀU KIỆN CHẠY (MATCH URL)
    // ==========================================
    function urlMatchesPattern(url, pattern) {
        if (pattern === "*://*/*") return true;
        const regexPattern = pattern
            .replace(/\./g, '\\.')
            .replace(/\*/g, '.*')
            .replace(/\\\.\.*/g, '(\\..*)?');
        return new RegExp('^' + regexPattern + '$').test(url);
    }

    function shouldRunScript(script) {
        // Kiểm tra xem user có tắt script này trong Dock không (mặc định là TRUE - Bật)
        const isEnabled = GM_getValue(`status_${script.id}`, true);
        if (!isEnabled) return false;

        // Kiểm tra xem URL hiện tại có khớp với list matches của script không
        const currentUrl = window.location.href;
        return script.matches.some(pattern => urlMatchesPattern(currentUrl, pattern));
    }

    // ==========================================
    // 3. LOGIC TẢI VÀ THỰC THI SCRIPT (EVAL ENGINE)
    // ==========================================
    function injectSubScript(script) {
        if (!shouldRunScript(script)) return;

        GM_xmlhttpRequest({
            method: "GET",
            url: script.url,
            onload: function(response) {
                if (response.status === 200) {
                    try {
                        // Khởi chạy script con trong môi trường cô lập bảo mật
                        eval(response.responseText);
                        console.log(`[Father Dock] Loaded: ${script.name}`);
                    } catch (e) {
                        console.error(`[Father Dock] Error running ${script.name}:`, e);
                    }
                }
            }
        });
    }

    // ==========================================
    // 4. CẤU TRÚC GIAO DIỆN DOCK (UI & CONTROLS)
    // ==========================================
    function createDockUI() {
        if (document.getElementById('father-script-dock')) return;

        // Tạo container chính cho Dock
        const dock = document.createElement('div');
        dock.id = 'father-script-dock';
        dock.innerHTML = `
            <div class="dock-header">
                <h3>🛠️ 2KGT Script Manager</h3>
                <span class="dock-close" id="dock-close-btn">×</span>
            </div>
            <div class="dock-body" id="dock-script-list"></div>
        `;

        // Inject CSS cho Dock bắt mắt, hiện đại
        const style = document.createElement('style');
        style.innerHTML = `
            #father-script-dock {
                position: fixed; top: 20px; right: 20px; width: 320px;
                background: #1e1e2e; color: #cdd6f4; border: 1px solid #45475a;
                border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.3);
                z-index: 999999; font-family: system-ui, -apple-system, sans-serif;
                overflow: hidden; display: none;
            }
            .dock-header {
                background: #313244; padding: 12px 16px;
                display: flex; justify-content: space-between; align-items: center;
                border-bottom: 1px solid #45475a; cursor: move;
            }
            .dock-header h3 { margin: 0; font-size: 14px; color: #f5c2e7; }
            .dock-close { cursor: pointer; font-size: 20px; color: #a6adc8; }
            .dock-close:hover { color: #f38ba8; }
            .dock-body { padding: 12px; max-height: 400px; overflow-y: auto; }
            .script-item {
                display: flex; justify-content: space-between; align-items: center;
                padding: 8px 4px; border-bottom: 1px solid #313244;
            }
            .script-item:last-child { border-bottom: none; }
            .script-name { font-size: 13px; }
            /* Custom Switch Toggle button */
            .switch { position: relative; display: inline-block; width: 40px; height: 22px; }
            .switch input { opacity: 0; width: 0; height: 0; }
            .slider {
                position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
                background-color: #45475a; transition: .3s; border-radius: 22px;
            }
            .slider:before {
                position: absolute; content: ""; height: 16px; width: 16px; left: 3px; bottom: 3px;
                background-color: #cdd6f4; transition: .3s; border-radius: 50%;
            }
            input:checked + .slider { background-color: #a6e3a1; }
            input:checked + .slider:before { transform: translateX(18px); background-color: #11111b; }
        `;
        document.head.appendChild(style);
        document.body.appendChild(dock);

        // Render danh sách các Script kèm công tắc bật tắt
        const listContainer = document.getElementById('dock-script-list');
        subScripts.forEach(script => {
            const isEnabled = GM_getValue(`status_${script.id}`, true);
            const item = document.createElement('div');
            item.className = 'script-item';
            item.innerHTML = `
                <span class="script-name">${script.name}</span>
                <label class="switch">
                    <input type="checkbox" id="chk-${script.id}" ${isEnabled ? 'checked' : ''}>
                    <span class="slider"></span>
                </label>
            `;
            listContainer.appendChild(item);

            // Bắt sự kiện Toggle để lưu trạng thái runtime
            document.getElementById(`chk-${script.id}`).addEventListener('change', function(e) {
                GM_setValue(`status_${script.id}`, e.target.checked);
            });
        });

        // Đóng dock
        document.getElementById('dock-close-btn').addEventListener('click', () => {
            dock.style.display = 'none';
        });

        // Logic Kéo thả Dock (Drag and Drop)
        let isDragging = false, currentX, currentY, initialX, initialY, xOffset = 0, yOffset = 0;
        const header = dock.querySelector('.dock-header');
        header.addEventListener('mousedown', dragStart);
        document.addEventListener('mousemove', drag);
        document.addEventListener('mouseup', dragEnd);

        function dragStart(e) {
            initialX = e.clientX - xOffset;
            initialY = e.clientY - yOffset;
            if (e.target === header || header.contains(e.target)) isDragging = true;
        }
        function drag(e) {
            if (isDragging) {
                e.preventDefault();
                currentX = e.clientX - initialX;
                currentY = e.clientY - initialY;
                xOffset = currentX;
                yOffset = currentY;
                dock.style.transform = `translate(${currentX}px, ${currentY}px)`;
            }
        }
        function dragEnd() { initialX = currentX; initialY = currentY; isDragging = false; }
    }

    // ==========================================
    // 5. KHỞI CHẠY HỆ THỐNG
    // ==========================================
    // Đăng ký menu mở Dock nhanh bằng Tampermonkey/Violentmonkey menu
    GM_registerMenuCommand("打开/Đóng Mở Control Dock", () => {
        const dock = document.getElementById('father-script-dock');
        if (dock) {
            dock.style.display = (dock.style.display === 'none' || dock.style.display === '') ? 'block' : 'none';
        }
    });

    // Tạo UI khi trang tải xong DOM phần body
    if (document.body) {
        createDockUI();
    } else {
        document.addEventListener('DOMContentLoaded', createDockUI);
    }

    // Thực thi nạp ngầm các script thoả mãn điều kiện match
    subScripts.forEach(injectSubScript);
})();
