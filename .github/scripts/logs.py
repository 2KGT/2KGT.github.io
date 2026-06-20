"""
Script tổng hợp cho workflow "Auto sync feather sileo".

Thứ tự chạy (quan trọng):
  1) generate_changelog()  -> ghi docs/CHANGELOG.md trước
  2) generate_tree()       -> ghi docs/info.md sau, để cây thư mục
                               phản ánh đúng luôn cả CHANGELOG.md vừa cập nhật

Lý do thứ tự này:
- Script này chạy SAU khi main.py / views.py đã sửa file nhưng TRƯỚC khi
  commit, nên generate_changelog() phải đọc thay đổi từ WORKING TREE hiện
  tại (git status), KHÔNG đọc từ git diff HEAD~1 HEAD — vì những thay đổi
  đó chưa hề được commit, `HEAD~1 HEAD` chỉ thấy lịch sử commit cũ.
- generate_tree() liệt kê toàn bộ cấu trúc thư mục hiện tại, nên chạy sau
  cùng để info.md là bản chụp mới nhất, bao gồm cả CHANGELOG.md đã cập nhật.
"""

import os
import subprocess
import datetime


# ==========================================
# PHẦN 1: SINH CHANGELOG (bảng dọc 2 cột, gộp theo lần chạy)
# ==========================================

ACTION_LABELS = {
    "A": "✨ Thêm",
    "M": "✏️ Sửa",
    "D": "🗑️ Xoá",
    "R": "🔀 Đổi tên",
    "?": "✨ Thêm",  # untracked file mới = coi như Thêm
}

# Thứ tự ưu tiên hiển thị từng nhóm hành động trong 1 lần chạy
ACTION_ORDER = ["A", "M", "D", "R", "?"]

MAX_VISIBLE_ROWS = 12  # số file hiện trực tiếp trước khi gói vào <details> để cuộn


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

        # Bỏ dấu ngoặc kép nếu git bọc path có ký tự đặc biệt
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]

        # Xác định mã hành động ưu tiên: D (xoá) > R (đổi tên) > A (mới) > M (sửa) > ? (untracked)
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


def build_changelog_entry():
    """Xây 1 block changelog (bảng dọc 2 cột) cho lần chạy hiện tại."""
    grouped = collect_working_tree_changes()
    if not grouped:
        return None

    author = run("git log -1 --pretty=format:'%an'") or "GitHub Action"
    msg = run("git log -1 --pretty=format:'%s'").replace("\n", " ").strip() or "(không có commit message)"
    if len(msg) > 80:
        msg = msg[:77] + "..."

    ict_now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=7)
    time_str = ict_now.strftime("%d/%m/%Y %H:%M:%S")

    total_files = sum(len(v) for v in grouped.values())

    lines = []
    lines.append("| 🏷️ Tiêu đề | 📋 Thay đổi |")
    lines.append("|---|---|")

    summary_bits = ", ".join(
        f"{ACTION_LABELS[c]}: {len(grouped[c])}" for c in ACTION_ORDER if c in grouped
    )
    lines.append(f"| ⏱️ Thời gian | {time_str} (ICT) |")
    lines.append(f"| 👤 Tác giả | {author} |")
    lines.append(f"| 💬 Commit | {msg} |")
    lines.append(f"| 📊 Tổng quan | {total_files} file thay đổi — {summary_bits} |")

    # Chi tiết từng nhóm hành động, dùng <details> để cuộn gọn trên điện thoại
    for code in ACTION_ORDER:
        if code not in grouped:
            continue
        label = ACTION_LABELS[code]
        files = grouped[code]

        file_list_html = "<br>".join(f"`{f}`" for f in files)

        if len(files) > MAX_VISIBLE_ROWS:
            detail_cell = (
                f"<details><summary>{label} — {len(files)} file (bấm để xem đầy đủ)</summary><br>"
                f"{file_list_html}</details>"
            )
        else:
            detail_cell = f"{label} — {len(files)} file<br>{file_list_html}"

        lines.append(f"| {label} | {detail_cell} |")

    return "\n".join(lines)


def write_changelog(entry):
    """Tạo docs/CHANGELOG.md nếu chưa có, rồi chèn block mới ngay dưới marker, mới nhất ở trên cùng."""
    header = (
        "# 🔰 CHANGELOG SYSTEM 🔰\n\n"
        "> *Hệ thống ghi nhận thay đổi tự động từ GitHub Actions. "
        "Mỗi lần chạy là một bảng riêng, mới nhất nằm trên cùng.*\n\n"
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
    '.svg': '🎨 Đồ họa SVG',
    '.deb': '📦 Gói tinh chỉnh .deb',
    '.ipa': '📱 Ứng dụng iOS .ipa',
    '.json': '⚙️ Cấu hình .json'
}

# Loại các thư mục sinh ra bởi chính workflow này / không liên quan
EXCLUDE_DIRS = {'.git', '.github', 'docs', 'node_modules', '.venv', '__pycache__'}


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
        summary_str = f"[ 📊 Tóm tắt tài nguyên: {', '.join(summary_parts)} ]"
        lines.append(f"{prefix}{connector}{summary_str}")

    return "\n".join([l for l in lines if l.strip()])


def generate_tree():
    tree_content = generate_smart_tree(".")
    with open("docs/info.md", "w", encoding="utf-8") as f:
        ict_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=7)
        time_str = ict_time.strftime("%d/%m/%Y %H:%M:%S")

        f.write("# 📂 CẤU TRÚC HỆ THỐNG\n")
        f.write(f"⏱️ *Cập nhật tự động lúc: {time_str} (ICT)*\n\n")
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
