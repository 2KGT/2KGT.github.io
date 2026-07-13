// ==UserScript==
// @name         2KGT Multi-Script Loader (Father)
// @namespace    http://tampermonkey.net/
// @version      13.0
// @description  Nút chính vuông 37px đồng bộ app con, Dock 45px, nạp script động và hỗ trợ kéo vuốt ẩn thủ công 2/3 vào mép viền.
// @author       2KGT
// @match        *://*/*
// @run-at       document-end
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // ==== CẤU HÌNH NẠP SCRIPT ĐỘNG ====
    const BASE_URL = "https://raw.githubusercontent.com/2KGT/2KGT.github.io/main/js/";

    // Danh sách ứng dụng con đồng bộ từ kho lưu trữ của bạn
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

    // ==== QUẢN LÝ TRẠNG THÁI BẬT/TẮT (sessionStorage) ====
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
        } catch {}
    }

    let activeState = loadActiveState();

    // ==== TẢI VÀ CHẠY SCRIPT CON ====
    async function loadAndRun(scriptDef) {
        const url = BASE_URL + encodeURIComponent(scriptDef.file).replace(/%2F/g, "/");
        try {
            const res = await fetch(url, { cache: "no-store" });
            if (!res.ok) throw new Error("HTTP " + res.status);
            const code = await res.text();
            const runner = new Function(code);
            runner();
            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }

    // ==== KÍCH HOẠT / KHÔI PHỤC SCRIPT KHI CLICK APP CON ====
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
            const confirmReload = confirm(scriptDef.name + " đang bật.\nBấm OK để tải lại trang (khái phục bản gốc).");
            if (confirmReload) {
                delete activeState[scriptDef.key];
                saveActiveState(activeState);
                location.reload();
            }
        }
    }

    function createSVG(dPath, styleStr = '', viewBox = '0 0 24 24') {
        return `<svg viewBox="${viewBox}" style="width:18px;height:18px;fill:currentColor;display:block;${styleStr}"><path d="${dPath}"/></svg>`;
    }

    // 1. Tạo Container gốc cho giao diện mới
    const container = document.createElement('div');
    container.id = 'lc-multitask-container';
    container.style.cssText = 'position:fixed !important; z-index:999999 !important; right:4px !important; top:50% !important; transform:translateY(-50%) !important; touch-action:none !important; user-select:none !important;';
    const shadow = container.attachShadow({ mode: 'open' });

    // 2. Định dạng CSS hệ thống - Gọn gàng 45px & Ẩn 2/3 thủ công/tự động
    const style = document.createElement('style');
    style.textContent = `
        :host {
            display: block !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            transition: right 0.4s cubic-bezier(0.16, 1, 0.3, 1), left 0.4s cubic-bezier(0.16, 1, 0.3, 1), top 0.4s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.3s ease !important;
        }
        
        :host(.dragging) {
            transition: none !important;
        }
        
        /* LOGIC VUỐT SÁT MÉP GIẤU 2/3 THÂN MÌNH (Thò lại khoảng 14px vừa đủ chạm nhẹ) */
        :host(.edge-hidden-right) { right: -31px !important; opacity: 0.6 !important; }
        :host(.edge-hidden-left) { left: -31px !important; opacity: 0.6 !important; }
        
        :host(:hover) { opacity: 1 !important; }

        /* DOCK CHA CHUẨN ĐẸP 45PX */
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
            
            min-width: 45px !important;
            max-width: 45px !important;
            min-height: 45px !important;
            max-height: 45px !important;
        }

        .dock-main.expanded {
            border-radius: 14px !important;
            min-height: 150px !important;
            max-height: 240px !important;
            background: rgba(255, 255, 255, 0.95) !important;
            box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.08), 0 12px 36px rgba(0, 0, 0, 0.15) !important;
        }

        /* NÚT CHÍNH HÌNH VUÔNG BO 9PX ĐỒNG BỘ HOÀN HẢO */
        .btn-main-toggle { 
            width: 37px !important;  
            height: 37px !important;
            border-radius: 9px !important; 
            border: none !important;
            background: #10a37f !important; 
            color: #ffffff !important; 
            cursor: move !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            outline: none !important;
            box-sizing: border-box !important;
            flex-shrink: 0 !important;
            touch-action: none !important;
            transition: background 0.2s, border-radius 0.3s, transform 0.1s !important;
            z-index: 5 !important;
            box-shadow: 0 2px 6px rgba(16, 163, 127, 0.25) !important;
        }
        
        .btn-main-toggle:active { transform: scale(0.92) !important; }
        .btn-main-toggle svg { transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important; }
        .dock-main.expanded .btn-main-toggle svg { transform: rotate(180deg) !important; }

        /* ĐỒNG BỘ DARK MODE */
        @media (prefers-color-scheme: dark) {
            .dock-main {
                background: rgba(28, 28, 30, 0.85) !important;
                box-shadow: inset 0 0 0 0.5px rgba(255, 255, 255, 0.08), 0 8px 24px rgba(0, 0, 0, 0.25) !important;
            }
            .dock-main.expanded {
                background: rgba(28, 28, 30, 0.96) !important;
            }
        }

        /* LỚP LÓT CHỨA DANH SÁCH APP CON CUỘN */
        .apps-sub-container-bg {
            width: 37px !important;
            display: flex !important;
            flex-direction: column !important;
            background: transparent !important;
            border-radius: 9px !important;
            margin-top: 0px !important;
            box-sizing: border-box !important;
            overflow: hidden !important;
            flex-shrink: 0 !important;
            
            opacity: 0 !important;
            max-height: 0px !important;
            transform: scale(0.95) translateY(-6px) !important;
            transition: opacity 0.2s ease, transform 0.28s cubic-bezier(0.16, 1, 0.3, 1), max-height 0.3s ease, margin-top 0.2s !important;
        }

        .dock-main.expanded .apps-sub-container-bg {
            opacity: 1 !important;
            max-height: 185px !important;
            margin-top: 6px !important;
            transform: scale(1) translateY(0) !important;
        }

        /* VÙNG CUỘN CHỨA APP CON (Giới hạn hiển thị mượt mà) */
        .apps-scroll-layer {
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            gap: 7px !important;
            width: 37px !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            scrollbar-width: none !important;
            -webkit-overflow-scrolling: touch !important;
        }
        .apps-scroll-layer::-webkit-scrollbar { display: none !important; }

        /* CÁC NÚT APP CON TIÊU CHUẨN VUÔNG 37PX */
        .btn-app {
            position: relative !important;
            width: 37px !important;  
            height: 37px !important;
            border-radius: 9px !important;
            border: none !important;
            background: linear-gradient(145deg, #3a3a3c, #1c1c1e) !important;
            cursor: pointer !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-size: 17px !important;
            transition: transform 0.12s ease !important;
            padding: 0 !important;
            overflow: visible !important;
            outline: none !important;
            box-sizing: border-box !important;
            flex-shrink: 0 !important;
            box-shadow: 0 3px 8px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.06) !important;
        }
        .btn-app:active { transform: scale(0.88) !important; }

        /* VÒNG SÁNG GLOW BÁO TRẠNG THÁI SCRIPT CON */
        .father-app-glow {
            position: absolute !important;
            inset: -3px !important;
            border-radius: 12px !important;
            z-index: 1 !important;
            opacity: 0 !important;
            transition: opacity 0.25s ease !important;
            background: radial-gradient(circle, rgba(48,209,88,0.55) 0%, rgba(48,209,88,0.15) 60%, transparent 75%) !important;
            box-shadow: 0 0 6px 2px rgba(48,209,88,0.5) !important;
            pointer-events: none !important;
        }
        .father-app-glow.on { opacity: 1 !important; }
        .father-app-glow.loading {
            opacity: 1 !important;
            background: radial-gradient(circle, rgba(255,159,10,0.55) 0%, rgba(255,159,10,0.15) 60%, transparent 75%) !important;
            box-shadow: 0 0 6px 2px rgba(255,159,10,0.5) !important;
            animation: father-pulse 0.9s ease-in-out infinite !important;
        }
        .father-app-glow.error {
            opacity: 1 !important;
            background: radial-gradient(circle, rgba(255,69,58,0.55) 0%, rgba(255,69,58,0.15) 60%, transparent 75%) !important;
            box-shadow: 0 0 6px 2px rgba(255,69,58,0.5) !important;
        }
        @keyframes father-pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
    `;

    // 3. Xây dựng cây cấu trúc DOM giao diện Father mới
    const dock = document.createElement('div');
    dock.className = 'dock-main';

    const pathArrow = "M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z";

    // Khởi tạo nút Toggle chính
    dock.innerHTML = `
        <button class="btn-main-toggle" title="Kéo di chuyển / Vuốt sát mép để ẩn 2/3 thủ công">
            ${createSVG(pathArrow)}
        </button>
        <div class="apps-sub-container-bg">
            <div class="apps-scroll-layer"></div>
        </div>
    `;

    const mainToggleBtn = dock.querySelector('.btn-main-toggle');
    const appsScrollLayer = dock.querySelector('.apps-scroll-layer');
    let currentSide = 'right';

    // Đổ danh sách Script con vào layer cuộn
    SCRIPTS.forEach((scriptDef) => {
        const itemBtn = document.createElement("button");
        itemBtn.className = "btn-app";
        itemBtn.title = scriptDef.name;

        const glow = document.createElement("div");
        glow.className = "father-app-glow" + (activeState[scriptDef.key] ? " on" : "");

        const iconSpan = document.createElement("span");
        iconSpan.style.cssText = "position:relative; z-index:2;";
        iconSpan.textContent = scriptDef.icon;

        itemBtn.appendChild(glow);
        itemBtn.appendChild(iconSpan);

        itemBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            toggleScript(scriptDef, glow);
        });

        appsScrollLayer.appendChild(itemBtn);
    });

    // --- LOGIC KÉO THẢ & CHỦ ĐỘNG VUỐT CẤT VÀO MÉP ---
    let isDragging = false;
    let startX, startY, initialX, initialY;
    let hasMoved = false;

    function onStart(e) {
        if (e.target.closest('.apps-sub-container-bg')) return; 

        isDragging = true;
        hasMoved = false;
        container.classList.add('dragging');
        stopAutoHideTimer();

        const clientX = e.type.startsWith('touch') ? e.touches[0].clientX : e.clientX;
        const clientY = e.type.startsWith('touch') ? e.touches[0].clientY : e.clientY;

        startX = clientX;
        startY = clientY;

        const rect = container.getBoundingClientRect();
        initialX = rect.left;
        initialY = rect.top;
    }

    function onMove(e) {
        if (!isDragging) return;
        
        const clientX = e.type.startsWith('touch') ? e.touches[0].clientX : e.clientX;
        const clientY = e.type.startsWith('touch') ? e.touches[0].clientY : e.clientY;

        const dx = clientX - startX;
        const dy = clientY - startY;

        if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
            hasMoved = true;
        }

        if (!hasMoved) return;

        let targetX = initialX + dx;
        let targetY = initialY + dy;

        // Cho phép kéo dôi hẳn ra viền để kích hoạt ẩn thủ công ngay lập tức
        targetX = Math.max(-35, Math.min(window.innerWidth - container.offsetWidth + 35, targetX));
        targetY = Math.max(10, Math.min(window.innerHeight - container.offsetHeight - 10, targetY));

        container.style.removeProperty('right');
        container.style.removeProperty('top');
        container.style.removeProperty('transform');
        container.style.left = `${targetX}px`;
        container.style.top = `${targetY}px`;
    }

    function onEnd() {
        if (!isDragging) return;
        isDragging = false;
        container.classList.remove('dragging');

        if (!hasMoved) {
            // Nếu đang ẩn 2/3 mà chạm nhẹ, khôi phục lại trạng thái lộ diện
            if (container.classList.contains('edge-hidden-left') || container.classList.contains('edge-hidden-right')) {
                resetAutoHideTimer();
            } else {
                startAutoHideTimer();
            }
            return;
        }

        const rect = container.getBoundingClientRect();
        const midPoint = window.innerWidth / 2;
        
        container.style.removeProperty('left');
        container.style.removeProperty('right');

        if (rect.left + rect.width / 2 < midPoint) {
            currentSide = 'left';
            if (rect.left < 15) { // Kéo sát lề trái thủ công
                container.style.left = '4px';
                container.classList.add('edge-hidden-left');
            } else {
                container.style.left = '4px';
                startAutoHideTimer();
            }
        } else {
            currentSide = 'right';
            if (window.innerWidth - rect.right < 15) { // Kéo sát lề phải thủ công
                container.style.right = '4px';
                container.classList.add('edge-hidden-right');
            } else {
                container.style.right = '4px';
                startAutoHideTimer();
            }
        }

        let finalTop = rect.top + rect.height / 2;
        finalTop = Math.max(rect.height / 2 + 10, Math.min(window.innerHeight - rect.height / 2 - 10, finalTop));
        container.style.top = `${finalTop}px`;
        container.style.transform = 'translateY(-50%)';
    }

    mainToggleBtn.addEventListener('mousedown', onStart);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onEnd);

    mainToggleBtn.addEventListener('touchstart', onStart, { passive: true });
    window.addEventListener('touchmove', onMove, { passive: false });
    window.addEventListener('touchend', onEnd);

    // --- LOGIC BẤM ĐÓNG / MỞ DOCK ---
    mainToggleBtn.addEventListener('click', (e) => {
        if (hasMoved) return; 
        
        e.preventDefault();
        e.stopPropagation();

        if (container.classList.contains('edge-hidden-left') || container.classList.contains('edge-hidden-right')) {
            resetAutoHideTimer();
            return;
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

    // --- CÔ LẬP SỰ KIỆN CUỘN TRÊN ĐIỆN THOẠI ---
    appsScrollLayer.addEventListener('touchstart', (e) => e.stopPropagation(), { passive: true });
    appsScrollLayer.addEventListener('touchmove', (e) => e.stopPropagation(), { passive: false });

    // --- TỰ ĐỘNG THỤT ẨN 2/3 SAU 5 GIÂY KHÔNG DÙNG ---
    let hideTimer = null;

    function startAutoHideTimer() {
        stopAutoHideTimer();
        hideTimer = setTimeout(() => {
            if (dock.classList.contains('expanded')) return;
            if (currentSide === 'left') {
                container.classList.add('edge-hidden-left');
            } else {
                container.classList.add('edge-hidden-right');
            }
        }, 5000); 
    }

    function stopAutoHideTimer() {
        if (hideTimer) {
            clearTimeout(hideTimer);
            hideTimer = null;
        }
    }

    function resetAutoHideTimer() {
        container.classList.remove('edge-hidden-left', 'edge-hidden-right');
        startAutoHideTimer();
    }

    container.addEventListener('mouseenter', () => {
        container.classList.remove('edge-hidden-left', 'edge-hidden-right');
        stopAutoHideTimer();
    });
    container.addEventListener('mouseleave', () => startAutoHideTimer());

    // 4. Nhúng giao diện vào trang web thông qua Shadow DOM
    shadow.appendChild(style);
    shadow.appendChild(dock);
    
    if (document.body) {
        document.body.appendChild(container);
    } else {
        window.addEventListener('DOMContentLoaded', () => document.body.appendChild(container));
    }

    startAutoHideTimer();
})();
