# .github/scripts/logger.py
import os
import requests
import sys
import time

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_CHANNEL")

_msg_id = None
_log_buffer = []

# Cấu hình thời gian chờ tự hủy ban đầu (Tính bằng giây)
X_TIME = 15  
time_to_expire = time.time() + X_TIME
extended_count = 1

def _get_keyboard():
    """Tạo nút bấm hiển thị số giây đếm ngược để anh Đức tương tác gia hạn"""
    global time_to_expire
    remaining = int(max(0, time_to_expire - time.time()))
    return {
        "inline_keyboard": [[
            {"text": f"⏱️ Giữ thêm log ({remaining}s)", "callback_data": "extend_log"}
        ]]
    }

def _send_or_edit_telegram(text, should_delete=False, check_timeout=False):
    """Hàm lõi điều khiển vòng đời tin nhắn Log trực tuyến"""
    if not TOKEN or not CHAT_ID:
        return

    global _msg_id, time_to_expire, extended_count

    # KỊCH BẢN 1: Tự động hủy tin nhắn nếu hết thời gian chờ
    if check_timeout and _msg_id is not None:
        if time.time() > time_to_expire:
            try:
                url = f"https://api.telegram.org/bot{TOKEN}/deleteMessage"
                requests.post(url, json={"chat_id": CHAT_ID, "message_id": _msg_id}, timeout=5)
                _msg_id = None
            except Exception:
                pass
        else:
            try:
                url = f"https://api.telegram.org/bot{TOKEN}/editMessageReplyMarkup"
                requests.post(url, json={"chat_id": CHAT_ID, "message_id": _msg_id, "reply_markup": _get_keyboard()}, timeout=5)
            except Exception:
                pass
        return

    # KỊCH BẢN 2: Lệnh chủ động dọn dẹp sạch sẽ khi chạy xong
    if should_delete:
        if _msg_id is not None:
            try:
                url = f"https://api.telegram.org/bot{TOKEN}/deleteMessage"
                requests.post(url, json={"chat_id": CHAT_ID, "message_id": _msg_id}, timeout=10)
                _msg_id = None
            except Exception:
                pass
        return

    # KỊCH BẢN 3: Cập nhật nội dung log chạy trực tuyến (Tối đa 3 dòng)
    payload = {
        "chat_id": CHAT_ID,
        "text": f"<pre>{text}</pre>",
        "parse_mode": "HTML",
        "reply_markup": _get_keyboard()
    }

    try:
        _check_and_handle_callback()

        if _msg_id is None:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            res = requests.post(url, json=payload, timeout=10).json()
            if res.get("ok"):
                _msg_id = res["result"]["message_id"]
                time_to_expire = time.time() + X_TIME
                extended_count = 1
        else:
            payload["message_id"] = _msg_id
            url = f"https://api.telegram.org/bot{TOKEN}/editMessageText"
            requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ Lỗi cập nhật log: {e}", file=sys.stderr)

def _check_and_handle_callback():
    """Nhận diện tín hiệu bấm nút từ anh Đức để nhân đôi thời gian sống của log"""
    global time_to_expire, extended_count
    if not _msg_id:
        return
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        res = requests.get(url, json={"offset": -1, "timeout": 0}, timeout=5).json()
        if res.get("ok") and res.get("result"):
            for update in res["result"]:
                callback = update.get("callback_query")
                if callback and callback.get("message", {}).get("message_id") == _msg_id:
                    if callback.get("data") == "extend_log":
                        extended_count *= 2
                        time_to_expire = time.time() + (X_TIME * extended_count)
                        
                        confirm_url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
                        requests.post(confirm_url, json={"callback_query_id": callback["id"], "text": f"🚀 Đã gia hạn! Log sẽ giữ thêm {X_TIME * extended_count} giây."}, timeout=5)
    except Exception:
        pass

def maintenance_heartbeat():
    _send_or_edit_telegram("", check_timeout=True)

def clear_live_logs():
    _send_or_edit_telegram("", should_delete=True)
    time.sleep(1.0)

def info(text):
    clean_text = f"[INFO] {text}"
    print(clean_text)
    _log_buffer.append(clean_text)
    if len(_log_buffer) > 3: _log_buffer.pop(0)  # Giữ đúng 3 dòng
    _send_or_edit_telegram("\n".join(_log_buffer))

def success(text):
    clean_text = f"[SUCCESS] ✅ {text}"
    print(clean_text)
    _log_buffer.append(clean_text)
    if len(_log_buffer) > 3: _log_buffer.pop(0)  # Giữ đúng 3 dòng
    _send_or_edit_telegram("\n".join(_log_buffer))

def error(text):
    clean_text = f"[ERROR] ❌ {text}"
    print(clean_text, file=sys.stderr)
    _log_buffer.append(clean_text)
    if len(_log_buffer) > 3: _log_buffer.pop(0)  # Giữ đúng 3 dòng
    _send_or_edit_telegram("\n".join(_log_buffer))

def ai(text):
    clean_text = f"[AI] 🔮 {text}"
    print(clean_text)
    _log_buffer.append(clean_text)
    if len(_log_buffer) > 3: _log_buffer.pop(0)  # Giữ đúng 3 dòng
    _send_or_edit_telegram("\n".join(_log_buffer))
