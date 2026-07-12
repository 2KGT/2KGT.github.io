// ==UserScript==
// @name         Master Loader
// @namespace    http://tampermonkey.net/
// @version      4.0
// @description  Trung tâm điều khiển script con - Sửa triệt để lỗi xung đột logic trên iOS Safari
// @author       2KGT
// @match        *://*/*
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @run-at       document-start
// ==/UserScript==

(function() {
    'use strict';

    const BASE_URL = "https://raw.githubusercontent.com/2KGT/2KGT.github.io/refs/heads/main/js/";
    const SCRIPTS = [
        "ACT_YouTube_DM_Auto-translate_user.js",
        "auto-translate-vi_user.js",
        "ABPVN_AdsBlock.user.js",
        "AdGuard_Extra.user.js",
        "AdGuard_Popup_Blocker.user.js",
        "image-grid-lister_user.js",
        "open_inapp.js"
    ];

    // --- 1. KHỞI TẠO GIAO DIỆN TRƯỚC (ĐỂ TRÁNH TREO SCRIPT) ---
    function initMasterUI() {
        if (document.getElementById("kgt-container")) return;

        const container = document.createElement('div');
        container.id = "kgt-container";
        
        const floatBtn = document.createElement('div');
        floatBtn.id = "kgt-float-btn";
        floatBtn.innerText = "⚙️";
        
        // Cố định vị trí nằm TRÊN nút Xem media của file con (cách đáy 90px)
        Object.assign(floatBtn.style, {
            position: 'fixed', bottom: '90px', right: '20px', zIndex: '2147483647',
            background: '#111', color: '#fff', border: '1px solid #333', width: '45px', height: '45px',
            borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '18px', boxShadow: '0 4px 14px rgba(0,0,0,.35)', cursor: 'pointer',
            webkitUserSelect: 'none', userSelect: 'none'
        });

        const menu = document.createElement('div');
        menu.id = "kgt-menu";
        Object.assign(menu.style, {
            position: 'fixed', bottom: '145px', right: '20px', zIndex: '2147483647',
            background: '#ffffff', color: '#1e293b', width: '280px', borderRadius: '12px',
            boxShadow: '0 10px 25px rgba(0,0,0,0.2)', padding: '14px', display: 'none',
            fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif',
            border: '1px solid #e2e8f0', boxSizing: 'border-box'
        });

        const title = document.createElement('div');
        title.innerHTML = `<b style="font-size:14px; color:#0f172a;">🛠️ 2KGT Control Center</b>`;
        title.style.borderBottom = '1px solid #e2e8f0';
        title.style.paddingBottom = '6px';
        title.style.marginBottom = '8px';
        menu.appendChild(title);

        SCRIPTS.forEach((script, index) => {
            let isChecked = true;
            try { isChecked = GM_getValue(`running_${script}`, true); } catch(e) {}
            
            const displayName = script.replace("_user.js", "").replace(".user.js", "").replace(".js", "");
            const item = document.createElement('div');
            Object.assign(item.style, {
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '6px 0', borderBottom: '1px dashed #f1f5f9', fontSize: '12px'
            });

            item.innerHTML = `
                <span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:180px; color:#334155;">${index + 1}. ${displayName}</span>
                <input type="checkbox" id="kgt-chk-${index}" ${isChecked ? 'checked' : ''} style="width:34px; height:18px; cursor:pointer;">
            `;
            menu.appendChild(item);
        });

        const note = document.createElement('div');
        note.innerText = "* Vui lòng tải lại trang sau khi bật/tắt.";
        Object.assign(note.style, { fontSize: '10px', color: '#94a3b8', marginTop: '10px', textAlign: 'center' });
        menu.appendChild(note);

        container.appendChild(floatBtn);
        container.appendChild(menu);
        
        // Găm trực tiếp vào cấu trúc tài liệu gốc
        document.documentElement.appendChild(container);

        // Sự kiện click mở menu
        floatBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
        });

        document.addEventListener('click', (e) => {
            if (!container.contains(e.target)) menu.style.display = 'none';
        });

        SCRIPTS.forEach((script, index) => {
            const chk = document.getElementById(`kgt-chk-${index}`);
            if (chk) {
                chk.addEventListener('change', function() {
                    try { GM_setValue(`running_${script}`, this.checked); } catch(e) {}
                });
            }
        });
    }

    // --- 2. TẢI VÀ BIÊN DỊCH FILE CON THÀNH BLOB URL (CÔ LẬP HOÀN TOÀN LOGIC) ---
    function loadAndExecuteScript(scriptName) {
        let isEnabled = true;
        try { isEnabled = GM_getValue(`running_${scriptName}`, true); } catch(e) {}
        if (!isEnabled) return;

        if (scriptName.includes("YouTube") && !window.location.hostname.includes("youtube.com")) return; 

        const fullUrl = `${BASE_URL}${scriptName}`;
        GM_xmlhttpRequest({
            method: "GET",
            url: fullUrl,
            onload: function(response) {
                if (response.status === 200) {
                    try {
                        // Chuyển mã nguồn thành một File ảo (Blob) giúp chạy tách luồng dữ liệu độc lập,
                        // triệt tiêu hoàn toàn lỗi trùng tên biến gây sập script ngầm trên iOS.
                        const blob = new Blob([response.responseText], { type: 'text/javascript' });
                        const blobUrl = URL.createObjectURL(blob);
                        
                        const scriptEl = document.createElement('script');
                        scriptEl.src = blobUrl;
                        
                        // Đưa vào DOM để kích hoạt file con hoạt động độc lập
                        (document.head || document.documentElement).appendChild(scriptEl);
                        console.log(`[2KGT Master] Đã tải luồng biệt lập: ${scriptName}`);
                    } catch (e) {
                        console.error(`[2KGT Master] Lỗi phân tách luồng ${scriptName}:`, e);
                    }
                }
            }
        });
    }

    // Khởi chạy tiến trình kiểm tra cấu trúc trang
    if (document.documentElement) {
        initMasterUI();
    } else {
        const checkExist = setInterval(function() {
            if (document.documentElement) {
                initMasterUI();
                clearInterval(checkExist);
            }
        }, 5);
    }

    // Thực thi kích hoạt danh sách file con
    SCRIPTS.forEach(script => loadAndExecuteScript(script));
})();
