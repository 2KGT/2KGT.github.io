# .github/scripts/logs_info.py
import os
import datetime
import subprocess
import sys

# Đảm bảo script luôn chạy từ thư mục gốc của Repo
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)


          # ==========================================
          # 1. SCRIPT PYTHON: CÂY THƯ MỤC
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

          tree_content = generate_smart_tree(".")
          with open("docs/info.md", "w", encoding="utf-8") as f:
              ict_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=7)
              time_str = ict_time.strftime("%d/%m/%Y %H:%M:%S")

              f.write("# 📂 CẤU TRÚC HỆ THỐNG\n")
              f.write(f"⏱️ *Cập nhật tự động lúc: {time_str} (ICT)*\n\n")
              f.write("```text\n🗺️ Root/\n")
              f.write(tree_content)
              f.write("\n```\n")
          EOF

          python generate_tree.py
          rm generate_tree.py

def update_changelog():
    # Sử dụng logic git diff của bạn
    def run(cmd):
        return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()
    
          # ==========================================
          # 2. SCRIPT PYTHON: CHANGELOG DẠNG BẢNG (gọn, dễ đọc)
          # ==========================================

          def run(cmd):
              return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()

          EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

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

          ACTIONS = {"A": "✨ Thêm", "M": "✏️ Sửa", "D": "🗑️ Xoá"}

          rows = []
          for line in lines:
              parts = line.split("\t")
              action_code = parts[0][0]
              fname = parts[1] if len(parts) < 3 else f"{parts[1]} → {parts[2]}"
              action_label = ACTIONS.get(action_code, "❓ Khác")
              status = "✅" if action_code in ACTIONS else "❌"
              rows.append(f"| {time_str} | `{fname}` | {action_label} | {author} | {msg} | {status} |")

          with open("temp_log.md", "w", encoding="utf-8") as f:
              if rows:
                  f.write("\n".join(rows) + "\n")
          EOF

          python generate_changelog.py
          rm generate_changelog.py

          # ==========================================
          # 3. GHI VÀO docs/CHANGELOG.md (chèn dòng mới ngay dưới header bảng)
          # ==========================================
          if [ ! -f docs/CHANGELOG.md ]; then
            {
              echo "# 🔰CHANGELOG SYSTEM🔰"
              echo ""
              echo "> *Hệ thống ghi nhận thay đổi tự động từ GitHub Actions. Mục mới nhất nằm trên cùng.*"
              echo ""
              echo "| 🗓️ Thời gian | 📄 Tệp | 🛠️ Hành động | 👤 Tác giả | 💬 Commit | 📊 |"
              echo "|---|---|---|---|---|---|"
              echo "<!-- CHANGELOG_ROWS -->"
            } > docs/CHANGELOG.md
          fi

          if [ -f temp_log.md ] && [ -s temp_log.md ]; then
            sed -i "/<!-- CHANGELOG_ROWS -->/r temp_log.md" docs/CHANGELOG.md
            rm temp_log.md
          fi
    
    # Ghi vào file docs/CHANGELOG.md bằng Python thay vì sed
    log_path = "docs/CHANGELOG.md"
    new_rows = ... # Nội dung log mới
    
    if not os.path.exists(log_path):
        header = "# 🔰CHANGELOG SYSTEM🔰\n\n| 🗓️ Thời gian | 📄 Tệp | ... |\n|---|---|---|\n"
        with open(log_path, 'w') as f: f.write(header)
    
    with open(log_path, 'r') as f: content = f.read()
    
    # Chèn nội dung mới sau tag updated_content = content.replace("", f"\n{new_rows}")
    with open(log_path, 'w') as f: f.write(updated_content)

if __name__ == "__main__":
    os.makedirs("docs", exist_ok=True)
    # 1. Tạo info.md
    with open("docs/info.md", "w") as f: f.write(generate_smart_tree("."))
    # 2. Tạo/Cập nhật changelog

