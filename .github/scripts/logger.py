# .github/scripts/logger.py
import os
import requests
import html
import time

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
MSG_ID_FILE = ".github_telegram_msg_id"

MAX_LOG_LINES = 6
_accumulated_logs = []

def _get_saved_msg_id():
    if os.path.exists(MSG_ID_FILE):
        with open(MSG_ID_FILE, "r") as f:
            val = f.read().strip()
            return int(val) if val.isdigit() else None
    return None

def _save_msg_id(msg_id):
    with open(MSG_ID_FILE, "w") as f:
        f.write(str(msg_id))

def _clear_saved_msg_id():
    if os.path.exists(MSG_ID_FILE):
        os.remove(MSG_ID_FILE)

def log_step(current_step, status="running", live_log=""):
    """
    Hàm log Terminal: Cuộn 6 dòng, hiển thị đếm ngược 9 giây real-time và tự hủy.
    """
    if not TOKEN or not CHAT_ID: return

    global _accumulated_logs
    msg_id = _get_saved_msg_id()
    
    # 1. Nạp và cuộn log chi tiết (Tối đa 6 dòng)
    if live_log:
        if any(keyword in live_log.lower() for keyword in ["khởi động", "feather", "sileo", "deploy", "hoàn thành"]):
            live_log = f"<b>{live_log}</b>"
            
        _accumulated_logs.append(live_log)
        if len(_accumulated_logs) > MAX_LOG_LINES:
            _accumulated_logs.pop(0)

    # 2. Giao diện Terminal bọc khung siêu sạch
    lines = ["<code>──────────────────────────────</code>"]
    
    if _accumulated_logs:
        formatted_lines = []
        for log in _accumulated_logs:
            if log.startswith("<b>") and log.endswith("</b>"):
                inner_text = log[3:-4]
                formatted_lines.append(f"<b>{html.escape(inner_text)}</b>")
            else:
                formatted_lines.append(f"<code>{html.escape(log)}</code>")
        lines.append("\n".join(formatted_lines))
    else:
        lines.append("<code>⏳ System initializing...</code>")
        
    lines.append("<code>──────────────────────────────</code>")
    
    # Trạng thái tổng quát dưới cùng khi đang chạy
    if not (current_step == "deploy" and status == "success"):
        lines.append("⚡ <b>Status:</b> Running...")

    text = "\n".join(lines)
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}

    try:
        # 3. Gửi hoặc chỉnh sửa tin nhắn trạng thái hiện tại
        if msg_id is None:
            res = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json=payload, timeout=10).json()
            if res.get("ok"):
                msg_id = res["result"]["message_id"]
                _save_msg_id(msg_id)
        else:
            payload["message_id"] = msg_id
            requests.post(f"https://api.telegram.org/bot{TOKEN}/editMessageText", json=payload, timeout=10)
            
        # 4. Cơ chế ĐẾM NGƯỢC THỜI GIAN THỰC (9 giây) VÀ TỰ HỦY LOG
        if current_step == "deploy" and status == "success":
            # Chạy vòng lặp đếm ngược từ 9 về 1 giây
            for seconds_left in range(9, 0, -1):
                # Tạo giao diện kèm dòng chữ cảnh báo đếm ngược của anh
                countdown_lines = list(lines) # Sao chép lại khung log hiện tại
                countdown_lines.append(f"🏁 <b>Status:</b> Success")
                countdown_lines.append(f"⚠️ <i>Tin nhắn này sẽ tự hủy sau {seconds_left} giây...</i>")
                
                payload["text"] = "\n".join(countdown_lines)
                requests.post(f"https://api.telegram.org/bot{TOKEN}/editMessageText", json=payload, timeout=5)
                
                time.sleep(1) # Nghỉ đúng 1 giây trước khi hạ số xuống
            
            # Kích hoạt xóa hoàn toàn tin nhắn sau khi đếm ngược về 0
            del_res = requests.post(f"https://api.telegram.org/bot{TOKEN}/deleteMessage", json={
                "chat_id": CHAT_ID, "message_id": msg_id
            }, timeout=10).json()
            
            if del_res.get("ok"):
                _clear_saved_msg_id()
                
    except Exception as e:
        print(f"Telegram Live Log Error: {e}")
