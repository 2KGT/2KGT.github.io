// ==UserScript==
// @name         TEST - Fetch Local File Check
// @description  Script kiểm tra xem fetch() có đọc được file cùng thư mục iCloud không
// @version      1.0
// @match        *://*/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function () {
    "use strict";

    // Các đường dẫn thử nghiệm - chạy thử từng cái để xem cái nào (nếu có) hoạt động
    const testPaths = [
        "ACT_YouTube_DM_Auto-translate_user.js",              // đường dẫn tương đối cùng thư mục
        "./ACT_YouTube_DM_Auto-translate_user.js",
        "../Script JS/ACT_YouTube_DM_Auto-translate_user.js",
        "file:///var/mobile/Library/Mobile Documents/com~apple~CloudDocs/Documents/Script JS/ACT_YouTube_DM_Auto-translate_user.js",
    ];

    async function testFetch(path) {
        try {
            const res = await fetch(path);
            const text = await res.text();
            return {
                path,
                success: true,
                status: res.status,
                contentType: res.headers.get("content-type"),
                preview: text.substring(0, 100),
            };
        } catch (e) {
            return {
                path,
                success: false,
                error: e.message,
            };
        }
    }

    async function runAllTests() {
        console.log("=== BẮT ĐẦU TEST FETCH LOCAL FILE ===");
        for (const path of testPaths) {
            const result = await testFetch(path);
            console.log(JSON.stringify(result, null, 2));
        }
        console.log("=== KẾT THÚC TEST ===");

        // Hiện kết quả trực quan trên màn hình luôn, không cần mở console
        const box = document.createElement("div");
        box.style.cssText = `
            position: fixed; top: 50px; left: 10px; right: 10px;
            background: #1c1c1e; color: #0f0; font-family: monospace;
            font-size: 11px; padding: 12px; border-radius: 8px;
            z-index: 999999; max-height: 70vh; overflow-y: auto;
            white-space: pre-wrap; word-break: break-all;
        `;
        let output = "KẾT QUẢ TEST FETCH:\n\n";
        for (const path of testPaths) {
            const result = await testFetch(path);
            output += `Path: ${path}\n`;
            output += result.success
                ? `✅ THÀNH CÔNG - status ${result.status}\n`
                : `❌ THẤT BẠI - ${result.error}\n`;
            output += "\n";
        }
        box.textContent = output;
        document.body.appendChild(box);
    }

    if (document.body) {
        runAllTests();
    } else {
        document.addEventListener("DOMContentLoaded", runAllTests);
    }
})();
