# .github/scripts/views.py
#!/usr/bin/env python3
"""AppStore-style HTML generator cho Apps/Tweaks/Dylibs."""
import os
import json
import time
import datetime
import inspect
import config


# ────────────────────────────────────────────────────────
# HTML TEMPLATE
# ────────────────────────────────────────────────────────
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi" data-lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta name="theme-color" content="#0a1428">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>{title} - {repo_name}</title>
    <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }}

        /* ─────────────────────────── PHẢN HỒI NHẤN TOÀN HỆ THỐNG ───────────────────────────
           Áp dụng nhất quán cho mọi nút/phần tử có thể nhấn: thu nhỏ nhẹ + tối hơn một chút
           khi nhấn giữ, nhả ra phục hồi mượt. Các class có hiệu ứng đặc thù riêng (transform
           khác, scale khác) khai báo sau trong file sẽ tự override nhờ thứ tự CSS. */
        .icon-btn, .tab-btn, .search-clear, .item, .item-action, .page-btn,
        .screenshot, .lightbox-close, .lightbox-nav, .detail-section-header,
        .version-item, .action-btn, .action-btn-icon, .modal-close,
        .settings-close, .settings-item, .pill-btn, .action-btn-version,
        .version-picker-item, .confirm-btn {{
            transition: transform 0.12s cubic-bezier(0.4, 0, 0.2, 1),
                        filter 0.12s cubic-bezier(0.4, 0, 0.2, 1),
                        background 0.2s ease, opacity 0.2s ease;
        }}

        .icon-btn:active, .tab-btn:active, .search-clear:active, .item:active,
        .item-action:active, .page-btn:active, .screenshot:active,
        .lightbox-close:active, .lightbox-nav:active, .detail-section-header:active,
        .version-item:active, .action-btn:active, .action-btn-icon:active,
        .modal-close:active, .settings-close:active, .settings-item:active,
        .pill-btn:active, .action-btn-version:active, .version-picker-item:active,
        .confirm-btn:active {{
            transform: scale(0.95);
            filter: brightness(0.92);
        }}

        :root {{
            --bg: #0a1428;
            --card: #0f1e3d;
            --text: #ffffff;
            --text-secondary: #8e9ab5;
            --tint: #{tint};
            --border: rgba(255, 255, 255, 0.1);

            /* ── iOS 27 Liquid Glass — bộ biến dùng chung toàn hệ thống ──
               nav-shell, settings-panel, version-picker-panel,
               version-popover, modal-content, confirm-dialog */
            --glass-bg:           rgba(8, 16, 40, 0.60);
            --glass-bg-light:     rgba(255, 255, 255, 0.62);
            --glass-blur:         blur(40px) saturate(220%) brightness(1.08);
            --glass-border:       1px solid rgba(255, 255, 255, 0.22);
            --glass-border-light: 1px solid rgba(0, 0, 0, 0.07);
            --glass-radius:       26px;
            --glass-shadow:       0 8px 32px rgba(0, 0, 0, 0.45),
                                  0 1px 0 rgba(255, 255, 255, 0.14) inset,
                                  0 -1px 0 rgba(0, 0, 0, 0.25) inset;
            --glass-shadow-light: 0 4px 20px rgba(0, 0, 0, 0.10),
                                  0 1px 0 rgba(255, 255, 255, 0.9) inset;
        }}

        /* ─────────────────────────── DARK MODE (DEFAULT) ─────────────────────────── */
        /* Giải pháp phông nền đúng: html và body đều dùng cùng màu nền solid.
           Gradient chỉ áp lên một lớp wrapper bên trong — không bao giờ để
           gradient chạm thẳng vào html/body vì sẽ bị cắt ở đầu/chân trên
           các thiết bị có notch, Dynamic Island, hay màn hình tròn góc.
           html giữ màu solid làm "backstop" cho mọi vùng ngoài body. */
        html {{
            color-scheme: dark;
            background: #0a1428;
            height: 100%;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro", "Segoe UI", sans-serif;
            background: #0a1428;
            color: var(--text);
            height: 100%;
            min-height: 100dvh;
            overflow-x: hidden;
            padding-top: env(safe-area-inset-top, 0);
            padding-bottom: env(safe-area-inset-bottom, 0);
            padding-left: env(safe-area-inset-left, 0);
            padding-right: env(safe-area-inset-right, 0);
            display: flex;
            flex-direction: column;
        }}

        /* ─────────────────────────── LIGHT MODE ─────────────────────────── */
        html[data-theme="light"] {{
            --bg: #f0f4ff;
            --card: #ffffff;
            --text: #1d1d1f;
            --text-secondary: #6b7a99;
            --border: rgba(0, 0, 0, 0.08);
            color-scheme: light;
            background: #f0f4ff;
        }}

        html[data-theme="light"] body {{
            background: #f0f4ff;
        }}

        /* ─────────────────────────── NAV SHELL (HEADER) ─────────────────────────── */
        /* Nav và banner dùng cùng --side-pad để đảm bảo khớp pixel hoàn toàn */
        :root {{ --side-pad: 16px; }}

        .nav-shell {{
            position: fixed;
            top: calc(env(safe-area-inset-top, 0px) + 10px);
            left: var(--side-pad);
            right: var(--side-pad);
            z-index: 50;
            margin: 0 auto;
            max-width: calc(500px - var(--side-pad) * 2);
            padding: 0;
            backdrop-filter: var(--glass-blur);
            -webkit-backdrop-filter: var(--glass-blur);
            background: var(--glass-bg);
            border: var(--glass-border);
            border-radius: var(--glass-radius);
            box-shadow: var(--glass-shadow);
            will-change: transform, opacity;
            transform: translateZ(0);
        }}

        /* ── HIỆU ỨNG THÔNG BÁO iPHONE ──
           Hiện: trượt xuống + scale từ nhỏ ra, easing spring tự nhiên
           Ẩn:  thu lên + scale nhỏ lại, nhanh gọn như notification dismiss */
        .nav-shell.nav-showing {{
            transition: transform 0.52s cubic-bezier(0.34, 1.56, 0.64, 1),
                        opacity 0.4s cubic-bezier(0.34, 1.2, 0.64, 1),
                        scale 0.52s cubic-bezier(0.34, 1.56, 0.64, 1);
            transform: translateY(0) translateZ(0);
            scale: 1;
            opacity: 1;
            clip-path: none;
            pointer-events: auto;
        }}

        .nav-shell.nav-hidden {{
            transition: transform 0.32s cubic-bezier(0.4, 0, 1, 0.8),
                        opacity 0.25s cubic-bezier(0.4, 0, 1, 1),
                        scale 0.32s cubic-bezier(0.4, 0, 1, 0.8);
            transform: translateY(-110%) translateZ(0);
            scale: 0.88;
            opacity: 0;
            clip-path: none;
            pointer-events: none;
        }}

        html[data-theme="light"] .nav-shell {{
            background: var(--glass-bg-light);
            border: var(--glass-border-light);
            box-shadow: var(--glass-shadow-light);
        }}

        .nav-inner {{
            margin: 0 auto;
            padding: 0 8px 6px;
        }}

        .header-row {{
            display: grid;
            grid-template-columns: 36px 1fr 36px;
            align-items: center;
            height: 50px;
            padding: 0 6px;
        }}

        .nav-repo-name {{
            text-align: center;
            font-weight: 800;
            font-size: 1.18em;
            line-height: 1.2;
            letter-spacing: 0.2px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            background: linear-gradient(90deg, var(--tint), #b39cff 55%, #ff9cd9);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            color: var(--tint);
            text-shadow: 0 1px 18px rgba(132, 142, 249, 0.35);
        }}

        .header-actions {{
            display: flex;
            gap: 6px;
        }}

        .icon-btn {{
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid var(--border);
            color: var(--text);
            width: 36px;
            height: 36px;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.05em;
            transition: all 0.2s;
            flex-shrink: 0;
        }}

        html[data-theme="light"] .icon-btn {{
            background: rgba(0, 0, 0, 0.05);
        }}

        .icon-btn:active {{
            background: rgba(255, 255, 255, 0.2);
            transform: scale(0.93);
        }}

        html[data-theme="light"] .icon-btn:active {{
            background: rgba(0, 0, 0, 0.12);
        }}

        /* ─────────────────────────── TABS ─────────────────────────── */
        .tabs-header {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 8px;
            padding: 0 4px 10px;
        }}

        .nav-inner .search-box {{
            margin: 0 4px 12px;
        }}

        .tab-btn {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            padding: 10px 6px;
            border-radius: 14px;
            cursor: pointer;
            font-weight: 600;
            font-size: 0.86em;
            transition: background 0.3s cubic-bezier(0.4, 0, 0.2, 1),
                        color 0.3s cubic-bezier(0.4, 0, 0.2, 1),
                        border-color 0.3s cubic-bezier(0.4, 0, 0.2, 1),
                        transform 0.18s cubic-bezier(0.4, 0, 0.2, 1),
                        box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            text-align: center;
            will-change: transform;
        }}

        html[data-theme="light"] .tab-btn {{
            background: rgba(0, 0, 0, 0.03);
        }}

        .tab-btn.active {{
            background: rgba(132, 142, 249, 0.2);
            color: var(--text);
            border-color: var(--tint);
            box-shadow: 0 4px 14px rgba(132, 142, 249, 0.25);
            transform: scale(1.02);
        }}

        html[data-theme="light"] .tab-btn.active {{
            background: rgba(132, 142, 249, 0.15);
        }}

        .tab-btn:active {{
            transform: scale(0.95);
            transition: transform 0.1s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        /* ─────────────────────────── CONTAINER ─────────────────────────── */
        .container {{
            max-width: 500px;
            width: 100%;
            margin: 0 auto;
            padding: 0 var(--side-pad) var(--side-pad);
            flex: 1;
            display: flex;
            flex-direction: column;
        }}

        /* Khoảng đệm cố định để item đầu list không bị nav-shell (fixed) che.
           FIX: body đã có padding-top: env(safe-area-inset-top) riêng, nên ở
           đây chỉ cần cộng thêm phần chiều cao thực của nav-shell (178px),
           không cộng lại env(safe-area-inset-top) lần 2 (tránh dư khoảng trống).
           CUỘN LỊCH: nav clip-path lên trên, banner đứng yên lộ ra — không cần
           dịch chuyển nav-spacer. */
        .nav-spacer {{
            height: 178px;
            margin-top: 0;
            margin-bottom: 12px;
            flex-shrink: 0;
            position: relative;
            /* Bo góc trên bằng nav (26px), góc dưới nhỏ hơn (16px) */
            border-radius: 26px 26px 16px 16px;
            overflow: hidden;
            width: 100%;
        }}

        .banner-img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: center;
            display: block;
        }}

        .banner-overlay {{
            position: absolute;
            inset: 0;
            background: linear-gradient(
                to bottom,
                rgba(0,0,0,0.0) 0%,
                rgba(0,0,0,0.45) 65%,
                rgba(0,0,0,0.75) 100%
            );
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            padding: 14px 16px;
        }}

        @keyframes shimmer {{
            0%   {{ background-position: -200% center; }}
            100% {{ background-position: 200% center; }}
        }}

        @keyframes blink-dot {{
            0%, 100% {{ opacity: 1; }}
            50%       {{ opacity: 0; }}
        }}

        .banner-title {{
            font-size: 1.25em;
            font-weight: 800;
            letter-spacing: 0.3px;
            line-height: 1.35;
            background: linear-gradient(
                90deg,
                #ff9cd9 0%,
                #c084fc 18%,
                #818cf8 35%,
                #38bdf8 52%,
                #34d399 68%,
                #facc15 84%,
                #ff9cd9 100%
            );
            background-size: 200% auto;
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: shimmer 3s linear infinite;
        }}

        .banner-sub {{
            font-size: 0.75em;
            color: rgba(255,255,255,0.6);
            margin-top: 4px;
            font-weight: 500;
            letter-spacing: 0.8px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .banner-dot {{
            display: inline-block;
            animation: blink-dot 1.1s ease-in-out infinite;
            color: #c084fc;
            -webkit-text-fill-color: #c084fc;
        }}

        /* ─────────────────────────── SEARCH ─────────────────────────── */
        .search-box {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 12px 16px;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        html[data-theme="light"] .search-box {{
            background: rgba(0, 0, 0, 0.04);
        }}

        .search-box input {{
            background: transparent;
            border: none;
            color: var(--text);
            width: 100%;
            outline: none;
            font-size: 1em;
        }}

        .search-box input::placeholder {{ color: var(--text-secondary); }}

        .search-clear {{
            background: rgba(255, 255, 255, 0.12);
            border: none;
            color: var(--text-secondary);
            width: 22px;
            height: 22px;
            border-radius: 50%;
            cursor: pointer;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.72em;
            line-height: 1;
            transition: all 0.15s;
        }}

        html[data-theme="light"] .search-clear {{
            background: rgba(0, 0, 0, 0.1);
        }}

        .search-clear:active {{
            background: rgba(255, 255, 255, 0.22);
            transform: scale(0.9);
        }}

        html[data-theme="light"] .search-clear:active {{
            background: rgba(0, 0, 0, 0.18);
        }}

        /* ─────────────────────────── LIST ─────────────────────────── */
        .list {{ display: flex; flex-direction: column; gap: 12px; min-height: 200px; flex-shrink: 0; }}

        .item {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 12px;
            display: flex;
            align-items: center;
            gap: 12px;
            cursor: pointer;
            transition: background 0.2s, transform 0.15s;
            animation: itemDropIn 0.36s cubic-bezier(0.2, 0.8, 0.2, 1) backwards;
            animation-delay: calc(var(--item-i, 0) * 35ms);
        }}

        @keyframes itemDropIn {{
            from {{ opacity: 0; transform: translateY(10px) scale(0.97); }}
            to {{ opacity: 1; transform: translateY(0) scale(1); }}
        }}

        html[data-theme="light"] .item {{
            background: rgba(0, 0, 0, 0.04);
        }}

        .item:active {{ background: rgba(255, 255, 255, 0.1); transform: scale(0.99); }}

        .item-icon {{
            width: 56px; height: 56px; border-radius: 12px;
            object-fit: cover; flex-shrink: 0;
            background: rgba(255, 255, 255, 0.05);
        }}

        .item-info {{ flex: 1; min-width: 0; }}

        .item-name {{
            font-weight: 600; font-size: 1em; margin-bottom: 4px;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}

        .item-id {{
            font-size: 0.85em; color: var(--text-secondary);
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}

        .item-version {{ font-size: 0.8em; color: var(--text-secondary); margin-top: 2px; }}

        .item-action {{
            background: var(--tint); color: white; border: none;
            padding: 9px 20px; border-radius: 20px; font-weight: 600;
            cursor: pointer; font-size: 0.9em; white-space: nowrap;
            transition: all 0.2s; flex-shrink: 0;
        }}

        .item-action:active {{ transform: scale(0.93); opacity: 0.85; }}

        .item-action.loading {{ opacity: 0.6; pointer-events: none; }}

        .item-action-buy {{
            background: linear-gradient(135deg, #6be8a0, #4fd88a);
            color: #0a1428;
        }}

        /* ─────────────────────────── PAGINATION ─────────────────────────── */
        .pagination {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 4px;
            flex-wrap: wrap;
            margin-top: 20px;
            padding-top: 6px;
            flex-shrink: 0;
        }}

        .page-btn {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border);
            color: var(--text);
            min-width: 38px;
            height: 38px;
            padding: 0 6px;
            border-radius: 10px;
            cursor: pointer;
            font-size: 1em;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.15s;
        }}

        html[data-theme="light"] .page-btn {{
            background: rgba(0, 0, 0, 0.04);
        }}

        .page-btn.active {{
            background: rgba(132, 142, 249, 0.25);
            border-color: var(--tint);
        }}

        .page-btn:disabled {{
            opacity: 0.35;
            pointer-events: none;
        }}

        .page-btn:active {{ transform: scale(0.92); }}

        .page-info {{
            width: 100%;
            text-align: center;
            color: var(--text-secondary);
            font-size: 0.8em;
            margin-top: 8px;
        }}

        /* ─────────────────────────── FOOTER ─────────────────────────── */
        .repo-footer {{
            text-align: center;
            margin-top: auto;
            padding: 28px 12px 0;
            flex-shrink: 0;
        }}

        .repo-footer p {{
            color: var(--text-secondary);
            font-size: 0.8em;
            line-height: 1.6;
            max-width: 380px;
            margin: 0 auto;
        }}

        .repo-footer-divider {{
            margin: 14px auto;
            font-size: 0.85em;
            letter-spacing: 1px;
            color: var(--tint);
            opacity: 0.55;
        }}

        .repo-footer-credit {{
            font-weight: 600;
            font-size: 0.82em !important;
            color: var(--text-secondary);
            opacity: 0.8;
        }}

        /* ─────────────────────────── MODAL ─────────────────────────── */
        .modal {{
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(10px);
            z-index: 100;
            /* FIX: Trước đây padding: 0 khiến modal-content dính sát mép dưới và
               2 bên màn hình -> chỉ bo được 2 góc trên, 2 góc dưới buộc phải vuông.
               Giờ thêm padding đều quanh để modal "lơ lửng" cách mép, cho phép bo
               tròn đủ cả 4 góc. Vẫn giữ animation trượt lên từ dưới như trước. */
            padding: 16px;
            padding-bottom: calc(16px + env(safe-area-inset-bottom, 0px));
            box-sizing: border-box;
            will-change: opacity;
        }}

        .modal.active {{ display: flex; align-items: flex-end; }}

        .modal-content {{
            position: relative;
            background: var(--glass-bg);
            backdrop-filter: var(--glass-blur);
            -webkit-backdrop-filter: var(--glass-blur);
            border: var(--glass-border);
            border-radius: var(--glass-radius);
            width: 100%;
            max-width: 500px;
            margin: 0 auto;
            max-height: calc(88vh - 32px);
            display: flex;
            flex-direction: column;
            animation: slideUp 0.25s ease;
            overflow: hidden;
            will-change: transform;
        }}

        html[data-theme="light"] .modal-content {{
            background: linear-gradient(135deg, #ffffff, #f9f9fb);
        }}

        @keyframes slideUp {{
            from {{ transform: translateY(100%); }}
            to {{ transform: translateY(0); }}
        }}

        /* Header CỐ ĐỊNH — không cuộn theo nội dung */
        .modal-fixed-header {{
            position: sticky;
            top: 0;
            z-index: 5;
            background: linear-gradient(135deg, #0a1428, #0f1e3d);
            padding: 18px 20px 14px;
            border-bottom: 1px solid var(--border);
            flex-shrink: 0;
        }}

        html[data-theme="light"] .modal-fixed-header {{
            background: linear-gradient(135deg, #ffffff, #f9f9fb);
        }}

        .modal-scroll-body {{
            overflow-y: auto;
            overscroll-behavior: contain;
            padding: 18px 20px 20px;
            flex: 1;
        }}

        .modal-header {{
            display: flex; gap: 16px;
            align-items: flex-start; padding-right: 40px;
        }}

        .modal-icon {{ width: 76px; height: 76px; border-radius: 18px; object-fit: cover; flex-shrink: 0; }}

        .modal-title-block {{ flex: 1; min-width: 0; }}

        .modal-name {{
            font-size: 1.3em; font-weight: 700; margin-bottom: 4px;
            overflow-wrap: break-word;
        }}

        .modal-id {{ color: var(--text-secondary); font-size: 0.88em; margin-bottom: 6px; word-break: break-all; }}

        .modal-version {{ color: var(--tint); font-size: 0.95em; font-weight: 600; }}

        /* X giờ neo theo modal-fixed-header (luôn đứng yên) */
        .modal-close {{
            position: absolute;
            top: 14px;
            right: 14px;
            background: rgba(255, 255, 255, 0.12);
            border: 1px solid var(--border);
            width: 36px; height: 36px;
            border-radius: 50%;
            cursor: pointer;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.1em; color: var(--text);
            z-index: 6;
            transition: all 0.2s;
        }}

        html[data-theme="light"] .modal-close {{
            background: rgba(0, 0, 0, 0.08);
        }}

        .modal-close:active {{
            background: rgba(255, 255, 255, 0.25);
            transform: scale(0.93);
        }}

        /* ─────────────────────────── SCREENSHOTS ─────────────────────────── */
        .screenshots {{ display: flex; gap: 10px; overflow-x: auto; margin-bottom: 4px; padding-bottom: 6px; scroll-snap-type: x proximity; }}

        .screenshot {{
            width: 140px; height: 248px; border-radius: 14px; object-fit: cover;
            flex-shrink: 0; border: 1px solid var(--border);
            cursor: pointer; transition: transform 0.15s;
            scroll-snap-align: start;
        }}

        .screenshot:active {{ transform: scale(0.96); }}

        /* LIGHTBOX */
        .lightbox {{
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.92);
            z-index: 300;
            align-items: center;
            justify-content: center;
            touch-action: pan-y;
        }}

        .lightbox.active {{ display: flex; }}

        .lightbox-img {{
            max-width: 92vw;
            max-height: 80vh;
            border-radius: 14px;
            object-fit: contain;
            user-select: none;
            -webkit-user-drag: none;
        }}

        .lightbox-close {{
            position: absolute; top: 18px; right: 18px;
            width: 36px; height: 36px; border-radius: 50%;
            background: rgba(255,255,255,0.12); border: 1px solid var(--border);
            color: var(--text); font-size: 1.1em;
            display: flex; align-items: center; justify-content: center;
            cursor: pointer; transition: all 0.2s;
        }}

        .lightbox-nav {{
            position: absolute; top: 50%; transform: translateY(-50%);
            width: 44px; height: 44px; border-radius: 50%;
            background: rgba(255,255,255,0.12); border: 1px solid var(--border);
            color: var(--text); font-size: 1.3em;
            display: flex; align-items: center; justify-content: center;
            cursor: pointer;
        }}

        .lightbox-prev {{ left: 14px; }}
        .lightbox-next {{ right: 14px; }}

        .lightbox-counter {{
            position: absolute; bottom: 22px; left: 50%; transform: translateX(-50%);
            color: var(--text-secondary); font-size: 0.85em;
            background: rgba(255,255,255,0.08); padding: 5px 12px; border-radius: 20px;
        }}

        /* ─────────────────────────── ACCORDION SECTIONS ─────────────────────────── */
        .detail-section {{
            margin-top: 14px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border);
            border-radius: 14px;
            overflow: hidden;
        }}

        html[data-theme="light"] .detail-section {{
            background: rgba(0, 0, 0, 0.03);
        }}

        .detail-section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 13px 14px;
            cursor: pointer;
            user-select: none;
        }}

        .detail-section-title {{
            font-weight: 600; color: var(--text); font-size: 0.92em;
            display: flex; align-items: center; gap: 8px;
        }}

        .detail-section-toggle {{
            font-size: 0.85em;
            color: var(--text-secondary);
            width: 26px; height: 26px;
            border-radius: 8px;
            background: rgba(255,255,255,0.06);
            display: flex; align-items: center; justify-content: center;
            flex-shrink: 0;
            transition: transform 0.2s;
        }}

        html[data-theme="light"] .detail-section-toggle {{
            background: rgba(0, 0, 0, 0.06);
        }}

        .detail-section-body {{
            display: grid;
            grid-template-rows: 0fr;
            overflow: hidden;
            transition: grid-template-rows 0.32s cubic-bezier(0.4, 0, 0.2, 1);
            padding: 0 14px;
        }}

        .detail-section-body > * {{
            min-height: 0;
            overflow: hidden;
        }}

        .detail-section.open .detail-section-body {{
            grid-template-rows: 1fr;
            padding: 0 14px 14px;
        }}

        .detail-section.open .detail-section-toggle {{ transform: rotate(180deg); }}

        .detail-section-content {{ color: var(--text); font-size: 0.93em; line-height: 1.55; }}

        /* Version list bên trong accordion */
        .version-history {{
            background: rgba(255, 255, 255, 0.02);
            border-radius: 12px; padding: 4px;
        }}

        html[data-theme="light"] .version-history {{
            background: rgba(0, 0, 0, 0.02);
        }}

        .version-item {{
            padding: 11px 12px;
            border: 1.5px solid transparent;
            border-radius: 10px;
            margin-bottom: 4px;
            font-size: 0.9em;
            cursor: pointer;
            transition: all 0.15s;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 8px;
        }}

        .version-item:active {{ background: rgba(255, 255, 255, 0.06); }}

        html[data-theme="light"] .version-item:active {{ background: rgba(0, 0, 0, 0.06); }}

        .version-item.selected {{
            border-color: var(--tint);
            background: rgba(132, 142, 249, 0.12);
        }}

        .version-item-left {{ flex: 1; min-width: 0; }}

        .version-num {{ font-weight: 600; color: var(--tint); }}

        .version-check {{
            font-size: 1.1em; color: var(--tint);
            opacity: 0; transition: opacity 0.15s; flex-shrink: 0;
        }}

        .version-item.selected .version-check {{ opacity: 1; }}

        .permissions-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}

        .permission-item {{
            background: rgba(255, 255, 255, 0.05); border: 1px solid var(--border);
            border-radius: 8px; padding: 10px; font-size: 0.85em; color: var(--text-secondary);
        }}

        html[data-theme="light"] .permission-item {{
            background: rgba(0, 0, 0, 0.04);
        }}

        /* Khối thông tin phiên bản đang chọn — luôn hiện, không thu gọn */
        .info-box {{
            margin-top: 14px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 13px 14px;
        }}

        html[data-theme="light"] .info-box {{
            background: rgba(0, 0, 0, 0.03);
        }}

        .info-row {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            gap: 12px;
            padding: 5px 0;
            border-bottom: 1px solid var(--border);
        }}

        .info-row:last-child {{ border-bottom: none; padding-bottom: 0; }}
        .info-row:first-child {{ padding-top: 0; }}

        .info-row.info-row-wrap {{
            flex-direction: column;
            align-items: flex-start;
            gap: 3px;
        }}

        .info-label {{
            font-weight: 600;
            font-size: 0.85em;
            color: var(--text-secondary);
            flex-shrink: 0;
        }}

        .info-value {{
            color: var(--text);
            font-size: 0.9em;
            text-align: right;
            word-break: break-word;
        }}

        .info-row-wrap .info-value {{
            text-align: left;
            line-height: 1.5;
        }}

        /* ─────────────────────────── ACTION BAR ─────────────────────────── */
        .action-buttons {{
            display: flex; gap: 8px;
            flex-shrink: 0;
            padding: 12px 20px calc(14px + env(safe-area-inset-bottom, 0px));
            border-top: 1px solid var(--border);
            background: var(--card);
        }}

        .action-btn {{
            flex: 1 1 auto;
            min-width: 0;
            background: var(--tint); color: white; border: none;
            padding: 14px 12px; border-radius: 999px; font-weight: 700;
            cursor: pointer; font-size: 1em; transition: all 0.15s;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}

        .action-btn:active {{ transform: scale(0.97); opacity: 0.9; }}

        .action-btn.loading {{ opacity: 0.6; pointer-events: none; }}

        .action-btn-version {{
            flex: 0 0 auto;
            max-width: 34%;
            background: rgba(132, 142, 249, 0.16);
            color: var(--tint); border: 1.5px solid var(--tint);
            padding: 14px 12px; border-radius: 999px; font-weight: 700;
            font-size: 0.92em; cursor: pointer; transition: all 0.15s;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}

        .action-btn-version:active {{ transform: scale(0.97); opacity: 0.9; }}

        .action-btn-icon {{
            width: 50px; flex: 0 0 auto;
            background: rgba(255, 255, 255, 0.1);
            color: var(--text); border: 1px solid var(--border);
            border-radius: 999px; font-size: 1.2em; cursor: pointer;
        }}

        html[data-theme="light"] .action-btn-icon {{
            background: rgba(0, 0, 0, 0.05);
        }}

        .action-btn-icon:active {{ background: rgba(255, 255, 255, 0.2); }}

        /* ─────────────────────────── LOADING / EMPTY ─────────────────────────── */
        .loading, .empty-state {{ text-align: center; color: var(--text-secondary); padding: 50px 20px; }}

        .spinner {{
            width: 38px; height: 38px; border: 3px solid rgba(255, 255, 255, 0.1);
            border-top-color: var(--tint); border-radius: 50%;
            animation: spin 0.9s linear infinite; margin: 0 auto 18px;
        }}

        html[data-theme="light"] .spinner {{
            border-color: rgba(0, 0, 0, 0.1);
            border-top-color: var(--tint);
        }}

        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}

        .toast {{
            position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
            background: rgba(28,28,46,0.95); border: 1px solid var(--border);
            padding: 12px 20px; border-radius: 12px; font-size: 0.9em;
            z-index: 200; opacity: 0; transition: opacity 0.25s; pointer-events: none;
            max-width: 86vw; text-align: center;
        }}

        html[data-theme="light"] .toast {{
            background: rgba(255,255,255,0.95);
        }}

        .toast.show {{ opacity: 1; }}

        /* ─────────────────────────── SETTINGS PANEL (layer trượt từ phải) ─────────────────────────── */
        .settings-overlay {{
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.35);
            backdrop-filter: blur(2px);
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
            z-index: 300;
            will-change: opacity;
            transform: translateZ(0);
        }}

        .settings-overlay.active {{
            opacity: 1;
            pointer-events: auto;
        }}

        .settings-panel {{
            position: fixed;
            top: max(16px, env(safe-area-inset-top, 16px));
            right: 12px;
            max-height: calc(100vh - 32px);
            width: fit-content;
            min-width: 210px;
            max-width: min(85vw, 320px);
            background: var(--glass-bg);
            backdrop-filter: var(--glass-blur);
            -webkit-backdrop-filter: var(--glass-blur);
            border: var(--glass-border);
            border-radius: var(--glass-radius);
            box-shadow: var(--glass-shadow);
            transform: translateX(calc(100% + 24px)) translateZ(0);
            transition: transform 0.38s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 301;
            display: flex;
            flex-direction: column;
            padding: 6px 0 10px;
            overflow: hidden;
            will-change: transform;
        }}

        html[data-theme="light"] .settings-panel {{
            background: var(--glass-bg-light);
            border: var(--glass-border-light);
            box-shadow: var(--glass-shadow-light);
        }}

        .settings-panel.active {{
            transform: translateX(0) translateZ(0);
        }}

        /* ─────────────────────────── VERSION PICKER (modal căn giữa màn hình) ─────────────────────────── */
        /* FIX: Trước đây kế thừa .settings-panel (slide-in từ phải, neo top/right)
           khiến panel hiện lệch sang góc phải, khó bấm trên 1 tay. Giờ tách hẳn
           ra thành modal độc lập, luôn căn giữa cả chiều ngang và chiều đứng. */
        .version-picker-panel {{
            position: fixed;
            top: 50%;
            left: 50%;
            right: auto;
            width: min(86%, 360px);
            max-width: 360px;
            max-height: min(70vh, 520px);
            background: var(--glass-bg);
            backdrop-filter: var(--glass-blur);
            -webkit-backdrop-filter: var(--glass-blur);
            border: var(--glass-border);
            border-radius: var(--glass-radius);
            box-shadow: var(--glass-shadow);
            transform: translate(-50%, -50%) scale(0.92);
            opacity: 0;
            pointer-events: none;
            transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1),
                        opacity 0.22s ease;
            z-index: 401;
            display: flex;
            flex-direction: column;
            padding: 6px 0 10px;
            overflow: hidden;
            will-change: transform, opacity;
        }}

        html[data-theme="light"] .version-picker-panel {{
            background: rgba(255, 255, 255, 0.95);
            border: 1px solid rgba(0, 0, 0, 0.08);
        }}

        .version-picker-panel.active {{
            transform: translate(-50%, -50%) scale(1);
            opacity: 1;
            pointer-events: auto;
        }}

        #versionPickerOverlay {{ z-index: 400; }}

        .version-picker-item {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            background: rgba(255, 255, 255, 0.06);
            border: 1.5px solid var(--border);
            border-radius: 15px;
            padding: 12px 14px;
            cursor: pointer;
            transition: all 0.15s;
        }}

        html[data-theme="light"] .version-picker-item {{
            background: rgba(0, 0, 0, 0.035);
        }}

        .version-picker-item.selected {{
            border-color: var(--tint);
            background: rgba(132, 142, 249, 0.14);
        }}

        .version-picker-label {{
            font-weight: 600;
            font-size: 0.92em;
            color: var(--text);
        }}

        .version-picker-check {{
            color: var(--tint);
            font-weight: 700;
            opacity: 0;
        }}

        .version-picker-item.selected .version-picker-check {{ opacity: 1; }}

        /* ─────────────────────────── VERSION POPOVER (modal căn giữa, dùng cho nút Nhận) ─────────────────────────── */
        /* FIX: Trước đây neo theo vị trí nút bấm (positionVersionPopover tính
           top/left theo getBoundingClientRect của nút) khiến popup hiện ở góc
           màn hình, dễ bị mép/nav che mất, khó bấm. Giờ đổi sang modal cố định
           căn giữa màn hình giống version-picker-panel, đồng thời thêm tiêu đề
           là tên app vừa nhấn "Nhận" để rõ ràng hơn. */
        .version-popover-overlay {{
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.35);
            backdrop-filter: blur(2px);
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
            z-index: 400;
        }}

        .version-popover-overlay.active {{
            opacity: 1;
            pointer-events: auto;
        }}

        .version-popover {{
            position: fixed;
            top: 50%;
            left: 50%;
            width: min(86%, 320px);
            max-width: 320px;
            max-height: min(70vh, 480px);
            background: var(--glass-bg);
            backdrop-filter: var(--glass-blur);
            -webkit-backdrop-filter: var(--glass-blur);
            border: var(--glass-border);
            border-radius: var(--glass-radius);
            box-shadow: var(--glass-shadow);
            opacity: 0;
            pointer-events: none;
            transform: translate(-50%, -50%) scale(0.9);
            transition: opacity 0.18s cubic-bezier(0.4, 0, 0.2, 1),
                        transform 0.18s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 401;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}

        html[data-theme="light"] .version-popover {{
            background: var(--glass-bg-light);
            border: var(--glass-border-light);
            box-shadow: var(--glass-shadow-light);
        }}

        .version-popover.active {{
            opacity: 1;
            pointer-events: auto;
            transform: translate(-50%, -50%) scale(1);
        }}

        .version-popover .version-popover-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 14px 16px 12px;
            border-bottom: 1px solid var(--border);
            flex-shrink: 0;
        }}

        .version-popover .version-popover-header h3 {{
            font-size: 0.96em;
            font-weight: 700;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .version-popover .version-popover-list {{
            display: flex;
            flex-direction: column;
            gap: 6px;
            padding: 10px;
            overflow-y: auto;
            overscroll-behavior: contain;
        }}

        .version-popover .version-picker-item {{
            padding: 10px 12px;
            border-radius: 12px;
        }}

        .version-popover .version-picker-label {{
            font-size: 0.86em;
        }}

        /* ─────────────────────────── CONFIRM DIALOG ─────────────────────────── */
        .confirm-overlay {{
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.45);
            backdrop-filter: blur(3px);
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.25s ease;
            z-index: 500;
        }}

        .confirm-overlay.active {{ opacity: 1; pointer-events: auto; }}

        .confirm-dialog {{
            position: fixed;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%) scale(0.92);
            width: calc(100% - 64px);
            max-width: 300px;
            background: var(--glass-bg);
            backdrop-filter: var(--glass-blur);
            -webkit-backdrop-filter: var(--glass-blur);
            border: var(--glass-border);
            border-radius: var(--glass-radius);
            padding: 26px 22px 18px;
            text-align: center;
            box-shadow: var(--glass-shadow);
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.22s cubic-bezier(0.4, 0, 0.2, 1),
                        transform 0.22s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 501;
        }}

        .confirm-dialog.active {{
            opacity: 1;
            pointer-events: auto;
            transform: translate(-50%, -50%) scale(1);
        }}

        .confirm-icon {{ font-size: 2.2em; margin-bottom: 8px; }}

        .confirm-title {{ font-weight: 700; font-size: 1.05em; margin-bottom: 6px; }}

        .confirm-message {{
            color: var(--text-secondary);
            font-size: 0.86em;
            line-height: 1.5;
            margin-bottom: 18px;
        }}

        .confirm-actions {{ display: flex; gap: 8px; }}

        .confirm-btn {{
            flex: 1;
            padding: 12px;
            border-radius: 13px;
            font-weight: 700;
            font-size: 0.92em;
            cursor: pointer;
            border: none;
        }}

        .confirm-btn-cancel {{
            background: rgba(255, 255, 255, 0.08);
            color: var(--text);
            border: 1px solid var(--border);
        }}

        html[data-theme="light"] .confirm-btn-cancel {{
            background: rgba(0, 0, 0, 0.05);
        }}

        .confirm-btn-ok {{
            background: var(--tint);
            color: white;
        }}

        .settings-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 12px 7px;
            border-bottom: 1px solid var(--border);
        }}

        .settings-header h3 {{
            font-size: 0.82em;
            font-weight: 700;
            letter-spacing: 0.3px;
        }}

        .settings-close {{
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid var(--border);
            color: var(--text);
            width: 36px; height: 36px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 1.05em;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            transition: all 0.2s;
        }}

        .settings-close:active {{
            background: rgba(255, 255, 255, 0.2);
            transform: scale(0.93);
        }}

        html[data-theme="light"] .settings-close {{
            background: rgba(0, 0, 0, 0.05);
        }}

        html[data-theme="light"] .settings-close:active {{
            background: rgba(0, 0, 0, 0.12);
        }}

        /* ─────────────────────────── MODAL SEARCH BUTTON ─────────────────────────── */
        .modal-search-btn {{
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid var(--border);
            color: var(--text);
            width: 36px; height: 36px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 1.05em;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.15s;
            flex-shrink: 0;
        }}

        html[data-theme="light"] .modal-search-btn {{
            background: rgba(0, 0, 0, 0.05);
        }}

        .modal-search-btn:active {{
            background: rgba(255, 255, 255, 0.2);
            transform: scale(0.92);
        }}

        html[data-theme="light"] .modal-search-btn:active {{
            background: rgba(0, 0, 0, 0.12);
        }}

        .modal-header-actions {{
            display: flex;
            gap: 10px;
            align-items: center;
            flex-shrink: 0;
        }}

        .settings-list {{
            display: flex;
            flex-direction: column;
            gap: 3px;
            padding: 6px 7px;
            overflow-y: auto;
            overscroll-behavior: contain;
        }}

        .settings-item {{
            display: flex;
            align-items: center;
            gap: 7px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 10px;
            padding: 5px 8px;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
            color: var(--text);
        }}

        html[data-theme="light"] .settings-item {{
            background: rgba(0, 0, 0, 0.035);
        }}

        .settings-item-account {{
            background: linear-gradient(135deg, rgba(132,142,249,0.22), rgba(107,232,160,0.14));
            border: 1px solid rgba(132,142,249,0.4);
        }}

        .settings-item:active {{
            background: rgba(255, 255, 255, 0.14);
            transform: scale(0.98);
        }}

        html[data-theme="light"] .settings-item:active {{
            background: rgba(0, 0, 0, 0.08);
        }}

        .settings-item-icon {{
            font-size: 0.85em;
            width: 15px;
            text-align: center;
            flex-shrink: 0;
            line-height: 1;
        }}

        .settings-item-text {{
            display: flex;
            flex-direction: column;
            gap: 0px;
            flex: 1;
            min-width: 0;
        }}

        .settings-item-title {{
            font-weight: 500;
            font-size: 0.74em;
            line-height: 1.3;
        }}

        .settings-item-sub {{
            font-size: 0.60em;
            color: var(--text-secondary);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            line-height: 1.2;
        }}

        @media (max-width: 480px) {{
            :root {{ --side-pad: 12px; }}
            .container {{ padding: 0 var(--side-pad) var(--side-pad); }}
            .modal-icon {{ width: 64px; height: 64px; }}
            .modal-name {{ font-size: 1.15em; }}
            .permissions-grid {{ grid-template-columns: 1fr; }}
            .screenshot {{ width: 120px; height: 213px; }}
        }}
    </style>
</head>
<body>

<!-- NAV SHELL -->
<div class="nav-shell" id="navShell">
    <div class="nav-inner">
        <div class="header-row">
            <button class="icon-btn" onclick="location.href='./index.html'" title="Trang chủ">🏠</button>
            <div class="nav-repo-name">{repo_name}</div>
            <button class="icon-btn" onclick="toggleSettings()" title="Cài đặt">⚙️</button>
        </div>

        <div class="tabs-header">
            <button class="tab-btn {active_apps}" onclick="navigateTab('apps.html', this)">📱 Apps</button>
            <button class="tab-btn {active_tweaks}" onclick="navigateTab('debs.html', this)">🔧 Tweaks</button>
            <button class="tab-btn {active_dylibs}" onclick="navigateTab('dylibs.html', this)">📚 Dylibs</button>
        </div>

        <div class="search-box">
            <span>🔍</span>
            <input type="text" id="searchInput" placeholder="Tìm kiếm..." oninput="onSearchInput()">
            <button class="search-clear" id="searchClear" onclick="clearSearch()" title="Xoá" style="display:none;">❌</button>
        </div>
    </div>
</div>

<div class="container">
    <div class="nav-spacer">
        <img class="banner-img"
             src="https://raw.githubusercontent.com/2KGT/2KGT.github.io/main/repo/data/default/Kyic_banner.webp"
             alt=""
             onerror="this.style.display='none'">
        <div class="banner-overlay">
            <div class="banner-title" id="bannerTitle">💬 Chào mừng bạn 🦎</div>
        </div>
    </div>
    <div id="list" class="list">
        <div class="loading">
            <div class="spinner"></div>
            <p>Đang tải dữ liệu...</p>
        </div>
    </div>

    <div class="pagination" id="pagination" style="display:none;"></div>

    <div class="repo-footer">

        <div class="repo-footer-divider">──⋆⋅☆⋅⋆જ⁀➴ₖ🦎ᵢ꜀︵✰⋆⋅☆⋅⋆──</div>
        <p class="repo-footer-credit">Made with ❤️ by Kyic</p>
    </div>
</div>

<!-- SETTINGS PANEL -->
<div class="settings-overlay" id="settingsOverlay" onclick="closeSettings()"></div>
<div class="settings-panel" id="settingsPanel">
    <div class="settings-header">
        <h3 id="settingsTitle">⚙️ Cài đặt</h3>
        <button class="settings-close" onclick="closeSettings()">❌</button>
    </div>
    <div class="settings-list">
        <div class="settings-item settings-item-account" onclick="goAccount()">
            <div class="settings-item-icon">👤</div>
            <div class="settings-item-text">
                <div class="settings-item-title">Tài khoản</div>
                <div class="settings-item-sub" id="accountSub">Đăng nhập / Đăng ký</div>
            </div>
        </div>
        <a class="settings-item" href="./sign.html">
            <div class="settings-item-icon">🖊️</div>
            <div class="settings-item-text">
                <div class="settings-item-title">Sign IPA</div>
                <div class="settings-item-sub">Ký lại file .ipa để cài đặt</div>
            </div>
        </a>
        <div class="settings-item" onclick="toggleLanguage()">
            <div class="settings-item-icon">🌐</div>
            <div class="settings-item-text">
                <div class="settings-item-title" id="settingsLangTitle">Ngôn ngữ</div>
                <div class="settings-item-sub" id="settingsLangSub">Tiếng Việt</div>
            </div>
        </div>
        <div class="settings-item" onclick="cycleTheme()">
            <div class="settings-item-icon" id="settingsThemeIcon">🌓</div>
            <div class="settings-item-text">
                <div class="settings-item-title" id="settingsThemeTitle">Chủ đề</div>
                <div class="settings-item-sub" id="settingsThemeSub">Tối</div>
            </div>
        </div>
        <a class="settings-item" href="https://t.me/+uhoygGN-1Gc4NzZl" target="_blank" rel="noopener noreferrer">
            <div class="settings-item-icon">💬</div>
            <div class="settings-item-text">
                <div class="settings-item-title" id="settingsChatTitle">Nhắn tin</div>
                <div class="settings-item-sub" id="settingsChatSub">Tham gia kênh Telegram</div>
            </div>
        </a>
        <a class="settings-item" href="https://nativex.edu.vn/wp-content/uploads/2019/12/thanks-1024x576.jpg" target="_blank" rel="noopener noreferrer">
            <div class="settings-item-icon">☕️</div>
            <div class="settings-item-text">
                <div class="settings-item-title" id="settingsDonateTitle">Donate</div>
                <div class="settings-item-sub" id="settingsDonateSub">Ủng hộ một ly cà phê</div>
            </div>
        </a>
    </div>
</div>

<!-- VERSION PICKER (MODAL) — layer trượt từ phải, dùng cho nút [Version] trong modal chi tiết -->
<div class="settings-overlay" id="versionPickerOverlay" onclick="closeVersionPicker()"></div>
<div class="settings-panel version-picker-panel" id="versionPickerPanel">
    <div class="settings-header">
        <h3 id="versionPickerTitle">✨ Chọn phiên bản</h3>
        <div class="modal-header-actions">
            <button class="modal-search-btn" onclick="toggleVersionPickerSearch()" title="Tìm kiếm">🔍</button>
            <button class="settings-close" onclick="closeVersionPicker()">❌</button>
        </div>
    </div>
    <div id="versionPickerSearchBox" class="search-box" style="display:none; margin: 6px 10px 4px;">
        <input type="text" id="versionPickerSearchInput" placeholder="Tìm kiếm phiên bản..." onkeyup="filterVersionPickerList()">
        <button class="search-clear" onclick="clearVersionPickerSearch()">❌</button>
    </div>
    <div class="settings-list" id="versionPickerList"></div>
</div>

<!-- VERSION POPOVER (LIST) — modal căn giữa, dùng cho nút "Nhận" trong list -->
<div class="version-popover-overlay" id="versionPopoverOverlay" onclick="closeVersionPopover()"></div>
<div class="version-popover" id="versionPopover">
    <div class="version-popover-header">
        <h3 id="versionPopoverTitle">✨ Chọn phiên bản</h3>
        <div class="modal-header-actions">
            <button class="modal-search-btn" onclick="toggleVersionPopoverSearch()" title="Tìm kiếm">🔍</button>
            <button class="settings-close" onclick="closeVersionPopover()">❌</button>
        </div>
    </div>
    <div id="versionPopoverSearchBox" class="search-box" style="display:none; margin: 10px 12px 10px;">
        <input type="text" id="versionPopoverSearchInput" placeholder="Tìm kiếm phiên bản..." onkeyup="filterVersionPopoverList()">
        <button class="search-clear" onclick="clearVersionPopoverSearch()">❌</button>
    </div>
    <div class="version-popover-list" id="versionPopoverList"></div>
</div>

<!-- CONFIRM DOWNLOAD DIALOG -->
<div class="confirm-overlay" id="confirmOverlay" onclick="closeConfirmDownload()"></div>
<div class="confirm-dialog" id="confirmDialog">
    <div class="confirm-icon" id="confirmIcon">⬇️</div>
    <div class="confirm-title" id="confirmTitle">Tải xuống</div>
    <div class="confirm-message" id="confirmMessage">Bạn có muốn tải phiên bản này?</div>
    <div class="confirm-actions">
        <button class="confirm-btn confirm-btn-cancel" onclick="closeConfirmDownload()">Huỷ</button>
        <button class="confirm-btn confirm-btn-ok" id="confirmOkBtn" onclick="confirmDownloadProceed()">Tải xuống</button>
    </div>
</div>


<!-- MODAL -->
<div id="modal" class="modal" onclick="closeModal(event)">
    <div class="modal-content" onclick="event.stopPropagation()">

        <div class="modal-fixed-header">
            <button class="modal-close" onclick="closeModal()">❌</button>
            <div class="modal-header">
                <img id="modalIcon" class="modal-icon" src="" alt="Icon">
                <div class="modal-title-block">
                    <div class="modal-name" id="modalName"></div>
                    <div class="modal-id" id="modalId"></div>
                    <div class="modal-version" id="modalVersion"></div>
                </div>
            </div>
        </div>

        <div class="modal-scroll-body">

            <div id="screenshotsSection" style="display:none;">
                <div class="detail-section-title" style="margin-bottom:8px;">📸 Ảnh chụp màn hình</div>
                <div class="screenshots" id="screenshots"></div>
            </div>

            <div class="info-box">
                <div class="detail-section-title" style="margin-bottom:10px;">ℹ️ Thông tin</div>
                <div class="detail-section-content">
                    <div class="info-row" id="rowAuthor">
                        <div class="info-label">Tác giả</div>
                        <div class="info-value" id="infoAuthor">—</div>
                    </div>
                    <div class="info-row" id="rowProvider">
                        <div class="info-label">Nhà cung cấp</div>
                        <div class="info-value" id="infoProvider">—</div>
                    </div>
                    <div class="info-row" id="rowSection">
                        <div class="info-label">Phân loại</div>
                        <div class="info-value" id="infoSection">—</div>
                    </div>
                    <div class="info-row" id="rowVersion">
                        <div class="info-label">Phiên bản</div>
                        <div class="info-value" id="infoVersion">—</div>
                    </div>
                    <div class="info-row" id="rowAgeRating">
                        <div class="info-label">Độ tuổi</div>
                        <div class="info-value" id="infoAgeRating">—</div>
                    </div>
                    <div class="info-row" id="rowCategory">
                        <div class="info-label">Loại tệp</div>
                        <div class="info-value" id="infoCategory">—</div>
                    </div>
                    <div class="info-row" id="rowArch">
                        <div class="info-label">Kiến trúc</div>
                        <div class="info-value" id="infoArch">—</div>
                    </div>
                    <div class="info-row" id="rowSize">
                        <div class="info-label">Dung lượng</div>
                        <div class="info-value" id="infoSize">—</div>
                    </div>
                    <div class="info-row" id="rowInstalledSize">
                        <div class="info-label">Dung lượng cài đặt</div>
                        <div class="info-value" id="infoInstalledSize">—</div>
                    </div>
                    <div class="info-row" id="rowCompat">
                        <div class="info-label">Tương thích</div>
                        <div class="info-value" id="infoCompat">—</div>
                    </div>
                    <div class="info-row info-row-wrap" id="rowDepends">
                        <div class="info-label">Phụ thuộc</div>
                        <div class="info-value" id="infoDepends">—</div>
                    </div>
                    <div class="info-row" id="rowBundleId">
                        <div class="info-label">Định danh</div>
                        <div class="info-value" id="infoBundleId">—</div>
                    </div>
                    <div class="info-row" id="rowUpdateDate">
                        <div class="info-label">Ngày cập nhật</div>
                        <div class="info-value" id="infoUpdateDate">—</div>
                    </div>
                </div>
            </div>

            <div id="changelogBox" class="detail-section" style="display:none;">
                <div class="detail-section-header" onclick="toggleSection('changelogBox')">
                    <div class="detail-section-title">🆕 Có gì mới</div>
                    <div class="detail-section-toggle">🔽</div>
                </div>
                <div class="detail-section-body">
                    <div class="detail-section-content" id="modalChangelog"></div>
                </div>
            </div>

            <div id="descSection" class="detail-section" style="display:none;">
                <div class="detail-section-header" onclick="toggleSection('descSection')">
                    <div class="detail-section-title">📝 Mô tả</div>
                    <div class="detail-section-toggle">🔽</div>
                </div>
                <div class="detail-section-body">
                    <div class="detail-section-content" id="modalDesc"></div>
                </div>
            </div>

            <div id="permSection" class="detail-section" style="display:none;">
                <div class="detail-section-header" onclick="toggleSection('permSection')">
                    <div class="detail-section-title">🔐 Quyền hạn</div>
                    <div class="detail-section-toggle">🔽</div>
                </div>
                <div class="detail-section-body">
                    <div class="permissions-grid" id="permissions"></div>
                </div>
            </div>

        </div>

        <div class="action-buttons">
            <button class="action-btn-version" id="versionPickerBtn" onclick="openVersionPicker()">
                <span id="versionPickerLabel">Version</span>
            </button>
            <button class="action-btn-icon" onclick="copySelected()" title="Sao chép link">📋</button>
            <button class="action-btn" id="downloadBtn" onclick="downloadSelected()">Tải xuống</button>
        </div>
    </div>
</div>

<!-- LIGHTBOX -->
<div id="lightbox" class="lightbox" onclick="lightboxBackdropClick(event)">
    <button class="lightbox-close" onclick="closeLightbox()">❌</button>
    <button class="lightbox-nav lightbox-prev" onclick="lightboxNav(-1, event)">‹</button>
    <img id="lightboxImg" class="lightbox-img" src="" alt="Screenshot" onclick="event.stopPropagation()">
    <button class="lightbox-nav lightbox-next" onclick="lightboxNav(1, event)">›</button>
    <div class="lightbox-counter" id="lightboxCounter"></div>
</div>

<div id="toast" class="toast"></div>

<script>
    // ════════════════════════════════════════════════════════════
    // I18N & THEME SETUP
    // ════════════════════════════════════════════════════════════
    const I18N = {{
        vi: {{
            "loading": "Đang tải dữ liệu...",
            "no_results": "😕 Không tìm thấy kết quả",
            "no_data": "📭 Chưa có dữ liệu",
            "error": "❌ Lỗi tải dữ liệu: ",
            "page": "Trang",
            "results": "kết quả",
            "no_version": "❌ Không có phiên bản nào để tải",
            "no_link": "❌ Không tìm thấy link tải về",
            "no_results_copy": "❌ Không có link để sao chép",
            "download_start": "⏳ Đang tải...",
            "download_success": "✅ Đang tải xuống...",
            "download_fallback": "⚠️ Đang mở link tải (chế độ dự phòng)",
            "download_confirm": "Tải xuống",
            "no_changelog": "Phiên bản này chưa có thông tin cập nhật",
            "copy_success": "✅ Đã sao chép link!",
            "copy_error": "❌ Sao chép thất bại",
            "settings": "⚙️ Cài đặt (sẽ cập nhật sau)",
            "banner_title": "💬 Chào mừng bạn 🦎",
            "search_placeholder": "Tìm kiếm ứng dụng...",
            "tab_apps": "Apps",
            "tab_tweaks": "Tweaks",
            "tab_dylibs": "Dylibs",
            "install_source": "Thêm Nguồn",
            "install_source_sub": "Nhấn để thêm vào Feather / Sidestore",
            "version_label": "Phiên bản",
            "size_label": "Dung lượng",
            "changelog_label": "Nhật ký",
            "download_label": "Tải xuống",
            "copy_label": "Sao chép link",
            "all_versions": "Tất cả phiên bản"
        }},
        en: {{
            "loading": "Loading data...",
            "no_results": "😕 No results found",
            "no_data": "📭 No data",
            "error": "❌ Error loading data: ",
            "page": "Page",
            "results": "results",
            "no_version": "❌ No version to download",
            "no_link": "❌ No download link found",
            "no_results_copy": "❌ No link to copy",
            "download_start": "⏳ Downloading...",
            "download_success": "✅ Downloading...",
            "download_fallback": "⚠️ Opening link (fallback mode)",
            "download_confirm": "Download",
            "no_changelog": "No update information for this version",
            "copy_success": "✅ Link copied!",
            "copy_error": "❌ Copy failed",
            "settings": "⚙️ Settings (coming soon)",
            "banner_title": "💬 Welcome 🦎",
            "search_placeholder": "Search apps...",
            "tab_apps": "Apps",
            "tab_tweaks": "Tweaks",
            "tab_dylibs": "Dylibs",
            "install_source": "Add Source",
            "install_source_sub": "Tap to add to Feather / Sidestore",
            "version_label": "Version",
            "size_label": "Size",
            "changelog_label": "Changelog",
            "download_label": "Download",
            "copy_label": "Copy link",
            "all_versions": "All versions"
        }}
    }};

    function getLang() {{
        return document.documentElement.getAttribute('data-lang') || 'vi';
    }}

    function t(key) {{
        const lang = getLang();
        return (I18N[lang] || I18N.vi)[key] || key;
    }}

    function toggleLanguage() {{
        const current = getLang();
        const next = current === 'vi' ? 'en' : 'vi';
        document.documentElement.setAttribute('data-lang', next);
        document.documentElement.lang = next;
        localStorage.setItem('lang', next);
        sessionStorage.setItem('reopenSettings', '1');
        location.reload();
    }}

    function initTheme() {{
        // themeMode: 'auto' | 'light' | 'dark'
        const mode = localStorage.getItem('themeMode') || 'auto';
        applyThemeMode(mode);

        // Khi thiết bị đổi chế độ sáng/tối, cập nhật ngay nếu đang ở Auto
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {{
            if ((localStorage.getItem('themeMode') || 'auto') !== 'auto') return;
            document.documentElement.setAttribute('data-theme', e.matches ? 'dark' : 'light');
            updateSettingsPanelTexts();
        }});
    }}

    function applyThemeMode(mode) {{
        if (mode === 'auto') {{
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
        }} else {{
            document.documentElement.setAttribute('data-theme', mode);
        }}
    }}

    function cycleTheme() {{
        // Xoay vòng: auto -> light -> dark -> auto
        const current = localStorage.getItem('themeMode') || 'auto';
        const order = ['auto', 'light', 'dark'];
        const next = order[(order.indexOf(current) + 1) % order.length];
        localStorage.setItem('themeMode', next);
        applyThemeMode(next);
        updateSettingsPanelTexts();
    }}

    function navigateTab(url, btn) {{
        if (btn && btn.classList.contains('active')) return;
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        if (btn) btn.classList.add('active');
        location.href = url;
    }}

    let scrollLockY = 0;
    let scrollLockCount = 0;

    function lockBodyScroll() {{
        if (scrollLockCount === 0) {{
            scrollLockY = window.scrollY;
            document.body.style.position = 'fixed';
            document.body.style.top = (-scrollLockY) + 'px';
            document.body.style.left = '0';
            document.body.style.right = '0';
            document.body.style.width = '100%';
        }}
        scrollLockCount++;
    }}

    function unlockBodyScroll() {{
        scrollLockCount = Math.max(0, scrollLockCount - 1);
        if (scrollLockCount === 0) {{
            document.body.style.position = '';
            document.body.style.top = '';
            document.body.style.left = '';
            document.body.style.right = '';
            document.body.style.width = '';
            window.scrollTo(0, scrollLockY);
        }}
    }}

    function toggleSettings() {{
        const panel = document.getElementById('settingsPanel');
        const overlay = document.getElementById('settingsOverlay');
        if (!panel || !overlay) return;
        const isOpen = panel.classList.contains('active');
        if (isOpen) {{
            closeSettings();
        }} else {{
            updateSettingsPanelTexts();
            lockBodyScroll();
            panel.classList.add('active');
            overlay.classList.add('active');
            // Huỷ auto-hide timer khi panel đang mở
            if (window._navAutoHideTimer) {{
                clearTimeout(window._navAutoHideTimer);
                window._navAutoHideTimer = null;
            }}
        }}
    }}

    function closeSettings() {{
        const panel = document.getElementById('settingsPanel');
        const overlay = document.getElementById('settingsOverlay');
        if (panel) panel.classList.remove('active');
        if (overlay) overlay.classList.remove('active');
        unlockBodyScroll();
        // Khởi động lại timer sau khi đóng panel
        if (window._navResetAutoHide) window._navResetAutoHide();
    }}

    // ──────────────────────────────────────────────
    // TÀI KHOẢN — cùng logic với index.html/shop.html/dashboard.html
    // ──────────────────────────────────────────────
    const SUPABASE_URL = "{supabase_url}";
    const SUPABASE_ANON_KEY = "{supabase_anon_key}";
    const _sb = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

    async function updateAccountUI() {{
        try {{
            const {{ data: {{ session }} }} = await _sb.auth.getSession();
            const sub = document.getElementById('accountSub');
            if (!sub) return;
            sub.textContent = session
                ? (session.user.email || 'Xem license & đơn hàng của bạn')
                : 'Đăng nhập / Đăng ký';
        }} catch (e) {{ /* im lặng nếu chưa cấu hình Supabase */ }}
    }}

    async function goAccount() {{
        const {{ data: {{ session }} }} = await _sb.auth.getSession();
        closeSettings();
        window.location.href = session ? './dashboard.html' : './auth.html';
    }}

    updateAccountUI();

    function updateSettingsPanelTexts() {{
        try {{
            const lang = getLang();
            const isVi = lang === 'vi';

            const el = id => document.getElementById(id);
            if (el('settingsTitle')) el('settingsTitle').textContent = isVi ? '⚙️ Cài đặt' : '⚙️ Settings';

            const themeMode = localStorage.getItem('themeMode') || 'auto';
            const themeIconMap = {{ 'auto': '🌓', 'light': '☀️', 'dark': '🌙' }};
            if (el('settingsThemeIcon')) el('settingsThemeIcon').textContent = themeIconMap[themeMode] || '🌓';
            if (el('settingsThemeTitle')) el('settingsThemeTitle').textContent = isVi ? 'Chủ đề' : 'Theme';
            const themeLabelVi = themeMode === 'auto' ? 'Auto' : (themeMode === 'dark' ? 'Tối' : 'Sáng');
            const themeLabelEn = themeMode === 'auto' ? 'Auto' : (themeMode === 'dark' ? 'Dark' : 'Light');
            if (el('settingsThemeSub')) el('settingsThemeSub').textContent = isVi ? themeLabelVi : themeLabelEn;

            if (el('settingsLangTitle')) el('settingsLangTitle').textContent = isVi ? 'Ngôn ngữ' : 'Language';
            if (el('settingsLangSub')) el('settingsLangSub').textContent = isVi ? 'Tiếng Việt' : 'English';
            if (el('settingsChatTitle')) el('settingsChatTitle').textContent = isVi ? 'Nhắn tin' : 'Message us';
            if (el('settingsChatSub')) el('settingsChatSub').textContent = isVi ? 'Tham gia kênh Telegram' : 'Join our Telegram channel';
            if (el('settingsDonateTitle')) el('settingsDonateTitle').textContent = 'Donate';
            if (el('settingsDonateSub')) el('settingsDonateSub').textContent = isVi ? 'Ủng hộ một ly cà phê ☕️' : 'Buy us a coffee ☕️';
            if (el('bannerTitle')) el('bannerTitle').textContent = t('banner_title');
        }} catch(e) {{
            console.warn('updateSettingsPanelTexts error:', e);
        }}
    }}

    // ════════════════════════════════════════════════════════════
    // STATE & CONSTANTS
    // ════════════════════════════════════════════════════════════
    let rawItems = [];
    let groupedItems = [];
    let filteredItems = [];
    let currentGroup = null;
    let selectedVersionIdx = 0;
    let versionManuallyPicked = false;
    let priceMap = {{}}; // bundleIdentifier -> {{ price_usd, price_vnd }} — sản phẩm có bán

    const PAGE_SIZE = 15;
    let currentPage = 0;

    let lightboxList = [];
    let lightboxIdx = 0;

    const DEFAULT_ICON = '{default_icon}';
    const DATA_KEY = '{data_key}';
    const REPO_TYPE = '{repo_type}';  // "apps", "tweaks", "dylibs"

    const DIGIT_EMOJI = ['0️⃣','1️⃣','2️⃣','3️⃣','4️⃣','5️⃣','6️⃣','7️⃣','8️⃣','9️⃣'];

    // ════════════════════════════════════════════════════════════
    // UTILITIES
    // ════════════════════════════════════════════════════════════
    function formatSize(bytes) {{
        if (!bytes || bytes <= 0) return 'Không rõ';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i];
    }}

    function showToast(msg) {{
        const t = document.getElementById('toast');
        t.textContent = msg;
        t.classList.add('show');
        setTimeout(() => t.classList.remove('show'), 2200);
    }}

    function toggleSection(sectionId) {{
        const el = document.getElementById(sectionId);
        if (el) el.classList.toggle('open');
    }}

    function parseVersion(v) {{
        return String(v || '0').split(/[.\\-_]/).map(x => parseInt(x) || 0);
    }}

    function compareVersions(a, b) {{
        const pa = parseVersion(a), pb = parseVersion(b);
        const len = Math.max(pa.length, pb.length);
        for (let i = 0; i < len; i++) {{
            const diff = (pb[i] || 0) - (pa[i] || 0);
            if (diff !== 0) return diff;
        }}
        return 0;
    }}

    // ════════════════════════════════════════════════════════════
    // GROUPING & UNIVERSAL BUNDLING
    // ════════════════════════════════════════════════════════════
    function groupByBundle(items) {{
        const map = new Map();

        items.forEach(raw => {{
            const bundleKey = raw.bundle || raw.bundleIdentifier || raw.bid ||
                               raw.Package || raw.package || raw.id || raw.name;
            if (!bundleKey) return;

            if (!map.has(bundleKey)) {{
                map.set(bundleKey, {{
                    name: raw.name || raw.Name || 'Unknown',
                    bundle: bundleKey,
                    icon: raw.icon || raw.iconURL || raw.Icon || DEFAULT_ICON,
                    desc: raw.desc || raw.description || raw.localizedDescription || raw.Description || '',
                    author: raw.author || raw.Author || 'Kyic Store',
                    provider: raw.provider || raw.developer || raw.seller || raw.publisher || '',
                    ageRating: raw.ageRating || raw.contentRating || raw.rating || '',
                    screenshots: raw.screenshots || raw.screenshotURLs || [],
                    permissions: raw.appPermissions || raw.permissions || {{}},
                    versions: []
                }});
            }}

            const group = map.get(bundleKey);
            const curDesc = raw.desc || raw.description || raw.localizedDescription || '';
            if (curDesc.length > (group.desc || '').length) {{
                group.desc = curDesc;
                group.icon = raw.icon || raw.iconURL || raw.Icon || group.icon;
            }}
            if ((raw.screenshots || raw.screenshotURLs || []).length > group.screenshots.length) {{
                group.screenshots = raw.screenshots || raw.screenshotURLs || [];
            }}

            // FIX: Một số nguồn dữ liệu (Feather/apps.json) đã gom sẵn toàn bộ
            // lịch sử phiên bản vào field `versions[]` lồng bên trong mỗi app
            // (mỗi bundle chỉ có 1 object `raw`, không phải 1 object/version
            // như Sileo/Dylib). Nếu đọc thẳng raw.version (số ít) như cũ thì
            // chỉ lấy được bản mới nhất — toàn bộ versions[] bị bỏ qua.
            // -> Phát hiện trường hợp này và duyệt qua từng phần tử versions[],
            //    kế thừa field cấp app rồi override bằng field cấp version.
            const nestedVersions = Array.isArray(raw.versions) && raw.versions.length > 0
                ? raw.versions.map(v => Object.assign({{}}, raw, v))
                : [raw];

            nestedVersions.forEach(verRaw => {{
                const arch = verRaw.architecture || verRaw.Architecture || verRaw.arch || '';
                const ver = verRaw.version || verRaw.Version || verRaw.ver || '1.0';
                const dlUrl = verRaw.downloadURL || verRaw.dl || verRaw.url || verRaw.download || verRaw.downloadUrl || '';

                const exists = group.versions.find(v => v.version === ver && v.arch === arch && v.downloadURL === dlUrl);
                if (!exists) {{
                    // displayVersion: tách arch suffix ra khỏi version string để hiển thị label đúng.
                    // dylib_engine dùng composite version ("1.4.3-arm") để Feather phân biệt arch,
                    // nhưng views.py chỉ cần số version thuần ("1.4.3") cho label.
                    // Ưu tiên field ver (nếu có) → fallback strip "-arm/arm64/arm64e" từ cuối.
                    const displayVer = verRaw.ver || verRaw.displayVersion ||
                        ver.replace(/-(arm64e|arm64|armv7s|armv7|arm)(\.[a-z0-9]+)*$/i, '');
                    group.versions.push({{
                        version: ver,
                        displayVersion: displayVer,
                        arch: arch,
                        size: verRaw.size || 0,
                        downloadURL: dlUrl,
                        filename: verRaw.filename || verRaw.name || '',
                        date: verRaw.date || verRaw.releaseDate || verRaw.pubDate || '',
                        note: verRaw.changelog || verRaw.releaseNotes || verRaw.whatsNew || verRaw['Whats New'] || verRaw.localizedDescription || '',
                        section: verRaw.section || verRaw.Section || '',
                        installedSize: verRaw.installedSize || verRaw['Installed-Size'] || verRaw.installed_size || '',
                        compatibilityRaw: verRaw.compatibility || verRaw.Compatibility || verRaw.minVersion || '',
                        depends: verRaw.depends || verRaw.Depends || '',
                        devices: verRaw.devices || verRaw.supportedDevices || verRaw.Devices || '',
                        minOS: verRaw.minOSVersion || verRaw.minIOSVersion || verRaw.minOS || '',
                        maxOS: verRaw.maxOSVersion || verRaw.maxIOSVersion || verRaw.maxOS || '',
                        jbVersion: verRaw.jailbreakVersion || verRaw.jbVersion || verRaw.minJailbreak || '',
                        jbTool: verRaw.jailbreakTool || verRaw.jbTool || verRaw.tool || ''
                    }});
                }}
            }});
        }});

        const result = Array.from(map.values());
        result.forEach(g => {{
            g.versions.sort((a, b) => compareVersions(a.version, b.version) || a.arch.localeCompare(b.arch));
        }});
        result.sort((a, b) => a.name.localeCompare(b.name));
        return result;
    }}

    // ════════════════════════════════════════════════════════════
    // LOẠI TỆP — scan filename/downloadURL/bundle để xác định nền tảng
    // (iOS/macOS) và kiến trúc (arm/arm64/arm64e) thực tế, thay vì chỉ
    // đọc field có sẵn trong JSON (có thể thiếu hoặc không chính xác).
    // ════════════════════════════════════════════════════════════
    function detectFileExt(version) {{
        const src = ((version?.filename || '') + ' ' + (version?.downloadURL || '')).toLowerCase();
        const match = src.match(/\\.(ipa|deb|dylib|zip|tar|tipa)(\\?|$|[\\s"'])/);
        if (match) return match[1];
        const repoType = REPO_TYPE || 'apps';
        if (repoType === 'tweaks') return 'deb';
        if (repoType === 'dylibs') return 'dylib';
        return 'ipa';
    }}

    function detectPlatform(group, version) {{
        const src = ((version?.filename || '') + ' ' + (version?.downloadURL || '') + ' ' +
                     (group?.bundle || '') + ' ' + (group?.name || '')).toLowerCase();
        if (/(^|[^a-z0-9])(macos|osx|darwin|mac)([^a-z0-9]|$)/.test(src)) return 'mac';
        return 'ios';
    }}

    function detectArch(version) {{
        const src = ((version?.arch || '') + ' ' + (version?.filename || '') + ' ' +
                     (version?.downloadURL || '')).toLowerCase();
        const archPattern = /(^|[^a-z0-9])(arm64e|arm64|armv7s|armv7|arm)([^a-z0-9]|$)/g;
        const found = [];
        let m;
        while ((m = archPattern.exec(src)) !== null) {{
            let token = m[2];
            if (token === 'armv7s' || token === 'armv7') token = 'arm';
            if (!found.includes(token)) found.push(token);
            archPattern.lastIndex = m.index + m[1].length + token.length;
        }}
        if (found.length === 0) {{
            if (version?.arch && version.arch !== 'universal') return version.arch;
            return 'universal';
        }}
        return found.join('_');
    }}

    function getCategory(group, version) {{
        const repoType = REPO_TYPE || 'apps';
        const ext = detectFileExt(version);

        if (repoType === 'apps') {{
            const platform = detectPlatform(group, version);
            return platform + '-' + ext;
        }}
        const arch = detectArch(version);
        return arch + '-' + ext;
    }}

    // ════════════════════════════════════════════════════════════
    // TƯƠNG THÍCH — hợp nhất kiểu App Store (thiết bị + phiên bản iOS)
    // cho Apps, và kiểu Sileo/Cydia (thiết bị + phiên bản Jailbreak +
    // công cụ Jailbreak) cho Tweaks/Dylibs. Fallback về dữ liệu Debian
    // gốc (compatibilityRaw) khi JSON nguồn không có field chi tiết hơn.
    // ════════════════════════════════════════════════════════════
    function buildCompatibilityText(version) {{
        const repoType = REPO_TYPE || 'apps';
        const parts = [];

        if (version.devices) parts.push(version.devices);
        else parts.push(repoType === 'apps' ? 'iPhone, iPad' : 'Thiết bị jailbreak');

        if (repoType === 'apps') {{
            if (version.minOS) {{
                parts.push('yêu cầu iOS ' + version.minOS + (version.maxOS ? ' – ' + version.maxOS : '+'));
            }}
        }} else {{
            if (version.jbVersion) parts.push('iOS ' + version.jbVersion);
            if (version.jbTool) parts.push(version.jbTool);
        }}

        if (parts.length <= 1 && version.compatibilityRaw) {{
            return version.compatibilityRaw;
        }}
        if (parts.length <= 1) return '';
        return parts.join(' • ');
    }}

    // ════════════════════════════════════════════════════════════
    // SEARCH & PAGINATION
    // ════════════════════════════════════════════════════════════
    function onSearchInput() {{
        currentPage = 0;
        const clearBtn = document.getElementById('searchClear');
        const hasText = (document.getElementById('searchInput').value || '').length > 0;
        if (clearBtn) clearBtn.style.display = hasText ? 'flex' : 'none';
        renderList();
    }}

    function clearSearch() {{
        const input = document.getElementById('searchInput');
        input.value = '';
        input.focus();
        document.getElementById('searchClear').style.display = 'none';
        currentPage = 0;
        renderList();
    }}

    // Khoảng cách Levenshtein — dùng để chấm điểm "gần đúng" cho tìm kiếm mờ (fuzzy)
    function levenshtein(a, b) {{
        if (a === b) return 0;
        if (!a.length) return b.length;
        if (!b.length) return a.length;
        const prev = new Array(b.length + 1);
        const curr = new Array(b.length + 1);
        for (let j = 0; j <= b.length; j++) prev[j] = j;
        for (let i = 1; i <= a.length; i++) {{
            curr[0] = i;
            for (let j = 1; j <= b.length; j++) {{
                const cost = a[i - 1] === b[j - 1] ? 0 : 1;
                curr[j] = Math.min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost);
            }}
            for (let j = 0; j <= b.length; j++) prev[j] = curr[j];
        }}
        return prev[b.length];
    }}

    // Kiểm tra "gần đúng": khớp chuỗi con (ưu tiên cao) hoặc khoảng cách Levenshtein
    // trên từng từ đủ nhỏ so với độ dài từ (cho phép gõ sai vài ký tự / thiếu dấu).
    function fuzzyMatch(text, query) {{
        if (!query) return true;
        text = text.toLowerCase();
        query = query.toLowerCase().trim();
        if (!query) return true;

        if (text.includes(query)) return true;

        const words = text.split(/\\s+/);
        const threshold = query.length <= 4 ? 1 : (query.length <= 8 ? 2 : 3);

        for (const w of words) {{
            if (w.startsWith(query.slice(0, Math.max(1, query.length - threshold)))) return true;
            if (levenshtein(w, query) <= threshold) return true;
        }}

        // So khớp cả câu rút gọn (bỏ khoảng trắng) cho trường hợp gõ liền không dấu cách
        const compact = text.replace(/\\s+/g, '');
        if (compact.includes(query.replace(/\\s+/g, ''))) return true;

        return false;
    }}

    function applyFilter() {{
        const query = (document.getElementById('searchInput').value || '').trim();
        if (!query) {{
            filteredItems = groupedItems;
            return;
        }}
        filteredItems = groupedItems.filter(g =>
            fuzzyMatch(g.name || '', query) || fuzzyMatch(g.bundle || '', query)
        );
    }}

    function totalPages() {{
        return Math.max(1, Math.ceil(filteredItems.length / PAGE_SIZE));
    }}

    // ════════════════════════════════════════════════════════════
    // RENDER LIST
    // ════════════════════════════════════════════════════════════
    function renderList() {{
        applyFilter();

        if (filteredItems.length === 0) {{
            document.getElementById('list').innerHTML =
                '<div class="empty-state">' + t('no_results') + '</div>';
            document.getElementById('pagination').style.display = 'none';
            return;
        }}

        const pages = totalPages();
        if (currentPage >= pages) currentPage = pages - 1;
        if (currentPage < 0) currentPage = 0;

        const start = currentPage * PAGE_SIZE;
        const pageItems = filteredItems.slice(start, start + PAGE_SIZE);

        const html = pageItems.map((g, i) => {{
            const idx = groupedItems.indexOf(g);
            const latest = g.versions[0] || {{}};
            const priceInfo = priceMap[g.bundle]; // có bán = có trong DB
            let actionBtn;
            if (priceInfo) {{
                const priceLabel = priceInfo.price_usd ? '$' + priceInfo.price_usd
                    : (priceInfo.price_vnd ? Number(priceInfo.price_vnd).toLocaleString('vi-VN') + '₫' : 'Mua');
                actionBtn = `<button class="item-action item-action-buy" id="quickbtn-${{idx}}"
                    onclick="event.stopPropagation(); addToCart('${{g.bundle}}', this)">${{priceLabel}}</button>`;
            }} else {{
                actionBtn = `<button class="item-action" id="quickbtn-${{idx}}" onclick="event.stopPropagation(); openVersionPopover(${{idx}}, this)">Nhận</button>`;
            }}
            return `
                <div class="item" style="--item-i:${{i}}" onclick="openModal(${{idx}})">
                    <img class="item-icon" src="${{g.icon}}" alt="${{g.name}}" loading="lazy" onerror="this.onerror=null;this.src='${{DEFAULT_ICON}}'">
                    <div class="item-info">
                        <div class="item-name">${{g.name}}</div>
                        <div class="item-id">${{g.bundle}}</div>
                        <div class="item-version">v${{latest.version || '1.0'}}${{g.versions.length > 1 ? ' · ' + g.versions.length + ' bản' : ''}}</div>
                    </div>
                    ${{actionBtn}}
                </div>
            `;
        }}).join('');

        document.getElementById('list').innerHTML = html;
        window.scrollTo({{ top: document.querySelector('.container').offsetTop - 8, behavior: 'instant' }});

        renderPagination();
    }}

    // ────────────────────────────────────────────────────────
    // THÊM VÀO GIỎ HÀNG (sản phẩm có bán) — quản lý chính ở dashboard.html
    // ────────────────────────────────────────────────────────
    async function addToCart(bundleId, btnEl) {{
        const {{ data: {{ session }} }} = await _sb.auth.getSession();
        if (!session) {{
            if (confirm('Cần đăng nhập để mua hàng. Đăng nhập ngay?')) {{
                window.location.href = './auth.html';
            }}
            return;
        }}
        const original = btnEl.textContent;
        btnEl.textContent = '⏳...';
        btnEl.style.pointerEvents = 'none';
        const {{ error }} = await _sb.from('cart_items')
            .upsert({{ user_id: session.user.id, product_id: bundleId }}, {{ onConflict: 'user_id,product_id' }});
        btnEl.style.pointerEvents = '';
        if (error) {{
            btnEl.textContent = original;
            alert('❌ Lỗi thêm giỏ hàng: ' + error.message);
        }} else {{
            btnEl.textContent = '✅ Đã thêm';
            setTimeout(() => {{ btnEl.textContent = original; }}, 1800);
        }}
    }}

    function renderPagination() {{
        const pages = totalPages();
        const pag = document.getElementById('pagination');

        if (pages <= 1) {{
            pag.style.display = 'none';
            return;
        }}
        pag.style.display = 'flex';

        const windowSize = 10;
        let windowStart = Math.max(0, currentPage - Math.floor(windowSize / 2));
        let windowEnd = Math.min(pages, windowStart + windowSize);
        windowStart = Math.max(0, windowEnd - windowSize);

        let html = `<button class="page-btn" onclick="goToPage(${{currentPage - 1}})" ${{currentPage === 0 ? 'disabled' : ''}}>◀️</button>`;

        for (let p = windowStart; p < windowEnd; p++) {{
            const digit = DIGIT_EMOJI[p % 10];
            html += `<button class="page-btn ${{p === currentPage ? 'active' : ''}}" onclick="goToPage(${{p}})">${{digit}}</button>`;
        }}

        html += `<button class="page-btn" onclick="goToPage(${{currentPage + 1}})" ${{currentPage >= pages - 1 ? 'disabled' : ''}}>▶️</button>`;
        html += `<div class="page-info">` + t('page') + ` ${{currentPage + 1}} / ${{pages}} · ${{filteredItems.length}} ` + t('results') + `</div>`;

        pag.innerHTML = html;
    }}

    function goToPage(p) {{
        const pages = totalPages();
        if (p < 0 || p >= pages) return;
        currentPage = p;
        renderList();
    }}

    // ════════════════════════════════════════════════════════════
    // MODAL
    // ════════════════════════════════════════════════════════════
    function openModal(idx) {{
        currentGroup = groupedItems[idx];
        if (!currentGroup) return;
        selectedVersionIdx = 0;
        versionManuallyPicked = false;

        document.getElementById('modalIcon').src = currentGroup.icon;
        document.getElementById('modalIcon').onerror = function() {{ this.onerror = null; this.src = DEFAULT_ICON; }};
        document.getElementById('modalName').textContent = currentGroup.name;
        document.getElementById('modalId').textContent = currentGroup.bundle;

        // Description
        const descSection = document.getElementById('descSection');
        if (currentGroup.desc) {{
            descSection.style.display = 'block';
            descSection.classList.remove('open');
            document.getElementById('modalDesc').textContent = currentGroup.desc;
        }} else {{
            descSection.style.display = 'none';
        }}

        // Có gì mới — nội dung theo phiên bản đang chọn, cập nhật
        // trong updateSelectedVersionDisplay() mỗi khi người dùng đổi phiên bản.
        // Thu gọn/mở rộng giống hệt section Mô tả (đóng mặc định khi mở modal).
        const changelogBox = document.getElementById('changelogBox');
        const hasAnyChangelog = (currentGroup.versions || []).some(v => v.note);
        if (hasAnyChangelog) {{
            changelogBox.style.display = 'block';
            changelogBox.classList.remove('open');
        }} else {{
            changelogBox.style.display = 'none';
        }}

        // Nút chọn phiên bản (thanh hành động cố định đáy modal)
        const versionPickerBtn = document.getElementById('versionPickerBtn');
        if (currentGroup.versions && currentGroup.versions.length > 0) {{
            versionPickerBtn.style.display = '';
        }} else {{
            versionPickerBtn.style.display = 'none';
        }}

        // Screenshots
        if (currentGroup.screenshots && currentGroup.screenshots.length > 0) {{
            lightboxList = currentGroup.screenshots;
            document.getElementById('screenshotsSection').style.display = 'block';
            document.getElementById('screenshots').innerHTML = currentGroup.screenshots.map((s, i) =>
                `<img class="screenshot" src="${{s}}" alt="Screenshot" loading="lazy" onclick="openLightbox(${{i}})" onerror="this.style.display='none'">`
            ).join('');
        }} else {{
            lightboxList = [];
            document.getElementById('screenshotsSection').style.display = 'none';
        }}

        // Permissions
        const permSection = document.getElementById('permSection');
        const permKeys = Object.keys(currentGroup.permissions || {{}});
        if (permKeys.length > 0) {{
            permSection.style.display = 'block';
            permSection.classList.remove('open');
            document.getElementById('permissions').innerHTML = permKeys.map(k =>
                `<div class="permission-item">${{k}}</div>`
            ).join('');
        }} else {{
            permSection.style.display = 'none';
        }}

        updateSelectedVersionDisplay();

        const scrollBody = document.querySelector('.modal-scroll-body');
        if (scrollBody) scrollBody.scrollTop = 0;

        lockBodyScroll();
        document.getElementById('modal').classList.add('active');
    }}

    // Phiên bản — danh sách để chọn tải
    // ════════════════════════════════════════════════════════════
    // VERSION PICKER (MODAL) — panel trượt từ phải, dùng cho nút [Version] trong modal
    // ════════════════════════════════════════════════════════════
    function openVersionPicker() {{
        const group = currentGroup;
        if (!group || !group.versions || group.versions.length === 0) {{
            showToast(t('no_version'));
            return;
        }}

        document.getElementById('versionPickerTitle').textContent = '✨ ' + group.name;
        const html = group.versions.map((v, i) => {{
            const label = 'v' + (v.displayVersion || v.version) + ' - ' + getCategory(group, v);
            return `
                <div class="version-picker-item ${{i === selectedVersionIdx ? 'selected' : ''}}" onclick="pickModalVersion(${{i}})">
                    <div class="version-picker-label">${{label}}</div>
                    <div class="version-picker-check">✓</div>
                </div>
            `;
        }}).join('');
        document.getElementById('versionPickerList').innerHTML = html;

        lockBodyScroll();
        document.getElementById('versionPickerPanel').classList.add('active');
        document.getElementById('versionPickerOverlay').classList.add('active');
    }}

    function closeVersionPicker() {{
        document.getElementById('versionPickerPanel').classList.remove('active');
        document.getElementById('versionPickerOverlay').classList.remove('active');
        unlockBodyScroll();
        // Reset search
        const searchBox = document.getElementById('versionPickerSearchBox');
        const searchInput = document.getElementById('versionPickerSearchInput');
        if (searchBox) {{ searchBox.style.display = 'none'; }}
        if (searchInput) {{ searchInput.value = ''; filterVersionPickerList(); }}
    }}

    function pickModalVersion(i) {{
        if (!currentGroup || !currentGroup.versions[i]) return;
        selectedVersionIdx = i;
        versionManuallyPicked = true;
        updateSelectedVersionDisplay();
        closeVersionPicker();
    }}

    // ════════════════════════════════════════════════════════════
    // VERSION POPOVER (LIST) — modal căn giữa, dùng cho nút "Nhận" trong list
    // ════════════════════════════════════════════════════════════
    let popoverGroup = null;
    let popoverListIdx = null;

    function openVersionPopover(idx, btnEl) {{
        const group = groupedItems[idx];
        if (!group || !group.versions || group.versions.length === 0) {{
            showToast(t('no_version'));
            return;
        }}

        // Nếu nav đang ẩn (item nằm khuất dưới do đã cuộn xuống), bật nav hiện lại
        // ngay lập tức cùng lúc popover mở ra, tránh độ trễ gây cảm giác giật/lệch.
        const navShell = document.getElementById('navShell');
        if (navShell) navShell.classList.remove('nav-hidden');

        popoverGroup = group;
        popoverListIdx = idx;

        // FIX: Tiêu đề popup = tên app vừa nhấn "Nhận", giúp rõ ràng đang chọn
        // phiên bản cho app nào (đặc biệt hữu ích khi danh sách dài, dễ nhầm).
        document.getElementById('versionPopoverTitle').textContent = '✨ ' + group.name;

        const html = group.versions.map((v, i) => {{
            const label = 'v' + (v.displayVersion || v.version) + ' - ' + getCategory(group, v);
            return `
                <div class="version-picker-item ${{i === 0 ? 'selected' : ''}}" onclick="pickPopoverVersion(${{i}})">
                    <div class="version-picker-label">${{label}}</div>
                    <div class="version-picker-check">✓</div>
                </div>
            `;
        }}).join('');
        document.getElementById('versionPopoverList').innerHTML = html;

        lockBodyScroll();
        document.getElementById('versionPopover').classList.add('active');
        document.getElementById('versionPopoverOverlay').classList.add('active');
    }}

    function closeVersionPopover() {{
        document.getElementById('versionPopover').classList.remove('active');
        document.getElementById('versionPopoverOverlay').classList.remove('active');
        document.getElementById('versionPopoverSearchBox').style.display = 'none';
        document.getElementById('versionPopoverSearchInput').value = '';
        unlockBodyScroll();
    }}

    function pickPopoverVersion(i) {{
        const group = popoverGroup;
        const v = group.versions[i];
        if (!v) return;
        closeVersionPopover();
        openConfirmDownload(group, v, document.getElementById('quickbtn-' + popoverListIdx));
    }}

    // ════════════════════════════════════════════════════════════
    // CONFIRM DOWNLOAD DIALOG
    // ════════════════════════════════════════════════════════════
    let confirmDownloadData = null;

    function openConfirmDownload(group, version, btnEl) {{
        const label = 'v' + (version.displayVersion || version.version) + ' - ' + getCategory(group, version);
        document.getElementById('confirmTitle').textContent = t('download_confirm');
        document.getElementById('confirmMessage').textContent =
            group.name + ' — ' + label + (version.size ? ' (' + formatSize(version.size) + ')' : '');

        confirmDownloadData = {{ group, version, btnEl }};

        lockBodyScroll();
        document.getElementById('confirmDialog').classList.add('active');
        document.getElementById('confirmOverlay').classList.add('active');
    }}

    function closeConfirmDownload() {{
        document.getElementById('confirmDialog').classList.remove('active');
        document.getElementById('confirmOverlay').classList.remove('active');
        unlockBodyScroll();
        confirmDownloadData = null;
    }}

    function buildDownloadFilename(group, version) {{
        // FIX: Apps tải đúng tên tệp đầy đủ (vd "BiliBili_2.70.0.ipa") vì
        // downloadURL của GitHub Release LUÔN có tên tệp gốc ở cuối path,
        // và trình duyệt ưu tiên lấy tên đó. Tweaks/Dylibs lại hay dùng URL
        // cùng domain (2kgt.github.io) — same-origin khiến trình duyệt tôn
        // trọng tên do JS tự đặt qua thuộc tính `download`, mà tên đó trước
        // đây bị tự chế ("Tên_vPhiênBản", thiếu đuôi/rút gọn) do
        // version.filename không tồn tại trong dữ liệu. Cách thống nhất và
        // đúng nhất cho cả 3 loại: LUÔN lấy tên thật từ chính downloadURL
        // (đoạn cuối cùng của URL path, đã decode %xx), y hệt cách trình
        // duyệt tự làm với link cross-origin — đảm bảo Apps/Tweaks/Dylibs
        // đều tải về đúng tên tệp gốc đầy đủ kèm đuôi.
        try {{
            const u = new URL(version.downloadURL, window.location.href);
            const last = decodeURIComponent(u.pathname.split('/').pop() || '');
            if (last && last.includes('.')) return last;
        }} catch (e) {{ /* downloadURL không hợp lệ -> rơi xuống fallback bên dưới */ }}

        const base = group.name + '_v' + version.version;
        const ext = detectFileExt(version);
        return base + '.' + ext;
    }}

    function confirmDownloadProceed() {{
        if (!confirmDownloadData) return;
        const {{ group, version, btnEl }} = confirmDownloadData;
        const filename = buildDownloadFilename(group, version);

        document.getElementById('confirmDialog').classList.remove('active');
        document.getElementById('confirmOverlay').classList.remove('active');
        unlockBodyScroll();

        triggerDownload(version.downloadURL, filename, btnEl);
        confirmDownloadData = null;
    }}

    function setInfoRow(rowId, valueId, value) {{
        const row = document.getElementById(rowId);
        const el = document.getElementById(valueId);
        if (value === undefined || value === null || value === '') {{
            row.style.display = 'none';
            return;
        }}
        row.style.display = '';
        el.textContent = value;
    }}

    function updateSelectedVersionDisplay() {{
        const v = currentGroup.versions[selectedVersionIdx] || {{}};
        document.getElementById('modalVersion').textContent = 'v' + (v.version || '1.0');

        const versionPickerLabel = document.getElementById('versionPickerLabel');
        if (versionPickerLabel) {{
            versionPickerLabel.textContent = versionManuallyPicked ? ('v' + (v.version || '1.0')) : 'Version';
        }}

        setInfoRow('rowAuthor', 'infoAuthor', currentGroup.author);
        setInfoRow('rowProvider', 'infoProvider', currentGroup.provider);
        setInfoRow('rowAgeRating', 'infoAgeRating', currentGroup.ageRating);
        setInfoRow('rowSection', 'infoSection', v.section);
        setInfoRow('rowVersion', 'infoVersion', v.version || '1.0');
        setInfoRow('rowCategory', 'infoCategory', getCategory(currentGroup, v));
        setInfoRow('rowArch', 'infoArch', v.arch);
        setInfoRow('rowSize', 'infoSize', v.size ? formatSize(v.size) : '');
        setInfoRow('rowInstalledSize', 'infoInstalledSize', v.installedSize);
        setInfoRow('rowCompat', 'infoCompat', buildCompatibilityText(v));
        setInfoRow('rowDepends', 'infoDepends', v.depends);
        setInfoRow('rowBundleId', 'infoBundleId', currentGroup.bundle);
        setInfoRow('rowUpdateDate', 'infoUpdateDate', v.date);

        const modalChangelog = document.getElementById('modalChangelog');
        if (modalChangelog) {{
            modalChangelog.textContent = v.note || t('no_changelog');
        }}
    }}

    function closeModal(e) {{
        if (e && e.target.id !== 'modal') return;
        document.getElementById('modal').classList.remove('active');
        currentGroup = null;
        unlockBodyScroll();
    }}

    // ════════════════════════════════════════════════════════════
    // LIGHTBOX
    // ════════════════════════════════════════════════════════════
    let touchStartX = 0;

    function openLightbox(i) {{
        if (!lightboxList.length) return;
        lightboxIdx = i;
        updateLightboxImg();
        document.getElementById('lightbox').classList.add('active');
    }}

    function closeLightbox() {{
        document.getElementById('lightbox').classList.remove('active');
    }}

    function lightboxBackdropClick(e) {{
        if (e.target.id === 'lightbox') closeLightbox();
    }}

    function lightboxNav(dir, e) {{
        if (e) e.stopPropagation();
        if (!lightboxList.length) return;
        lightboxIdx = (lightboxIdx + dir + lightboxList.length) % lightboxList.length;
        updateLightboxImg();
    }}

    function updateLightboxImg() {{
        document.getElementById('lightboxImg').src = lightboxList[lightboxIdx];
        document.getElementById('lightboxCounter').textContent = (lightboxIdx + 1) + ' / ' + lightboxList.length;
    }}

    document.getElementById('lightbox').addEventListener('touchstart', e => {{
        touchStartX = e.changedTouches[0].screenX;
    }}, {{ passive: true }});

    document.getElementById('lightbox').addEventListener('touchend', e => {{
        const dx = e.changedTouches[0].screenX - touchStartX;
        if (Math.abs(dx) > 40) {{
            lightboxNav(dx > 0 ? -1 : 1);
        }}
    }}, {{ passive: true }});

    // ════════════════════════════════════════════════════════════
    // DOWNLOAD
    // ════════════════════════════════════════════════════════════
    function triggerDownload(url, filename, btnEl) {{
        if (!url) {{
            showToast(t('no_link'));
            return;
        }}

        // FIX: Trước đây dùng fetch() + blob để tải, nhưng fetch() đòi hỏi
        // CORS header từ server. File local (2kgt.github.io, cùng origin)
        // thì fetch được, nhưng file GitHub Release (github.com/.../releases/
        // download/...) KHÔNG trả CORS header cho fetch cross-origin -> fetch
        // luôn lỗi -> rơi vào catch -> fallback cũ điều hướng cả trang sang
        // url đó ("nhảy trang"). Giờ bỏ hẳn fetch/blob: dùng thẳng thẻ
        // <a href=url download> rồi click. Cách này không cần đọc nội dung
        // file qua JS nên không bị CORS chặn — browser tự xử lý tải xuống
        // (kể cả với GitHub Release, vốn đã trả đúng header
        // Content-Disposition: attachment cho asset thật), hoạt động đúng
        // cho cả file local lẫn file cloud, không còn nhảy trang.
        const originalText = btnEl ? btnEl.textContent : null;
        if (btnEl) {{ btnEl.textContent = t('download_start'); btnEl.classList.add('loading'); }}

        try {{
            const a = document.createElement('a');
            a.href = url;
            a.download = filename || 'download';
            a.rel = 'noopener';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            showToast(t('download_success'));
        }} catch (err) {{
            console.warn('Download failed:', err);
            showToast('❌ Tải thất bại: ' + (err && err.message ? err.message : 'Lỗi không xác định'));
        }} finally {{
            if (btnEl) {{ btnEl.textContent = originalText; btnEl.classList.remove('loading'); }}
        }}
    }}

    function downloadSelected() {{
        if (!currentGroup) return;
        const v = currentGroup.versions[selectedVersionIdx];
        if (!v) {{ showToast(t('no_version')); return; }}
        const filename = buildDownloadFilename(currentGroup, v);
        triggerDownload(v.downloadURL, filename, document.getElementById('downloadBtn'));
    }}

    function copySelected() {{
        if (!currentGroup) return;
        const v = currentGroup.versions[selectedVersionIdx];
        if (!v || !v.downloadURL) {{ showToast(t('no_results_copy')); return; }}
        navigator.clipboard.writeText(v.downloadURL).then(() => {{
            showToast(t('copy_success'));
        }}).catch(() => {{
            showToast(t('copy_error'));
        }});
    }}

    // ════════════════════════════════════════════════════════════
    // VERSION POPOVER SEARCH FUNCTIONALITY
    // ════════════════════════════════════════════════════════════
    function toggleVersionPopoverSearch() {{
        const searchBox = document.getElementById('versionPopoverSearchBox');
        const searchInput = document.getElementById('versionPopoverSearchInput');
        if (searchBox.style.display === 'none') {{
            searchBox.style.display = 'flex';
            searchInput.focus();
        }} else {{
            searchBox.style.display = 'none';
            clearVersionPopoverSearch();
        }}
    }}

    function clearVersionPopoverSearch() {{
        const searchInput = document.getElementById('versionPopoverSearchInput');
        searchInput.value = '';
        filterVersionPopoverList();
    }}

    function filterVersionPopoverList() {{
        const searchText = document.getElementById('versionPopoverSearchInput').value.toLowerCase();
        const items = document.querySelectorAll('.version-popover .version-picker-item');
        items.forEach(item => {{
            const label = item.querySelector('.version-picker-label')?.textContent || '';
            if (label.toLowerCase().includes(searchText)) {{
                item.style.display = '';
            }} else {{
                item.style.display = 'none';
            }}
        }});
    }}

    // ════════════════════════════════════════════════════════════
    // VERSION PICKER SEARCH FUNCTIONALITY
    // ════════════════════════════════════════════════════════════
    function toggleVersionPickerSearch() {{
        const searchBox = document.getElementById('versionPickerSearchBox');
        const searchInput = document.getElementById('versionPickerSearchInput');
        if (searchBox.style.display === 'none') {{
            searchBox.style.display = 'flex';
            searchInput.focus();
        }} else {{
            searchBox.style.display = 'none';
            clearVersionPickerSearch();
        }}
    }}

    function clearVersionPickerSearch() {{
        const searchInput = document.getElementById('versionPickerSearchInput');
        searchInput.value = '';
        filterVersionPickerList();
    }}

    function filterVersionPickerList() {{
        const searchText = document.getElementById('versionPickerSearchInput').value.toLowerCase();
        const items = document.querySelectorAll('#versionPickerList .version-picker-item');
        items.forEach(item => {{
            const label = item.querySelector('.version-picker-label')?.textContent || '';
            if (label.toLowerCase().includes(searchText)) {{
                item.style.display = '';
            }} else {{
                item.style.display = 'none';
            }}
        }});
    }}

    // ════════════════════════════════════════════════════════════
    // LOAD DATA
    // ════════════════════════════════════════════════════════════
    async function loadData() {{
        try {{
            const res = await fetch('{json_path}');
            const data = await res.json();
            const items = data[DATA_KEY];
            rawItems = Array.isArray(items) ? items : Object.values(items || {{}});

            // Tải giá sản phẩm riêng (không chặn catalog nếu lỗi)
            priceMap = {{}};
            try {{
                const dbResult = await _sb.from('products').select('id,price_usd,price_vnd');
                (dbResult?.data || []).forEach(p => {{ priceMap[p.id] = p; }});
            }} catch (e2) {{ /* im lặng, danh sách vẫn hiện bình thường không có giá */ }}

            groupedItems = groupByBundle(rawItems);

            if (groupedItems.length === 0) {{
                document.getElementById('list').innerHTML =
                    '<div class="empty-state">' + t('no_data') + '</div>';
                return;
            }}

            currentPage = 0;
            renderList();
        }} catch (e) {{
            document.getElementById('list').innerHTML =
                '<div class="empty-state" style="color:#ff6b6b;">' + t('error') + e.message + '</div>';
        }}
    }}

    // ════════════════════════════════════════════════════════════
    // NAV SHELL + BANNER SLIDE
    // - Tự động ẩn nav sau 3 giây không tương tác
    // - Khi nav ẩn: banner trượt mượt lên lấp chỗ (hiệu ứng cuốn lịch lật)
    // - Khi cuộn xuống: nav ẩn ngay + banner trượt lên
    // - Khi cuộn lên / chạm màn hình: nav hiện lại + banner trượt xuống
    // - Timer 3s reset mỗi khi có tương tác (cuộn, chạm)
    // ════════════════════════════════════════════════════════════
    (function setupNavAutoHide() {{
        const navShell = document.getElementById('navShell');
        if (!navShell) return;

        let lastScrollY = window.scrollY;
        let isHidden = false;
        let ticking = false;
        let autoHideTimer = null;
        const TOP_THRESHOLD = 12;
        const SHOW_DELTA = 4;
        const AUTO_HIDE_DELAY = 3000;

        function setNavHidden(hidden) {{
            if (isHidden === hidden) return;
            isHidden = hidden;
            if (hidden) {{
                navShell.classList.remove('nav-showing');
                navShell.classList.add('nav-hidden');
            }} else {{
                navShell.classList.add('nav-showing');
                navShell.classList.remove('nav-hidden');
            }}
        }}

        function resetAutoHideTimer() {{
            if (autoHideTimer) clearTimeout(autoHideTimer);
            autoHideTimer = setTimeout(() => {{
                setNavHidden(true);
            }}, AUTO_HIDE_DELAY);
            window._navAutoHideTimer = autoHideTimer;
        }}

        // Expose để closeSettings có thể reset timer
        window._navResetAutoHide = resetAutoHideTimer;

        function showNavTemporarily() {{
            setNavHidden(false);
            resetAutoHideTimer();
        }}

        function onScroll() {{
            const currentY = Math.max(0, window.scrollY);
            const delta = currentY - lastScrollY;

            if (currentY <= TOP_THRESHOLD) {{
                showNavTemporarily();
            }} else if (delta <= -SHOW_DELTA) {{
                showNavTemporarily();
            }} else if (delta > 0) {{
                if (autoHideTimer) clearTimeout(autoHideTimer);
                setNavHidden(true);
            }}

            lastScrollY = currentY;
            ticking = false;
        }}

        window.addEventListener('scroll', () => {{
            if (!ticking) {{
                window.requestAnimationFrame(onScroll);
                ticking = true;
            }}
        }}, {{ passive: true }});

        // Chạm vào màn hình → hiện nav + reset timer 3s
        document.addEventListener('touchstart', () => {{
            showNavTemporarily();
        }}, {{ passive: true }});

        // Khởi động timer ngay khi trang load
        resetAutoHideTimer();
    }})();

    // ════════════════════════════════════════════════════════════
    // INIT
    // ════════════════════════════════════════════════════════════
    initTheme();

    const saved_lang = localStorage.getItem('lang');
    if (saved_lang) {{
        document.documentElement.setAttribute('data-lang', saved_lang);
    }}

    // Luôn gọi sau mỗi lần load để đảm bảo text khớp ngôn ngữ hiện tại
    updateSettingsPanelTexts();

    if (sessionStorage.getItem('reopenSettings') === '1') {{
        sessionStorage.removeItem('reopenSettings');
        document.getElementById('settingsPanel').classList.add('active');
        document.getElementById('settingsOverlay').classList.add('active');
    }}

    loadData();
</script>

</body>
</html>
"""


AUTH_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="theme-color" content="#0a1428">
    <title>{title} — {repo_name}</title>
    <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }}
        html, body {{
            background: #0a1428;
            color: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif;
            min-height: 100vh;
        }}
        body {{
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }}
        .auth-card {{
            width: 100%;
            max-width: 400px;
            background: #0f1e3d;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 26px;
            padding: 32px 28px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.45);
        }}
        .auth-logo {{
            width: 64px; height: 64px; border-radius: 18px;
            margin: 0 auto 16px; display: block;
        }}
        h1 {{
            text-align: center; font-size: 22px; font-weight: 700; margin-bottom: 6px;
        }}
        .subtitle {{
            text-align: center; color: #8e9ab5; font-size: 14px; margin-bottom: 28px;
        }}
        .tabs {{
            display: flex; background: rgba(255,255,255,0.06);
            border-radius: 14px; padding: 4px; margin-bottom: 24px;
        }}
        .tab-btn {{
            flex: 1; padding: 10px; border: none; background: transparent;
            color: #8e9ab5; font-weight: 600; font-size: 14px; border-radius: 10px;
            cursor: pointer; transition: 0.2s;
        }}
        .tab-btn.active {{
            background: #{tint}; color: #fff;
        }}
        .form-group {{ margin-bottom: 16px; }}
        label {{ display: block; font-size: 13px; color: #8e9ab5; margin-bottom: 6px; }}
        input {{
            width: 100%; padding: 14px; border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.12);
            background: rgba(255,255,255,0.05); color: #fff; font-size: 15px;
        }}
        input:focus {{ outline: none; border-color: #{tint}; }}
        .submit-btn {{
            width: 100%; padding: 15px; border: none; border-radius: 14px;
            background: #{tint}; color: #fff; font-weight: 700; font-size: 15px;
            cursor: pointer; margin-top: 8px; transition: 0.15s;
        }}
        .submit-btn:active {{ transform: scale(0.97); filter: brightness(0.92); }}
        .submit-btn:disabled {{ opacity: 0.5; }}
        .msg {{
            margin-top: 16px; padding: 12px; border-radius: 10px;
            font-size: 13px; text-align: center; display: none;
        }}
        .msg.error {{ background: rgba(255,80,80,0.15); color: #ff8080; display: block; }}
        .msg.success {{ background: rgba(80,220,140,0.15); color: #6be8a0; display: block; }}
        .back-link {{
            display: block; text-align: center; margin-top: 20px;
            color: #8e9ab5; font-size: 13px; text-decoration: none;
        }}
        .form-panel {{ display: none; }}
        .form-panel.active {{ display: block; }}
    </style>
</head>
<body>
    <div class="auth-card">
        <img class="auth-logo" src="{default_icon}" alt="logo">
        <h1>{repo_name}</h1>
        <p class="subtitle">Đăng nhập để quản lý license &amp; đơn hàng</p>

        <div class="tabs">
            <button class="tab-btn active" id="tabLogin" onclick="switchTab('login')">Đăng nhập</button>
            <button class="tab-btn" id="tabSignup" onclick="switchTab('signup')">Đăng ký</button>
        </div>

        <!-- LOGIN -->
        <div class="form-panel active" id="panelLogin">
            <div class="form-group">
                <label>Email</label>
                <input type="email" id="loginEmail" placeholder="ban@email.com" autocomplete="email">
            </div>
            <div class="form-group">
                <label>Mật khẩu</label>
                <input type="password" id="loginPassword" placeholder="••••••••" autocomplete="current-password">
            </div>
            <button class="submit-btn" id="btnLogin" onclick="doLogin()">Đăng nhập</button>
        </div>

        <!-- SIGNUP -->
        <div class="form-panel" id="panelSignup">
            <div class="form-group">
                <label>Email</label>
                <input type="email" id="signupEmail" placeholder="ban@email.com" autocomplete="email">
            </div>
            <div class="form-group">
                <label>Mật khẩu (tối thiểu 6 ký tự)</label>
                <input type="password" id="signupPassword" placeholder="••••••••" autocomplete="new-password">
            </div>
            <button class="submit-btn" id="btnSignup" onclick="doSignup()">Tạo tài khoản</button>
        </div>

        <div class="msg" id="msgBox"></div>
        <a href="./index.html" class="back-link">← Về trang chủ</a>
    </div>

    <script>
        // ⚠️ Đây là ANON KEY (public), CHỈ có quyền hạn chế theo RLS —
        // KHÔNG BAO GIỜ đặt Service Role Key ở đây (file này công khai
        // trên GitHub Pages, ai cũng xem được source).
        const SUPABASE_URL = "{supabase_url}";
        const SUPABASE_ANON_KEY = "{supabase_anon_key}";
        const sb = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

        function switchTab(tab) {{
            document.getElementById('tabLogin').classList.toggle('active', tab === 'login');
            document.getElementById('tabSignup').classList.toggle('active', tab === 'signup');
            document.getElementById('panelLogin').classList.toggle('active', tab === 'login');
            document.getElementById('panelSignup').classList.toggle('active', tab === 'signup');
            hideMsg();
        }}

        function showMsg(text, type) {{
            const box = document.getElementById('msgBox');
            box.textContent = text;
            box.className = 'msg ' + type;
        }}
        function hideMsg() {{
            const box = document.getElementById('msgBox');
            box.className = 'msg';
        }}

        async function doLogin() {{
            const email = document.getElementById('loginEmail').value.trim();
            const password = document.getElementById('loginPassword').value;
            const btn = document.getElementById('btnLogin');
            if (!email || !password) {{ showMsg('Vui lòng nhập đủ email và mật khẩu', 'error'); return; }}
            btn.disabled = true;
            const {{ data, error }} = await sb.auth.signInWithPassword({{ email, password }});
            btn.disabled = false;
            if (error) {{ showMsg(error.message, 'error'); return; }}
            showMsg('Đăng nhập thành công! Đang chuyển hướng...', 'success');
            setTimeout(() => location.href = './dashboard.html', 800);
        }}

        async function doSignup() {{
            const email = document.getElementById('signupEmail').value.trim();
            const password = document.getElementById('signupPassword').value;
            const btn = document.getElementById('btnSignup');
            if (!email || password.length < 6) {{ showMsg('Email hợp lệ + mật khẩu tối thiểu 6 ký tự', 'error'); return; }}
            btn.disabled = true;
            const {{ data, error }} = await sb.auth.signUp({{ email, password }});
            btn.disabled = false;
            if (error) {{ showMsg(error.message, 'error'); return; }}
            showMsg('Đăng ký thành công! Kiểm tra email để xác nhận (nếu bật), sau đó đăng nhập.', 'success');
            setTimeout(() => switchTab('login'), 1500);
        }}

        // Nếu đã đăng nhập sẵn (session còn hiệu lực) → chuyển thẳng dashboard
        (async () => {{
            const {{ data: {{ session }} }} = await sb.auth.getSession();
            if (session) location.href = './dashboard.html';
        }})();
    </script>
</body>
</html>
"""


def build_auth_view(output_file, supabase_url, supabase_anon_key, title="Đăng nhập"):
    """
    Sinh trang login/signup tĩnh (auth.html) dùng Supabase Auth JS SDK.

    Trang này gọi TRỰC TIẾP Supabase Auth API từ trình duyệt (client-side),
    không cần server riêng — phù hợp lưu trữ tĩnh trên GitHub Pages.

    ⚠️ supabase_anon_key là khoá CÔNG KHAI theo thiết kế của Supabase
    (được bảo vệ bởi Row Level Security ở phía database), an toàn khi
    đặt trong file tĩnh. TUYỆT ĐỐI không dùng Service Role Key ở đây.

    Args:
        output_file: đường dẫn file HTML output (vd: repo/auth.html)
        supabase_url: URL project Supabase (vd: https://xxxx.supabase.co)
        supabase_anon_key: Anon/public API key của project Supabase
        title: tiêu đề trang
    """
    html = AUTH_HTML_TEMPLATE.format(
        title=title,
        repo_name=config.REPO_NAME,
        tint=config.TINT_COLOR,
        default_icon=config.SOURCE_LOGO,
        supabase_url=supabase_url,
        supabase_anon_key=supabase_anon_key,
    )

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ Tạo xong: {output_file}")


def build_view(output_file, title, json_path, data_key, default_tab="apps", repo_type="apps",
               supabase_url=None, supabase_anon_key=None):
    """
    Sinh HTML v4 cho Apps/Tweaks/Dylibs pages

    Args:
        output_file: đường dẫn file HTML output
        title: tiêu đề trang (Apps/Tweaks/Dylibs)
        json_path: đường dẫn tới JSON data
        data_key: tên key trong JSON
        default_tab: tab nào đang active
        repo_type: loại repo ("apps"/"tweaks"/"dylibs") — dùng để compute thể loại
        supabase_url/supabase_anon_key: dùng cho mục "Tài khoản" trong settings
            (đăng nhập/đăng ký hoặc dashboard tuỳ trạng thái đăng nhập)
    """
    # FIX: HTML giờ nằm trong repo/html/ nhưng JSON vẫn ở repo/ gốc.
    # Dùng URL TUYỆT ĐỐI (giống index.html/shop.html) thay vì tính relpath
    # theo REPO_OUTPUT_DIR — tránh lệch thư mục khi HTML/JSON không cùng cấp.
    json_filename = os.path.basename(json_path)
    absolute_json_url = f"{config.BASE_URL}{json_filename}"

    resolved_url = supabase_url or os.getenv("SUPABASE_URL") or "https://vubnjcnhdbwrwfstavft.supabase.co"
    resolved_key = supabase_anon_key or os.getenv("SUPABASE_ANON_KEY") or "sb_publishable_akuKZo7u5dAhvj8RQvltyg__T6Acs66"

    active_apps = "active" if default_tab == "apps" else ""
    active_tweaks = "active" if default_tab == "tweaks" else ""
    active_dylibs = "active" if default_tab == "dylibs" else ""

    html = HTML_TEMPLATE.format(
        title=title,
        repo_name=config.REPO_NAME,
        tint=config.TINT_COLOR,
        json_path=absolute_json_url,
        data_key=data_key,
        active_apps=active_apps,
        active_tweaks=active_tweaks,
        active_dylibs=active_dylibs,
        default_icon=config.SOURCE_LOGO,
        repo_type=repo_type,
        supabase_url=resolved_url,
        supabase_anon_key=resolved_key
    )

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ Tạo xong: {output_file}")


DASHBOARD_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="theme-color" content="#0a1428">
    <title>Dashboard — {repo_name}</title>
    <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
    <script src="https://www.paypal.com/sdk/js?client-id={paypal_client_id}&currency=USD&intent=capture"></script>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }}
        html, body {{
            background: #0a1428; color: #fff;
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif;
            min-height: 100vh;
        }}

        .header {{
            background: rgba(10,20,40,0.95);
            backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
            padding: 12px 16px;
            display: grid; grid-template-columns: 1fr auto 1fr;
            align-items: center;
            position: sticky; top: 0; z-index: 100;
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }}
        .header-brand {{ justify-self: center; font-weight: 800; font-size: 15px; letter-spacing: 0.2px; white-space: nowrap; }}
        .header-btn-left {{ justify-self: start; }}
        .header-more-wrap {{ position: relative; justify-self: end; }}
        .header-btn {{
            width: 36px; height: 36px;
            display: flex; align-items: center; justify-content: center;
            color: #{tint}; font-size: 16px;
            text-decoration: none; border-radius: 50%;
            background: rgba(132,142,249,0.15);
            transition: 0.15s; border: none; cursor: pointer;
            letter-spacing: -1px;
        }}
        .header-btn:active {{ background: rgba(132,142,249,0.28); transform: scale(0.93); }}

        .more-dropdown {{
            position: absolute; top: 44px; right: 0;
            background: #0f1e3d; border: 1px solid rgba(255,255,255,0.1);
            border-radius: 14px; padding: 6px;
            min-width: 160px; box-shadow: 0 8px 24px rgba(0,0,0,0.4);
            display: none; flex-direction: column; gap: 2px;
            z-index: 150;
        }}
        .more-dropdown.open {{ display: flex; }}
        .more-item {{
            display: flex; align-items: center; gap: 8px;
            padding: 10px 12px; border-radius: 10px;
            background: transparent; border: none;
            color: #fff; font-size: 13px; font-weight: 600;
            text-decoration: none; cursor: pointer; text-align: left;
            width: 100%; box-sizing: border-box;
        }}
        .more-item:active {{ background: rgba(255,255,255,0.08); }}

        .container {{ padding: 20px; max-width: 100%; }}

        /* PROFILE CARD */
        .profile-card {{
            background: linear-gradient(135deg, #0f1e3d, #1a2a50);
            border: 1px solid rgba(132,142,249,0.3);
            border-radius: 20px; padding: 20px;
            margin-bottom: 24px;
        }}
        .profile-header {{
            display: flex; align-items: center; gap: 14px; margin-bottom: 16px;
            padding-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .profile-avatar {{
            width: 56px; height: 56px;
            background: #{tint}; border-radius: 14px;
            display: flex; align-items: center; justify-content: center;
            font-weight: 700; font-size: 24px;
        }}
        .profile-info h2 {{ font-size: 16px; margin-bottom: 3px; }}
        .profile-info p {{ font-size: 12px; color: #8e9ab5; }}
        .profile-row {{
            display: flex; justify-content: space-between; padding: 8px 0;
            font-size: 13px; color: #b0bcd4;
        }}
        .profile-row span:first-child {{ color: #8e9ab5; }}

        /* UDID ĐÃ LƯU */
        .udid-saved-card {{
            background: #0f1e3d; border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px; padding: 16px; margin-bottom: 24px;
        }}
        .udid-saved-title {{ font-size: 13px; font-weight: 700; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }}
        .udid-saved-row {{ display: flex; gap: 8px; }}
        .udid-saved-input {{
            flex: 1; min-width: 0; padding: 10px 12px; border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.12);
            background: rgba(255,255,255,0.05); color: #fff; font-size: 12px;
            font-family: 'SF Mono', monospace;
        }}
        .udid-saved-input:focus {{ outline: none; border-color: #{tint}; }}
        .udid-saved-btn {{
            flex-shrink: 0; padding: 10px 14px; border: none; border-radius: 10px;
            background: #{tint}; color: #fff; font-weight: 700; font-size: 12px; cursor: pointer;
        }}
        .udid-saved-btn:active {{ transform: scale(0.96); }}
        .udid-saved-hint {{ font-size: 11px; color: #8e9ab5; margin-top: 8px; }}

        /* KHO ỨNG DỤNG (tabs + list) */
        .lib-tabs {{
            display: flex; background: rgba(255,255,255,0.06);
            border-radius: 14px; padding: 4px; margin-bottom: 14px;
        }}
        .lib-tab-btn {{
            flex: 1; padding: 9px; border: none; background: transparent;
            color: #8e9ab5; font-weight: 600; font-size: 12px;
            border-radius: 10px; cursor: pointer; transition: 0.2s;
        }}
        .lib-tab-btn.active {{ background: #{tint}; color: #fff; }}
        .lib-item {{
            background: #0f1e3d; border: 1px solid rgba(255,255,255,0.08);
            border-radius: 14px; padding: 12px; margin-bottom: 10px;
            display: flex; align-items: center; gap: 12px;
        }}
        .lib-item-icon {{ width: 40px; height: 40px; border-radius: 10px; flex-shrink: 0; object-fit: cover; }}
        .lib-item-info {{ flex: 1; min-width: 0; }}
        .lib-item-name {{ font-size: 13px; font-weight: 700; margin-bottom: 2px; }}
        .lib-item-dev {{ font-size: 11px; color: #8e9ab5; }}
        .lib-item-badge {{
            flex-shrink: 0; font-size: 10px; font-weight: 700; padding: 5px 10px;
            border-radius: 20px; white-space: nowrap;
        }}
        .lib-badge-free {{ background: rgba(107,232,160,0.15); color: #6be8a0; }}
        .lib-badge-owned {{ background: rgba(132,142,249,0.2); color: #{tint}; }}
        .lib-badge-buy {{
            background: rgba(255,255,255,0.08); color: #fff; cursor: pointer;
            text-decoration: none; display: inline-block;
        }}

        /* GIỎ HÀNG */
        .cart-item {{
            background: #0f1e3d; border: 1px solid rgba(255,255,255,0.08);
            border-radius: 14px; padding: 12px; margin-bottom: 10px;
            display: flex; align-items: center; gap: 12px;
        }}
        .cart-item-info {{ flex: 1; min-width: 0; }}
        .cart-item-name {{ font-size: 13px; font-weight: 700; margin-bottom: 2px; }}
        .cart-item-time {{ font-size: 10px; color: #8e9ab5; }}
        .cart-item-actions {{ display: flex; gap: 6px; flex-shrink: 0; }}
        .cart-buy-btn {{
            padding: 8px 14px; border: none; border-radius: 10px;
            background: #{tint}; color: #fff; font-weight: 700; font-size: 11px; cursor: pointer;
        }}
        .cart-remove-btn {{
            padding: 8px 10px; border: none; border-radius: 10px;
            background: rgba(255,80,80,0.15); color: #ff8080; font-size: 12px; cursor: pointer;
        }}

        /* LICENSES */
        .section-title {{
            font-size: 13px; font-weight: 700; color: #8e9ab5;
            text-transform: uppercase; letter-spacing: 0.5px;
            margin: 24px 0 12px;
            padding: 0 8px;
        }}
        .license-list {{
            display: flex; flex-direction: column; gap: 12px;
            margin-bottom: 24px;
        }}
        .license-card {{
            background: #0f1e3d; border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px; padding: 14px;
        }}
        .license-top {{
            display: flex; justify-content: space-between; align-items: flex-start;
            margin-bottom: 10px;
        }}
        .license-pkg {{
            font-size: 13px; font-weight: 700; color: #{tint};
            font-family: 'SF Mono', monospace; word-break: break-all;
        }}
        .license-type {{
            font-size: 10px; padding: 3px 8px;
            background: rgba(132,142,249,0.2); color: #{tint};
            border-radius: 6px;
        }}
        .license-udid {{
            font-size: 11px; color: #8e9ab5; font-family: monospace;
            margin-bottom: 6px; word-break: break-all;
        }}
        .license-key {{
            font-size: 12px; color: #b0bcd4;
            background: rgba(255,255,255,0.03); padding: 8px;
            border-radius: 10px; margin-bottom: 8px;
            font-family: 'SF Mono', monospace;
            white-space: pre-wrap; word-break: break-all;
            max-height: 100px; overflow: auto;
        }}
        .license-expires {{
            font-size: 11px; color: #8e9ab5; margin-bottom: 8px;
        }}
        .license-actions {{
            display: flex; gap: 8px;
        }}
        .btn-copy {{
            flex: 1; padding: 8px; border: none; border-radius: 10px;
            background: #{tint}; color: #fff; font-weight: 600; font-size: 12px;
            cursor: pointer;
        }}
        .btn-revoke {{
            flex: 1; padding: 8px; border: none; border-radius: 10px;
            background: rgba(255,80,80,0.15); color: #ff8080;
            font-weight: 600; font-size: 12px; cursor: pointer;
        }}

        .empty-state {{
            text-align: center; color: #8e9ab5; padding: 40px 20px;
            font-size: 14px;
        }}

        /* CHECKOUT SHEET (gộp từ shop.html) */
        .checkout-backdrop {{
            position: fixed; inset: 0; background: rgba(0,0,0,0.6);
            z-index: 200; display: none; align-items: flex-end;
            backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px);
        }}
        .checkout-backdrop.open {{ display: flex; }}
        .checkout-sheet {{
            width: 100%; background: #0f1e3d;
            border-radius: 24px 24px 0 0;
            padding: 24px 20px 40px;
            border-top: 1px solid rgba(255,255,255,0.1);
            max-height: 90vh; overflow-y: auto;
        }}
        .sheet-handle {{
            width: 36px; height: 4px; background: rgba(255,255,255,0.2);
            border-radius: 2px; margin: 0 auto 20px;
        }}
        .sheet-title {{ font-size: 18px; font-weight: 700; margin-bottom: 6px; }}
        .sheet-product {{ font-size: 14px; color: #8e9ab5; margin-bottom: 20px; }}
        .sheet-row {{
            display: flex; justify-content: space-between; align-items: center;
            padding: 12px 0; border-bottom: 1px solid rgba(255,255,255,0.06);
            font-size: 14px;
        }}
        .sheet-row:last-of-type {{ border-bottom: none; }}
        .sheet-row span:last-child {{ font-weight: 600; }}
        .total-row {{ margin-top: 8px; font-size: 16px; font-weight: 700; }}
        .total-row span:last-child {{ color: #{tint}; font-size: 18px; }}
        .payment-methods {{ margin-top: 20px; display: flex; flex-direction: column; gap: 10px; }}
        .pm-label {{
            font-size: 12px; color: #8e9ab5; font-weight: 600;
            text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;
        }}
        .pm-btn {{
            width: 100%; padding: 15px; border: none; border-radius: 14px;
            font-weight: 700; font-size: 15px; cursor: pointer;
            transition: 0.15s; display: flex; align-items: center;
            justify-content: center; gap: 8px;
        }}
        .pm-btn:active {{ transform: scale(0.97); filter: brightness(0.9); }}
        .pm-payos {{ background: #0066FF; color: #fff; }}
        .pm-momo {{ background: #A50064; color: #fff; }}
        #paypal-button-container {{ margin-top: 10px; }}
        .or-divider {{
            text-align: center; color: #8e9ab5; font-size: 12px;
            margin: 8px 0; position: relative;
        }}
        .or-divider::before, .or-divider::after {{
            content: ''; position: absolute; top: 50%;
            width: calc(50% - 24px); height: 1px;
            background: rgba(255,255,255,0.1);
        }}
        .or-divider::before {{ left: 0; }}
        .or-divider::after {{ right: 0; }}
        .close-sheet {{
            margin-top: 14px; width: 100%; padding: 14px; border: none;
            border-radius: 14px; background: rgba(255,255,255,0.06);
            color: #8e9ab5; font-size: 15px; cursor: pointer;
        }}

        .toast {{
            position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
            background: #1a2a50; color: #fff; padding: 12px 20px;
            border-radius: 12px; font-size: 14px; z-index: 999;
            opacity: 0; transition: 0.3s; pointer-events: none;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .toast.show {{ opacity: 1; }}
    </style>
</head>
<body>
    <div class="header">
        <a href="./index.html" class="header-btn header-btn-left" title="Trang chủ">🏠</a>
        <span class="header-brand">{repo_name}</span>
        <div class="header-more-wrap">
            <button class="header-btn" onclick="toggleMoreMenu()" title="Thêm">•••</button>
            <div class="more-dropdown" id="moreDropdown">
                <a href="./index.html" class="more-item">🛒 Mua thêm</a>
                <a href="./sign.html" class="more-item">🖊️ Sign IPA</a>
                <button class="more-item" onclick="logout()">↪ Đăng xuất</button>
            </div>
        </div>
    </div>

    <div class="container">
        <!-- Profile -->
        <div class="profile-card">
            <div class="profile-header">
                <div class="profile-avatar" id="avatar">👤</div>
                <div class="profile-info">
                    <h2 id="userName">—</h2>
                    <p id="userEmail">—</p>
                </div>
            </div>
            <div class="profile-row">
                <span>Mã ID</span>
                <span id="profileCode" style="font-family:monospace;color:#{tint};font-weight:700">—</span>
            </div>
            <div class="profile-row">
                <span>Email</span>
                <span id="profileEmail" style="font-family:monospace">—</span>
            </div>
            <div class="profile-row">
                <span>Tham gia</span>
                <span id="profileJoined">—</span>
            </div>
            <div class="profile-row" id="deviceModelRow" style="display:none">
                <span>Thiết bị</span>
                <span id="profileDeviceModel">—</span>
            </div>
        </div>

        <!-- UDID đã lưu -->
        <div class="udid-saved-card">
            <div class="udid-saved-title">🔑 UDID đã lưu</div>
            <div class="udid-saved-row">
                <input class="udid-saved-input" id="savedUdidInput" placeholder="Chưa lưu UDID nào..." oninput="onSavedUdidTyped()">
            </div>
            <div class="udid-saved-row" style="margin-top:8px">
                <button class="udid-saved-btn" id="btnGetUdidAuto" onclick="getUdidAuto()" style="flex:1">📱 Lấy tự động</button>
                <button class="udid-saved-btn" onclick="saveUdid()" style="flex:1;background:rgba(255,255,255,0.1)">💾 Lưu thủ công</button>
            </div>
            <div class="udid-saved-hint" id="udidAutoStatus">Bấm "Lấy tự động" → cài profile → UDID tự điền + tự lưu, hoặc dán tay rồi bấm Lưu.</div>
        </div>

        <!-- Giỏ hàng -->
        <div class="section-title">🛒 Giỏ hàng</div>
        <div id="cartList" style="margin-bottom:24px">
            <div class="empty-state">⏳ Đang tải...</div>
        </div>

        <!-- Kho ứng dụng -->
        <div class="section-title">📦 Kho ứng dụng</div>
        <div class="lib-tabs">
            <button class="lib-tab-btn active" id="libtab-apps" onclick="switchLibTab('apps')">📱 Apps</button>
            <button class="lib-tab-btn" id="libtab-debs" onclick="switchLibTab('debs')">🔧 Debs</button>
            <button class="lib-tab-btn" id="libtab-dylibs" onclick="switchLibTab('dylibs')">📚 Dylibs</button>
        </div>
        <div id="libList" style="margin-bottom:24px">
            <div class="empty-state">⏳ Đang tải...</div>
        </div>

        <!-- Licenses -->
        <div class="section-title">🔐 License của bạn</div>
        <div id="licenseList" class="license-list">
            <div class="empty-state">
                ⏳ Đang tải...
            </div>
        </div>
    </div>

    <!-- Checkout Sheet (gộp từ shop.html) -->
    <div class="checkout-backdrop" id="checkoutBackdrop" onclick="closeCheckout(event)">
        <div class="checkout-sheet">
            <div class="sheet-handle"></div>
            <div class="sheet-title">Xác nhận thanh toán</div>
            <div class="sheet-product" id="sheetProductName">—</div>
            <div class="sheet-row"><span>Gói</span><span id="sheetPkg">—</span></div>
            <div class="sheet-row"><span>UDID</span><span id="sheetUdid" style="font-family:monospace;font-size:11px">—</span></div>
            <div class="sheet-row total-row"><span>Tổng</span><span id="sheetPrice">—</span></div>

            <div class="payment-methods">
                <div class="pm-label">Chọn cổng thanh toán</div>
                <div id="paypal-button-container"></div>
                <div class="or-divider">hoặc</div>
                <button class="pm-btn pm-payos" onclick="payWithPayOS()">
                    💙 Thanh toán qua PayOS
                </button>
                <button class="pm-btn pm-momo" onclick="payWithMomo()">
                    💜 Thanh toán qua MoMo
                </button>
            </div>
            <button class="close-sheet" onclick="closeCheckout()">Huỷ</button>
        </div>
    </div>

    <div class="toast" id="toast"></div>

    <script>
        const SUPABASE_URL = "{supabase_url}";
        const SUPABASE_ANON_KEY = "{supabase_anon_key}";
        const sb = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
        const EDGE_FN_URL = SUPABASE_URL.replace(/\/$/, '') + '/functions/v1/udid-capture';

        let ownedProductIds = new Set();
        let currentLibTab = 'apps';
        let selectedProduct = null;
        let cartDataMap = {{}};
        let pollingTimer = null;
        const LIB_SOURCES = {{
            apps: {{ url: '{base_url}apps.json', label: 'IPA' }},
            debs: {{ url: '{base_url}debs.json', label: 'DEB' }},
            dylibs: {{ url: '{base_url}dylibs.json', label: 'DYLIB' }},
        }};

        async function init() {{
            // Kiểm tra auth
            const {{ data: {{ session }} }} = await sb.auth.getSession();
            if (!session) {{
                window.location.href = './auth.html';
                return;
            }}

            // Tải profile
            const {{ data: user }} = await sb.auth.getUser();
            const {{ data: profile }} = await sb.from('profiles')
                .select('*').eq('id', user.user.id).single();

            document.getElementById('userName').textContent = profile?.display_name || user.user.email;
            document.getElementById('userEmail').textContent = user.user.email;
            document.getElementById('profileEmail').textContent = user.user.email;
            document.getElementById('profileCode').textContent = profile?.customer_code || '—';
            document.getElementById('profileJoined').textContent =
                new Date(user.user.created_at).toLocaleDateString('vi-VN');
            document.getElementById('avatar').textContent =
                (profile?.display_name || user.user.email)[0].toUpperCase();

            // Điền UDID đã lưu (nếu có) + tra model máy qua udid.help
            if (profile?.saved_udid) {{
                document.getElementById('savedUdidInput').value = profile.saved_udid;
                lookupDeviceModel(profile.saved_udid);
            }}

            // Tải licenses (dùng lại cho phần "Đã sở hữu" trong Kho ứng dụng)
            const {{ data: licenses }} = await sb.from('licenses')
                .select('*').eq('user_id', user.user.id).not('revoked', 'is', true);
            ownedProductIds = new Set((licenses || []).map(l => l.product_id));

            renderLicenseList(licenses || []);
            loadLibrary(); // Tải Kho ứng dụng (cả 3 loại), mặc định tab 'apps'
            loadCart();    // Tải Giỏ hàng
        }}

        // ──────────────────────────────────────────────
        // TRA MODEL MÁY TỪ UDID — API công khai udid.help (không cần key)
        // ──────────────────────────────────────────────
        async function lookupDeviceModel(udid) {{
            try {{
                const resp = await fetch('https://udid.help/v1/device/lookup', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ udid, platform: 'ios' }})
                }});
                if (!resp.ok) return; // im lặng nếu lỗi, không quan trọng
                const result = await resp.json();
                if (result?.data?.model) {{
                    document.getElementById('profileDeviceModel').textContent = result.data.model;
                    document.getElementById('deviceModelRow').style.display = 'flex';
                }}
            }} catch (e) {{ /* bỏ qua lỗi mạng, không chặn trang */ }}
        }}

        function onSavedUdidTyped() {{
            document.getElementById('deviceModelRow').style.display = 'none';
        }}

        // ──────────────────────────────────────────────
        // GIỎ HÀNG
        // ──────────────────────────────────────────────
        async function loadCart() {{
            const listEl = document.getElementById('cartList');
            const {{ data: {{ session }} }} = await sb.auth.getSession();
            if (!session) return;

            const {{ data: cartItems }} = await sb.from('cart_items')
                .select('*, products(name, price_usd, price_vnd)')
                .eq('user_id', session.user.id)
                .order('added_at', {{ ascending: false }});

            if (!cartItems || cartItems.length === 0) {{
                listEl.innerHTML = '<div class="empty-state">Giỏ hàng trống. Bấm giá tiền ở danh sách "Kho ứng dụng" hoặc apps/debs/dylibs để thêm.</div>';
                return;
            }}

            cartDataMap = {{}};
            listEl.innerHTML = cartItems.map(item => {{
                const p = item.products;
                cartDataMap[item.product_id] = p;
                const priceLabel = p?.price_usd ? '$' + p.price_usd
                    : (p?.price_vnd ? Number(p.price_vnd).toLocaleString('vi-VN') + '₫' : '');
                const addedTime = new Date(item.added_at).toLocaleString('vi-VN');
                return `
                    <div class="cart-item">
                        <div class="cart-item-info">
                            <div class="cart-item-name">${{p?.name || item.product_id}} <span style="color:#{tint}">${{priceLabel}}</span></div>
                            <div class="cart-item-time">Thêm lúc: ${{addedTime}}</div>
                        </div>
                        <div class="cart-item-actions">
                            <button class="cart-buy-btn" onclick="buyFromCart('${{item.product_id}}')">Mua</button>
                            <button class="cart-remove-btn" onclick="removeFromCart('${{item.id}}')">✕</button>
                        </div>
                    </div>
                `;
            }}).join('');
        }}

        // ──────────────────────────────────────────────
        // CHECKOUT (gộp từ shop.html) — mua thẳng từ giỏ hàng, dùng UDID đã lưu
        // ──────────────────────────────────────────────
        function buyFromCart(productId) {{
            const udid = document.getElementById('savedUdidInput').value.trim();
            if (!udid) {{
                showToast('⚠️ Vui lòng lưu UDID trước khi mua (mục 🔑 UDID đã lưu ở trên)');
                document.getElementById('savedUdidInput').focus();
                return;
            }}
            const p = cartDataMap[productId];
            selectedProduct = {{
                bundleIdentifier: productId,
                name: p?.name || productId,
                _price_usd: p?.price_usd,
                _price_vnd: p?.price_vnd,
            }};

            document.getElementById('sheetProductName').textContent = selectedProduct.name;
            document.getElementById('sheetPkg').textContent = selectedProduct.bundleIdentifier;
            document.getElementById('sheetUdid').textContent = udid;
            document.getElementById('sheetPrice').textContent =
                (selectedProduct._price_usd ? '$' + selectedProduct._price_usd : '') +
                (selectedProduct._price_vnd ? ' / ' + Number(selectedProduct._price_vnd).toLocaleString('vi-VN') + '₫' : '');

            openCheckout();
            renderPayPalButton();
        }}

        let ppRendered = false;
        function renderPayPalButton() {{
            if (ppRendered) return;
            ppRendered = true;
            paypal.Buttons({{
                style: {{ color: 'gold', shape: 'rect', label: 'pay', height: 48 }},
                createOrder: (data, actions) => {{
                    const p = selectedProduct;
                    return actions.order.create({{
                        purchase_units: [{{
                            amount: {{ value: String(p._price_usd || '1.00'), currency_code: 'USD' }},
                            description: p.name + ' (' + p.bundleIdentifier + ')'
                        }}]
                    }});
                }},
                onApprove: async (data, actions) => {{
                    const order = await actions.order.capture();
                    showToast('✅ PayPal thành công! Đang tạo license...');
                    await requestLicense('paypal', order.id);
                }},
                onError: (err) => {{ showToast('❌ Lỗi PayPal: ' + err.message); }}
            }}).render('#paypal-button-container');
        }}

        async function payWithPayOS() {{
            if (!selectedProduct) return;
            showToast('⏳ Đang tạo link PayOS...');
            const udid = document.getElementById('savedUdidInput').value.trim();
            const {{ data: {{ session }} }} = await sb.auth.getSession();
            if (!session) {{ showToast('⚠️ Cần đăng nhập trước!'); return; }}
            const resp = await fetch(SUPABASE_URL + '/functions/v1/create-order', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + session.access_token }},
                body: JSON.stringify({{ product_id: selectedProduct.bundleIdentifier, udid, provider: 'payos' }})
            }});
            const result = await resp.json();
            if (result.checkout_url) window.location.href = result.checkout_url;
            else showToast('❌ Lỗi: ' + (result.error || 'Không tạo được link'));
        }}

        async function payWithMomo() {{
            showToast('⏳ Đang tạo link MoMo...');
            const udid = document.getElementById('savedUdidInput').value.trim();
            const {{ data: {{ session }} }} = await sb.auth.getSession();
            if (!session) {{ showToast('⚠️ Cần đăng nhập trước!'); return; }}
            const resp = await fetch(SUPABASE_URL + '/functions/v1/create-order', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + session.access_token }},
                body: JSON.stringify({{ product_id: selectedProduct.bundleIdentifier, udid, provider: 'momo' }})
            }});
            const result = await resp.json();
            if (result.pay_url) window.location.href = result.pay_url;
            else showToast('❌ Lỗi: ' + (result.error || 'Không tạo được link'));
        }}

        async function requestLicense(provider, txnId) {{
            const udid = document.getElementById('savedUdidInput').value.trim();
            const {{ data: {{ session }} }} = await sb.auth.getSession();
            if (!session) {{ showToast('⚠️ Cần đăng nhập!'); return; }}
            const resp = await fetch(SUPABASE_URL + '/functions/v1/issue-license', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + session.access_token }},
                body: JSON.stringify({{ product_id: selectedProduct.bundleIdentifier, udid, provider, txn_id: txnId }})
            }});
            const result = await resp.json();
            if (result.license_key) {{
                closeCheckout();
                showToast('🎉 License tạo thành công!');
                // Xoá khỏi giỏ hàng (đã mua xong) + tải lại toàn bộ danh sách
                await sb.from('cart_items').delete()
                    .eq('user_id', session.user.id).eq('product_id', selectedProduct.bundleIdentifier);
                loadCart();
                const {{ data: licenses }} = await sb.from('licenses')
                    .select('*').eq('user_id', session.user.id).not('revoked', 'is', true);
                ownedProductIds = new Set((licenses || []).map(l => l.product_id));
                renderLicenseList(licenses || []);
                loadLibrary();
            }} else {{
                showToast('❌ ' + (result.error || 'Lỗi tạo license'));
            }}
        }}

        function openCheckout() {{
            document.getElementById('checkoutBackdrop').classList.add('open');
        }}
        function closeCheckout(e) {{
            if (e && e.target !== document.getElementById('checkoutBackdrop')) return;
            document.getElementById('checkoutBackdrop').classList.remove('open');
        }}


        async function removeFromCart(cartItemId) {{
            const {{ error }} = await sb.from('cart_items').delete().eq('id', cartItemId);
            if (error) {{ showToast('❌ Lỗi: ' + error.message); return; }}
            showToast('🗑️ Đã xoá khỏi giỏ hàng');
            loadCart();
        }}

        function renderLicenseList(licenses) {{
            const list = document.getElementById('licenseList');
            if (!licenses || licenses.length === 0) {{
                list.innerHTML = `<div class="empty-state">
                    Bạn chưa mua license nào. Bấm ••• ở góc trên để mua thêm.
                </div>`;
                return;
            }}

            list.innerHTML = licenses.map(lic => `
                <div class="license-card">
                    <div class="license-top">
                        <div>
                            <div class="license-pkg">${{lic.product_id}}</div>
                            <div class="license-type">DYLIB</div>
                        </div>
                    </div>
                    <div class="license-udid">🔑 UDID: ${{lic.udid}}</div>
                    <div class="license-key" id="key-${{lic.id}}">${{lic.license_key}}</div>
                    <div class="license-expires">
                        ⏱️ Hết hạn: ${{new Date(lic.expires_at).toLocaleDateString('vi-VN')}}
                    </div>
                    <div class="license-actions">
                        <button class="btn-copy" onclick="copyLicense('${{lic.id}}')">
                            📋 Copy key
                        </button>
                        <button class="btn-revoke" onclick="revokeLicense('${{lic.id}}')">
                            🗑️ Hủy
                        </button>
                    </div>
                </div>
            `).join('');
        }}

        async function logout() {{
            await sb.auth.signOut();
            window.location.href = './auth.html';
        }}

        async function addToCartFromDashboard(bundleId, btnEl) {{
            const {{ data: {{ session }} }} = await sb.auth.getSession();
            if (!session) return;
            const original = btnEl.textContent;
            btnEl.textContent = '⏳';
            const {{ error }} = await sb.from('cart_items')
                .upsert({{ user_id: session.user.id, product_id: bundleId }}, {{ onConflict: 'user_id,product_id' }});
            if (error) {{
                btnEl.textContent = original;
                showToast('❌ Lỗi: ' + error.message);
            }} else {{
                btnEl.textContent = '✅';
                showToast('✅ Đã thêm vào giỏ hàng');
                loadCart();
                setTimeout(() => {{ btnEl.textContent = original; }}, 1500);
            }}
        }}

        // ──────────────────────────────────────────────
        // LƯU UDID VĨNH VIỄN VÀO PROFILE
        // ──────────────────────────────────────────────
        async function saveUdid() {{
            const val = document.getElementById('savedUdidInput').value.trim();
            if (!val) {{ showToast('⚠️ Chưa nhập UDID'); return; }}
            const {{ data: {{ session }} }} = await sb.auth.getSession();
            if (!session) return;
            const {{ error }} = await sb.from('profiles')
                .update({{ saved_udid: val }}).eq('id', session.user.id);
            if (error) {{
                showToast('❌ Lỗi lưu UDID: ' + error.message);
            }} else {{
                showToast('✅ Đã lưu UDID — lần sau mua sẽ tự điền');
                lookupDeviceModel(val);
            }}
        }}

        // ──────────────────────────────────────────────
        // LẤY UDID TỰ ĐỘNG qua .mobileconfig (gộp từ shop.html)
        // ──────────────────────────────────────────────
        async function getUdidAuto() {{
            const token = crypto.randomUUID().replace(/-/g, '');
            const btn = document.getElementById('btnGetUdidAuto');
            const status = document.getElementById('udidAutoStatus');
            btn.style.opacity = '0.6';
            btn.style.pointerEvents = 'none';
            btn.textContent = '⏳ Đang chờ...';
            status.textContent = 'Cài profile → quay lại trang này → UDID sẽ tự điền và tự lưu.';

            await sb.from('udid_sessions').insert({{ token, udid: null }});

            // Mở .mobileconfig (iOS hỏi cài không)
            window.location.href = `${{EDGE_FN_URL}}?token=${{token}}`;

            pollingTimer = setInterval(() => pollUdidAuto(token), 2000);
            setTimeout(() => stopPollingAuto(token, false), 300000);
        }}

        async function pollUdidAuto(token) {{
            const {{ data }} = await sb.from('udid_sessions')
                .select('udid').eq('token', token).single();
            if (data?.udid) {{
                stopPollingAuto(token, true);
                document.getElementById('savedUdidInput').value = data.udid;
                const {{ data: {{ session }} }} = await sb.auth.getSession();
                if (session) {{
                    await sb.from('profiles').update({{ saved_udid: data.udid }}).eq('id', session.user.id);
                }}
                const status = document.getElementById('udidAutoStatus');
                status.textContent = '✅ UDID đã lấy tự động và lưu thành công!';
                lookupDeviceModel(data.udid);
                showToast('✅ Đã lấy & lưu UDID tự động');
                await sb.from('udid_sessions').delete().eq('token', token);
            }}
        }}

        function stopPollingAuto(token, success) {{
            if (pollingTimer) {{ clearInterval(pollingTimer); pollingTimer = null; }}
            const btn = document.getElementById('btnGetUdidAuto');
            btn.style.opacity = '';
            btn.style.pointerEvents = '';
            btn.textContent = '📱 Lấy tự động';
            if (!success) {{
                document.getElementById('udidAutoStatus').textContent =
                    'Hết thời gian chờ. Thử lại hoặc dán tay UDID rồi bấm Lưu thủ công.';
            }}
        }}

        // ──────────────────────────────────────────────
        // KHO ỨNG DỤNG — 3 tab, phân loại Miễn phí / Đã sở hữu / Chưa mua
        // ──────────────────────────────────────────────
        async function switchLibTab(tab) {{
            currentLibTab = tab;
            document.querySelectorAll('.lib-tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById('libtab-' + tab).classList.add('active');
            await loadLibrary();
        }}

        async function loadLibrary() {{
            const listEl = document.getElementById('libList');
            listEl.innerHTML = '<div class="empty-state">⏳ Đang tải...</div>';
            try {{
                const source = LIB_SOURCES[currentLibTab];
                const {{ data: dbProducts }} = await sb.from('products').select('id,price_usd,price_vnd');
                const priceMap = {{}};
                (dbProducts || []).forEach(p => priceMap[p.id] = p);

                const resp = await fetch(source.url);
                const data = await resp.json();
                const apps = data.apps || [];

                if (apps.length === 0) {{
                    listEl.innerHTML = '<div class="empty-state">Không có sản phẩm nào.</div>';
                    return;
                }}

                listEl.innerHTML = apps.map(app => {{
                    const isPaid = !!priceMap[app.bundleIdentifier];
                    const isOwned = ownedProductIds.has(app.bundleIdentifier);
                    let badge;
                    if (isOwned) {{
                        badge = `<span class="lib-item-badge lib-badge-owned">✅ Đã sở hữu</span>`;
                    }} else if (isPaid) {{
                        badge = `<button class="lib-item-badge lib-badge-buy" onclick="addToCartFromDashboard('${{app.bundleIdentifier}}', this)">🛒 ${{priceMap[app.bundleIdentifier]?.price_usd ? '$' + priceMap[app.bundleIdentifier].price_usd : 'Mua'}}</button>`;
                    }} else {{
                        badge = `<span class="lib-item-badge lib-badge-free">Miễn phí</span>`;
                    }}
                    return `
                        <div class="lib-item">
                            <img class="lib-item-icon" src="${{app.iconURL || ''}}"
                                onerror="this.src='{default_icon}'" alt="${{app.name}}">
                            <div class="lib-item-info">
                                <div class="lib-item-name">${{app.name}}</div>
                                <div class="lib-item-dev">${{app.developerName || ''}}</div>
                            </div>
                            ${{badge}}
                        </div>
                    `;
                }}).join('');
            }} catch (e) {{
                listEl.innerHTML = '<div class="empty-state">Lỗi tải dữ liệu: ' + e.message + '</div>';
            }}
        }}

        function toggleMoreMenu() {{
            document.getElementById('moreDropdown').classList.toggle('open');
        }}
        document.addEventListener('click', (e) => {{
            const wrap = document.querySelector('.header-more-wrap');
            const dropdown = document.getElementById('moreDropdown');
            if (wrap && dropdown && !wrap.contains(e.target)) {{
                dropdown.classList.remove('open');
            }}
        }});

        function copyLicense(id) {{
            const key = document.getElementById('key-' + id)?.textContent;
            if (key) {{
                navigator.clipboard.writeText(key).then(() => {{
                    showToast('✅ Đã copy license key');
                }});
            }}
        }}

        async function revokeLicense(id) {{
            if (!confirm('Bạn chắc muốn hủy license này không?')) return;
            const {{ error }} = await sb.from('licenses')
                .update({{ revoked: true }}).eq('id', id);
            if (error) {{
                showToast('❌ Lỗi: ' + error.message);
            }} else {{
                showToast('✅ Đã hủy license');
                setTimeout(() => location.reload(), 1000);
            }}
        }}

        function showToast(msg) {{
            const t = document.getElementById('toast');
            t.textContent = msg; t.classList.add('show');
            setTimeout(() => t.classList.remove('show'), 2500);
        }}

        init();
    </script>
</body>
</html>
"""


def build_dashboard_view(output_file, supabase_url, supabase_anon_key, paypal_client_id="YOUR_PAYPAL_CLIENT_ID"):
    """
    Sinh trang dashboard.html — TRUNG TÂM QUẢN LÝ DUY NHẤT của user.

    Tính năng:
      • Thông tin tài khoản (Mã ID, tên, email, ngày tham gia, model máy)
      • UDID đã lưu (vĩnh viễn, tự điền khi mua)
      • Giỏ hàng (thêm/xoá, thời gian thêm)
      • Kho ứng dụng (3 tab, phân loại Miễn phí/Đã sở hữu/Giá tiền)
      • Danh sách license đã mua (copy key, hủy)
      • CHECKOUT (gộp từ shop.html) — mua thẳng từ giỏ hàng, dùng UDID
        đã lưu, chọn PayPal/PayOS/MoMo, gọi issue-license sau thanh toán

    shop.html KHÔNG còn tồn tại — toàn bộ chức năng mua hàng đã gộp
    vào đây theo yêu cầu đơn giản hoá kiến trúc.
    """
    html = DASHBOARD_HTML_TEMPLATE.format(
        repo_name=config.REPO_NAME,
        tint=config.TINT_COLOR,
        default_icon=config.SOURCE_LOGO,
        base_url=config.BASE_URL,
        supabase_url=supabase_url,
        supabase_anon_key=supabase_anon_key,
        paypal_client_id=paypal_client_id,
    )

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ Tạo xong: {output_file}")


INDEX_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta name="theme-color" content="#0a1428">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>{repo_name}</title>
    <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }}

        :root {{
            --radius-panel:  26px;
            --radius-card:   16px;
            --radius-btn:    12px;
            --radius-pill:   999px;
            --radius-circle: 50%;
        }}

        html {{
            --bg-1: #0a1428;
            --bg-2: #1e3a8a;
            --text: white;
            --text-secondary: rgba(255,255,255,0.6);
            --card-bg: rgba(255,255,255,0.08);
            --card-border: rgba(255,255,255,0.16);
            --card-shadow: rgba(31,38,135,0.37);
            --hover-bg: rgba(255,255,255,0.12);
            --btn-inactive: rgba(255,255,255,0.07);
            --btn-inactive-border: rgba(255,255,255,0.13);
            --btn-inactive-text: rgba(255,255,255,0.45);
            --tint: #{tint};
            --glass-bg: rgba(8, 16, 40, 0.60);
            --glass-blur: blur(40px) saturate(220%) brightness(1.08);
            --glass-border: 1px solid rgba(255, 255, 255, 0.22);
            --glass-radius: 26px;
            --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.45);
            font-size: clamp(14px, 2vw, 16px);
        }}

        html[data-theme="light"] {{
            --bg-1: #f0f4ff;
            --bg-2: #dce6f5;
            --text: #1d1d1f;
            --text-secondary: rgba(0,0,0,0.55);
            --card-bg: rgba(255,255,255,0.72);
            --card-border: rgba(0,0,0,0.10);
            --card-shadow: rgba(0,0,0,0.08);
            --hover-bg: rgba(0,0,0,0.06);
            --btn-inactive: rgba(0,0,0,0.05);
            --btn-inactive-border: rgba(0,0,0,0.10);
            --btn-inactive-text: rgba(0,0,0,0.45);
            --glass-bg-light: rgba(255, 255, 255, 0.95);
            --glass-border-light: 1px solid rgba(0, 0, 0, 0.08);
            --glass-shadow-light: 0 8px 32px rgba(0, 0, 0, 0.12);
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, var(--bg-1), var(--bg-2));
            color: var(--text);
            min-height: 100vh;
            overflow-x: hidden;
            position: relative;
            transition: background 0.4s, color 0.4s;
        }}

        .container {{
            text-align: center;
            padding: clamp(48px, 14vh, 84px) clamp(16px, 5vw, 20px) clamp(36px, 10vh, 60px);
            position: relative;
            z-index: 2;
            max-width: clamp(320px, 90vw, 480px);
            margin: 0 auto;
        }}

        .logo {{
            width: clamp(80px, 22vw, 120px);
            height: clamp(80px, 22vw, 120px);
            border-radius: var(--radius-card);
            margin-bottom: clamp(18px, 4vh, 28px);
            box-shadow: 0 16px 48px rgba(0,0,0,0.5);
        }}

        h1 {{
            font-size: clamp(1.8em, 6vw, 2.6em);
            margin-bottom: clamp(6px, 1.5vh, 10px);
            font-weight: 700;
            background: linear-gradient(135deg, #ff6b6b, #ffa94d, #74b9ff, #a29bfe, #fd79a8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .subtitle {{
            font-size: clamp(0.9em, 2.8vw, 1.1em);
            color: var(--text-secondary);
            margin-bottom: clamp(28px, 7vh, 42px);
            line-height: 1.5;
        }}

        .tabs-container {{
            background: var(--card-bg);
            backdrop-filter: blur(40px) saturate(180%);
            -webkit-backdrop-filter: blur(40px) saturate(180%);
            border-radius: var(--radius-panel);
            padding: 8px;
            border: 1px solid var(--card-border);
            box-shadow: 0 8px 32px var(--card-shadow);
            margin-bottom: clamp(24px, 6vh, 36px);
        }}

        .tabs-header {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 4px;
            margin-bottom: 8px;
        }}

        .tab-btn {{
            background: var(--btn-inactive);
            border: 1px solid var(--btn-inactive-border);
            color: var(--btn-inactive-text);
            padding: 10px 6px;
            border-radius: var(--radius-btn);
            cursor: pointer;
            font-weight: 600;
            font-size: 0.88em;
            transition: all 0.25s;
        }}

        .tab-btn.active {{
            background: rgba(100,180,255,0.18);
            border-color: rgba(100,180,255,0.7);
            color: var(--text);
        }}

        html[data-theme="light"] .tab-btn.active {{
            background: rgba(59,130,246,0.12);
            border-color: rgba(59,130,246,0.5);
            color: #1d4ed8;
        }}

        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; animation: fadeIn 0.25s ease; }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(4px); }} to {{ opacity: 1; transform: translateY(0); }} }}

        .tab-item {{
            background: var(--hover-bg);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-btn);
            padding: 13px 14px;
            margin-bottom: 6px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.2s;
            text-align: left; /* FIX: .container có text-align:center (cho hero),
                                  cần override lại vì tab-item là list item, phải
                                  canh trái như 1 danh sách bình thường */
        }}

        .tab-item:last-child {{ margin-bottom: 0; }}

        .tab-item:active {{
            transform: scale(0.98);
            filter: brightness(0.92);
        }}

        .tab-item h3 {{
            font-size: 0.95em;
            font-weight: 600;
            margin-bottom: 2px;
        }}

        .tab-item p {{
            font-size: 0.75em;
            color: var(--text-secondary);
            margin: 0;
        }}

        .tab-item-icon {{
            font-size: 1.2em;
            flex-shrink: 0;
            margin-left: 10px;
        }}

        /* Mục Premium (trả phí) — tách biệt rõ khỏi mục free bên trên */
        .tab-item-premium {{
            background: linear-gradient(135deg, rgba(132,142,249,0.18), rgba(107,232,160,0.12));
            border: 1px solid rgba(132,142,249,0.4);
            margin-top: 10px;
        }}
        .tab-item-premium h3 {{ color: #a8b1ff; }}
        .premium-divider {{
            display: flex; align-items: center; gap: 8px;
            margin: 10px 0 6px; font-size: 0.7em;
            color: var(--text-secondary); text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .premium-divider::before, .premium-divider::after {{
            content: ''; flex: 1; height: 1px; background: var(--card-border);
        }}

        .info {{
            margin-top: 8px;
            color: var(--text-secondary);
            font-size: 0.85em;
            line-height: 1.8;
        }}

        .top-actions {{
            position: fixed;
            top: max(16px, env(safe-area-inset-top, 16px));
            right: 16px;
            z-index: 100;
            display: flex;
            gap: 8px;
        }}

        .icon-btn {{
            cursor: pointer;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid var(--card-border);
            border-radius: 50%;
            width: 36px; height: 36px;
            font-size: 1.05em;
            color: var(--text);
            display: flex; align-items: center; justify-content: center;
            transition: all 0.2s;
            flex-shrink: 0;
        }}
        html[data-theme="light"] .icon-btn {{ background: rgba(0,0,0,0.05); }}
        .icon-btn:active {{ background: rgba(255,255,255,0.2); transform: scale(0.93); }}
        html[data-theme="light"] .icon-btn:active {{ background: rgba(0,0,0,0.12); }}

        .particle {{ position: fixed; pointer-events: none; z-index: 1; animation: fall linear infinite; }}
        @keyframes fall {{ to {{ transform: translateY(120vh) rotate(360deg); }} }}

        /* ── SETTINGS PANEL — giống hệt apps/debs/dylibs.html (glass, trượt từ phải) ── */

        .settings-overlay {{
            position: fixed; inset: 0;
            background: rgba(0, 0, 0, 0.35);
            backdrop-filter: blur(2px);
            opacity: 0; pointer-events: none;
            transition: opacity 0.3s ease;
            z-index: 300;
        }}
        .settings-overlay.active {{ opacity: 1; pointer-events: auto; }}

        .settings-panel {{
            position: fixed;
            top: max(16px, env(safe-area-inset-top, 16px));
            right: 12px;
            max-height: calc(100vh - 32px);
            width: fit-content;
            min-width: 220px;
            max-width: min(85vw, 320px);
            background: var(--glass-bg);
            backdrop-filter: var(--glass-blur);
            -webkit-backdrop-filter: var(--glass-blur);
            border: var(--glass-border);
            border-radius: var(--glass-radius);
            box-shadow: var(--glass-shadow);
            transform: translateX(calc(100% + 24px)) translateZ(0);
            transition: transform 0.38s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 301;
            display: flex; flex-direction: column;
            padding: 6px 0 10px;
            overflow: hidden;
        }}
        html[data-theme="light"] .settings-panel {{
            background: var(--glass-bg-light);
            border: var(--glass-border-light);
            box-shadow: var(--glass-shadow-light);
        }}
        .settings-panel.active {{ transform: translateX(0) translateZ(0); }}

        .settings-header {{
            display: flex; align-items: center; justify-content: space-between;
            padding: 10px 14px 9px;
            border-bottom: 1px solid var(--card-border);
        }}
        .settings-header h3 {{ font-size: 0.95em; font-weight: 700; letter-spacing: 0.3px; }}

        .settings-close {{
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid var(--card-border);
            color: var(--text);
            width: 32px; height: 32px; border-radius: 50%;
            cursor: pointer; font-size: 0.95em;
            display: flex; align-items: center; justify-content: center;
            flex-shrink: 0; transition: all 0.2s;
        }}
        .settings-close:active {{ background: rgba(255,255,255,0.2); transform: scale(0.93); }}
        html[data-theme="light"] .settings-close {{ background: rgba(0,0,0,0.05); }}

        .settings-list {{
            display: flex; flex-direction: column; gap: 6px;
            padding: 10px 12px;
            overflow-y: auto;
        }}

        .settings-item {{
            display: flex; align-items: center; gap: 10px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 12px;
            padding: 10px 12px;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none; color: var(--text);
        }}
        html[data-theme="light"] .settings-item {{ background: rgba(0,0,0,0.035); }}
        .settings-item:active {{ background: rgba(255,255,255,0.14); transform: scale(0.98); }}
        html[data-theme="light"] .settings-item:active {{ background: rgba(0,0,0,0.08); }}

        .settings-item-account {{
            background: linear-gradient(135deg, rgba(132,142,249,0.22), rgba(107,232,160,0.14));
            border: 1px solid rgba(132,142,249,0.4);
        }}

        .settings-item-icon {{ font-size: 1.1em; width: 20px; text-align: center; flex-shrink: 0; }}
        .settings-item-text {{ display: flex; flex-direction: column; flex: 1; min-width: 0; }}
        .settings-item-title {{ font-weight: 600; font-size: 0.88em; line-height: 1.3; }}
        .settings-item-sub {{
            font-size: 0.72em; color: var(--text-secondary);
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}
    </style>
</head>
<body>

<div class="top-actions">
    <button class="icon-btn" onclick="toggleSettings()" title="Cài đặt">⚙️</button>
</div>

<div class="container">
    <img class="logo" src="{default_icon}" alt="{repo_name}">
    <h1>{repo_name}</h1>
    <p class="subtitle">Kho lưu trữ tổng hợp</p>

    <div class="tabs-container">
        <div class="tabs-header">
            <button class="tab-btn active" onclick="switchTab(event,'ipa')">📱 IPA</button>
            <button class="tab-btn" onclick="switchTab(event,'deb')">🔧 DEB</button>
            <button class="tab-btn" onclick="switchTab(event,'dylib')">📚 DYLIB</button>
        </div>

        <!-- IPA: miễn phí (repo) + trả phí (shop) rõ ràng -->
        <div id="ipa" class="tab-content active">
            <div class="tab-item" onclick="copyText('{base_url}apps.json')">
                <div><h3>Add to Feather</h3><p>Sao chép source link (miễn phí)</p></div>
                <span class="tab-item-icon">📋</span>
            </div>
            <div class="tab-item" onclick="openApp('feather')">
                <div><h3>Open in Feather</h3><p>Mở ứng dụng</p></div>
                <span class="tab-item-icon">🚀</span>
            </div>
            <div class="tab-item" onclick="navigate('./apps.html')">
                <div><h3>View All Apps</h3><p>Danh sách đầy đủ (miễn phí)</p></div>
                <span class="tab-item-icon">→</span>
            </div>
            <div class="premium-divider">Bản trả phí</div>
            <div class="tab-item tab-item-premium" onclick="navigate('./apps.html')">
                <div><h3>🛒 IPA Premium</h3><p>Xem giá & mua trong danh sách đầy đủ</p></div>
                <span class="tab-item-icon">→</span>
            </div>
        </div>

        <!-- DEB: miễn phí (repo) + trả phí (shop) -->
        <div id="deb" class="tab-content">
            <div class="tab-item" onclick="copyText('{base_url}')">
                <div><h3>Add to Sileo</h3><p>Sao chép source link (miễn phí)</p></div>
                <span class="tab-item-icon">📋</span>
            </div>
            <div class="tab-item" onclick="openApp('sileo')">
                <div><h3>Open in Sileo</h3><p>Mở ứng dụng</p></div>
                <span class="tab-item-icon">🚀</span>
            </div>
            <div class="tab-item" onclick="navigate('./debs.html')">
                <div><h3>View All Tweaks</h3><p>Danh sách đầy đủ (miễn phí)</p></div>
                <span class="tab-item-icon">→</span>
            </div>
            <div class="premium-divider">Bản trả phí</div>
            <div class="tab-item tab-item-premium" onclick="navigate('./debs.html')">
                <div><h3>🛒 Tweak Premium</h3><p>Xem giá & mua trong danh sách đầy đủ</p></div>
                <span class="tab-item-icon">→</span>
            </div>
        </div>

        <!-- DYLIB: miễn phí (repo) + trả phí (shop) -->
        <div id="dylib" class="tab-content">
            <div class="tab-item" onclick="copyText('{base_url}dylibs.json')">
                <div><h3>Add to Developer</h3><p>Sao chép source link (miễn phí)</p></div>
                <span class="tab-item-icon">📋</span>
            </div>
            <div class="tab-item" onclick="openApp('developer')">
                <div><h3>Open in Developer</h3><p>Mở ứng dụng</p></div>
                <span class="tab-item-icon">🚀</span>
            </div>
            <div class="tab-item" onclick="navigate('./dylibs.html')">
                <div><h3>View All Dylibs</h3><p>Danh sách đầy đủ (miễn phí)</p></div>
                <span class="tab-item-icon">→</span>
            </div>
            <div class="premium-divider">Bản trả phí</div>
            <div class="tab-item tab-item-premium" onclick="navigate('./dylibs.html')">
                <div><h3>🛒 Dylib Premium</h3><p>Xem giá & mua trong danh sách đầy đủ</p></div>
                <span class="tab-item-icon">→</span>
            </div>
        </div>
    </div>

    <div class="info">
        <p><b>──⋆⋅☆⋅⋆જ⁀➴ₖ🦎ᵢ꜀︵✰⋆⋅☆⋅⋆──</b></p>
        <p>Made with ❤️ by <b>Kyic</b></p>
    </div>
</div>

<!-- Settings Panel — cùng cấu trúc HTML với apps/debs/dylibs.html -->
<div class="settings-overlay" id="settingsOverlay" onclick="closeSettings()"></div>
<div class="settings-panel" id="settingsPanel">
    <div class="settings-header">
        <h3>⚙️ Cài đặt</h3>
        <button class="settings-close" onclick="closeSettings()">✕</button>
    </div>
    <div class="settings-list">
        <!-- Account - ĐẦU TIÊN, quyết định luồng đăng nhập/dashboard -->
        <div class="settings-item settings-item-account" onclick="goAccount()">
            <div class="settings-item-icon">👤</div>
            <div class="settings-item-text">
                <div class="settings-item-title" id="accountLabel">Tài khoản</div>
                <div class="settings-item-sub" id="accountSub">Đăng nhập / Đăng ký</div>
            </div>
        </div>

        <a class="settings-item" href="./sign.html">
            <div class="settings-item-icon">🖊️</div>
            <div class="settings-item-text">
                <div class="settings-item-title">Sign IPA</div>
                <div class="settings-item-sub">Ký lại file .ipa để cài đặt</div>
            </div>
        </a>

        <div class="settings-item" onclick="alert('🌐 Ngôn ngữ: Tiếng Việt (mặc định)')">
            <div class="settings-item-icon">🌐</div>
            <div class="settings-item-text">
                <div class="settings-item-title">Ngôn ngữ</div>
                <div class="settings-item-sub">Tiếng Việt</div>
            </div>
        </div>

        <div class="settings-item" onclick="toggleTheme()">
            <div class="settings-item-icon">🌙</div>
            <div class="settings-item-text">
                <div class="settings-item-title">Chủ đề</div>
                <div class="settings-item-sub" id="themeSub">Tối</div>
            </div>
        </div>

        <a class="settings-item" href="{telegram_channel_url}" target="_blank" rel="noopener noreferrer">
            <div class="settings-item-icon">💬</div>
            <div class="settings-item-text">
                <div class="settings-item-title">Nhắn tin</div>
                <div class="settings-item-sub">Tham gia kênh Telegram</div>
            </div>
        </a>

        <a class="settings-item" href="{donate_url}" target="_blank" rel="noopener noreferrer">
            <div class="settings-item-icon">☕</div>
            <div class="settings-item-text">
                <div class="settings-item-title">Donate</div>
                <div class="settings-item-sub">Ủng hộ một ly cà phê ☕</div>
            </div>
        </a>
    </div>
</div>

<script>
    const SUPABASE_URL = "{supabase_url}";
    const SUPABASE_ANON_KEY = "{supabase_anon_key}";
    const sb = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

    const emojis = ['🍂','❄️','🌿','✨','☀️','🌸','🦎','💧','⚡️'];
    function createParticle() {{
        const p = document.createElement('div');
        p.className = 'particle';
        p.textContent = emojis[Math.floor(Math.random() * emojis.length)];
        p.style.cssText = `left:${{Math.random()*100}}vw;top:-30px;animation-duration:${{Math.random()*12+8}}s`;
        document.body.appendChild(p);
        setTimeout(() => p.remove(), 20000);
    }}
    setInterval(createParticle, 500);

    function toggleTheme() {{
        const h = document.documentElement;
        const isLight = h.getAttribute('data-theme') === 'light';
        h.setAttribute('data-theme', isLight ? '' : 'light');
        const sub = document.getElementById('themeSub');
        if (sub) sub.textContent = isLight ? 'Tối' : 'Sáng';
    }}

    function switchTab(e, id) {{
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.getElementById(id).classList.add('active');
        e.currentTarget.classList.add('active');
    }}

    function copyText(t) {{
        navigator.clipboard.writeText(t).then(() => alert('✅ Đã copy!'));
    }}

    function navigate(u) {{ window.location.href = u; }}

    function openApp(t) {{
        const urls = {{
            feather:   'feather://add-source?url={base_url}apps.json',
            sileo:     'sileo://source/{base_url}',
            developer: 'developer://add-source?url={base_url}dylibs.json'
        }};
        window.location.href = urls[t];
    }}

    // ──────────────────────────────────────────────
    // SETTINGS PANEL — cùng pattern với apps/debs/dylibs.html
    // (overlay + panel trượt từ phải, dùng class "active")
    // ──────────────────────────────────────────────
    function toggleSettings() {{
        const panel = document.getElementById('settingsPanel');
        const overlay = document.getElementById('settingsOverlay');
        if (!panel || !overlay) return;
        const isOpen = panel.classList.contains('active');
        if (isOpen) {{
            closeSettings();
        }} else {{
            panel.classList.add('active');
            overlay.classList.add('active');
        }}
    }}
    function closeSettings() {{
        const panel = document.getElementById('settingsPanel');
        const overlay = document.getElementById('settingsOverlay');
        if (panel) panel.classList.remove('active');
        if (overlay) overlay.classList.remove('active');
    }}

    // ──────────────────────────────────────────────
    // ACCOUNT LOGIC — phân biệt rõ: chưa login → auth.html,
    // đã login → dashboard.html (KHÔNG code trùng ở đây, chỉ điều hướng)
    // ──────────────────────────────────────────────
    async function updateAccountUI() {{
        const {{ data: {{ session }} }} = await sb.auth.getSession();
        const sub = document.getElementById('accountSub');
        if (session) {{
            sub.textContent = session.user.email || 'Xem license & đơn hàng của bạn';
        }} else {{
            sub.textContent = 'Đăng nhập / Đăng ký';
        }}
    }}

    async function goAccount() {{
        const {{ data: {{ session }} }} = await sb.auth.getSession();
        closeSettings();
        window.location.href = session ? './dashboard.html' : './auth.html';
    }}

    updateAccountUI();
</script>
</body>
</html>
"""


def build_index_view(output_file, supabase_url, supabase_anon_key):
    """
    Sinh trang index.html — TRANG CHỦ (browse, KHÔNG phải trang mua hàng).

    Giữ nguyên thiết kế gốc (particle background, gradient, 3 tab IPA/DEB/DYLIB,
    theme toggle) — chỉ bổ sung:
      • Nút ⚙️ mở sheet "Cài đặt" (Tài khoản/Ngôn ngữ/Chủ đề/Telegram/Donate)
      • Mỗi tab phân tách RÕ 2 khu vực:
        - Mục MIỄN PHÍ (Add to X / Open in X / View All) — hành vi cũ, không đổi
        - Mục TRẢ PHÍ ("🛒 X Premium") — dẫn sang apps/debs/dylibs.html (View All),
          nơi giá tiền hiện trực tiếp ngay trên từng sản phẩm

    Phân biệt vai trò các trang (kiến trúc đã đơn giản hoá — KHÔNG còn shop.html):
      • index.html      = TRANG CHỦ — chỉ để duyệt/điều hướng, không xử lý mua bán
      • apps/debs/dylibs.html = danh sách ĐẦY ĐỦ (miễn phí "Nhận" + trả phí hiện
        giá trực tiếp, bấm giá = thêm vào giỏ hàng)
      • dashboard.html   = TRUNG TÂM QUẢN LÝ DUY NHẤT — Mã ID, UDID đã lưu
        (tự động lấy qua .mobileconfig), giỏ hàng, kho ứng dụng, checkout
        (PayPal/PayOS/MoMo), license đã mua
      • auth.html        = đăng nhập/đăng ký (điều kiện tiên quyết cho dashboard)
    """
    html = INDEX_HTML_TEMPLATE.format(
        repo_name=config.REPO_NAME,
        tint=config.TINT_COLOR,
        default_icon=config.SOURCE_LOGO,
        base_url=config.BASE_URL,
        supabase_url=supabase_url,
        supabase_anon_key=supabase_anon_key,
        telegram_channel_url="#",  # TODO: set from config (link kênh Telegram thật)
        donate_url="#",  # TODO: set from config (link donate thật)
    )

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ Tạo xong: {output_file}")



SIGN_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="theme-color" content="#0a1428">
    <title>Sign IPA — {repo_name}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }}
        html, body {{
            background: #0a1428; color: #fff;
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif;
            min-height: 100vh;
        }}
        .header {{
            background: rgba(10,20,40,0.95);
            backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
            padding: 12px 16px;
            display: grid; grid-template-columns: 1fr auto 1fr;
            align-items: center;
            position: sticky; top: 0; z-index: 100;
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }}
        .header-brand {{ justify-self: center; font-weight: 800; font-size: 15px; white-space: nowrap; }}
        .header-btn {{
            width: 36px; height: 36px; justify-self: start;
            display: flex; align-items: center; justify-content: center;
            color: #{tint}; font-size: 16px; text-decoration: none;
            border-radius: 50%; background: rgba(132,142,249,0.15);
            transition: 0.15s; border: none; cursor: pointer;
        }}
        .header-btn:active {{ background: rgba(132,142,249,0.28); transform: scale(0.93); }}

        .container {{ padding: 20px; padding-bottom: 60px; }}

        .intro-card {{
            background: linear-gradient(135deg, #0f1e3d, #1a2a50);
            border: 1px solid rgba(132,142,249,0.3);
            border-radius: 20px; padding: 20px; margin-bottom: 20px;
        }}
        .intro-title {{ font-size: 17px; font-weight: 700; margin-bottom: 8px; }}
        .intro-desc {{ font-size: 13px; color: #b0bcd4; line-height: 1.6; }}
        .intro-note {{
            margin-top: 12px; padding: 10px 12px; border-radius: 12px;
            background: rgba(255,193,7,0.1); border: 1px solid rgba(255,193,7,0.25);
            font-size: 12px; color: #ffd166; line-height: 1.5;
        }}

        .section-title {{
            padding: 0 4px 10px; font-size: 13px; font-weight: 600;
            color: #8e9ab5; text-transform: uppercase; letter-spacing: 0.5px;
        }}

        .tool-list {{ display: flex; flex-direction: column; gap: 12px; }}
        .tool-card {{
            background: #0f1e3d; border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px; padding: 16px;
            display: flex; align-items: center; gap: 14px;
            text-decoration: none; color: #fff;
            transition: 0.15s;
        }}
        .tool-card:active {{ transform: scale(0.98); background: #142544; }}
        .tool-icon {{
            width: 44px; height: 44px; border-radius: 12px; flex-shrink: 0;
            background: rgba(132,142,249,0.15);
            display: flex; align-items: center; justify-content: center;
            font-size: 20px;
        }}
        .tool-info {{ flex: 1; min-width: 0; }}
        .tool-name {{ font-size: 15px; font-weight: 700; margin-bottom: 2px; }}
        .tool-desc {{ font-size: 12px; color: #8e9ab5; }}
        .tool-arrow {{ color: #{tint}; font-size: 16px; flex-shrink: 0; }}

        .disclaimer {{
            margin-top: 24px; padding: 14px; border-radius: 14px;
            background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
            font-size: 11px; color: #8e9ab5; line-height: 1.6;
        }}
    </style>
</head>
<body>
    <div class="header">
        <a href="./index.html" class="header-btn" title="Trang chủ">🏠</a>
        <span class="header-brand">{repo_name}</span>
        <span></span>
    </div>

    <div class="container">
        <div class="intro-card">
            <div class="intro-title">🖊️ Sign IPA</div>
            <div class="intro-desc">
                Ký lại file .ipa để cài đặt trên thiết bị không jailbreak,
                dùng chứng chỉ riêng của bạn hoặc chứng chỉ công khai từ
                các công cụ bên dưới.
            </div>
            <div class="intro-note">
                ⚠️ Đây là các công cụ BÊN THỨ BA, không thuộc {repo_name}.
                Bấm vào sẽ mở tab mới sang trang của họ — hãy tự kiểm tra
                độ tin cậy trước khi upload file/chứng chỉ.
            </div>
        </div>

        <div class="section-title">Công cụ ký công khai</div>
        <div class="tool-list">
            <a class="tool-card" href="https://sign.ipasign.cc/" target="_blank" rel="noopener noreferrer">
                <div class="tool-icon">📝</div>
                <div class="tool-info">
                    <div class="tool-name">IPASignX</div>
                    <div class="tool-desc">Ký IPA online, không cần macOS</div>
                </div>
                <div class="tool-arrow">↗</div>
            </a>
            <a class="tool-card" href="https://swiftsign.dev/pages/signer" target="_blank" rel="noopener noreferrer">
                <div class="tool-icon">🪶</div>
                <div class="tool-info">
                    <div class="tool-name">SwiftSign</div>
                    <div class="tool-desc">Ký bằng chứng chỉ riêng của bạn, file giữ 6 giờ</div>
                </div>
                <div class="tool-arrow">↗</div>
            </a>
            <a class="tool-card" href="https://signtools.ipaomtk.com/" target="_blank" rel="noopener noreferrer">
                <div class="tool-icon">📲</div>
                <div class="tool-info">
                    <div class="tool-name">IPA Installer (SignTools)</div>
                    <div class="tool-desc">Ký & cài trực tiếp từ trình duyệt di động</div>
                </div>
                <div class="tool-arrow">↗</div>
            </a>
            <a class="tool-card" href="https://signer.apptesters.org/" target="_blank" rel="noopener noreferrer">
                <div class="tool-icon">🧪</div>
                <div class="tool-info">
                    <div class="tool-name">AppTesters Signer</div>
                    <div class="tool-desc">Hỗ trợ inject dylib tuỳ chọn khi ký</div>
                </div>
                <div class="tool-arrow">↗</div>
            </a>
        </div>

        <div class="disclaimer">
            {repo_name} chỉ cung cấp liên kết điều hướng tới các công cụ ký
            công khai có sẵn trên internet, không lưu trữ, không xử lý,
            và không chịu trách nhiệm về nội dung/chứng chỉ/độ an toàn
            của các dịch vụ bên thứ ba nói trên.
        </div>
    </div>
</body>
</html>
"""


def build_sign_view(output_file):
    """
    Sinh trang sign.html — trang ĐIỀU HƯỚNG (không tự ký) tới các công
    cụ ký .ipa công khai có sẵn trên internet (mở tab mới khi bấm).

    KHÔNG tích hợp API thật với các dịch vụ này vì:
      • Không dịch vụ nào công bố Public API chính thức cho bên thứ 3
      • Gọi ngầm endpoint nội bộ của họ sẽ không ổn định và có thể vi
        phạm điều khoản dịch vụ

    Nếu về sau có VPS/server riêng, có thể nâng cấp thành tích hợp thật
    bằng cách tự host zsign (https://github.com/zhlynn/zsign) + viết
    1 API HTTP wrapper riêng.
    """
    html = SIGN_HTML_TEMPLATE.format(
        repo_name=config.REPO_NAME,
        tint=config.TINT_COLOR,
    )
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ Tạo xong: {output_file}")


CHECKOUT_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#0a1428">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        html, body {{
            background: #0a1428; color: #fff;
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif;
            min-height: 100vh; display: flex; align-items: center; justify-content: center;
        }}
        .card {{
            background: #0f1e3d; border-radius: 20px; padding: 40px 24px;
            text-align: center; max-width: 400px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .icon {{
            font-size: 64px; margin-bottom: 16px;
        }}
        h1 {{ font-size: 24px; margin-bottom: 8px; }}
        p {{ color: #8e9ab5; font-size: 14px; margin-bottom: 24px; }}
        .btn {{
            display: inline-block;
            padding: 12px 28px; border-radius: 12px;
            border: none; cursor: pointer; font-weight: 700;
            text-decoration: none; font-size: 14px;
            transition: 0.15s;
        }}
        .btn-primary {{
            background: #{tint}; color: #fff;
        }}
        .btn-primary:active {{ transform: scale(0.96); }}
        .btn-secondary {{
            background: rgba(255,255,255,0.1); color: #8e9ab5;
        }}
        .space {{ margin: 12px; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon" id="icon">{icon}</div>
        <h1 id="title">{title}</h1>
        <p id="message">{message}</p>
        <a href="./dashboard.html" class="btn btn-primary">Xem License</a>
        <div class="space"></div>
        <a href="./index.html" class="btn btn-secondary">Tiếp tục mua</a>
    </div>

    <script>
        const SUPABASE_URL = "{supabase_url}";
        const SUPABASE_ANON_KEY = "{supabase_anon_key}";
        const sb = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

        async function processCallback() {{
            const params = new URLSearchParams(location.search);
            const orderId = params.get('order');
            
            if (!orderId) {{
                document.getElementById('message').textContent = 'Không tìm thấy đơn hàng.';
                return;
            }}

            const {{ data: {{ session }} }} = await sb.auth.getSession();
            if (!session) {{
                location.href = './auth.html';
                return;
            }}

            // Nếu là success → gọi issue-license
            if ('{status}' === 'success') {{
                const {{ data: order }} = await sb.from('orders')
                    .select('*').eq('id', orderId).single();
                
                if (order && order.status === 'paid') {{
                    // Đơn hàng đã thanh toán, License đã được cấp
                    return;
                }}
                
                // Nếu chưa → gọi issue-license
                const resp = await fetch(SUPABASE_URL + '/functions/v1/issue-license', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + session.access_token
                    }},
                    body: JSON.stringify({{
                        product_id: order.product_id,
                        udid: order.udid,
                        provider: order.provider,
                        txn_id: order.provider_txn_id
                    }})
                }});
                const result = await resp.json();
                if (!result.license_key) {{
                    document.getElementById('message').textContent = '❌ Lỗi: ' + result.error;
                }}
            }}
        }}

        processCallback();
    </script>
</body>
</html>
"""


def build_checkout_view(status, output_file, supabase_url, supabase_anon_key):
    """
    Sinh trang checkout-success.html hoặc checkout-cancel.html
    
    status: 'success' hoặc 'cancel'
    """
    if status == 'success':
        icon = '✅'
        title = 'Thanh toán thành công!'
        message = 'Hệ thống đang tạo license cho bạn. Xem chi tiết ở dashboard.'
    else:
        icon = '❌'
        title = 'Thanh toán bị huỷ'
        message = 'Bạn đã huỷ quá trình thanh toán. Thử lại bất cứ lúc nào.'

    html = CHECKOUT_TEMPLATE.format(
        status=status,
        icon=icon,
        title=title,
        message=message,
        tint=config.TINT_COLOR,
        supabase_url=supabase_url,
        supabase_anon_key=supabase_anon_key,
    )

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ Tạo xong: {output_file}")


ROOT_REDIRECT_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0; url=./html/index.html">
    <link rel="canonical" href="./html/index.html">
    <title>Đang chuyển hướng...</title>
    <style>
        body {{ background:#0a1428; color:#fff; font-family:-apple-system,sans-serif;
                display:flex; align-items:center; justify-content:center; height:100vh; margin:0; }}
        a {{ color:#{tint}; }}
    </style>
</head>
<body>
    <p>Đang chuyển hướng... nếu không tự chuyển, <a href="./html/index.html">bấm vào đây</a>.</p>
    <script>window.location.replace('./html/index.html');</script>
</body>
</html>
"""


def build_root_redirect(output_file):
    """
    Sinh file repo/index.html (redirect) — giữ cho URL gốc
    https://2kgt.github.io/repo/ vẫn hoạt động bình thường sau khi
    trang chủ THẬT đã chuyển vào repo/html/index.html.
    """
    html = ROOT_REDIRECT_TEMPLATE.format(tint=config.TINT_COLOR)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ Tạo xong: {output_file} (redirect → html/index.html)")


def build_all_views(supabase_url=None, supabase_anon_key=None):
    """
    Sinh toàn bộ HTML views (index/apps/debs/dylibs/auth/shop/dashboard) trong 1 lần gọi.
    Được main.py gọi tự động sau mỗi lần chạy pipeline, và cũng có thể
    chạy độc lập qua `python3 views.py` để test riêng phần giao diện.

    supabase_url/supabase_anon_key/paypal_client_id: nếu không truyền vào,
    sẽ đọc từ biến môi trường (GitHub Secrets khi chạy trong Actions).
    """
    # ──── Định nghĩa config từ env hoặc tham số ────
    resolved_url = supabase_url or os.getenv("SUPABASE_URL") or "https://vubnjcnhdbwrwfstavft.supabase.co"
    resolved_key = supabase_anon_key or os.getenv("SUPABASE_ANON_KEY") or "sb_publishable_akuKZo7u5dAhvj8RQvltyg__T6Acs66"
    paypal_id    = os.getenv("PAYPAL_CLIENT_ID") or "YOUR_PAYPAL_CLIENT_ID"

    path_apps = os.path.join(config.REPO_OUTPUT_DIR, "apps.json")
    path_tweaks = os.path.join(config.REPO_OUTPUT_DIR, "debs.json")
    path_dylibs = os.path.join(config.REPO_OUTPUT_DIR, "dylibs.json")

    # ──── Sinh tất cả HTML → repo/html/  (+ JS tách riêng → repo/js/) ────
    # 0. Trang redirect ở repo root (giữ URL gốc .../repo/ hoạt động bình thường
    #    sau khi index.html thật đã chuyển vào repo/html/)
    build_root_redirect(os.path.join(config.REPO_OUTPUT_DIR, "index.html"))

    # 1. Trang chủ (index.html) — phải trước vì reference apps/debs/dylibs.json
    build_index_view(
        os.path.join(config.REPO_HTML_DIR, "index.html"),
        supabase_url=resolved_url,
        supabase_anon_key=resolved_key
    )

    # 2. Trang danh sách sản phẩm (apps/debs/dylibs.html) — từ JSON (vẫn ở repo/ gốc)
    build_view(os.path.join(config.REPO_HTML_DIR, "apps.html"), "Apps", path_apps, "apps", "apps", "apps",
               supabase_url=resolved_url, supabase_anon_key=resolved_key)
    build_view(os.path.join(config.REPO_HTML_DIR, "debs.html"), "Tweaks", path_tweaks, "apps", "tweaks", "tweaks",
               supabase_url=resolved_url, supabase_anon_key=resolved_key)
    build_view(os.path.join(config.REPO_HTML_DIR, "dylibs.html"), "Dylibs", path_dylibs, "apps", "dylibs", "dylibs",
               supabase_url=resolved_url, supabase_anon_key=resolved_key)

    # 3. Trang đăng nhập/đăng ký (auth.html) — Giai đoạn 2
    build_auth_view(
        os.path.join(config.REPO_HTML_DIR, "auth.html"),
        supabase_url=resolved_url,
        supabase_anon_key=resolved_key
    )

    # 4. Trang quản lý tài khoản (dashboard.html) — TRUNG TÂM DUY NHẤT
    # (đã gộp toàn bộ chức năng mua hàng/checkout từ shop.html vào đây —
    #  shop.html không còn tồn tại nữa)
    build_dashboard_view(
        os.path.join(config.REPO_HTML_DIR, "dashboard.html"),
        supabase_url=resolved_url,
        supabase_anon_key=resolved_key,
        paypal_client_id=paypal_id
    )

    # 5. Trang thành công/huỷ thanh toán (checkout-success/cancel) — Giai đoạn 4
    build_checkout_view("success", os.path.join(config.REPO_HTML_DIR, "checkout-success.html"), resolved_url, resolved_key)
    build_checkout_view("cancel", os.path.join(config.REPO_HTML_DIR, "checkout-cancel.html"), resolved_url, resolved_key)

    # 6. Trang Sign IPA (điều hướng tới công cụ ký công khai bên ngoài)
    build_sign_view(os.path.join(config.REPO_HTML_DIR, "sign.html"))

    print("🎉 Tất cả HTML views v4 đã được tạo thành công!")


if __name__ == "__main__":
    build_all_views()
