// ==UserScript==
// @name         Father Script Manager - iOS Safari Fixed
// @namespace    https://github.com/2KGT/2KGT.github.io
// @version      12.3
// @description  Bản đặc chế tương thích 100% với Userscripts trên iOS/iPhone. Kích thước 45px, nạp ngầm github script, vuốt ẩn 2/3.
// @author       2KGT
// @match        *://*/*
// @run-at       document-end
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// ==/UserScript==

(function() {
    'use strict';

    // ==========================================
    // DATA: DANH SÁCH SCRIPT CON
    // ==========================================
    const subScripts = [
        {
            id: "abpvn_adsblock",
            name: "ABPVN AdsBlock",
            url: "https://raw.githubusercontent.com/2KGT/2KGT.github.io/refs/heads/main/repo/js/ABPVN%20AdsBlock.user.js"
        },
        {
            id: "yt_autotranslate",
            name: "YouTube Auto-translate",
            url: "https://raw.githubusercontent.com/2KGT/2KGT.github.io/refs/heads/main/repo/js/ACT.YouTube.DM.Auto-translate.user.js"
        },
        {
            id: "adguard_extra",
            name: "AdGuard Extra",
            url: "https://raw.githubusercontent.com/2KGT/2KGT.github.io/refs/heads/main/repo/js/AdGuard%20Extra.user.js"
        },
        {
            id: "adguard_popup",
            name: "AdGuard Popup Blocker",
            url: "https://raw.githubusercontent.com/2KGT/2KGT.github.io/refs/heads/main/repo/js/AdGuard%20Popup%20Blocker.user.js"
        },
        {
            id: "auto_trans_vi",
            name: "Dịch sang Tiếng VI",
            url: "https://raw.githubusercontent.com/2KGT/2KGT.github.io/refs/heads/main/repo/js/auto%20translate%20vi_user.js"
        },
        {
            id: "img_grid_lister",
            name: "Image Grid Lister",
            url: "https://raw.githubusercontent.com/2KGT/2KGT.github.io/refs/heads/main/repo/js/image-grid-lister_user.js"
        },
        {
            id: "open_inapp",
            name: "Mở App khi bấm link",
            url: "https://raw.githubusercontent.com/2KGT/2KGT.github.io/refs/heads/main/repo/js/open%20inapp.user.js"
        }
    ];

    // ==========================================
    // ENGINE: NẠP NGẦM SCRIPT CON (Tối ưu cho iOS)
    // ==========================================
    function loadSubScript(script) {
        const isEnabled = GM_getValue(`status_${script.id}`, true);
        if (!isEnabled) return;

        GM_xmlhttpRequest({
            method: "GET",
            url: script.url,
            onload: function(response) {
                if (response.status === 200) {
                    try {
                        // Sử dụng hàm gián tiếp để eval chạy trên phạm vi global, tối ưu cho môi trường iOS Userscripts
                        (0, eval)(response.responseText);
                        console.log(`[Father Dock] Loaded: ${script.name}`);
                    } catch (e) {
                        console.error(`[Father Dock] Error running ${script.name}:`, e);
                    }
                }
            }
        });
    }

    // Kích hoạt nạp ngay lập tức
    subScripts.forEach(loadSubScript);

    // ==========================================
    // UI ENGINE: KHỞI TẠO DOCK 45PX
    // ==========================================
    function initDockUI() {
        if (!document.body || document.getElementById('lc-multitask-container')) return;

        function createSVG(dPath, styleStr = '', viewBox = '0 0 24 24') {
            return `<svg viewBox="${viewBox}" style="width:18px;height:18px;fill:currentColor;display:block;${styleStr}"><path d="${dPath}"/></svg>`;
        }

        const container = document.createElement('div');
        container.id = 'lc-multitask-container';
        container.style.cssText = 'position:fixed !important; z-index:999999 !important; right:4px !important; top:50% !important; transform:translateY(-50%) !important; touch-action:none !important; user-select:none !important;';
        const shadow = container.attachShadow({ mode: 'open' });

        const style = document.createElement('style');
        style.textContent = `
            :host {
                display: block !important;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
                transition: right 0.4s cubic-bezier(0.16, 1, 0.3, 1), left 0.4s cubic-bezier(0.16, 1, 0.3, 1), top 0.4s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.3s ease !important;
            }
            :host(.dragging) { transition: none !important; }
            :host(.edge-hidden-right) { right: -31px !important; opacity: 0.6 !important; }
            :host(.edge-hidden-left) { left: -31px !important; opacity: 0.6 !important; }
            :host(:hover) { opacity: 1 !important; }

            .dock-main {
                display: inline-flex !important;
                flex-direction: column !important;
                align-items: center !important;
                padding: 4px !important;
                background: rgba(245, 245, 247, 0.85) !important; 
                backdrop-filter: blur(20px) saturate(190%) !important;
                -webkit-backdrop-filter: blur(20px) saturate(190%) !important;
                border-radius: 13px !important;
                box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.06), 0 8px 24px rgba(0, 0, 0, 0.08) !important;
                box-sizing: border-box !important;
                transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1) !important;
                overflow: hidden !important;
                min-width: 45px !important; max-width: 45px !important;
                min-height: 45px !important; max-height: 45px !important;
            }
            .dock-main.expanded {
                border-radius: 14px !important;
                min-height: 380px !important; max-height: 450px !important;
                background: rgba(255, 255, 255, 0.95) !important;
                box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.08), 0 12px 36px rgba(0, 0, 0, 0.15) !important;
            }
            .btn-main-toggle { 
                width: 37px !important; height: 37px !important;
                border-radius: 9px !important; border: none !important;
                background: #10a37f !important; color: #ffffff !important; 
                cursor: move !important; display: flex !important;
                align-items: center !important; justify-content: center !important;
                outline: none !important; box-sizing: border-box !important;
                flex-shrink: 0 !important; touch-action: none !important;
                transition: background 0.2s, border-radius 0.3s, transform 0.1s !important;
                z-index: 5 !important; box-shadow: 0 2px 6px rgba(16, 163, 127, 0.25) !important;
            }
            .btn-main-toggle:active { transform: scale(0.92) !important; }
            .btn-main-toggle svg { transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important; }
            .dock-main.expanded .btn-main-toggle svg { transform: rotate(180deg) !important; }

            @media (prefers-color-scheme: dark) {
                .dock-main {
                    background: rgba(28, 28, 30, 0.85) !important;
                    box-shadow: inset 0 0 0 0.5px rgba(255, 255, 255, 0.08), 0 8px 24px rgba(0, 0, 0, 0.25) !important;
                }
                .dock-main.expanded { background: rgba(28, 28, 30, 0.96) !important; }
            }

            .apps-sub-container-bg {
                width: 37px !important; display: flex !important; flex-direction: column !important;
                background: transparent !important; border-radius: 9px !important;
                margin-top: 0px !important; box-sizing: border-box !important;
                overflow: hidden !important; flex-shrink: 0 !important;
                opacity: 0 !important; max-height: 0px !important;
                transform: scale(0.95) translateY(-6px) !important;
                transition: opacity 0.2s ease, transform 0.28s cubic-bezier(0.16, 1, 0.3, 1), max-height 0.3s ease, margin-top 0.2s !important;
            }
            .dock-main.expanded .apps-sub-container-bg {
                opacity: 1 !important; max-height: 380px !important;
                margin-top: 6px !important; transform: scale(1) translateY(0) !important;
            }
            .apps-scroll-layer {
                display: flex !important; flex-direction: column !important;
                align-items: center !important; gap: 8px !important; width: 37px !important;
                overflow-y: auto !important; overflow-x: hidden !important;
                scrollbar-width: none !important; -webkit-overflow-scrolling: touch !important;
            }
            .apps-scroll-layer::-webkit-scrollbar { display: none !important; }

            .btn-app {
                width: 37px !important; height: 37px !important;
                border-radius: 9px !important; border: none !important;
                cursor: pointer !important; display: flex !important;
                align-items: center !important; justify-content: center !important;
                transition: transform 0.12s ease, background 0.2s !important;
                padding: 0 !important; overflow: hidden !important; outline: none !important;
                box-sizing: border-box !important; flex-shrink: 0 !important;
                font-size: 10px !important; font-weight: bold !important;
            }
            .btn-app:active { transform: scale(0.88) !important; }
            .btn-app.script-on { background: #a6e3a1 !important; color: #11111b !important; border: 1px solid #a6e3a1 !important; }
            .btn-app.script-off { background: rgba(0, 0, 0, 0.08) !important; color: #a6adc8 !important; border: 1px solid rgba(0, 0, 0, 0.1) !important; }

            @media (prefers-color-scheme: dark) { 
                .btn-app.script-off { background: rgba(255, 255, 255, 0.1) !important; color: #585b70 !important; border: 1px solid rgba(255, 255, 255, 0.05) !important; }
            }
        `;

        const dock = document.createElement('div');
        dock.className = 'dock-main';
        const pathArrow = "M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z";
        
        let appButtonsHTML = '';
        subScripts.forEach(script => {
            const isEnabled = GM_getValue(`status_${script.id}`, true);
            const stateClass = isEnabled ? 'script-on' : 'script-off';
            const shortName = script.name.substring(0, 2).toUpperCase(); 
            appButtonsHTML += `<button class="btn-app ${stateClass}" data-id="${script.id}" title="${script.name}">${shortName}</button>`;
        });

        dock.innerHTML = `
            <button class="btn-main-toggle" title="Kéo để di chuyển / Vuốt sát mép để ẩn thủ công">
                ${createSVG(pathArrow)}
            </button>
            <div class="apps-sub-container-bg">
                <div class="apps-scroll-layer">
                    ${appButtonsHTML}
                </div>
            </div>
        `;

        const mainToggleBtn = dock.querySelector('.btn-main-toggle');
        const appsScrollLayer = dock.querySelector('.apps-scroll-layer');
        let currentSide = 'right';

        // --- DI CHUYỂN & VUỐT ẨN ---
        let isDragging = false;
        let startX, startY, initialX, initialY;
        let hasMoved = false;

        function onStart(e) {
            if (e.target.closest('.apps-sub-container-bg')) return; 
            isDragging = true; hasMoved = false;
            container.classList.add('dragging');
            stopAutoHideTimer();

            const clientX = e.type.startsWith('touch') ? e.touches[0].clientX : e.clientX;
            const clientY = e.type.startsWith('touch') ? e.touches[0].clientY : e.clientY;
            startX = clientX; startY = clientY;
            const rect = container.getBoundingClientRect();
            initialX = rect.left; initialY = rect.top;
        }

        function onMove(e) {
            if (!isDragging) return;
            const clientX = e.type.startsWith('touch') ? e.touches[0].clientX : e.clientX;
            const clientY = e.type.startsWith('touch') ? e.touches[0].clientY : e.clientY;
            const dx = clientX - startX; const dy = clientY - startY;

            if (Math.abs(dx) > 5 || Math.abs(dy) > 5) hasMoved = true;
            if (!hasMoved) return;

            let targetX = initialX + dx;
            let targetY = initialY + dy;
            targetX = Math.max(-35, Math.min(window.innerWidth - container.offsetWidth + 35, targetX));
            targetY = Math.max(10, Math.min(window.innerHeight - container.offsetHeight - 10, targetY));

            container.style.removeProperty('right'); container.style.removeProperty('top'); container.style.removeProperty('transform');
            container.style.left = `${targetX}px`; container.style.top = `${targetY}px`;
        }

        function onEnd() {
            if (!isDragging) return;
            isDragging = false; container.classList.remove('dragging');

            if (!hasMoved) {
                if (container.classList.contains('edge-hidden-left') || container.classList.contains('edge-hidden-right')) {
                    resetAutoHideTimer();
                } else {
                    startAutoHideTimer();
                }
                return;
            }

            const rect = container.getBoundingClientRect();
            const midPoint = window.innerWidth / 2;
            container.style.removeProperty('left'); container.style.removeProperty('right');

            if (rect.left + rect.width / 2 < midPoint) {
                currentSide = 'left';
                if (rect.left < 15) { container.style.left = '4px'; container.classList.add('edge-hidden-left'); }
                else { container.style.left = '4px'; startAutoHideTimer(); }
            } else {
                currentSide = 'right';
                if (window.innerWidth - rect.right < 15) { container.style.right = '4px'; container.classList.add('edge-hidden-right'); }
                else { container.style.right = '4px'; startAutoHideTimer(); }
            }

            let finalTop = rect.top + rect.height / 2;
            finalTop = Math.max(rect.height / 2 + 10, Math.min(window.innerHeight - rect.height / 2 - 10, finalTop));
            container.style.top = `${finalTop}px`; container.style.transform = 'translateY(-50%)';
        }

        mainToggleBtn.addEventListener('mousedown', onStart);
        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onEnd);
        mainToggleBtn.addEventListener('touchstart', onStart, { passive: true });
        window.addEventListener('touchmove', onMove, { passive: false });
        window.addEventListener('touchend', onEnd);

        // --- ĐÓNG / MỞ DOCK ---
        mainToggleBtn.addEventListener('click', (e) => {
            if (hasMoved) return; 
            e.preventDefault(); e.stopPropagation();

            if (container.classList.contains('edge-hidden-left') || container.classList.contains('edge-hidden-right')) {
                resetAutoHideTimer(); return;
            }

            const isExpanded = dock.classList.contains('expanded');
            if (isExpanded) {
                dock.classList.remove('expanded');
            } else {
                dock.classList.add('expanded');
                setTimeout(() => { appsScrollLayer.scrollTop = 0; }, 50);
            }
            resetAutoHideTimer();
        });

        dock.addEventListener('click', (e) => e.stopPropagation());
        appsScrollLayer.addEventListener('touchstart', (e) => e.stopPropagation(), { passive: true });
        appsScrollLayer.addEventListener('touchmove', (e) => e.stopPropagation(), { passive: false });

        // --- TỰ ĐỘNG ẨN SAU 5S ---
        let hideTimer = null;
        function startAutoHideTimer() {
            stopAutoHideTimer();
            hideTimer = setTimeout(() => {
                if (dock.classList.contains('expanded')) return;
                if (currentSide === 'left') container.classList.add('edge-hidden-left');
                else container.classList.add('edge-hidden-right');
            }, 5000);
        }
        function stopAutoHideTimer() { if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; } }
        function resetAutoHideTimer() { container.classList.remove('edge-hidden-left', 'edge-hidden-right'); startAutoHideTimer(); }

        container.addEventListener('mouseenter', () => {
            container.classList.remove('edge-hidden-left', 'edge-hidden-right'); stopAutoHideTimer();
        });
        container.addEventListener('mouseleave', () => startAutoHideTimer());

        // --- CLICK BẬT TẮT ---
        appsScrollLayer.addEventListener('click', (e) => {
            const btn = e.target.closest('.btn-app');
            if (!btn) return;
            
            const scriptId = btn.getAttribute('data-id');
            const currentStatus = GM_getValue(`status_${scriptId}`, true);
            const newStatus = !currentStatus;
            
            GM_setValue(`status_${scriptId}`, newStatus);
            btn.className = newStatus ? 'btn-app script-on' : 'btn-app script-off';
            console.log(`[Father] ${scriptId} -> ${newStatus ? "BẬT" : "TẮT"}`);
        });

        shadow.appendChild(style);
        shadow.appendChild(dock);
        document.body.appendChild(container);
        startAutoHideTimer();
    }

    // Chạy render UI luôn vì lúc này document-end bảo đảm body đã sẵn sàng hoàn toàn
    initDockUI();
})();
