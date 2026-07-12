// ==UserScript==
// @name         2KGT Multi-Script Loader
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Tự động tải và chạy các script con từ GitHub của 2KGT
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
        "ABPVN_AdsBlock.user.js", // Lưu ý: Nên thêm đuôi .js nếu trên GitHub file tên như vậy
        "AdGuard_Extra.user.js",
        "AdGuard_Popup_Blocker.user.js",
        "image-grid-lister_user.js",
        "open_inapp.js"
    ];

    // Hàm tải script an toàn qua XHR (Tránh bị chặn bởi Content Security Policy của trang web)
    function loadAndExecuteScript(scriptName) {
        const fullUrl = `${BASE_URL}${scriptName}`;

        GM_xmlhttpRequest({
            method: "GET",
            url: fullUrl,
            onload: function(response) {
                if (response.status === 200) {
                    try {
                        // Khởi tạo script trong môi trường của Userscript thay vì cửa sổ gốc (Window)
                        // Giúp bảo vệ quyền lợi GM_* của các script adblock
                        const runScript = new Function(response.responseText);
                        runScript();
                        console.log(`✅ Chạy thành công script: ${scriptName}`);
                    } catch (e) {
                        console.error(`❌ Lỗi khi thực thi script [${scriptName}]:`, e);
                    }
                } else {
                    console.warn(`⚠️ Không thể tải script (Status ${response.status}): ${scriptName}`);
                }
            },
            onerror: function(err) {
                console.error(`💥 Lỗi kết nối khi tải: ${scriptName}`, err);
            }
        });
    }

    // Tự động kích hoạt toàn bộ danh sách khi vào trang web
    // Bạn có thể viết thêm điều kiện if (window.location.href...) nếu muốn lọc script theo trang.
    SCRIPTS.forEach(script => {
        // Ví dụ lọc nhỏ: Chỉ tải script youtube khi ở trang youtube
        if (script.includes("YouTube") && !window.location.hostname.includes("youtube.com")) {
            return; // Bỏ qua nếu không phải YouTube
        }
        
        loadAndExecuteScript(script);
    });
})();
