"""
Script tổng hợp cho workflow "Auto sync generate info".

Thứ tự chạy (quan trọng):
  1) generate_changelog()  -> ghi docs/CHANGELOG.md trước
  2) generate_tree()       -> ghi docs/info.md sau, để cây thư mục
                               phản ánh đúng luôn cả CHANGELOG.md vừa cập nhật

Lý do thứ tự này:
- generate_changelog() dựa vào `git diff` giữa HEAD~1 và HEAD nên cần chạy
  trước khi docs/ bị thay đổi thêm bởi bước sinh cây thư mục.
- generate_tree() liệt kê toàn bộ cấu trúc thư mục hiện tại, nên chạy sau
  cùng để info.md là bản chụp mới nhất, bao gồm cả CHANGELOG.md đã cập nhật.
"""

import os
import subprocess
import datetime


# ==========================================
# PHẦN 1: SINH CHANGELOG DẠNG BẢNG
# ==========================================

ACTIONS = {"A": "✨ Thêm", "M": "✏️ Sửa", "D": "🗑️ Xoá"}
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


def generate_changelog_rows():
    """Trả về danh sách dòng markdown mô tả thay đổi của commit hiện tại."""
    prev = run("git rev-parse HEAD~1 2>/dev/null")
    if not prev:
        prev = EMPTY_TREE  # commit đầu tiên của repo: so sánh với cây rỗng

    curr = run("git rev-parse HEAD")
    author = run("git log -1 --pretty=format:'%an'").replace("|", "/")
    msg = run("git log -1 --pretty=format:'%s'").replace("|", "/").replace("\n", " ").strip()
    if len(msg) > 60:
        msg = msg[:57] + "..."

    ict_now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=7)
    time_str = ict_now.strftime("%d/%m %H:%M")

    diffs = run(f"git diff --name-status -M \"{prev}\" \"{curr}\" -- . ':!docs' ':!.github'")
    lines = [l for l in diffs.splitlines() if l.strip()]

    rows = []
    for line in lines:
        parts = line.split("\t")
        action_code = parts[0][0]
        fname = parts[1] if len(parts) < 3 else f"{parts[1]} → {parts[2]}"
        action_label = ACTIONS.get(action_code, "❓ Khác")
        status = "✅" if action_code in ACTIONS else "❌"
        rows.append(f"| {time_str} | `{fname}` | {action_label} | {author} | {msg} | {status} |")

    return rows


def write_changelog(rows):
    """Tạo docs/CHANGELOG.md nếu chưa có, rồi chèn các dòng mới ngay dưới header bảng."""
    if not os.path.exists("docs/CHANGELOG.md"):
        with open("docs/CHANGELOG.md", "w", encoding="utf-8") as f:
            f.write("# 🔰CHANGELOG SYSTEM🔰\n\n")
            f.write("> *Hệ thống ghi nhận thay đổi tự động từ GitHub Actions. Mục mới nhất nằm trên cùng.*\n\n")
            f.write("| 🗓️ Thời gian | 📄 Tệp | 🛠️ Hành động | 👤 Tác giả | 💬 Commit | 📊 |\n")
            f.write("|---|---|---|---|---|---|\n")
            f.write("<!-- CHANGELOG_ROWS -->\n")

    if not rows:
        return

    with open("docs/CHANGELOG.md", "r", encoding="utf-8") as f:
        content = f.read()

    content = content.replace(
        "<!-- CHANGELOG_ROWS -->",
        "<!-- CHANGELOG_ROWS -->\n" + "\n".join(rows),
    )

    with open("docs/CHANGELOG.md", "w", encoding="utf-8") as f:
        f.write(content)


def generate_changelog():
    rows = generate_changelog_rows()
    write_changelog(rows)


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

    # 1) Changelog trước (dựa vào git diff của commit hiện tại)
    generate_changelog()

    # 2) Cây thư mục sau (chụp lại trạng thái mới nhất, gồm cả CHANGELOG.md)
    generate_tree()


if __name__ == "__main__":
    main()
