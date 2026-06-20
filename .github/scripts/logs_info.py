# .github/scripts/logs_info.py
import os
import datetime
import subprocess
import sys

# Đảm bảo script luôn chạy từ thư mục gốc của Repo
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)

# --- CONFIG ---
SUMMARY_EXTENSIONS = {
    '.png': '🖼️ Ảnh PNG', '.jpg': '📸 Ảnh JPG', '.svg': '🎨 Đồ họa SVG',
    '.deb': '📦 Gói tinh chỉnh .deb', '.ipa': '📱 Ứng dụng iOS .ipa', '.json': '⚙️ Cấu hình .json'
}
EXCLUDE_DIRS = {'.git', '.github', 'docs', 'node_modules', '.venv', '__pycache__'}

def generate_smart_tree(dir_path=".", prefix=""):
    entries = sorted([e for e in os.listdir(dir_path) if e not in EXCLUDE_DIRS])
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

    # Xử lý tóm tắt
    summary_parts = [f"{SUMMARY_EXTENSIONS[ext]}: {count} file" for ext, count in sorted(files_to_summarize.items())]
    
    # Render cây
    for i, (item, is_dir) in enumerate(items_to_show):
        is_last = (i == len(items_to_show) - 1) and (not summary_parts)
        connector = "└── " if is_last else "├── "
        if is_dir:
            lines.append(f"{prefix}{connector}📂 {item}/")
            subtree = generate_smart_tree(os.path.join(dir_path, item), prefix + ("    " if is_last else "│   "))
            if subtree: lines.append(subtree)
        else:
            lines.append(f"{prefix}{connector}{item}")

    if summary_parts:
        lines.append(f"{prefix}└── [ 📊 Tóm tắt: {', '.join(summary_parts)} ]")
    return "\n".join(lines)

def update_changelog():
    def run(cmd):
        return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()

    # Lấy thông tin git
    prev = run("git rev-parse HEAD~1 2>/dev/null") or "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    curr = run("git rev-parse HEAD")
    author = run("git log -1 --pretty=format:'%an'").replace("|", "/")
    msg = run("git log -1 --pretty=format:'%s'").replace("|", "/").strip()[:60]
    
    ict_now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=7)
    time_str = ict_now.strftime("%d/%m %H:%M")

    diffs = run(f"git diff --name-status -M \"{prev}\" \"{curr}\" -- . ':!docs' ':!.github'")
    
    rows = []
    ACTIONS = {"A": "✨ Thêm", "M": "✏️ Sửa", "D": "🗑️ Xoá"}
    for line in diffs.splitlines():
        parts = line.split("\t")
        if not parts: continue
        action = ACTIONS.get(parts[0][0], "❓ Khác")
        fname = parts[1] if len(parts) < 3 else f"{parts[1]} → {parts[2]}"
        rows.append(f"| {time_str} | `{fname}` | {action} | {author} | {msg} | ✅ |")

    if not rows: return

    # Ghi file
    os.makedirs("docs", exist_ok=True)
    log_path = "docs/CHANGELOG.md"
    
    header = "# 🔰CHANGELOG SYSTEM🔰\n\n> *Tự động bởi GitHub Actions.*\n\n| 🗓️ Thời gian | 📄 Tệp | 🛠️ Hành động | 👤 Tác giả | 💬 Commit | 📊 |\n|---|---|---|---|---|---|\n\n"
    
    if not os.path.exists(log_path):
        content = header
    else:
        with open(log_path, 'r', encoding='utf-8') as f: content = f.read()
    
    new_data = "\n".join(rows) + "\n"
    final_content = content.replace("", f"\n{new_data}")
    
    with open(log_path, 'w', encoding='utf-8') as f: f.write(final_content)

if __name__ == "__main__":
    # 1. Info
    tree = generate_smart_tree(".")
    time_str = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=7)).strftime("%d/%m/%Y %H:%M:%S")
    with open("docs/info.md", "w", encoding="utf-8") as f:
        f.write(f"# 📂 CẤU TRÚC HỆ THỐNG\n⏱️ *Cập nhật: {time_str} (ICT)*\n\n```text\n🗺️ Root/\n{tree}\n```\n")
    
    # 2. Changelog
    update_changelog()
