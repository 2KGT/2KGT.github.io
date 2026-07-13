// ==UserScript==
// @name         Media & File Grid Lister
// @namespace    https://kyic.local/scripts
// @version      3.4
// @description  Mặc định luôn tắt. Chỉ khởi tạo và hiển thị khi nhận tín hiệu từ nút Dock.
// @author       Kyic
// @match        *://*/*
// @grant        none
// @run-at       document-end
// ==/UserScript==

(function () {
  'use strict';

  const PANEL_ID = 'igl-panel';
  let isInitialized = false; // Trạng thái kiểm tra xem menu đã từng được tạo chưa
  let activeTab = 'img';
  let filterOpen = false;

  const NON_IMG_EXT_RE = /\.(html?|php|aspx?|jsp|json|xml|js|css|woff2?|ttf|eot)(\?.*)?(#.*)?$/i;
  const VIDEO_EXT_RE = /\.(mp4|webm|mov|m3u8|mkv|avi|m4v|ogv)(\?.*)?(#.*)?$/i;
  const FILE_EXT_RE = /\.(pdf|zip|rar|7z|tar|gz|doc|docx|xls|xlsx|ppt|pptx|txt|csv|apk|ipa|deb|dylib|exe|dmg|json|xml)(\?.*)?(#.*)?$/i;

  // ---------- 1. Hàm nhúng CSS (Chỉ chạy khi kích hoạt) ----------
  function injectStyles() {
    const style = document.createElement('style');
    style.textContent = `
      #${PANEL_ID} {
        position: fixed; top: 0; left: 0; right: 0; bottom: 0;
        width: 100vw; height: 100vh; height: 100dvh;
        z-index: 2147483646; background: #000;
        display: none; flex-direction: column;
        font: 13px/1.4 -apple-system, sans-serif; color: #eee;
      }
      #${PANEL_ID}.open { display: flex; }
      .igl-header { flex: 0 0 auto; padding: 10px 12px; background: rgba(20,20,22,.86); border-bottom: 1px solid rgba(255,255,255,.08); }
      .igl-header-row { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
      .igl-close { background: rgba(255,69,58,.9); border: none; color: #fff; border-radius: 999px; width: 36px; height: 36px; cursor: pointer; font-weight: 700; }
      .igl-navbar { flex: 1 1 auto; display: flex; gap: 4px; overflow-x: auto; padding: 4px; background: rgba(118,118,128,.18); border-radius: 20px; }
      .igl-tab { background: transparent; border: none; color: #c7c7cc; border-radius: 16px; padding: 8px 12px; font-weight: 590; cursor: pointer; }
      .igl-tab.active { background: #fff; color: #000; }
      .igl-filter-panel { display: none; align-items: center; gap: 14px; padding: 0 2px 14px; border-top: 1px solid rgba(255,255,255,.08); margin-top: -4px; }
      .igl-filter-panel.open { display: flex; }
      .igl-filter-panel input { width: 60px; background: rgba(118,118,128,.24); border: none; color: #fff; border-radius: 9px; padding: 6px 8px; }
      .igl-count { color: #8e8e93; font-size: 12px; padding: 0 14px 8px; }
      .igl-grid { flex: 1 1 auto; overflow-y: auto; display: grid; grid-template-columns: repeat(3, 1fr); gap: 2px; }
      @media (min-width: 700px) { .igl-grid { grid-template-columns: repeat(6, 1fr); } }
      .igl-cell { position: relative; aspect-ratio: 1 / 1; background: #151515; cursor: pointer; }
      .igl-cell img { width: 100%; height: 100%; object-fit: cover; opacity: 0; transition: opacity .2s; }
      .igl-cell img.loaded { opacity: 1; }
      .igl-list { flex: 1 1 auto; overflow-y: auto; padding: 6px 10px; }
      .igl-list-item { display: flex; align-items: center; gap: 12px; padding: 11px 6px; border-bottom: 1px solid #1a1a1a; }
      .igl-list-info { flex: 1; }
      .igl-list-name { font-size: 13px; color: #eee; }
    `;
    document.head.appendChild(style);
  }

  // ---------- 2. Các hàm bổ trợ quét nội dung ----------
  function resolveUrl(u) { try { return new URL(u, location.href).href; } catch (e) { return null; } }
  
  function collectImages() {
    const found = new Map();
    document.querySelectorAll('img').forEach(img => {
      const raw = img.currentSrc || img.src;
      const url = resolveUrl(raw);
      if (url && !url.startsWith('data:') && !NON_IMG_EXT_RE.test(url) && !VIDEO_EXT_RE.test(url)) {
        found.set(url, { url, width: img.naturalWidth || img.width || 0, height: img.naturalHeight || img.height || 0 });
      }
    });
    return Array.from(found.values());
  }

  // ---------- 3. Hàm nhúng HTML Giao diện (Chỉ chạy khi kích hoạt) ----------
  let panel, gridEl, listEl, countEl, tabbarEl, filterPanelEl, minWInput, minHInput;
  let allImages = [], filteredImages = [];

  function injectContainer() {
    panel = document.createElement('div');
    panel.id = PANEL_ID;
    panel.innerHTML = `
      <div class="igl-header">
        <div class="igl-header-row">
          <div class="igl-navbar" id="igl-tabbar">
            <button class="igl-btn" id="igl-refresh" style="background:transparent;border:none;color:#fff;cursor:pointer;">🔄 Quét lại</button>
            <button class="igl-tab" data-tab="filter">⚙️ Lọc</button>
            <button class="igl-tab active" data-tab="img">🖼️ Ảnh</button>
          </div>
          <button class="igl-close" id="igl-close">✕</button>
        </div>
        <div class="igl-filter-panel" id="igl-filter-panel">
          <label style="color:#8e8e93">Rộng ≥ <input type="number" id="igl-min-w" value="0"></label>
          <label style="color:#8e8e93">Cao ≥ <input type="number" id="igl-min-h" value="0"></label>
        </div>
      </div>
      <div class="igl-count" id="igl-count"></div>
      <div class="igl-grid" id="igl-grid"></div>
      <div class="igl-list" id="igl-list" style="display:none"></div>
    `;
    document.body.appendChild(panel);

    // Gán Element vào biến toàn cục của IIFE
    gridEl = panel.querySelector('#igl-grid');
    listEl = panel.querySelector('#igl-list');
    countEl = panel.querySelector('#igl-count');
    tabbarEl = panel.querySelector('#igl-tabbar');
    filterPanelEl = panel.querySelector('#igl-filter-panel');
    minWInput = panel.querySelector('#igl-min-w');
    minHInput = panel.querySelector('#igl-min-h');

    // Đăng ký sự kiện nút bấm bên trong menu
    panel.querySelector('#igl-close').addEventListener('click', () => panel.classList.remove('open'));
    panel.querySelector('#igl-refresh').addEventListener('click', refreshData);
    
    tabbarEl.querySelectorAll('.igl-tab').forEach(btn => {
      btn.addEventListener('click', () => {
        if (btn.dataset.tab === 'filter') {
          filterOpen = !filterOpen;
          filterPanelEl.classList.toggle('open', filterOpen);
          btn.classList.toggle('active', filterOpen);
          return;
        }
        tabbarEl.querySelectorAll('.igl-tab:not([data-tab="filter"])').forEach(t => t.classList.remove('active'));
        btn.classList.add('active');
        activeTab = btn.dataset.tab;
        renderData();
      });
    });

    // Bắt sự kiện thay đổi bộ lọc
    minWInput.addEventListener('input', renderData);
    minHInput.addEventListener('input', renderData);
  }

  function renderData() {
    const minW = parseInt(minWInput.value, 10) || 0;
    const minH = parseInt(minHInput.value, 10) || 0;
    filteredImages = allImages.filter(img => img.width >= minW && img.height >= minH);
    
    gridEl.innerHTML = '';
    countEl.textContent = `Đã tìm thấy: ${filteredImages.length} ảnh`;
    
    filteredImages.forEach(img => {
      const cell = document.createElement('div');
      cell.className = 'igl-cell';
      cell.innerHTML = `<img referrerpolicy="no-referrer" src="${img.url}">`;
      cell.querySelector('img').addEventListener('load', (e) => e.target.classList.add('loaded'));
      gridEl.appendChild(cell);
    });
  }

  function refreshData() {
    allImages = collectImages();
    renderData();
  }

  // ---------- 4. HÀM KÍCH HOẠT CHÍNH (Chỉ chạy khi gọi) ----------
  function openOrToggleMenu() {
    // Nếu chưa từng khởi tạo lần nào, tiến hành dựng cấu trúc HTML/CSS vào trang[span_4](start_span)[span_4](end_span)
    if (!isInitialized) {
      injectStyles();
      injectContainer();
      isInitialized = true;
    }
    
    // Thực hiện bật/tắt (Toggle) lớp hiển thị giao diện
    if (panel.classList.contains('open')) {
      panel.classList.remove('open');
    } else {
      panel.classList.add('open');
      refreshData(); // Quét dữ liệu mới khi mở
    }
  }

  // ---------- 5. LẮNG NGHE SỰ KIỆN TỪ NÚT DOCK CỦA FATHER ----------
  // Mặc định đoạn code này chạy ngầm không sinh ra bất kỳ giao diện nào cho đến khi nhận được sự kiện này[span_5](start_span)[span_5](end_span)
  window.addEventListener('father-toggle-image-menu', function () {
    openOrToggleMenu();
  });

})();
