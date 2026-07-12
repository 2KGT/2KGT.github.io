// ==UserScript==
// @name         2KGT Multi-Script Loader (Father)
// @description  Nút nổi double-tap để bật/tắt các userscript con tải từ GitHub raw
// @version      1.0
// @match        *://*/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function () {
    "use strict";

    // ==== CẤU HÌNH ====
    const BASE_URL = "https://raw.githubusercontent.com/2KGT/2KGT.github.io/main/js/";

    // Danh sách các script con - name hiển thị, file để ghép URL, key để lưu trạng thái bật/tắt
    const SCRIPTS = [
        { key: "abpvn", name: "ABPVN AdsBlock", file: "ABPVN AdsBlock.user.js" },
        { key: "act_yt_translate", name: "YouTube Auto-translate (Phụ đề)", file: "ACT.YouTube.DM.Auto-translate.user.js" },
        { key: "adguard_extra", name: "AdGuard Extra", file: "AdGuard Extra.user.js" },
        { key: "adguard_popup", name: "AdGuard Popup Blocker", file: "AdGuard Popup Blocker.user.js" },
        { key: "auto_translate_vi", name: "Dịch trang sang Tiếng Việt", file: "auto translate vi.user.js" },
        { key: "image_grid", name: "Image Grid Lister", file: "image-grid-lister.user.js" },
        { key: "open_inapp", name: "Tự mở App khi bấm link", file: "open inapp.user.js" },
    ];

    const STORAGE_KEY = "father_active_scripts";

    // ==== QUẢN LÝ TRẠNG THÁI BẬT/TẮT (lưu qua sessionStorage - mỗi tab/phiên riêng) ====
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
        } catch {
            /* ignore quota errors */
        }
    }

    let activeState = loadActiveState();

    // ==== TẢI VÀ CHẠY 1 SCRIPT CON ====
    async function loadAndRun(scriptDef) {
        const url = BASE_URL + encodeURIComponent(scriptDef.file).replace(/%2F/g, "/");
        try {
            const res = await fetch(url, { cache: "no-store" });
            if (!res.ok) {
                throw new Error("HTTP " + res.status);
            }
            const code = await res.text();
            // Chạy code trong scope hàm riêng để tránh xung đột biến toàn cục
            const runner = new Function(code);
            runner();
            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }

    // ==== KÍCH HOẠT / KHÔI PHỤC 1 SCRIPT ====
    async function toggleScript(scriptDef, statusEl) {
        const isActive = !!activeState[scriptDef.key];

        if (!isActive) {
            statusEl.textContent = "Đang tải...";
            const result = await loadAndRun(scriptDef);
            if (result.success) {
                activeState[scriptDef.key] = true;
                saveActiveState(activeState);
                statusEl.textContent = "✅ Đã bật";
            } else {
                statusEl.textContent = "❌ Lỗi: " + result.error;
            }
        } else {
            // Không có cách "gỡ" 1 script đã chạy (không đảo ngược DOM/patch được an toàn),
            // nên "khôi phục" thực tế = tải lại trang để về trạng thái gốc.
            const confirmReload = confirm(
                scriptDef.name + " đang bật.\nBấm OK để TẢI LẠI TRANG (khôi phục bản gốc)."
            );
            if (confirmReload) {
                delete activeState[scriptDef.key];
                saveActiveState(activeState);
                location.reload();
            }
        }
    }

    // ==== GIAO DIỆN: NÚT NỔI + DANH SÁCH ====
    function buildUI() {
        const container = document.createElement("div");
        container.id = "father-loader-ui";
        container.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 16px;
            z-index: 2147483647;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        `;

        // Nút nổi
        const fab = document.createElement("div");
        fab.textContent = "⚙️";
        fab.style.cssText = `
            width: 52px; height: 52px;
            background: rgba(28,28,30,0.85);
            backdrop-filter: blur(10px);
            border-radius: 26px;
            display: flex; align-items: center; justify-content: center;
            font-size: 24px;
            box-shadow: 0 4px 14px rgba(0,0,0,0.35);
            cursor: pointer;
            user-select: none;
        `;

        // Panel danh sách (ẩn mặc định)
        const panel = document.createElement("div");
        panel.style.cssText = `
            display: none;
            position: absolute;
            bottom: 62px;
            right: 0;
            width: 280px;
            max-height: 60vh;
            overflow-y: auto;
            background: rgba(28,28,30,0.96);
            backdrop-filter: blur(16px);
            border-radius: 16px;
            padding: 8px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        `;

        SCRIPTS.forEach((scriptDef) => {
            const row = document.createElement("div");
            row.style.cssText = `
                display: flex; justify-content: space-between; align-items: center;
                padding: 10px 12px;
                border-radius: 10px;
                color: #fff;
                font-size: 13px;
            `;

            const label = document.createElement("span");
            label.textContent = scriptDef.name;
            label.style.cssText = "flex: 1; margin-right: 8px;";

            const status = document.createElement("span");
            status.textContent = activeState[scriptDef.key] ? "✅ Đã bật" : "Bấm để bật";
            status.style.cssText = "font-size: 11px; color: #8e8e93; white-space: nowrap;";

            row.addEventListener("click", () => toggleScript(scriptDef, status));
            row.addEventListener("mousedown", () => (row.style.background = "rgba(255,255,255,0.08)"));
            row.addEventListener("mouseup", () => (row.style.background = "transparent"));

            row.appendChild(label);
            row.appendChild(status);
            panel.appendChild(row);
        });

        // ==== Double-tap để mở/đóng panel ====
        let lastTap = 0;
        fab.addEventListener("click", () => {
            const now = Date.now();
            if (now - lastTap < 400) {
                panel.style.display = panel.style.display === "none" ? "block" : "none";
            }
            lastTap = now;
        });

        container.appendChild(panel);
        container.appendChild(fab);
        document.body.appendChild(container);
    }

    if (document.body) {
        buildUI();
    } else {
        document.addEventListener("DOMContentLoaded", buildUI);
    }
})();
