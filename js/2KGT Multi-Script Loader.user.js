// ==UserScript==
// @name         2KGT Multi-Script Control Center
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  Trung tâm điều khiển bật/tắt trực quan cho các script con của 2KGT
// @author       You
// @match        *://*/*
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_addStyle
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

    // --- 1. TỰ ĐỘNG CHẠY CÁC SCRIPT ĐƯỢC BẬT ---
    function loadAndExecuteScript(scriptName) {
        // Kiểm tra xem người dùng có tắt script này không (Mặc định là TRUE - Bật)
        const isEnabled = GM_getValue(`running_${scriptName}`, true);
        if (!isEnabled) {
            console.log(`⏸️ Script [${scriptName}] đang TẮT.`);
            return;
        }

        // Lọc nhanh: Script YouTube chỉ chạy trên trang YouTube
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
                        console.log(`✅ Đã chạy: ${scriptName}`);
                    } catch (e) {
                        console.error(`❌ Lỗi thực thi [${scriptName}]:`, e);
                    }
                }
            }
        });
    }

    // Kích hoạt chạy ngầm các script hợp lệ ngay lập tức
    SCRIPTS.forEach(script => loadAndExecuteScript(script));


    // --- 2. XÂY DỰNG GIAO DIỆN ĐIỀU KHIỂN (UI) MÀN HÌNH ---
    // Thêm CSS cho giao diện (Nút nổi, Menu, Công tắc)
    GM_addStyle(`
        #kgt-float-btn { position: fixed; bottom: 20px; right: 20px; z-index: 999999; background: #2563eb; color: #fff; padding: 10px 14px; borderRadius: 50px; cursor: pointer; boxShadow: 0 4px 12px rgba(0,0,0,0.3); fontSize: 13px; fontWeight: bold; fontFamily: system-ui, -apple-system, sans-serif; userSelect: none; transition: transform 0.2s; }
        #kgt-float-btn:hover { transform: scale(1.05); background: #1d4ed8; }
        #kgt-menu { position: fixed; bottom: 75px; right: 20px; z-index: 999999; background: #ffffff; color: #1e293b; width: 320px; borderRadius: 12px; boxShadow: 0 10px 25px rgba(0,0,0,0.2); padding: 16px; fontFamily: system-ui, -apple-system, sans-serif; display: none; border: 1px solid #e2e8f0; }
        #kgt-menu h3 { margin: 0 0 12px 0; fontSize: 16px; fontWeight: 700; color: #0f172a; borderBottom: 1px solid #f1f5f9; paddingBottom: 8px; display: flex; justify-content: space-between; align-items: center; }
        .kgt-script-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; borderBottom: 1px dashed #f1f5f9; }
        .kgt-script-name { fontSize: 12px; whiteSpace: nowrap; overflow: hidden; textOverflow: ellipsis; maxWidth: 220px; color: #334155; }
        
        /* CSS Công tắc bật tắt (Toggle Switch) */
        .kgt-switch { position: relative; display: inline-block; width: 36px; height: 20px; }
        .kgt-switch input { opacity: 0; width: 0; height: 0; }
        .kgt-slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #cbd5e1; transition: .3s; borderRadius: 20px; }
        .kgt-slider:before { position: absolute; content: ""; height: 14px; width: 14px; left: 3px; bottom: 3px; background-color: white; transition: .3s; borderRadius: 50%; }
        input:checked + .kgt-slider { background-color: #22c55e; }
        input:checked + .kgt-slider:before { transform: translateX(16px); }
        
        .kgt-note { font-size: 10px; color: #94a3b8; text-align: center; margin-top: 12px; }
    `);

    // Đợi trang tải xong phần Body để vẽ Giao diện
    window.addEventListener('DOMContentLoaded', () => {
        // Tạo Container chính để không bị ảnh hưởng bởi CSS của trang web
        const container = document.createElement('div');
        container.id = "kgt-control-center";

        // 1. Tạo Nút Nổi
        const floatBtn = document.createElement('div');
        floatBtn.id = "kgt-float-btn";
        floatBtn.innerText = "⚙️ 2KGT Menu";

        // 2. Tạo Bảng Menu Điều Khiển
        const menu = document.createElement('div');
        menu.id = "kgt-menu";
        
        let menuHTML = `<h3>🛠️ Hệ thống Script <span>v2.0</span></h3>`;
        
        // Tự động duyệt danh sách tạo công tắc
        SCRIPTS.forEach((script, index) => {
            const isChecked = GM_getValue(`running_${script}`, true) ? "checked" : "";
            // Rút gọn tên hiển thị cho đẹp giao diện
            const displayName = script.replace("_user.js", "").replace(".user.js", "").replace(".js", "");
            
            menuHTML += `
                <div class="kgt-script-item">
                    <span class="kgt-script-name" title="${script}">${index + 1}. ${displayName}</span>
                    <label class="kgt-switch">
                        <input type="checkbox" id="kgt-chk-${index}" data-script="${script}" ${isChecked}>
                        <span class="kgt-slider"></span>
                    </label>
                </div>
            `;
        });
        
        menuHTML += `<div class="kgt-note">* Vui lòng F5 (Tải lại trang) sau khi bật/tắt.</div>`;
        menu.innerHTML = menuHTML;

        // Tích hợp vào container và đẩy ra màn hình
        container.appendChild(floatBtn);
        container.appendChild(menu);
        document.body.appendChild(container);

        // --- 3. XỬ LÝ SỰ KIỆN TƯƠNG TÁC ---
        // Bấm nút nổi để Ẩn/Hiện Menu
        floatBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const isDisplayed = menu.style.display === "block";
            menu.style.display = isDisplayed ? "none" : "block";
        });

        // Click ra ngoài Menu thì tự động đóng menu lại cho gọn
        document.addEventListener('click', (e) => {
            if (!container.contains(e.target)) {
                menu.style.display = "none";
            }
        });

        // Lắng nghe sự kiện gạt công tắc Bật/Tắt
        SCRIPTS.forEach((script, index) => {
            const checkbox = document.getElementById(`kgt-chk-${index}`);
            checkbox.addEventListener('change', function() {
                GM_setValue(`running_${script}`, this.checked);
                console.log(`🔄 Đã thay đổi trạng thái [${script}] thành: ${this.checked ? "BẬT" : "TẮT"}`);
            });
        });
    });

})();
