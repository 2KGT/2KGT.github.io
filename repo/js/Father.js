// ==UserScript==
// @name         Father Script Manager
// @namespace    https://github.com/2KGT/2KGT.github.io
// @version      1.1
// @description  Quản lý và kích hoạt các script con từ kho lưu trữ GitHub
// @author       2KGT
// @match        *://*/*
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @run-at       document-start
// ==/UserScript==

(function() {
    'is use strict';

    // Cấu hình danh sách các script con với link raw chuẩn xác
    const subScripts = [
        {
            name: "ABPVN AdsBlock",
            url: "https://raw.githubusercontent.com/2KGT/2KGT.github.io/refs/heads/main/repo/js/ABPVN%20AdsBlock.user.js"
        },
        {
            name: "YouTube Auto-translate",
            url: "https://raw.githubusercontent.com/2KGT/2KGT.github.io/refs/heads/main/repo/js/ACT.YouTube.DM.Auto-translate.user.js"
        },
        {
            name: "AdGuard Extra",
            url: "https://raw.githubusercontent.com/2KGT/2KGT.github.io/refs/heads/main/repo/js/AdGuard%20Extra.user.js"
        },
        {
            name: "AdGuard Popup Blocker",
            url: "https://raw.githubusercontent.com/2KGT/2KGT.github.io/refs/heads/main/repo/js/AdGuard%20Popup%20Blocker.user.js"
        },
        {
            name: "Dịch sang Tiếng Việt",
            url: "https://raw.githubusercontent.com/2KGT/2KGT.github.io/refs/heads/main/repo/js/auto%20translate%20vi_user.js"
        },
        {
            name: "Image Grid Lister",
            url: "https://raw.githubusercontent.com/2KGT/2KGT.github.io/refs/heads/main/repo/js/image-grid-lister_user.js"
        },
        {
            name: "Mở App khi bấm link",
            url: "https://raw.githubusercontent.com/2KGT/2KGT.github.io/refs/heads/main/repo/js/open%20inapp.user.js"
        }
    ];

    // Hàm tải và thực thi script con
    function loadSubScript(script) {
        GM_xmlhttpRequest({
            method: "GET",
            url: script.url,
            onload: function(response) {
                if (response.status === 200) {
                    try {
                        eval(response.responseText);
                        console.log(`[Father.js] Đã tải và kích hoạt thành công: ${script.name}`);
                    } catch (e) {
                        console.error(`[Father.js] Lỗi khi thực thi script ${script.name}:`, e);
                    }
                } else {
                    console.error(`[Father.js] Không thể tải script ${script.name}. Mã lỗi: ${response.status}`);
                }
            },
            onerror: function(err) {
                console.error(`[Father.js] Lỗi kết nối khi tải script ${script.name}:`, err);
            }
        });
    }

    // Khởi chạy toàn bộ script con
    subScripts.forEach(loadSubScript);
})();
