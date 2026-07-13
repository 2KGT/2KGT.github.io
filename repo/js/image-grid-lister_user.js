// ==UserScript==
// @name         Media & File Grid Lister
// @namespace    https://kyic.local/scripts
// @version      3.2
// @description  Chạy trực tiếp từ Father Loader, tự động bung giao diện ngay khi nạp.
// @author       Kyic
// @match        *://*/*
// @grant        GM_addStyle
// @grant        GM_download
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  const PANEL_ID = 'igl-panel';
  let panelOpen = false;
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

    .igl-navbar .igl-btn {
      flex: 0 0 auto;
      min-width: 88px;
      border-radius: 16px;
      text-align: center;
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
      .igl-grid { --igl-cols-default: 6; }
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
    .igl-cell .igl-duration-badge {
      position: absolute;
      bottom: 4px;
      right: 6px;
      color: #fff;
      font-size: 12px;
      font-weight: 600;
      text-shadow: 0 1px 3px rgba(0,0,0,.9), 0 0 2px rgba(0,0,0,.9);
      pointer-events: none;
    }
    .igl-cell .igl-play-badge {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(0,0,0,.15);
      pointer-events: none;
    }
    .igl-cell .igl-play-badge svg { width: 26px; height: 26px; filter: drop-shadow(0 1px 3px rgba(0,0,0,.6)); }

    .igl-empty {
      color: #777;
      padding: 40px;
      text-align: center;
      grid-column: 1 / -1;
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
    .igl-list-info {
      flex: 1;
      min-width: 0;
    }
    .igl-list-name {
      font-size: 13px;
      color: #eee;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .igl-list-meta {
      font-size: 11px;
      color: #777;
      margin-top: 2px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .igl-list-actions {
      flex: 0 0 auto;
      display: flex;
      gap: 6px;
    }
    .igl-list-actions a, .igl-list-actions button {
      background: #1c1c1c;
      border: 1px solid #333;
      color: #ddd;
      border-radius: 6px;
      padding: 6px 10px;
      font-size: 11px;
      text-decoration: none;
      cursor: pointer;
    }

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
    .igl-lightbox * {
      touch-action: none;
    }

    .igl-lb-top {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 10px 14px;
      padding-top: max(10px, env(safe-area-inset-top));
      background: linear-gradient(to bottom, rgba(0,0,0,.6), transparent);
      position: absolute;
      top: 0; left: 0; right: 0;
      z-index: 2;
    }
    .igl-lb-top button {
      background: rgba(40,40,40,.7);
      border: none;
      color: #fff;
      border-radius: 999px;
      width: 34px;
      height: 34px;
      font-size: 16px;
      cursor: pointer;
      flex: 0 0 auto;
    }
    .igl-lb-counter {
      color: #ddd;
      font-size: 13px;
      background: rgba(40,40,40,.7);
      padding: 4px 10px;
      border-radius: 999px;
    }

    .igl-lb-track {
      flex: 1;
      display: flex;
      height: 100%;
      transition: transform .28s ease;
      will-change: transform;
    }
    .igl-lb-slide {
      flex: 0 0 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
      overflow: hidden;
      touch-action: none;
    }
    .igl-lb-slide img {
      max-width: 96vw;
      max-height: 82vh;
      object-fit: contain;
      transform-origin: center center;
      will-change: transform;
      user-select: none;
      -webkit-user-drag: none;
    }

    .igl-lb-bottom {
      position: absolute;
      bottom: 0; left: 0; right: 0;
      padding: 12px 16px;
      padding-bottom: max(14px, env(safe-area-inset-bottom));
      background: linear-gradient(to top, rgba(0,0,0,.7), transparent);
      display: flex;
      flex-direction: column;
      gap: 8px;
      z-index: 2;
    }
    .igl-lb-meta {
      color: #aaa;
      font-size: 11px;
      text-align: center;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .igl-lb-actions {
      display: flex;
      gap: 10px;
      justify-content: center;
    }
    .igl-lb-actions button, .igl-lb-actions a {
      display: flex;
      align-items: center;
      gap: 6px;
      background: rgba(50,50,50,.75);
      border: 1px solid rgba(255,255,255,.12);
      color: #fff;
      border-radius: 999px;
      padding: 9px 18px;
      font-size: 13px;
      text-decoration: none;
      cursor: pointer;
    }
    .igl-lb-actions .igl-lb-open { background: rgba(30,80,180,.55); }
    .igl-lb-actions .igl-lb-dl { background: rgba(30,140,80,.55); }
    .igl-lb-actions .igl-lb-close-btn {
      background: rgba(255,69,58,.65);
      border-color: rgba(255,255,255,.15);
      width: 42px;
      padding: 9px 0;
      justify-content: center;
      flex: 0 0 auto;
    }
    .igl-lb-actions .igl-lb-close-btn:active { background: rgba(255,69,58,.9); }

    .igl-lb-zoom-dock {
      position: absolute;
      top: max(56px, calc(env(safe-area-inset-top) + 46px));
      right: 14px;
      z-index: 3;
      width: 40px;
      height: 40px;
      border-radius: 999px;
      background: rgba(255,159,10,.85);
      border: 1px solid rgba(255,255,255,.2);
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 2px 8px rgba(0,0,0,.4);
    }
    .igl-lb-zoom-dock svg { width: 18px; height: 18px; }
    .igl-lb-zoom-dock:active { background: rgba(255,159,10,1); }
  `;

  if (typeof GM_addStyle === 'function') {
    GM_addStyle(style);
  } else {
    const s = document.createElement('style');
    s.textContent = style;
    document.head.appendChild(s);
  }

  // ---------- Helpers ----------
  function resolveUrl(u) {
    try { return new URL(u, location.href).href; } catch (e) { return null; }
  }

  function filename(url) {
    try {
      const u = new URL(url);
      const parts = u.pathname.split('/').filter(Boolean);
      return decodeURIComponent(parts[parts.length - 1] || 'file');
    } catch (e) {
      return 'file';
    }
  }

  function extOf(url) {
    const name = filename(url).split('?')[0];
    const m = name.match(/\.([a-z0-9]+)$/i);
    return m ? m[1].toLowerCase() : '';
  }

  function formatDuration(seconds) {
    if (!seconds || !isFinite(seconds)) return '';
    const s = Math.round(seconds);
    const m = Math.floor(s / 60);
    const rem = s % 60;
    return `${m}:${rem.toString().padStart(2, '0')}`;
  }

  // ---------- Collect Functions ----------
  function looksLikeImage(url) {
    if (!url) return false;
    if (NON_IMG_EXT_RE.test(url)) return false;
    if (VIDEO_EXT_RE.test(url)) return false;
    return true;
  }

  function iconForFile(ext) {
    const map = {
      pdf: '📕', zip: '🗜️', rar: '🗜️', '7z': '🗜️', tar: '🗜️', gz: '🗜️',
      doc: '📄', docx: '📄', xls: '📊', xlsx: '📊', ppt: '📽️', pptx: '📽️',
      txt: '📄', csv: '📊', apk: '📦', ipa: '📦', deb: '📦', dylib: '⚙️',
      exe: '⚙️', dmg: '💿', json: '🧾', xml: '🧾'
    };
    return map[ext] || '📁';
  }

  function collectImages() {
    const found = new Map();
    document.querySelectorAll('img').forEach(img => {
      const raw = img.currentSrc || img.src;
      if (!raw || raw.startsWith('data:')) return;
      const url = resolveUrl(raw);
      if (!url || !looksLikeImage(url)) return;
      if (!found.has(url)) {
        found.set(url, { url, width: img.naturalWidth || img.width || 0, height: img.naturalHeight || img.height || 0 });
      }
    });
    document.querySelectorAll('*').forEach(el => {
      const bg = getComputedStyle(el).backgroundImage;
      if (bg && bg !== 'none') {
        for (const m of bg.matchAll(/url\(["']?([^"')]+)["']?\)/g)) {
          const raw = m[1];
          if (!raw || raw.startsWith('data:')) continue;
          const u = resolveUrl(raw);
          if (u && looksLikeImage(u) && !found.has(u)) found.set(u, { url: u, width: 0, height: 0 });
        }
      }
    });
    return Array.from(found.values());
  }

  function collectVideos() {
    const found = new Map();
    document.querySelectorAll('video').forEach(v => {
      const candidates = [v.currentSrc, v.src].filter(Boolean);
      v.querySelectorAll('source[src]').forEach(s => candidates.push(s.src));
      const duration = (isFinite(v.duration) && v.duration > 0) ? v.duration : null;
      candidates.forEach(raw => {
        const url = resolveUrl(raw);
        if (url && !url.startsWith('data:') && !found.has(url)) {
          found.set(url, { url, poster: v.poster ? resolveUrl(v.poster) : null, duration });
        }
      });
    });
    document.querySelectorAll('a[href]').forEach(el => {
      const raw = el.getAttribute('href');
      if (!raw) return;
      const url = resolveUrl(raw);
      if (url && VIDEO_EXT_RE.test(url) && !found.has(url)) {
        found.set(url, { url, poster: null });
      }
    });
    return Array.from(found.values());
  }

  function collectFiles() {
    const found = new Map();
    document.querySelectorAll('a[href]').forEach(a => {
      const raw = a.getAttribute('href');
      if (!raw) return;
      const url = resolveUrl(raw);
      if (!url || url.startsWith('data:')) return;
      if (FILE_EXT_RE.test(url) && !found.has(url)) {
        found.set(url, { url, text: (a.textContent || '').trim().slice(0, 80) });
      }
    });
    return Array.from(found.values());
  }

  // ---------- UI Build ----------
  const panel = document.createElement('div');
  panel.id = PANEL_ID;
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
        <label>Cỡ ảnh
          <span class="igl-zoom-group">
            <button class="igl-btn igl-zoom-btn" id="igl-zoom-out">➖</button>
            <span id="igl-zoom-val">3 cột</span>
            <button class="igl-btn igl-zoom-btn" id="igl-zoom-in">➕</button>
          </span>
        </label>
        <button class="igl-btn" id="igl-download-all">⬇️ Tải tất cả</button>
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
    <button class="igl-lb-zoom-dock" id="igl-lb-reset-zoom" style="display:none">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M9 3 L9 9 L3 9 M15 21 L15 15 L21 15"/></svg>
    </button>
    <div class="igl-lb-track" id="igl-lb-track"></div>
    <div class="igl-lb-bottom">
      <div class="igl-lb-meta" id="igl-lb-meta"></div>
      <div class="igl-lb-actions">
        <a class="igl-lb-open" id="igl-lb-open" target="_blank">↗ Mở gốc</a>
        <button class="igl-lb-dl" id="igl-lb-dl">⬇ Tải về</button>
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
  const zoomOutBtn = panel.querySelector('#igl-zoom-out');
  const zoomInBtn = panel.querySelector('#igl-zoom-in');
  const zoomValEl = panel.querySelector('#igl-zoom-val');

  const lbTrack = lightbox.querySelector('#igl-lb-track');
  const lbCounter = lightbox.querySelector('#igl-lb-counter');
  const lbMeta = lightbox.querySelector('#igl-lb-meta');
  const lbOpen = lightbox.querySelector('#igl-lb-open');
  const lbDl = lightbox.querySelector('#igl-lb-dl');
  const lbClose = lightbox.querySelector('#igl-lb-close');

  let allImages = [], allVideos = [], allFiles = [], filteredImages = [], lbIndex = 0;

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
      cell.addEventListener('click', () => openLightbox(idx));
      gridEl.appendChild(cell);
    });
  }

  function renderVideos() {
    gridEl.style.display = 'grid'; listEl.style.display = 'none'; gridEl.innerHTML = '';
    allVideos.forEach(v => {
      const cell = document.createElement('div');
      cell.className = 'igl-cell';
      cell.innerHTML = `<div class="igl-skel"></div>${v.poster ? `<img src="${v.poster}">` : ''}<div class="igl-play-badge"><svg viewBox="0 0 24 24" fill="white"><path d="M8 5v14l11-7z"/></svg></div>`;
      gridEl.appendChild(cell);
    });
  }

  function renderFiles() {
    gridEl.style.display = 'none'; listEl.style.display = 'block'; listEl.innerHTML = '';
    allFiles.forEach(f => {
      const row = document.createElement('div');
      row.className = 'igl-list-item';
      row.innerHTML = `<div class="igl-list-icon">${iconForFile(extOf(f.url))}</div><div class="igl-list-info"><div class="igl-list-name">${f.text || filename(f.url)}</div></div>`;
      listEl.appendChild(row);
    });
  }

  function renderCurrentTab() {
    if (activeTab === 'img') renderImages();
    else if (activeTab === 'video') renderVideos();
    else if (activeTab === 'file') renderFiles();
  }

  tabbarEl.querySelectorAll('.igl-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.dataset.tab === 'filter') { filterOpen = !filterOpen; filterPanelEl.classList.toggle('open', filterOpen); return; }
      activeTab = btn.dataset.tab;
      renderCurrentTab();
    });
  });

  function openLightbox(idx) {
    lbIndex = idx; lightbox.classList.add('open');
    lbTrack.innerHTML = `<div class="igl-lb-slide"><img src="${filteredImages[idx].url}"></div>`;
    lbCounter.textContent = `${idx + 1} / ${filteredImages.length}`;
  }
  lbClose.addEventListener('click', () => lightbox.classList.remove('open'));

  function refresh() {
    allImages = collectImages(); allVideos = collectVideos(); allFiles = collectFiles();
    renderCurrentTab();
  }

  panel.querySelector('#igl-close').addEventListener('click', () => panel.classList.remove('open'));
  panel.querySelector('#igl-refresh').addEventListener('click', refresh);

  // ---------- ĐỊNH NGHĨA HÀM TOÀN CỤC ----------
  window.initImageGridLister = function() {
    panel.classList.add('open');
    refresh();
  };

  // 🔥 LỆNH TỰ ĐỘNG KÍCH HOẠT KHI PHẦN MỀM TẢI XONG CODE
  window.initImageGridLister();

})();
