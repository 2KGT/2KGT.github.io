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
    async function toggleScript(scriptDef, dotEl) {
        const isActive = !!activeState[scriptDef.key];

        if (!isActive) {
            dotEl.className = "father-dot loading";
            const result = await loadAndRun(scriptDef);
            if (result.success) {
                activeState[scriptDef.key] = true;
                saveActiveState(activeState);
                dotEl.className = "father-dot on";
            } else {
                dotEl.className = "father-dot error";
                setTimeout(() => { dotEl.className = "father-dot"; }, 2000);
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

    // ==== GIAO DIỆN: NÚT NỔI + ICON CON THẢ RA DẠNG CUNG TRÒN ====
    function injectStyles() {
        const style = document.createElement("style");
        style.textContent = `
            #father-loader-ui * { box-sizing: border-box; }
            #father-loader-ui {
                position: fixed;
                bottom: 24px;
                right: 16px;
                z-index: 2147483647;
                width: 50px;
                height: 50px;
            }
            #father-loader-fab {
                position: relative;
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
                z-index: 2;
            }
            #father-loader-fab:active { transform: scale(0.9); }
            #father-loader-fab.open { transform: rotate(135deg); }

            .father-icon-btn {
                position: absolute;
                top: 0; left: 0;
                width: 46px; height: 46px;
                background: rgba(28,28,30,0.85);
                backdrop-filter: blur(16px) saturate(180%);
                -webkit-backdrop-filter: blur(16px) saturate(180%);
                border-radius: 23px;
                display: flex; align-items: center; justify-content: center;
                font-size: 19px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.28), 0 0 0 0.5px rgba(255,255,255,0.08);
                cursor: pointer;
                user-select: none;
                -webkit-tap-highlight-color: transparent;
                opacity: 0;
                transform: translate(0, 0) scale(0.3);
                transition: transform 0s, opacity 0s;
                pointer-events: none;
                z-index: 1;
            }
            .father-icon-btn.show {
                opacity: 1;
                pointer-events: auto;
                transition: transform 0.42s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.2s ease;
            }
            .father-icon-btn:active { transform: scale(0.85) !important; }

            .father-status-ring {
                position: absolute;
                top: -3px; right: -3px;
                width: 12px; height: 12px;
                border-radius: 6px;
                background: #48484a;
                border: 2px solid rgba(20,20,22,0.9);
                transition: background 0.2s ease;
            }
            .father-status-ring.on { background: #30d158; }
            .father-status-ring.loading {
                background: #ff9f0a;
                animation: father-pulse 0.8s ease-in-out infinite;
            }
            .father-status-ring.error { background: #ff453a; }
            @keyframes father-pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.4; }
            }

            .father-tooltip {
                position: fixed;
                background: rgba(28,28,30,0.92);
                backdrop-filter: blur(12px);
                color: #fff;
                font-size: 12px;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                padding: 6px 10px;
                border-radius: 8px;
                white-space: nowrap;
                pointer-events: none;
                opacity: 0;
                transition: opacity 0.15s ease;
                z-index: 2147483647;
            }
            .father-tooltip.show { opacity: 1; }
        `;
        document.head.appendChild(style);
    }

    function buildUI() {
        injectStyles();

        const container = document.createElement("div");
        container.id = "father-loader-ui";

        const fab = document.createElement("div");
        fab.id = "father-loader-fab";
        fab.textContent = "⚙️";

        const tooltip = document.createElement("div");
        tooltip.className = "father-tooltip";
        document.body.appendChild(tooltip);

        const iconBtns = [];

        // Bố trí các icon theo cung 1/4 hình tròn (90°) phía trên-trái nút chính,
        // bán kính tăng dần để không chồng lấn, giống hiệu ứng "thả nở" (spring fan-out)
        const RADIUS = 92;
        const ANGLE_START = 180; // độ, bắt đầu từ hướng trái
        const ANGLE_END = 270;   // kết thúc hướng lên trên
        const count = SCRIPTS.length;

        SCRIPTS.forEach((scriptDef, i) => {
            const btn = document.createElement("div");
            btn.className = "father-icon-btn";
            btn.textContent = scriptDef.icon;

            const ring = document.createElement("div");
            ring.className = "father-status-ring" + (activeState[scriptDef.key] ? " on" : "");
            btn.appendChild(ring);

            // Góc riêng cho icon này, phân bố đều trên cung
            const angleDeg = ANGLE_START + ((ANGLE_END - ANGLE_START) * i) / Math.max(1, count - 1);
            const angleRad = (angleDeg * Math.PI) / 180;
            const targetX = Math.cos(angleRad) * RADIUS;
            const targetY = Math.sin(angleRad) * RADIUS;

            btn._targetX = targetX;
            btn._targetY = targetY;
            btn._delay = i * 28; // ms, so le thời gian bung ra cho hiệu ứng "rơi" lần lượt

            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                toggleScript(scriptDef, ring);
            });
            btn.addEventListener("touchstart", (e) => {
                const rect = btn.getBoundingClientRect();
                tooltip.textContent = scriptDef.name;
                tooltip.style.left = (rect.left - 20) + "px";
                tooltip.style.top = (rect.top - 34) + "px";
                tooltip.classList.add("show");
            }, { passive: true });
            btn.addEventListener("touchend", () => {
                setTimeout(() => tooltip.classList.remove("show"), 300);
            });

            iconBtns.push(btn);
            container.appendChild(btn);
        });

        container.appendChild(fab);
        document.body.appendChild(container);

        let isOpen = false;

        function openMenu() {
            isOpen = true;
            fab.classList.add("open");
            iconBtns.forEach((btn) => {
                setTimeout(() => {
                    btn.classList.add("show");
                    btn.style.transform = `translate(${btn._targetX}px, ${btn._targetY}px) scale(1)`;
                }, btn._delay);
            });
        }

        function closeMenu() {
            isOpen = false;
            fab.classList.remove("open");
            iconBtns.forEach((btn) => {
                btn.style.transform = "translate(0, 0) scale(0.3)";
                btn.classList.remove("show");
            });
        }

        let lastTap = 0;
        fab.addEventListener("click", () => {
            const now = Date.now();
            if (now - lastTap < 400) {
                isOpen ? closeMenu() : openMenu();
            }
            lastTap = now;
        });

        // Bấm ra ngoài để đóng menu
        document.addEventListener("click", (e) => {
            if (isOpen && !container.contains(e.target)) {
                closeMenu();
            }
        });
    }

    if (document.body) {
        buildUI();
    } else {
        document.addEventListener("DOMContentLoaded", buildUI);
    }
})();
