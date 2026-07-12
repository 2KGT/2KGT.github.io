// ==UserScript==
// @name         Master Loader
// @namespace    http://tampermonkey.net/
// @version      3.0
// @description  Trung tâm điều khiển script con - Sửa lỗi không hiện nút trên Safari iOS
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

    // --- 1. TẢI VÀ THỰC THI SCRIPT CON AN TOÀN TRÊN SAFARI iOS ---
    function loadAndExecuteScript(scriptName) {
        const isEnabled = GM_getValue(`running_${scriptName}`, true);
        if (!isEnabled) return;

        if (scriptName.includes("YouTube") && !window.location.hostname.includes("youtube.com")) return; 

        const fullUrl = `${BASE_URL}${scriptName}`;
        GM_xmlhttpRequest({
            method: "GET",
            url: fullUrl,
            onload: function(response) {
                if (response.status === 200) {
                    try {
                        // Chèn mã nguồn trực tiếp vào tài liệu để vượt rào Isolated Context của iOS
                        const scriptEl = document.createElement('script');
                        scriptEl.textContent = response.responseText;
                        (document.head || document.documentElement).appendChild(scriptEl);
                        console.log(`[2KGT Master] Đã kích hoạt thành công: ${scriptName}`);
                    } catch (e) {
                        console.error(`[2KGT Master] Lỗi khi thực thi ${scriptName}:`, e);
                    }
                }
            }
        });
    }

    // Kích hoạt tiến trình tải file con ngay lập tức
    SCRIPTS.forEach(script => loadAndExecuteScript(script));


    // --- 2. XÂY DỰNG GIAO DIỆN NÚT NỔI HỆ THỐNG ---
    function initMasterUI() {
        if (document.getElementById("kgt-container")) return;

        // Tạo container và chèn thẳng vào gốc HTML giống cấu trúc file con của bạn
        const container = document.createElement('div');
        container.id = "kgt-container";
        
        const floatBtn = document.createElement('div');
        floatBtn.id = "kgt-float-btn";
        floatBtn.innerText = "⚙️";
        
        // CSS Inline với Z-Index tối đa để không bị che khuất trên iPhone
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

        const note = document.createElement('div');
        note.innerText = "* Vui lòng tải lại trang sau khi bật/tắt.";
        Object.assign(note.style, { fontSize: '10px', color: '#94a3b8', marginTop: '10px', textAlign: 'center' });
        menu.appendChild(note);

        container.appendChild(floatBtn);
        container.appendChild(menu);
        
        // Phương thức chèn phần tử ép buộc hiển thị (chuẩn gốc HTML)
        document.documentElement.appendChild(container);

        // Đăng ký tương tác sự kiện chạm cảm ứng trên màn hình iPhone
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
                    GM_setValue(`running_${script}`, this.checked);
                });
            }
        });
    }

    // --- 3. ĐẢM BẢO CHẠY UI NGAY KHI PHẦN TỬ GỐC ĐẦU TIÊN CỦA TRANG XUẤT HIỆN ---
    if (document.documentElement) {
        initMasterUI();
    } else {
        const checkExist = setInterval(function() {
            if (document.documentElement) {
                initMasterUI();
                clearInterval(checkExist);
            }
        }, 10);
    }
})();
