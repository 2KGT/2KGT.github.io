// ==UserScript==
// @name         Auto Translate to Vietnamese (Google Translate)
// @namespace    https://2kgt.github.io/
// @version      1.0
// @description  Tự động nhúng Google Translate widget và dịch trang sang tiếng Việt
// @author       Pass Just
// @match        *://*/*
// @grant        none
// @run-at       document-end
// ==/UserScript==

(function () {
  'use strict';

  const TARGET_LANG = 'vi';
  const COOKIE_NAME = 'googtrans';

  // Bỏ qua nếu trang đã là Google Translate hoặc đã có widget
  if (location.hostname.includes('translate.google.com')) return;
  if (document.getElementById('google_translate_element')) return;

  // Không dịch lại nếu trang có vẻ đã ở tiếng Việt (heuristic đơn giản qua thẻ <html lang>)
  const htmlLang = (document.documentElement.lang || '').toLowerCase();
  if (htmlLang.startsWith('vi')) return;

  function setGoogTransCookie() {
    const value = `/auto/${TARGET_LANG}`;
    const domain = location.hostname;
    // Set cho domain hiện tại và cả domain cha (phòng subdomain)
    document.cookie = `${COOKIE_NAME}=${value}; path=/;`;
    document.cookie = `${COOKIE_NAME}=${value}; path=/; domain=.${domain};`;
  }

  function injectContainer() {
    if (document.getElementById('google_translate_element')) return;
    const div = document.createElement('div');
    div.id = 'google_translate_element';
    // Ẩn widget khỏi giao diện, chỉ dùng để kích hoạt engine dịch
    div.style.position = 'fixed';
    div.style.top = '-9999px';
    div.style.left = '-9999px';
    document.body.appendChild(div);
  }

  function injectInitFunction() {
    window.googleTranslateElementInit = function () {
      new google.translate.TranslateElement(
        {
          pageLanguage: 'auto',
          includedLanguages: TARGET_LANG,
          autoDisplay: true,
        },
        'google_translate_element'
      );
    };
  }

  function injectScript() {
    if (document.getElementById('google-translate-sdk')) return;
    const script = document.createElement('script');
    script.id = 'google-translate-sdk';
    script.src = 'https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';
    script.async = true;
    document.body.appendChild(script);
  }

  function hideGoogleBanner() {
    // Ẩn thanh banner + tránh trang bị đẩy xuống (do Google Translate chèn iframe/top margin)
    const style = document.createElement('style');
    style.textContent = `
      .goog-te-banner-frame, .goog-te-gadget-icon { display: none !important; }
      body { top: 0 !important; position: static !important; }
      .skiptranslate iframe { display: none !important; }
    `;
    document.head.appendChild(style);
  }

  function init() {
    setGoogTransCookie();
    hideGoogleBanner();
    injectInitFunction();
    injectContainer();
    injectScript();
  }

  if (document.body) {
    init();
  } else {
    document.addEventListener('DOMContentLoaded', init);
  }
})();
