// ==UserScript==
// @name         Master Loader
// @namespace    http://tampermonkey.net/
// @version      4.1
// @description  Trung tâm điều khiển script con - Sửa lỗi không mở được menu trên iOS Safari
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

    // --- 1. KHỞI TẠO GIAO DIỆN VÀ FIX LỖI SỰ KIỆN CHẠM ---
    function initMasterUI() {
        if (document.getElementById("kgt-container")) return;

        const container = document.createElement('div');
        container.id = "kgt-container";
        
        const floatBtn = document.createElement('div');
        floatBtn.id = "kgt-float-btn";
        floatBtn.innerText = "⚙️";
        
        // Vị trí cố định phía trên nút Xem media của file con
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
        
        document.documentElement.appendChild(container);

        // Hàm xử lý bật tắt menu chung cho cả Click và Chạm ngón tay
        function toggleMenu(e) {
            e.preventDefault();
            e.stopPropagation();
            if (menu.style.display === 'block') {
                menu.style.display = 'none';
            } else {
                menu.style.display = 'block';
            }
        }

        // Sử dụng touchstart để nhạy hơn gấp 4 lần trên màn hình cảm ứng iOS
        floatBtn.addEventListener('touchstart', toggleMenu, { passive: false });
        floatBtn.addEventListener('click', toggleMenu);

        // Đóng menu an toàn khi chạm ra ngoài vùng menu trên Safari
        var closeHandler = function(e) {
            if (!container.contains(e.target)) {
                menu.style.display = 'none';
            }
        };
        document.addEventListener('touchstart', closeHandler, { passive: true });
        document.addEventListener('click', closeHandler);

        SCRIPTS.forEach((script, index) => {
            const chk = document.getElementById(`kgt-chk-${index}`);
            if (chk) {
                // Đăng ký sự kiện thay đổi công tắc bật tắt
                var changeHandler = function() {
                    try { GM_setValue(`running_${script}`, this.checked); } catch(e) {}
                };
                chk.addEventListener('change', changeHandler);
            }
        });
    }

    // --- 2. TẢI FILE CON THÀNH BLOB URL ---
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
                        const blob = new Blob([response.responseText], { type: 'text/javascript' });
                        const blobUrl = URL.createObjectURL(blob);
                        
                        const scriptEl = document.createElement('script');
                        scriptEl.src = blobUrl;
                        
                        (document.head || document.documentElement).appendChild(scriptEl);
                        console.log(`[2KGT Master] Đã tải luồng biệt lập: ${scriptName}`);
                    } catch (e) {
                        console.error(`[2KGT Master] Lỗi phân tách luồng ${scriptName}:`, e);
                    }
                }
            }
        });
    }

    // Tiến trình găm UI hệ thống lên trang web
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

    SCRIPTS.forEach(script => loadAndExecuteScript(script));
})();
