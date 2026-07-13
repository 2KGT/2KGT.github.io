// ==UserScript==
// @name         Media & File Grid Lister
// @namespace    https://kyic.local/scripts
// @version      3.3
// @description  Mặc định luôn tắt. Chỉ mở hoặc đóng khi nhận lệnh từ nút Dock của Father Loader.
// @author       Kyic
// @match        *://*/*
// @grant        GM_addStyle
// @grant        GM_download
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  const PANEL_ID = 'igl-panel';
  let activeTab = 'img'; // 'img' | 'video' | 'file' | 'filter'
  let filterOpen = false;

  const NON_IMG_EXT_RE = /\.(html?|php|aspx?|jsp|json|xml|js|css|woff2?|ttf|eot)(\?.*)?(#.*)?$/i;
  const VIDEO_EXT_RE = /\.(mp4|webm|mov|m3u8|mkv|avi|m4v|ogv)(\?.*)?(#.*)?$/i;
  const FILE_EXT_RE = /\.(pdf|zip|rar|7z|tar|gz|doc|docx|xls|xlsx|ppt|pptx|txt|csv|apk|ipa|deb|dylib|exe|dmg|json|xml)(\?.*)?(#.*)?$/i;

  // ---------- Styles ----------
  const style = `
    #${PANEL_ID} {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      width: 100vw;
      height: 100vh;
      height: 100dvh;
      z-index: 2147483646;
      background: #000;
      display: none;
      flex-direction: column;
      font: 13px/1.4 -apple-system, sans-serif;
      color: #eee;
      isolation: isolate;
      contain: paint;
      overscroll-behavior: contain;
      touch-action: pan-y;
    }
    #${PANEL_ID}.open { display: flex; }

    .igl-header {
      flex: 0 0 auto;
      padding: 10px 12px;
      padding-top: max(10px, env(safe-area-inset-top));
      background: rgba(20,20,22,.86);
      -webkit-backdrop-filter: saturate(180%) blur(20px);
      backdrop-filter: saturate(180%) blur(20px);
      border-bottom: 1px solid rgba(255,255,255,.08);
    }
    .igl-header-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
    }
    .igl-close {
      flex: 0 0 auto;
      background: rgba(255,69,58,.9);
      border: none;
      color: #fff;
      border-radius: 999px;
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-weight: 700;
      font-size: 16px;
      padding: 0;
    }
    .igl-close:active { background: rgba(255,69,58,1); }

    .igl-navbar {
      flex: 1 1 auto;
      min-width: 0;
      display: flex;
      align-items: center;
      gap: 4px;
      overflow-x: auto;
      margin: 0;
      padding: 4px;
      background: rgba(118,118,128,.18);
      -webkit-backdrop-filter: blur(14px);
      backdrop-filter: blur(14px);
      border: 1px solid rgba(255,255,255,.06);
      border-radius: 20px;
      scrollbar-width: none;
    }
    .igl-navbar::-webkit-scrollbar { display: none; }
    .igl-tab {
      flex: 0 0 auto;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 5px;
      min-width: 88px;
      background: transparent;
      border: none;
      color: #c7c7cc;
      border-radius: 16px;
      padding: 8px 12px;
      font-size: 13px;
      font-weight: 590;
      cursor: pointer;
      white-space: nowrap;
      letter-spacing: -.1px;
      transition: background .15s ease, color .15s ease;
    }
    .igl-tab.active {
      background: #fff;
      color: #000;
      box-shadow: 0 1px 3px rgba(0,0,0,.25);
    }
    .igl-tab.igl-tab-filter.active {
      background: #0a84ff;
      color: #fff;
    }

    .igl-filter-panel {
      display: none;
      align-items: center;
      gap: 14px;
      flex-wrap: wrap;
      padding: 0 2px 14px;
      border-top: 1px solid rgba(255,255,255,.08);
      margin-top: -4px;
    }
    .igl-filter-panel.open { display: flex; }
    .igl-filter-panel label {
      display: flex;
      align-items: center;
      gap: 6px;
      color: #8e8e93;
      font-size: 13px;
      font-weight: 500;
    }
    .igl-filter-panel input[type="number"] {
      width: 60px;
      background: rgba(118,118,128,.24);
      border: none;
      color: #fff;
      border-radius: 9px;
      padding: 6px 8px;
      font-size: 13px;
    }
    .igl-zoom-group {
      display: flex;
      align-items: center;
      gap: 8px;
      background: rgba(118,118,128,.24);
      border: none;
      border-radius: 10px;
      padding: 3px 6px;
    }
    .igl-zoom-btn {
      padding: 4px 10px;
      font-size: 13px;
      background: rgba(255,255,255,.08) !important;
    }
    #igl-zoom-val {
      color: #eee;
      font-size: 12px;
      min-width: 44px;
      text-align: center;
      font-weight: 600;
    }
    .igl-btn {
      background: rgba(118,118,128,.24);
      border: none;
      color: #f2f2f2;
      border-radius: 16px;
      padding: 8px 12px;
      cursor: pointer;
      white-space: nowrap;
      font-size: 13px;
      font-weight: 590;
    }
    .igl-btn:active { background: rgba(118,118,128,.4); }

    .igl-count {
      flex: 0 0 auto;
      color: #8e8e93;
      font-size: 12px;
      font-weight: 500;
      padding: 0 14px 8px;
    }

    .igl-grid {
      flex: 1 1 auto;
      min-height: 0;
      overflow-y: auto;
      -webkit-overflow-scrolling: touch;
      overscroll-behavior: contain;
      display: grid;
      grid-template-columns: repeat(var(--igl-cols, 3), 1fr);
      grid-auto-rows: min-content;
      gap: 2px;
      padding: 0;
      background: #000;
      align-content: start;
      width: 100%;
      box-sizing: border-box;
    }
    @media (min-width: 700px) {
      .igl-grid { --igl-cols: 6; }
    }
    .igl-cell {
      position: relative;
      aspect-ratio: 1 / 1;
      width: 100%;
      overflow: hidden;
      background: #151515;
      cursor: pointer;
    }
    .igl-cell img {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
      opacity: 0;
      transition: opacity .2s ease;
    }
    .igl-cell img.loaded { opacity: 1; }
    .igl-cell .igl-skel {
      position: absolute;
      inset: 0;
      background: linear-gradient(100deg, #161616 30%, #1f1f1f 50%, #161616 70%);
      background-size: 200% 100%;
      animation: igl-shimmer 1.3s infinite;
    }
    .igl-cell img.loaded + .igl-skel { display: none; }
    @keyframes igl-shimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
    .igl-cell .igl-dim-badge {
      position: absolute;
      bottom: 4px;
      right: 6px;
      color: #fff;
      font-size: 10px;
      font-weight: 600;
      text-shadow: 0 1px 3px rgba(0,0,0,.9), 0 0 2px rgba(0,0,0,.9);
      pointer-events: none;
    }

    .igl-list {
      flex: 1 1 auto;
      min-height: 0;
      overflow-y: auto;
      -webkit-overflow-scrolling: touch;
      padding: 6px 10px;
    }
    .igl-list-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 11px 6px;
      border-bottom: 1px solid #1a1a1a;
    }
    .igl-list-icon {
      flex: 0 0 auto;
      width: 38px;
      height: 38px;
      border-radius: 8px;
      background: #1c1c1c;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
    }
    .igl-list-info { flex: 1; min-width: 0; }
    .igl-list-name { font-size: 13px; color: #eee; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    .igl-lightbox {
      position: fixed;
      inset: 0;
      z-index: 2147483647;
      background: #000;
      display: none;
      flex-direction: column;
      touch-action: none;
    }
    .igl-lightbox.open { display: flex; }
    .igl-lb-top {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 10px 14px;
      padding-top: max(10px, env(safe-area-inset-top));
      position: absolute; top: 0; left: 0; right: 0; z-index: 2;
    }
    .igl-lb-counter { color: #ddd; font-size: 13px; background: rgba(40,40,40,.7); padding: 4px 10px; border-radius: 999px; }
    .igl-lb-track { flex: 1; display: flex; height: 100%; }
    .igl-lb-slide { flex: 0 0 100%; display: flex; align-items: center; justify-content: center; height: 100%; }
    .igl-lb-slide img { max-width: 96vw; max-height: 82vh; object-fit: contain; }
    .igl-lb-bottom {
      position: absolute; bottom: 0; left: 0; right: 0;
      padding: 12px 16px; padding-bottom: max(14px, env(safe-area-inset-bottom));
      display: flex; flex-direction: column; gap: 8px; z-index: 2;
    }
    .igl-lb-actions { display: flex; gap: 10px; justify-content: center; }
    .igl-lb-actions button, .igl-lb-actions a {
      background: rgba(50,50,50,.75); border: 1px solid rgba(255,255,255,.12);
      color: #fff; border-radius: 999px; padding: 9px 18px; font-size: 13px; text-decoration: none; cursor: pointer;
    }
    .igl-lb-actions .igl-lb-close-btn { background: rgba(255,69,58,.65); width: 42px; padding: 9px 0; text-align: center; }
  `;

  if (typeof GM_addStyle === 'function') {
    GM_addStyle(style);
  } else {
    const s = document.createElement('style');
    s.textContent = style;
    document.head.appendChild(s);
  }

  // ---------- Helpers ----------
  function resolveUrl(u) { try { return new URL(u, location.href).href; } catch (e) { return null; } }
  function filename(url) { try { return decodeURIComponent(url.split('/').pop().split('?')[0] || 'file'); } catch(e) { return 'file'; } }
  function extOf(url) { const name = filename(url); return name.includes('.') ? name.split('.').pop().toLowerCase() : ''; }

  function looksLikeImage(url) {
    if (!url || url.startsWith('data:')) return false;
    if (NON_IMG_EXT_RE.test(url) || VIDEO_EXT_RE.test(url)) return false;
    return true;
  }

  // ---------- Collect ----------
  function collectImages() {
    const found = new Map();
    document.querySelectorAll('img').forEach(img => {
      const raw = img.currentSrc || img.src;
      const url = resolveUrl(raw);
      if (url && looksLikeImage(url) && !found.has(url)) {
        found.set(url, { url, width: img.naturalWidth || img.width || 0, height: img.naturalHeight || img.height || 0 });
      }
    });
    return Array.from(found.values());
  }

  function collectVideos() {
    const found = new Map();
    document.querySelectorAll('video').forEach(v => {
      const src = resolveUrl(v.currentSrc || v.src);
      if (src && !found.has(src)) found.set(src, { url: src, poster: v.poster ? resolveUrl(v.poster) : null });
    });
    return Array.from(found.values());
  }

  function collectFiles() {
    const found = new Map();
    document.querySelectorAll('a[href]').forEach(a => {
      const url = resolveUrl(a.getAttribute('href'));
      if (url && FILE_EXT_RE.test(url) && !found.has(url)) found.set(url, { url, text: a.textContent.trim() });
    });
    return Array.from(found.values());
  }

  // ---------- Build UI ----------
  const panel = document.createElement('div');
  panel.id = PANEL_ID;
  // 🟢 MẶC ĐỊNH LUÔN ẨN KHI KHỞI TẠO
  panel.classList.remove('open'); 
  
  panel.innerHTML = `
    <div class="igl-header">
      <div class="igl-header-row">
        <div class="igl-navbar" id="igl-tabbar">
          <button class="igl-btn" id="igl-refresh">🔄 Quét lại</button>
          <button class="igl-tab igl-tab-filter" data-tab="filter">⚙️ Filter</button>
          <button class="igl-tab active" data-tab="img">🖼️ Ảnh</button>
          <button class="igl-tab" data-tab="video">🎬 Video</button>
          <button class="igl-tab" data-tab="file">📁 File</button>
        </div>
        <button class="igl-close" id="igl-close">✕</button>
      </div>
      <div class="igl-filter-panel" id="igl-filter-panel">
        <label>Rộng ≥ <input type="number" id="igl-min-w" value="0"></label>
        <label>Cao ≥ <input type="number" id="igl-min-h" value="0"></label>
      </div>
    </div>
    <div class="igl-count" id="igl-count"></div>
    <div class="igl-grid" id="igl-grid"></div>
    <div class="igl-list" id="igl-list" style="display:none"></div>
  `;
  document.documentElement.appendChild(panel);

  const lightbox = document.createElement('div');
  lightbox.className = 'igl-lightbox';
  lightbox.innerHTML = `
    <div class="igl-lb-top"><span class="igl-lb-counter" id="igl-lb-counter">1 / 1</span></div>
    <div class="igl-lb-track" id="igl-lb-track"></div>
    <div class="igl-lb-bottom">
      <div class="igl-lb-actions">
        <button class="igl-lb-close-btn" id="igl-lb-close">✕</button>
      </div>
    </div>
  `;
  document.documentElement.appendChild(lightbox);

  const gridEl = panel.querySelector('#igl-grid');
  const listEl = panel.querySelector('#igl-list');
  const countEl = panel.querySelector('#igl-count');
  const tabbarEl = panel.querySelector('#igl-tabbar');
  const filterPanelEl = panel.querySelector('#igl-filter-panel');
  const minWInput = panel.querySelector('#igl-min-w');
  const minHInput = panel.querySelector('#igl-min-h');

  let allImages = [], allVideos = [], allFiles = [], filteredImages = [];

  function renderImages() {
    const minW = parseInt(minWInput.value, 10) || 0;
    const minH = parseInt(minHInput.value, 10) || 0;
    filteredImages = allImages.filter(img => img.width >= minW && img.height >= minH);
    gridEl.style.display = 'grid'; listEl.style.display = 'none'; gridEl.innerHTML = '';
    countEl.textContent = `${filteredImages.length} ảnh`;
    filteredImages.forEach((img, idx) => {
      const cell = document.createElement('div');
      cell.className = 'igl-cell';
      cell.innerHTML = `<div class="igl-skel"></div><img referrerpolicy="no-referrer" src="${img.url}">`;
      cell.querySelector('img').addEventListener('load', (e) => e.target.classList.add('loaded'));
      cell.addEventListener('click', () => {
        lightbox.classList.add('open');
        lightbox.querySelector('#igl-lb-track').innerHTML = `<div class="igl-lb-slide"><img src="${img.url}"></div>`;
      });
      gridEl.appendChild(cell);
    });
  }

  function renderCurrentTab() {
    if (activeTab === 'img') renderImages();
    // Các tab video/file render tương tự...
  }

  tabbarEl.querySelectorAll('.igl-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.dataset.tab === 'filter') { filterOpen = !filterOpen; filterPanelEl.classList.toggle('open', filterOpen); return; }
      activeTab = btn.dataset.tab;
      renderCurrentTab();
    });
  });

  function refresh() {
    allImages = collectImages(); allVideos = collectVideos(); allFiles = collectFiles();
    renderCurrentTab();
  }

  panel.querySelector('#igl-close').addEventListener('click', () => panel.classList.remove('open'));
  panel.querySelector('#igl-refresh').addEventListener('click', refresh);
  lightbox.querySelector('#igl-lb-close').addEventListener('click', () => lightbox.classList.remove('open'));

  // --------------------------------------------------------
  // LOGIC ĐIỀU KHIỂN CHÍNH (XUẤT RA TOÀN CỤC CHO DOCK CODES)
  // --------------------------------------------------------
  window.toggleImageGridLister = function () {
    if (panel.classList.contains('open')) {
      // Nếu đang mở -> Đóng lại
      panel.classList.remove('open');
    } else {
      // Nếu đang đóng -> Mở ra và tiến hành quét dữ liệu mới
      panel.classList.add('open');
      refresh();
    }
  };

})();
