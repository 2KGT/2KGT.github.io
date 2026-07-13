// ==UserScript==
// @name         2KGT Multi-Script Loader (Father)
// @description  Nút nổi kéo thả kiểu AssistiveTouch, double-tap mở popup nhỏ để bật/tắt các userscript con
// @version      7.0.0
// @match        *://*/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function () {
    "use strict";

    console.log("[Father.js] Đang chạy phiên bản 7.0.0 (layer cuộn cố định, click đơn giản, mặc định 3 icon) - " + new Date().toISOString());

    // ==== CẤU HÌNH ====
    const BASE_URL = "https://raw.githubusercontent.com/2KGT/2KGT.github.io/main/js/";

    // Danh sách các script con - name hiển thị, icon, file để ghép URL, key để lưu trạng thái bật/tắt
    const SCRIPTS = [
        { key: "abpvn", name: "ABPVN AdsBlock", icon: "🛡️", file: "ABPVN AdsBlock.user.js" },
        { key: "act_yt_translate", name: "YouTube Auto-translate", icon: "📺", file: "ACT.YouTube.DM.Auto-translate.user.js" },
        { key: "adguard_extra", name: "AdGuard Extra", icon: "🧩", file: "AdGuard Extra.user.js" },
        { key: "adguard_popup", name: "AdGuard Popup Blocker", icon: "🚫", file: "AdGuard Popup Blocker.user.js" },
        { key: "auto_translate_vi", name: "Dịch sang Tiếng Việt", icon: "🇻🇳", file: "auto translate vi.user.js" },
        { key: "image_grid", name: "Image Grid Lister", icon: "🖼️", file: "image-grid-lister.user.js" },
        { key: "open_inapp", name: "Mở App khi bấm link", icon: "📲", file: "open inapp.user.js" },
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
    async function toggleScript(scriptDef, glowEl) {
        const isActive = !!activeState[scriptDef.key];

        if (!isActive) {
            glowEl.className = "father-app-glow loading";
            const result = await loadAndRun(scriptDef);
            if (result.success) {
                activeState[scriptDef.key] = true;
                saveActiveState(activeState);
                glowEl.className = "father-app-glow on";
            } else {
                glowEl.className = "father-app-glow error";
                setTimeout(() => { glowEl.className = "father-app-glow"; }, 2000);
            }
        } else {
            const confirmReload = confirm(
                scriptDef.name + " đang bật.\nBấm OK để tải lại trang (khôi phục bản gốc)."
            );
            if (confirmReload) {
                delete activeState[scriptDef.key];
                saveActiveState(activeState);
                location.reload();
            }
        }
    }

    // ==== GIAO DIỆN: NÚT NỔI KÉO THẢ (KIỂU ASSISTIVETOUCH) + POPUP NHỎ CẠNH NÚT ====
    function injectStyles() {
        const style = document.createElement("style");
        style.textContent = `
            #father-loader-ui * { box-sizing: border-box; }

            #father-loader-fab {
                position: fixed;
                bottom: 90px;
                right: 16px;
                width: 46px; height: 46px;
                background: rgba(28,28,30,0.72);
                backdrop-filter: blur(18px) saturate(180%);
                -webkit-backdrop-filter: blur(18px) saturate(180%);
                border-radius: 14px;
                display: flex; align-items: center; justify-content: center;
                box-shadow: 0 4px 14px rgba(0,0,0,0.3), 0 0 0 0.5px rgba(255,255,255,0.08);
                cursor: pointer;
                user-select: none;
                transition: transform 0.12s ease, box-shadow 0.15s ease, background 0.15s ease;
                z-index: 2147483646;
                -webkit-tap-highlight-color: transparent;
            }
            #father-loader-fab:active {
                transform: scale(0.9);
            }

            /* Icon 4 ô vuông kiểu grid/Windows - luôn cố định, không đổi hình dạng */
            .father-fab-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                grid-template-rows: repeat(2, 1fr);
                gap: 3px;
                width: 18px; height: 18px;
            }
            .father-fab-grid span {
                background: rgba(255,255,255,0.92);
                border-radius: 2.5px;
            }

            /* Khi dock đang mở: chỉ đổi màu nền fab để báo hiệu trạng thái */
            #father-loader-fab.menu-open {
                background: rgba(10,132,255,0.85);
            }

            /* ===== Popup dạng layer cuộn dọc, cao vừa đúng 3 icon để luôn thấy cần cuộn ===== */
            #father-popup {
                position: fixed;
                bottom: 144px;
                right: 16px;
                width: 60px;
                /* Chiều cao vừa đúng 3 item: mỗi item 44px icon-wrap + 8px gap.
                   3 item = 44*3 + 8*2 = 148px, cộng padding 6px*2 = 160px */
                height: 160px;
                background: rgba(30,30,32,0.55);
                backdrop-filter: blur(20px) saturate(180%);
                -webkit-backdrop-filter: blur(20px) saturate(180%);
                border-radius: 18px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.35), 0 0 0 0.5px rgba(255,255,255,0.08);
                opacity: 0;
                transform: scale(0.85);
                transform-origin: bottom right;
                pointer-events: none;
                transition: opacity 0.18s ease, transform 0.18s cubic-bezier(0.34, 1.4, 0.64, 1);
                z-index: 2147483647;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                padding: 6px;
                display: flex;
                flex-direction: column;
            }
            #father-popup.open {
                opacity: 1;
                transform: scale(1);
                pointer-events: auto;
            }

            /* Layer cuộn thật: overflow-y: auto đơn giản, không có logic JS can thiệp,
               giống cách image-grid-lister.user.js xử lý .igl-navbar/.igl-grid */
            .father-popup-list {
                flex: 1;
                overflow-y: auto;
                -webkit-overflow-scrolling: touch;
                overscroll-behavior: contain;
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 8px;
                scrollbar-width: none;
            }
            .father-popup-list::-webkit-scrollbar { display: none; }

            /* Icon app nhỏ gọn, không có label chữ bên dưới */
            .father-app-item {
                display: flex;
                cursor: pointer;
                -webkit-tap-highlight-color: transparent;
                flex-shrink: 0;
            }
            .father-app-icon-wrap {
                position: relative;
                width: 44px; height: 44px;
                display: flex; align-items: center; justify-content: center;
            }
            .father-app-icon {
                width: 40px; height: 40px;
                border-radius: 11px;
                background: linear-gradient(145deg, #3a3a3c, #1c1c1e);
                display: flex; align-items: center; justify-content: center;
                font-size: 18px;
                box-shadow: 0 3px 8px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.06);
                transition: transform 0.15s ease;
                position: relative;
                z-index: 2;
            }
            .father-app-item:active .father-app-icon {
                transform: scale(0.9);
            }

            /* Vòng sáng xanh bao quanh khi script đang bật */
            .father-app-glow {
                position: absolute;
                inset: -4px;
                border-radius: 15px;
                z-index: 1;
                opacity: 0;
                transition: opacity 0.25s ease;
                background: radial-gradient(circle, rgba(48,209,88,0.55) 0%, rgba(48,209,88,0.15) 60%, transparent 75%);
                box-shadow: 0 0 8px 2px rgba(48,209,88,0.5);
            }
            .father-app-glow.on { opacity: 1; }
            .father-app-glow.loading {
                opacity: 1;
                background: radial-gradient(circle, rgba(255,159,10,0.55) 0%, rgba(255,159,10,0.15) 60%, transparent 75%);
                box-shadow: 0 0 8px 2px rgba(255,159,10,0.5);
                animation: father-pulse 0.9s ease-in-out infinite;
            }
            .father-app-glow.error {
                opacity: 1;
                background: radial-gradient(circle, rgba(255,69,58,0.55) 0%, rgba(255,69,58,0.15) 60%, transparent 75%);
                box-shadow: 0 0 8px 2px rgba(255,69,58,0.5);
            }
            @keyframes father-pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
        `;
        document.head.appendChild(style);
    }

    function buildUI() {
        injectStyles();

        // ==== Nút nổi cố định vị trí (không kéo thả, chỉ click để mở/đóng) ====
        const fab = document.createElement("div");
        fab.id = "father-loader-fab";
        fab.innerHTML = `
            <div class="father-fab-grid">
                <span></span><span></span><span></span><span></span>
            </div>
        `;
        document.body.appendChild(fab);

        // ==== Dock các icon script con - layer cuộn dọc thật, luôn ở vị trí cố định trên fab ====
        const popup = document.createElement("div");
        popup.id = "father-popup";

        const list = document.createElement("div");
        list.className = "father-popup-list";

        SCRIPTS.forEach((scriptDef) => {
            const item = document.createElement("div");
            item.className = "father-app-item";

            const iconWrap = document.createElement("div");
            iconWrap.className = "father-app-icon-wrap";

            const glow = document.createElement("div");
            glow.className = "father-app-glow" + (activeState[scriptDef.key] ? " on" : "");

            const icon = document.createElement("div");
            icon.className = "father-app-icon";
            icon.textContent = scriptDef.icon;

            iconWrap.appendChild(glow);
            iconWrap.appendChild(icon);
            item.appendChild(iconWrap);
            item.title = scriptDef.name;

            item.addEventListener("click", (e) => {
                e.stopPropagation();
                toggleScript(scriptDef, glow);
            });

            list.appendChild(item);
        });

        popup.appendChild(list);
        document.body.appendChild(popup);

        // ==== Mở / đóng dock: chỉ 1 lần click duy nhất trên fab, không phụ thuộc kéo/double-tap ====
        function openPopup() {
            popup.classList.add("open");
            fab.classList.add("menu-open");
        }
        function closePopup() {
            popup.classList.remove("open");
            fab.classList.remove("menu-open");
        }

        fab.addEventListener("click", (e) => {
            e.stopPropagation();
            popup.classList.contains("open") ? closePopup() : openPopup();
        });

        // Đóng popup khi bấm ra ngoài (ra ngoài cả fab lẫn popup)
        document.addEventListener("click", (e) => {
            if (
                popup.classList.contains("open") &&
                !popup.contains(e.target) &&
                !fab.contains(e.target)
            ) {
                closePopup();
            }
        });
    }

    if (document.body) {
        buildUI();
    } else {
        document.addEventListener("DOMContentLoaded", buildUI);
    }
})();
