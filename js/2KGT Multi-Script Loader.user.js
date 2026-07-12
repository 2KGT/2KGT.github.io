// ==UserScript==
// @name         2KGT Multi-Script Loader
// @namespace    http://tampermonkey.net/
// @version      2.2
// @description  Trung tâm điều khiển tích hợp nút nổi tối ưu riêng cho Safari iOS
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

    // --- 1. TỰ ĐỘNG TẢI VÀ CHẠY SCRIPT CON ---
    function loadAndExecuteScript(scriptName) {
        const isEnabled = GM_getValue(`running_${scriptName}`, true);
        if (!isEnabled) return;

        // Tối ưu bộ lọc cho thiết bị di động
        if (scriptName.includes("YouTube") && !window.location.hostname.includes("youtube.com")) {
            return; 
        }

        const fullUrl = `${BASE_URL}${scriptName}`;
        GM_xmlhttpRequest({
            method: "GET",
            url: fullUrl,
            onload: function(response) {
                if (response.status === 200) {
                    try {
                        const runScript = new Function(response.responseText);
                        runScript();
                    } catch (e) {
                        console.error(`[2KGT] Lỗi thực thi ${scriptName}:`, e);
                    }
                }
            }
        });
    }

    SCRIPTS.forEach(script => loadAndExecuteScript(script));

    // --- 2. KHỞI TẠO GIAO DIỆN NÚT NỔI (TỐI ƯU CHO IOS) ---
    function initUI() {
        if (document.getElementById("kgt-container")) return;

        const container = document.createElement('div');
        container.id = "kgt-container";
        
        // Tạo Nút Nổi
        const floatBtn = document.createElement('div');
        floatBtn.id = "kgt-float-btn";
        floatBtn.innerText = "⚙️";
        
        // Tối ưu CSS Inline tránh xung đột thuộc tính trên Safari di động
        Object.assign(floatBtn.style, {
            position: 'fixed', bottom: '30px', right: '20px', zIndex: '2147483647',
            background: '#2563eb', color: '#ffffff', width: '45px', height: '45px',
            borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '20px', boxShadow: '0 4px 12px rgba(0,0,0,0.3)', cursor: 'pointer',
            webkitUserSelect: 'none', userSelect: 'none'
        });

        // Tạo Bảng Menu
        const menu = document.createElement('div');
        menu.id = "kgt-menu";
        Object.assign(menu.style, {
            position: 'fixed', bottom: '85px', right: '20px', zIndex: '2147483647',
            background: '#ffffff', color: '#1e293b', width: '280px', borderRadius: '12px',
            boxShadow: '0 10px 25px rgba(0,0,0,0.2)', padding: '14px', display: 'none',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            border: '1px solid #e2e8f0', boxSizing: 'border-box'
        });

        // Tạo tiêu đề Menu
        const title = document.createElement('div');
        title.innerHTML = `<b style="font-size:15px; color:#0f172a;">🛠️ 2KGT Control Center</b>`;
        title.style.borderBottom = '1px solid #e2e8f0';
        title.style.paddingBottom = '8px';
        title.style.marginBottom = '8px';
        menu.appendChild(title);

        // Duyệt danh sách tạo các dòng Bật/Tắt
        SCRIPTS.forEach((script, index) => {
            const isChecked = GM_getValue(`running_${script}`, true);
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

        // Thêm ghi chú dưới cùng
        const note = document.createElement('div');
        note.innerText = "* Vui lòng tải lại trang sau khi thay đổi.";
        Object.assign(note.style, { fontSize: '10px', color: '#94a3b8', marginTop: '10px', textAlign: 'center' });
        menu.appendChild(note);

        container.appendChild(floatBtn);
        container.appendChild(menu);
        
        // Chèn vào tài liệu một cách an toàn nhất
        if (document.body) {
            document.body.appendChild(container);
        } else {
            document.documentElement.appendChild(container);
        }

        // --- SỰ KIỆN CHẠM (TOUCH EVENTS) CHO IPHONE ---
        floatBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
        });

        document.addEventListener('click', (e) => {
            if (!container.contains(e.target)) menu.style.display = 'none';
        });

        // Gán sự kiện lưu trạng thái cho Checkbox
        SCRIPTS.forEach((script, index) => {
            const chk = document.getElementById(`kgt-chk-${index}`);
            if (chk) {
                chk.addEventListener('change', function() {
                    GM_setValue(`running_${script}`, this.checked);
                });
            }
        });
    }

    // Cơ chế kích hoạt giao diện đa tầng chống bỏ lỡ sự kiện trên iOS
    if (document.readyState === "complete" || document.readyState === "interactive") {
        initUI();
    } else {
        window.addEventListener('DOMContentLoaded', initUI);
        window.addEventListener('load', initUI);
    }
})();
