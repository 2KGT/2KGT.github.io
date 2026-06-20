# 
import os
import subprocess
import datetime

try:
    from zoneinfo import ZoneInfo
    HANOI_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
except Exception:
    HANOI_TZ = datetime.timezone(datetime.timedelta(hours=7))  # fallback nếu thiếu tzdata


def now_hanoi():
    return datetime.datetime.now(HANOI_TZ)


# ==========================================
# PHẦN 1: SINH CHANGELOG (bảng dọc 2 cột, gọn cho màn hình điện thoại)
# ==========================================

ACTION_LABELS = {
    "A": "✨ Thêm",
    "M": "✏️ Sửa",
    "D": "🗑️ Xoá",
    "R": "🔀 Đổi tên",
    "?": "✨ Thêm",  # untracked file mới = coi như Thêm
}

ACTION_ORDER = ["A", "M", "D", "R", "?"]

MAX_VISIBLE_ROWS = 12  # số file hiện trực tiếp trước khi gói vào <details> để cuộn

# Suy luận "Nguyên nhân" theo phần mở rộng / thư mục bị động tới
CAUSE_RULES = [
    (("repo/apps/",), "Cập nhật danh sách ứng dụng"),
    (("repo/debs/", ".deb"), "Cập nhật gói .deb"),
    (("repo/depictions/icons/", ".png", ".jpg", ".jpeg", ".svg"), "Cập nhật hình ảnh / icon"),
    (("repo/depictions/",), "Cập nhật mô tả ứng dụng (depiction)"),
    ((".py",), "Cập nhật logic script tự động hoá"),
    ((".html",), "Sinh lại trang web (views)"),
    ((".json",), "Cập nhật cấu hình"),
    ((".yml", ".yaml"), "Cập nhật workflow CI/CD"),
]


def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


def run_raw(cmd):
    """Như run(), nhưng KHÔNG strip() toàn chuỗi — chỉ bỏ newline cuối.
    Bắt buộc dùng cho `git status --porcelain`, vì status code có thể là
    khoảng trắng (" D", " M"...) và .strip() sẽ ăn mất nó ở dòng đầu tiên."""
    out = subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout
    return out.rstrip("\n")


def collect_working_tree_changes():
    """
    Lấy toàn bộ thay đổi hiện có ở working tree (staged + unstaged + untracked),
    bất kể đã commit hay chưa. Đây là trạng thái thật của lần chạy workflow này,
    vì logs.py chạy trước bước commit.
    """
    raw = run_raw("git status --porcelain -- . ':!docs' ':!.github'")
    if not raw:
        return {}

    grouped = {}
    for line in raw.splitlines():
        if not line:
            continue
        status = line[:2]
        path = line[3:]

        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]

        if "D" in status:
            code = "D"
        elif "R" in status:
            code = "R"
            if " -> " in path:
                old, new = path.split(" -> ", 1)
                path = f"{old} → {new}"
        elif status == "??":
            code = "?"
        elif "A" in status:
            code = "A"
        else:
            code = "M"

        grouped.setdefault(code, []).append(path)

    return grouped


def guess_cause(all_paths, trigger_event, commit_msg):
    """
    Suy luận nguyên nhân thay đổi, kết hợp 3 nguồn:
    1. Loại sự kiện kích hoạt workflow (push / release / workflow_dispatch)
    2. Loại file/thư mục bị động tới nhiều nhất
    3. Nội dung commit message (nếu đủ rõ nghĩa, ưu tiên hiển thị kèm)
    """
    trigger_map = {
        "push": "Hệ thống tự động kích hoạt khi có push lên nhánh main",
        "release": "Hệ thống tự động kích hoạt khi có release mới (published/created/edited)",
        "workflow_dispatch": "Được kích hoạt thủ công (workflow_dispatch)",
        "schedule": "Hệ thống tự động chạy theo lịch định kỳ",
    }
    trigger_text = trigger_map.get(trigger_event, "Hệ thống tự động đồng bộ theo workflow CI/CD")

    # Đếm match theo CAUSE_RULES để tìm nguyên nhân kỹ thuật nổi bật nhất
    rule_hits = {}
    for path in all_paths:
        low = path.lower()
        for keys, label in CAUSE_RULES:
            if any(k in low for k in keys):
                rule_hits[label] = rule_hits.get(label, 0) + 1
                break  # mỗi file chỉ tính 1 lý do nổi bật nhất

    if rule_hits:
        top_label = max(rule_hits, key=rule_hits.get)
        technical_text = top_label
    else:
        technical_text = "Cập nhật dữ liệu kho lưu trữ"

    parts = [trigger_text, technical_text]
    if commit_msg and commit_msg != "(không có commit message)":
        parts.append(f"Commit: {commit_msg}")

    return " · ".join(parts)


def guess_result():
    """
    Cột "Kết quả": chỉ phản ánh trạng thái KỸ THUẬT, lấy từ biến môi trường
    do workflow YAML truyền vào (kết quả của các step trước đó).
    Không tự suy đoán tích cực/tiêu cực về mặt nội dung.
    """
    main_status = os.environ.get("MAIN_STATUS", "success")
    views_status = os.environ.get("VIEWS_STATUS", "success")

    failed_steps = []
    if main_status not in ("success", ""):
        failed_steps.append("Core Engine")
    if views_status not in ("success", ""):
        failed_steps.append("Generate Views")

    if failed_steps:
        return f"⚠️ Có lỗi ở bước: {', '.join(failed_steps)}"
    return "✅ Hoàn tất"


def build_changelog_entry():
    """Xây 1 block changelog (bảng dọc 2 cột, gọn cho điện thoại) cho lần chạy hiện tại."""
    grouped = collect_working_tree_changes()
    if not grouped:
        return None

    author = run("git log -1 --pretty=format:'%an'") or "GitHub Action"
    msg = run("git log -1 --pretty=format:'%s'").replace("\n", " ").strip() or "(không có commit message)"
    if len(msg) > 70:
        msg = msg[:67] + "..."

    time_str = now_hanoi().strftime("%d/%m/%Y %H:%M")

    total_files = sum(len(v) for v in grouped.values())
    all_paths = [p for files in grouped.values() for p in files]
    trigger_event = os.environ.get("GITHUB_EVENT_NAME", "")

    lines = []
    lines.append("| Tiêu đề | Nội dung |")
    lines.append("|---|---|")
    lines.append(f"| ⏱️ Time | {time_str} |")
    lines.append(f"| 👤 Author | {author} |")
    lines.append(f"| 💬 Commit | {msg} |")
    lines.append(f"| 📊 Overview | {total_files} file thay đổi |")

    # Các thay đổi: gộp tất cả nhóm hành động vào 1 ô duy nhất, mỗi nhóm 1 dòng
    change_blocks = []
    for code in ACTION_ORDER:
        if code not in grouped:
            continue
        label = ACTION_LABELS[code]
        files = grouped[code]
        file_list_html = "<br>".join(f"`{f}`" for f in files)

        if len(files) > MAX_VISIBLE_ROWS:
            block = (
                f"<details><summary>{label} ({len(files)})</summary><br>{file_list_html}</details>"
            )
        else:
            block = f"{label} ({len(files)})<br>{file_list_html}"
        change_blocks.append(block)

    lines.append(f"| 🛠️ Các thay đổi | {'<br>'.join(change_blocks)} |")
    lines.append(f"| ❓ Nguyên nhân | {guess_cause(all_paths, trigger_event, msg)} |")
    lines.append(f"| 🎯 Kết quả | {guess_result()} |")

    return "\n".join(lines)


def write_changelog(entry):
    """Tạo docs/CHANGELOG.md nếu chưa có, rồi chèn block mới ngay dưới marker, mới nhất ở trên cùng."""
    header = (
        "# 🏛 Core System Changelog\n\n"
        "> *Ghi nhận thay đổi tự động. Mới nhất ở trên cùng.*\n\n"
        "<!-- CHANGELOG_ENTRIES -->\n"
    )

    if not os.path.exists("docs/CHANGELOG.md"):
        with open("docs/CHANGELOG.md", "w", encoding="utf-8") as f:
            f.write(header)

    if not entry:
        return

    with open("docs/CHANGELOG.md", "r", encoding="utf-8") as f:
        content = f.read()

    if "<!-- CHANGELOG_ENTRIES -->" not in content:
        content = header  # file cũ sai định dạng / bị sửa tay -> reset lại header chuẩn

    block = entry + "\n\n---\n"
    content = content.replace(
        "<!-- CHANGELOG_ENTRIES -->",
        "<!-- CHANGELOG_ENTRIES -->\n\n" + block,
    )

    with open("docs/CHANGELOG.md", "w", encoding="utf-8") as f:
        f.write(content)


def generate_changelog():
    entry = build_changelog_entry()
    write_changelog(entry)


# ==========================================
# PHẦN 2: SINH CÂY THƯ MỤC
# ==========================================

SUMMARY_EXTENSIONS = {
    '.png': '🖼️ Ảnh PNG',
    '.jpg': '📸 Ảnh JPG',
    '.jpeg': '📸 Ảnh JPEG',
    '.svg': '🎨 Graphics SVG',
    '.deb': '📦 Package .deb',
    '.ipa': '📱 Apps iOS .ipa',
    '.json': '⚙️ Config .json'
    '.txt': '📝 Notes .txt'
}

EXCLUDE_DIRS = {'.git', 'docs', 'node_modules', '.venv', '__pycache__'}


def generate_smart_tree(dir_path, prefix=""):
    try:
        entries = sorted(os.listdir(dir_path))
    except PermissionError:
        return ""

    entries = [e for e in entries if e not in EXCLUDE_DIRS]

    lines = []
    files_to_summarize = {}
    items_to_show = []

    for entry in entries:
        full_path = os.path.join(dir_path, entry)
        if os.path.isdir(full_path):
            items_to_show.append((entry, True))
        else:
            _, ext = os.path.splitext(entry.lower())
            if ext in SUMMARY_EXTENSIONS:
                files_to_summarize[ext] = files_to_summarize.get(ext, 0) + 1
            else:
                items_to_show.append((entry, False))

    summary_parts = []
    for ext, count in sorted(files_to_summarize.items()):
        summary_parts.append(f"{SUMMARY_EXTENSIONS[ext]}: {count} file")

    count = len(items_to_show)
    for i, (item, is_dir) in enumerate(items_to_show):
        is_last_item = (i == count - 1) and (not summary_parts)
        connector = "└── " if is_last_item else "├── "

        if is_dir:
            lines.append(f"{prefix}{connector}📂 {item}/")
            new_prefix = prefix + ("    " if is_last_item else "│   ")
            subtree = generate_smart_tree(os.path.join(dir_path, item), new_prefix)
            if subtree:
                lines.append(subtree)
        else:
            lines.append(f"{prefix}{connector}{item}")

    if summary_parts:
        connector = "└── "
        summary_str = f"[ 📊 Số lượng: {', '.join(summary_parts)} ]"
        lines.append(f"{prefix}{connector}{summary_str}")

    return "\n".join([l for l in lines if l.strip()])


def generate_tree():
    tree_content = generate_smart_tree(".")
    with open("docs/info.md", "w", encoding="utf-8") as f:
        time_str = now_hanoi().strftime("%d/%m/%Y %H:%M:%S")

        f.write("# 📂 CẤU TRÚC HỆ THỐNG\n")
        f.write(f"⏱️ *Cập nhật tự động lúc: {time_str} (Giờ Hà Nội)*\n\n")
        f.write("```text\n🗺️ Root/\n")
        f.write(tree_content)
        f.write("\n```\n")


# ==========================================
# MAIN: chạy đúng thứ tự
# ==========================================

def main():
    os.makedirs("docs", exist_ok=True)

    # 1) Changelog trước (đọc working tree hiện tại, trước khi commit)
    generate_changelog()

    # 2) Cây thư mục sau (chụp lại trạng thái mới nhất, gồm cả CHANGELOG.md)
    generate_tree()


if __name__ == "__main__":
    main()
