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
    async function toggleScript(scriptDef, dotEl, statusTextEl) {
        const isActive = !!activeState[scriptDef.key];

        if (!isActive) {
            dotEl.className = "father-status-dot loading";
            statusTextEl.textContent = "Đang tải...";
            const result = await loadAndRun(scriptDef);
            if (result.success) {
                activeState[scriptDef.key] = true;
                saveActiveState(activeState);
                dotEl.className = "father-status-dot on";
                statusTextEl.textContent = "Đang bật";
            } else {
                dotEl.className = "father-status-dot error";
                statusTextEl.textContent = "Lỗi";
                setTimeout(() => {
                    dotEl.className = "father-status-dot";
                    statusTextEl.textContent = "";
                }, 2000);
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
                width: 46px; height: 46px;
                background: rgba(28,28,30,0.72);
                backdrop-filter: blur(18px) saturate(180%);
                -webkit-backdrop-filter: blur(18px) saturate(180%);
                border-radius: 14px;
                display: flex; align-items: center; justify-content: center;
                box-shadow: 0 4px 14px rgba(0,0,0,0.3), 0 0 0 0.5px rgba(255,255,255,0.08);
                cursor: grab;
                user-select: none;
                touch-action: none;
                transition: transform 0.15s ease, box-shadow 0.15s ease;
                z-index: 2147483646;
                -webkit-tap-highlight-color: transparent;
            }
            #father-loader-fab.dragging {
                cursor: grabbing;
                box-shadow: 0 8px 24px rgba(0,0,0,0.4), 0 0 0 0.5px rgba(255,255,255,0.12);
                transform: scale(1.08);
            }

            /* Icon 4 ô vuông kiểu grid/Windows */
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

            /* ===== Popup nhỏ cạnh nút (không che màn hình) ===== */
            #father-popup {
                position: fixed;
                width: 244px;
                max-height: 340px;
                background: rgba(44,44,46,0.9);
                backdrop-filter: blur(22px) saturate(180%);
                -webkit-backdrop-filter: blur(22px) saturate(180%);
                border-radius: 16px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.35), 0 0 0 0.5px rgba(255,255,255,0.08);
                opacity: 0;
                transform: scale(0.85);
                transform-origin: var(--father-origin, center);
                pointer-events: none;
                transition: opacity 0.18s ease, transform 0.18s cubic-bezier(0.34, 1.4, 0.64, 1);
                z-index: 2147483647;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                overflow: hidden;
                display: flex;
                flex-direction: column;
            }
            #father-popup.open {
                opacity: 1;
                transform: scale(1);
                pointer-events: auto;
            }

            .father-popup-header {
                text-align: center;
                font-size: 11.5px;
                color: rgba(235,235,245,0.55);
                padding: 10px 14px 6px;
                font-weight: 500;
                flex-shrink: 0;
            }

            .father-popup-list {
                overflow-y: auto;
                -webkit-overflow-scrolling: touch;
                flex: 1;
            }

            .father-row {
                display: flex; align-items: center;
                padding: 10px 14px;
                border-top: 0.5px solid rgba(255,255,255,0.09);
                cursor: pointer;
                -webkit-tap-highlight-color: transparent;
                transition: background 0.1s ease;
            }
            .father-row:first-of-type { border-top: none; }
            .father-row:active { background: rgba(255,255,255,0.06); }

            .father-row-icon {
                font-size: 18px;
                width: 26px;
                text-align: center;
                margin-right: 10px;
                flex-shrink: 0;
            }
            .father-row-label {
                flex: 1;
                font-size: 14.5px;
                color: #fff;
                letter-spacing: -0.1px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .father-row-status {
                font-size: 11px;
                color: rgba(235,235,245,0.5);
                margin-right: 6px;
                white-space: nowrap;
                flex-shrink: 0;
            }

            .father-status-dot {
                width: 8px; height: 8px;
                border-radius: 4px;
                background: #636366;
                flex-shrink: 0;
                transition: background 0.2s ease, box-shadow 0.2s ease;
            }
            .father-status-dot.on {
                background: #30d158;
                box-shadow: 0 0 5px rgba(48,209,88,0.6);
            }
            .father-status-dot.loading {
                background: #ff9f0a;
                animation: father-pulse 0.8s ease-in-out infinite;
            }
            .father-status-dot.error { background: #ff453a; }
            @keyframes father-pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.35; }
            }
        `;
        document.head.appendChild(style);
    }

    function buildUI() {
        injectStyles();

        // ==== Nút nổi (icon 4 ô vuông) ====
        const fab = document.createElement("div");
        fab.id = "father-loader-fab";
        fab.innerHTML = `
            <div class="father-fab-grid">
                <span></span><span></span><span></span><span></span>
            </div>
        `;

        // Vị trí ban đầu: góc dưới phải (khôi phục vị trí đã lưu nếu có)
        const savedPos = (() => {
            try {
                return JSON.parse(sessionStorage.getItem("father_fab_pos") || "null");
            } catch {
                return null;
            }
        })();
        fab.style.right = savedPos ? "auto" : "16px";
        fab.style.bottom = savedPos ? "auto" : "90px";
        fab.style.left = savedPos ? savedPos.left + "px" : "auto";
        fab.style.top = savedPos ? savedPos.top + "px" : "auto";

        document.body.appendChild(fab);

        // ==== Popup ====
        const popup = document.createElement("div");
        popup.id = "father-popup";

        const header = document.createElement("div");
        header.className = "father-popup-header";
        header.textContent = "Tiện ích";

        const list = document.createElement("div");
        list.className = "father-popup-list";

        SCRIPTS.forEach((scriptDef) => {
            const row = document.createElement("div");
            row.className = "father-row";

            const icon = document.createElement("span");
            icon.className = "father-row-icon";
            icon.textContent = scriptDef.icon;

            const label = document.createElement("span");
            label.className = "father-row-label";
            label.textContent = scriptDef.name;

            const statusText = document.createElement("span");
            statusText.className = "father-row-status";
            statusText.textContent = activeState[scriptDef.key] ? "Bật" : "";

            const dot = document.createElement("span");
            dot.className = "father-status-dot" + (activeState[scriptDef.key] ? " on" : "");

            row.appendChild(icon);
            row.appendChild(label);
            row.appendChild(statusText);
            row.appendChild(dot);

            row.addEventListener("click", () => toggleScript(scriptDef, dot, statusText));

            list.appendChild(row);
        });

        popup.appendChild(header);
        popup.appendChild(list);
        document.body.appendChild(popup);

        // ==== Định vị popup cạnh nút, tự chọn hướng để không tràn màn hình ====
        function positionPopup() {
            const fabRect = fab.getBoundingClientRect();
            const popupWidth = 244;
            const popupMaxHeight = 340;
            const margin = 10;

            const spaceRight = window.innerWidth - fabRect.right;
            const spaceLeft = fabRect.left;
            const spaceAbove = fabRect.top;
            const spaceBelow = window.innerHeight - fabRect.bottom;

            let left, top, origin;

            // Ưu tiên đặt popup bên trái hoặc phải nút, thẳng hàng dọc
            if (spaceRight >= popupWidth + margin || spaceRight >= spaceLeft) {
                left = Math.min(fabRect.right + margin, window.innerWidth - popupWidth - margin);
                origin = "left ";
            } else {
                left = Math.max(fabRect.left - popupWidth - margin, margin);
                origin = "right ";
            }

            if (spaceBelow >= popupMaxHeight + margin || spaceBelow >= spaceAbove) {
                top = fabRect.top;
                origin += "top";
            } else {
                top = Math.max(fabRect.bottom - popupMaxHeight, margin);
                origin += "bottom";
            }

            // Nếu quá gần mép trên/dưới, kẹp lại trong khung nhìn
            top = Math.max(margin, Math.min(top, window.innerHeight - popupMaxHeight - margin));

            popup.style.left = left + "px";
            popup.style.top = top + "px";
            popup.style.setProperty("--father-origin", origin);
        }

        function openPopup() {
            positionPopup();
            popup.classList.add("open");
        }
        function closePopup() {
            popup.classList.remove("open");
        }

        // ==== Kéo thả nút nổi (giống AssistiveTouch) ====
        let isDragging = false;
        let dragMoved = false;
        let startX, startY, startLeft, startTop;

        function onDragStart(e) {
            const point = e.touches ? e.touches[0] : e;
            const rect = fab.getBoundingClientRect();
            isDragging = true;
            dragMoved = false;
            startX = point.clientX;
            startY = point.clientY;
            startLeft = rect.left;
            startTop = rect.top;
            fab.classList.add("dragging");
            fab.style.right = "auto";
            fab.style.bottom = "auto";
            fab.style.left = startLeft + "px";
            fab.style.top = startTop + "px";
            closePopup();
        }

        function onDragMove(e) {
            if (!isDragging) return;
            const point = e.touches ? e.touches[0] : e;
            const dx = point.clientX - startX;
            const dy = point.clientY - startY;
            if (Math.abs(dx) > 4 || Math.abs(dy) > 4) dragMoved = true;

            let newLeft = startLeft + dx;
            let newTop = startTop + dy;

            // Giới hạn trong khung nhìn
            newLeft = Math.max(4, Math.min(newLeft, window.innerWidth - 46 - 4));
            newTop = Math.max(4, Math.min(newTop, window.innerHeight - 46 - 4));

            fab.style.left = newLeft + "px";
            fab.style.top = newTop + "px";
            e.preventDefault();
        }

        function onDragEnd() {
            if (!isDragging) return;
            isDragging = false;
            fab.classList.remove("dragging");

            // Hút nút về sát mép trái hoặc phải gần nhất (giống AssistiveTouch)
            const rect = fab.getBoundingClientRect();
            const centerX = rect.left + rect.width / 2;
            const snapLeft = centerX < window.innerWidth / 2 ? 8 : window.innerWidth - 46 - 8;
            fab.style.left = snapLeft + "px";

            // Lưu vị trí cho lần tải trang sau (trong cùng phiên)
            try {
                sessionStorage.setItem(
                    "father_fab_pos",
                    JSON.stringify({ left: snapLeft, top: rect.top })
                );
            } catch { /* ignore */ }

            // Nếu chỉ là bấm (không kéo), coi như 1 lần tap cho logic double-tap
            if (!dragMoved) {
                handleTap();
            }
        }

        fab.addEventListener("mousedown", onDragStart);
        window.addEventListener("mousemove", onDragMove);
        window.addEventListener("mouseup", onDragEnd);

        fab.addEventListener("touchstart", onDragStart, { passive: true });
        window.addEventListener("touchmove", onDragMove, { passive: false });
        window.addEventListener("touchend", onDragEnd);

        // ==== Double-tap để mở popup ====
        let lastTap = 0;
        function handleTap() {
            const now = Date.now();
            if (now - lastTap < 400) {
                popup.classList.contains("open") ? closePopup() : openPopup();
            }
            lastTap = now;
        }

        // Đóng popup khi bấm ra ngoài
        document.addEventListener("click", (e) => {
            if (
                popup.classList.contains("open") &&
                !popup.contains(e.target) &&
                !fab.contains(e.target)
            ) {
                closePopup();
            }
        });

        window.addEventListener("resize", () => {
            if (popup.classList.contains("open")) positionPopup();
        });
    }

    if (document.body) {
        buildUI();
    } else {
        document.addEventListener("DOMContentLoaded", buildUI);
    }
})();
