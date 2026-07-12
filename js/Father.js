// ==UserScript==
// @name         2KGT Multi-Script Loader (Father)
// @description  Nút nổi double-tap để bật/tắt các userscript con tải từ GitHub raw
// @version      1.0
// @match        *://*/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function () {
    "use strict";

    // ==== CẤU HÌNH ====
    const BASE_URL = "https://raw.githubusercontent.com/2KGT/2KGT.github.io/main/js/";

    // Danh sách các script con - name hiển thị, file để ghép URL, key để lưu trạng thái bật/tắt
    const SCRIPTS = [
        { key: "abpvn", name: "ABPVN AdsBlock", file: "ABPVN AdsBlock.user.js" },
        { key: "act_yt_translate", name: "YouTube Auto-translate (Phụ đề)", file: "ACT.YouTube.DM.Auto-translate.user.js" },
        { key: "adguard_extra", name: "AdGuard Extra", file: "AdGuard Extra.user.js" },
        { key: "adguard_popup", name: "AdGuard Popup Blocker", file: "AdGuard Popup Blocker.user.js" },
        { key: "auto_translate_vi", name: "Dịch trang sang Tiếng Việt", file: "auto translate vi.user.js" },
        { key: "image_grid", name: "Image Grid Lister", file: "image-grid-lister.user.js" },
        { key: "open_inapp", name: "Tự mở App khi bấm link", file: "open inapp.user.js" },
    ];

    const STORAGE_KEY = "father_active_scripts";

    // ==== QUẢN LÝ TRẠNG THÁI BẬT/TẮT (lưu qua sessionStorage - mỗi tab/phiên riêng) ====
    function loadActiveState() {
        try {
            const raw = sessionStorage.getItem(STORAGE_KEY);
            return raw ? JSON.parse(raw) : {};
        } catch {
            return {};
        }
    }
    function saveActiveState(state) {
        try {
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
        } catch {
            /* ignore quota errors */
        }
    }

    let activeState = loadActiveState();

    // ==== TẢI VÀ CHẠY 1 SCRIPT CON ====
    async function loadAndRun(scriptDef) {
        const url = BASE_URL + encodeURIComponent(scriptDef.file).replace(/%2F/g, "/");
        try {
            const res = await fetch(url, { cache: "no-store" });
            if (!res.ok) {
                throw new Error("HTTP " + res.status);
            }
            const code = await res.text();
            // Chạy code trong scope hàm riêng để tránh xung đột biến toàn cục
            const runner = new Function(code);
            runner();
            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }

    // ==== KÍCH HOẠT / KHÔI PHỤC 1 SCRIPT ====
    async function toggleScript(scriptDef, statusEl) {
        const isActive = !!activeState[scriptDef.key];

        if (!isActive) {
            statusEl.textContent = "Đang tải...";
            const result = await loadAndRun(scriptDef);
            if (result.success) {
                activeState[scriptDef.key] = true;
                saveActiveState(activeState);
                statusEl.textContent = "✅ Đã bật";
            } else {
                statusEl.textContent = "❌ Lỗi: " + result.error;
            }
        } else {
            // Không có cách "gỡ" 1 script đã chạy (không đảo ngược DOM/patch được an toàn),
            // nên "khôi phục" thực tế = tải lại trang để về trạng thái gốc.
            const confirmReload = confirm(
                scriptDef.name + " đang bật.\nBấm OK để TẢI LẠI TRANG (khôi phục bản gốc)."
            );
            if (confirmReload) {
                delete activeState[scriptDef.key];
                saveActiveState(activeState);
                location.reload();
            }
        }
    }

    // ==== GIAO DIỆN: NÚT NỔI + DANH SÁCH ====
    function injectStyles() {
        const style = document.createElement("style");
        style.textContent = `
            #father-loader-ui * { box-sizing: border-box; }
            #father-loader-fab {
                width: 50px; height: 50px;
                background: rgba(28,28,30,0.78);
                backdrop-filter: blur(20px) saturate(180%);
                -webkit-backdrop-filter: blur(20px) saturate(180%);
                border-radius: 25px;
                display: flex; align-items: center; justify-content: center;
                font-size: 22px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.3), 0 0 0 0.5px rgba(255,255,255,0.08);
                cursor: pointer;
                user-select: none;
                transition: transform 0.15s ease;
            }
            #father-loader-fab:active { transform: scale(0.9); }
            #father-loader-panel {
                position: absolute;
                bottom: 60px;
                right: 0;
                width: 268px;
                background: rgba(30,30,32,0.82);
                backdrop-filter: blur(24px) saturate(180%);
                -webkit-backdrop-filter: blur(24px) saturate(180%);
                border-radius: 18px;
                padding: 6px;
                box-shadow: 0 12px 32px rgba(0,0,0,0.35), 0 0 0 0.5px rgba(255,255,255,0.08);
                opacity: 0;
                transform: scale(0.92) translateY(8px);
                transform-origin: bottom right;
                pointer-events: none;
                transition: opacity 0.2s ease, transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
                max-height: 65vh;
                overflow-y: auto;
            }
            #father-loader-panel.open {
                opacity: 1;
                transform: scale(1) translateY(0);
                pointer-events: auto;
            }
            .father-row {
                display: flex; align-items: center;
                padding: 11px 12px;
                border-radius: 12px;
                color: #fff;
                font-size: 13.5px;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                cursor: pointer;
                transition: background 0.1s ease;
                -webkit-tap-highlight-color: transparent;
            }
            .father-row:active { background: rgba(255,255,255,0.1); }
            .father-row + .father-row { margin-top: 1px; }
            .father-dot {
                width: 8px; height: 8px;
                border-radius: 4px;
                margin-right: 10px;
                flex-shrink: 0;
                background: #48484a;
                transition: background 0.2s ease;
            }
            .father-dot.on { background: #30d158; box-shadow: 0 0 6px rgba(48,209,88,0.6); }
            .father-dot.loading {
                background: #ff9f0a;
                animation: father-pulse 0.8s ease-in-out infinite;
            }
            .father-dot.error { background: #ff453a; }
            @keyframes father-pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.4; }
            }
            .father-label {
                flex: 1;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
        `;
        document.head.appendChild(style);
    }

    function buildUI() {
        injectStyles();

        const container = document.createElement("div");
        container.id = "father-loader-ui";
        container.style.cssText = "position: fixed; bottom: 24px; right: 16px; z-index: 2147483647;";

        const fab = document.createElement("div");
        fab.id = "father-loader-fab";
        fab.textContent = "⚙️";

        const panel = document.createElement("div");
        panel.id = "father-loader-panel";

        const dotEls = {};

        SCRIPTS.forEach((scriptDef) => {
            const row = document.createElement("div");
            row.className = "father-row";

            const dot = document.createElement("div");
            dot.className = "father-dot" + (activeState[scriptDef.key] ? " on" : "");
            dotEls[scriptDef.key] = dot;

            const label = document.createElement("span");
            label.className = "father-label";
            label.textContent = scriptDef.name;

            row.appendChild(dot);
            row.appendChild(label);
            row.addEventListener("click", () => toggleScript(scriptDef, dot));

            panel.appendChild(row);
        });

        let lastTap = 0;
        fab.addEventListener("click", () => {
            const now = Date.now();
            if (now - lastTap < 400) {
                panel.classList.toggle("open");
            }
            lastTap = now;
        });

        container.appendChild(panel);
        container.appendChild(fab);
        document.body.appendChild(container);
    }

    if (document.body) {
        buildUI();
    } else {
        document.addEventListener("DOMContentLoaded", buildUI);
    }
})();
