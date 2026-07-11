# .github/scripts/logs.py
import os
import json
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
# PHẦN 0: SNAPSHOT CÂY THƯ MỤC (dùng chung cho changelog + info.md)
# ==========================================
# Vì git không track thư mục rỗng, ta tự chụp ảnh toàn bộ cây thư mục mỗi
# lần chạy và so sánh với ảnh chụp lần trước để phát hiện thư mục mới /
# thư mục bị xoá / thư mục đổi tên — độc lập hoàn toàn với git status.

SNAPSHOT_PATH = "docs/.tree_snapshot.json"
EXCLUDE_DIRS = {'.git', 'docs', 'node_modules', '.venv', '__pycache__'}


def scan_directory_tree(root="."):
    """
    Quét đệ quy toàn bộ thư mục, trả về:
    - dirs: set các đường dẫn thư mục (tương đối, dùng '/' làm phân tách)
    - dir_children: dict {đường dẫn thư mục: sorted set tên file con trực tiếp}
      (dùng để suy luận đổi tên thư mục bằng cách so khớp nội dung)
    """
    dirs = set()
    dir_children = {}

    for current_root, subdirs, files in os.walk(root):
        subdirs[:] = [d for d in subdirs if d not in EXCLUDE_DIRS and not d.startswith('.')]

        rel_root = os.path.relpath(current_root, root)
        rel_root = "" if rel_root == "." else rel_root.replace(os.sep, "/")

        if rel_root != "":
            dirs.add(rel_root)
            dir_children[rel_root] = sorted(files)

        for d in subdirs:
            child_path = f"{rel_root}/{d}" if rel_root else d
            dirs.add(child_path)

    return dirs, dir_children


def load_previous_snapshot():
    if not os.path.exists(SNAPSHOT_PATH):
        return set(), {}
    try:
        with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("dirs", [])), data.get("dir_children", {})
    except Exception:
        return set(), {}


def save_snapshot(dirs, dir_children):
    os.makedirs(os.path.dirname(SNAPSHOT_PATH), exist_ok=True)
    with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
        json.dump({"dirs": sorted(dirs), "dir_children": dir_children}, f, ensure_ascii=False, indent=2)


def diff_directory_changes(old_dirs, old_children, new_dirs, new_children):
    """
    So sánh 2 ảnh chụp cây thư mục, trả về dict:
    {
      "added": [...],       # thư mục mới hoàn toàn
      "removed": [...],     # thư mục bị xoá hoàn toàn
      "renamed": [(old, new)],  # suy luận đổi tên (nội dung file con khớp nhau)
    }
    Một thư mục "added" có thể được tái phân loại thành "renamed" nếu một
    thư mục "removed" có cùng tập file con trực tiếp (basename) — dấu hiệu
    mạnh cho thấy đây là cùng 1 thư mục bị đổi tên/di chuyển.
    """
    added = sorted(new_dirs - old_dirs)
    removed = sorted(old_dirs - new_dirs)

    renamed = []
    matched_added = set()
    matched_removed = set()

    for r in removed:
        r_children = tuple(old_children.get(r, []))
        if not r_children:
            continue
        for a in added:
            if a in matched_added:
                continue
            if tuple(new_children.get(a, [])) == r_children:
                renamed.append((r, a))
                matched_added.add(a)
                matched_removed.add(r)
                break

    added = [a for a in added if a not in matched_added]
    removed = [r for r in removed if r not in matched_removed]

    return {"added": added, "removed": removed, "renamed": renamed}


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
    (("repo/data/icons/", ".png", ".jpg", ".jpeg", ".svg"), "Cập nhật hình ảnh / icon"),
    (("repo/data/",), "Cập nhật mô tả ứng dụng (depiction)"),
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


# --- Cấu hình các step CI cần theo dõi trạng thái ---
# Mỗi step: (tên hiển thị, tên biến môi trường trạng thái, tên biến môi trường thời gian [tùy chọn])
CI_STEPS = [
    ("Core Engine", "MAIN_STATUS", "MAIN_DURATION"),
    ("Generate Views", "VIEWS_STATUS", "VIEWS_DURATION"),
    ("Validate Repo", "VALIDATE_STATUS", "VALIDATE_DURATION"),
    ("Deploy Pages", "DEPLOY_STATUS", "DEPLOY_DURATION"),
]


def build_ci_status_table():
    """
    Bảng trạng thái từng step CI, chỉ hiện những step có biến môi trường
    được workflow YAML truyền vào (step không tồn tại trong lần chạy này
    thì không hiện dòng, tránh gây hiểu lầm là 'đã chạy nhưng thành công').
    """
    rows = []
    any_failed = False

    for label, status_var, duration_var in CI_STEPS:
        status_val = os.environ.get(status_var)
        if status_val is None:
            continue  # step này không tồn tại / không báo cáo trong lần chạy

        if status_val == "success":
            icon = "✅"
        elif status_val in ("skipped", "cancelled"):
            icon = "⏭️"
        else:
            icon = "❌"
            any_failed = True

        duration_val = os.environ.get(duration_var, "") if duration_var else ""
        duration_text = f" · {duration_val}" if duration_val else ""

        rows.append(f"{icon} {label}: `{status_val}`{duration_text}")

    return rows, any_failed


def build_change_stats(grouped, dir_diff):
    """
    Thống kê số liệu thay đổi: số file theo từng loại hành động + số thư
    mục thêm/xoá/đổi tên phát hiện được qua snapshot cây.
    """
    stats = []
    file_total = sum(len(v) for v in grouped.values())

    # Gộp theo label (A và ? đều là "Thêm") để khớp với cách hiển thị ở
    # change_blocks, tránh thống kê 2 dòng "Thêm" tách rời nhau
    label_counts = {}
    for code in ACTION_ORDER:
        if code in grouped:
            label = ACTION_LABELS[code]
            label_counts[label] = label_counts.get(label, 0) + len(grouped[code])

    file_parts = [f"{label} {count}" for label, count in label_counts.items()]
    if file_parts:
        stats.append(f"📄 File ({file_total}): " + ", ".join(file_parts))

    dir_added = len(dir_diff["added"])
    dir_removed = len(dir_diff["removed"])
    dir_renamed = len(dir_diff["renamed"])
    dir_total = dir_added + dir_removed + dir_renamed

    if dir_total:
        dir_parts = []
        if dir_added:
            dir_parts.append(f"✨ Thêm {dir_added}")
        if dir_removed:
            dir_parts.append(f"🗑️ Xoá {dir_removed}")
        if dir_renamed:
            dir_parts.append(f"🔀 Đổi tên {dir_renamed}")
        stats.append(f"📂 Thư mục ({dir_total}): " + ", ".join(dir_parts))

    return stats


def build_result_cell(grouped, dir_diff):
    """
    Cột "Kết quả": kết hợp bảng trạng thái từng step CI + thống kê số liệu
    thay đổi (file/thư mục). Không tự suy đoán tích cực/tiêu cực về mặt nội
    dung — chỉ phản ánh trạng thái kỹ thuật lấy từ biến môi trường và dữ
    liệu diff thực tế.
    """
    ci_rows, any_failed = build_ci_status_table()
    stats_rows = build_change_stats(grouped, dir_diff)

    parts = []

    if ci_rows:
        parts.append("<br>".join(ci_rows))
    else:
        # Không có biến môi trường nào được truyền vào -> không rõ trạng thái step
        parts.append("✅ Hoàn tất" if not any_failed else "⚠️ Có lỗi")

    if stats_rows:
        parts.append("<br>".join(stats_rows))

    return "<br><br>".join(parts)


def build_directory_change_blocks(dir_diff):
    """
    Sinh các dòng mô tả thay đổi thư mục (thêm/xoá/đổi tên) để chèn vào
    cùng ô '🛠️ Các thay đổi' bên cạnh các dòng thay đổi file.
    """
    blocks = []

    if dir_diff["added"]:
        items = "<br>".join(f"`{d}/`" for d in dir_diff["added"])
        label = f"✨ Thêm thư mục ({len(dir_diff['added'])})"
        if len(dir_diff["added"]) > MAX_VISIBLE_ROWS:
            blocks.append(f"<details><summary>{label}</summary><br>{items}</details>")
        else:
            blocks.append(f"{label}<br>{items}")

    if dir_diff["removed"]:
        items = "<br>".join(f"`{d}/`" for d in dir_diff["removed"])
        label = f"🗑️ Xoá thư mục ({len(dir_diff['removed'])})"
        if len(dir_diff["removed"]) > MAX_VISIBLE_ROWS:
            blocks.append(f"<details><summary>{label}</summary><br>{items}</details>")
        else:
            blocks.append(f"{label}<br>{items}")

    if dir_diff["renamed"]:
        items = "<br>".join(f"`{old}/` → `{new}/`" for old, new in dir_diff["renamed"])
        label = f"🔀 Đổi tên thư mục ({len(dir_diff['renamed'])})"
        blocks.append(f"{label}<br>{items}")

    return blocks


def build_changelog_entry(dir_diff):
    """Xây 1 block changelog (bảng dọc 2 cột, gọn cho điện thoại) cho lần chạy hiện tại."""
    grouped = collect_working_tree_changes()

    has_dir_changes = dir_diff["added"] or dir_diff["removed"] or dir_diff["renamed"]
    if not grouped and not has_dir_changes:
        return None

    author = run("git log -1 --pretty=format:'%an'") or "GitHub Action"
    msg = run("git log -1 --pretty=format:'%s'").replace("\n", " ").strip() or "(không có commit message)"
    if len(msg) > 70:
        msg = msg[:67] + "..."

    time_str = now_hanoi().strftime("%d/%m/%Y %H:%M")

    file_total = sum(len(v) for v in grouped.values())
    dir_total = len(dir_diff["added"]) + len(dir_diff["removed"]) + len(dir_diff["renamed"])
    all_paths = [p for files in grouped.values() for p in files]
    trigger_event = os.environ.get("GITHUB_EVENT_NAME", "")

    lines = []
    lines.append("| Tiêu đề | Nội dung |")
    lines.append("|---|---|")
    lines.append(f"| ⏱️ Time | {time_str} |")
    lines.append(f"| 👤 Author | {author} |")
    lines.append(f"| 💬 Commit | {msg} |")
    lines.append(f"| 📊 Overview | {file_total} file · {dir_total} thư mục thay đổi |")

    # Các thay đổi: gộp tất cả nhóm hành động (file) + thay đổi thư mục vào 1 ô
    # ('A' và '?' đều là "Thêm", nên gộp file của 2 mã này lại để không hiện
    # 2 dòng "✨ Thêm" tách rời nhau)
    merged_groups = {}
    for code, files in grouped.items():
        label = ACTION_LABELS[code]
        merged_groups.setdefault(label, []).extend(files)

    change_blocks = []
    for code in ACTION_ORDER:
        label = ACTION_LABELS[code]
        if label not in merged_groups:
            continue
        files = merged_groups.pop(label)  # pop để không xử lý lại nếu trùng label
        file_list_html = "<br>".join(f"`{f}`" for f in files)

        if len(files) > MAX_VISIBLE_ROWS:
            block = (
                f"<details><summary>{label} ({len(files)})</summary><br>{file_list_html}</details>"
            )
        else:
            block = f"{label} ({len(files)})<br>{file_list_html}"
        change_blocks.append(block)

    change_blocks.extend(build_directory_change_blocks(dir_diff))

    if change_blocks:
        lines.append(f"| 🛠️ Các thay đổi | {'<br>'.join(change_blocks)} |")
    else:
        lines.append("| 🛠️ Các thay đổi | (không có) |")

    lines.append(f"| ❓ Nguyên nhân | {guess_cause(all_paths, trigger_event, msg)} |")
    lines.append(f"| 🎯 Kết quả | {build_result_cell(grouped, dir_diff)} |")

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


def generate_changelog(dir_diff):
    entry = build_changelog_entry(dir_diff)
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
}


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


def build_recent_dir_changes_note(dir_diff):
    """
    Dòng tóm tắt thay đổi thư mục gần nhất, hiển thị ngay trong info.md để
    đối chiếu nhanh với CHANGELOG.md mà không cần mở 2 file riêng.
    """
    if not (dir_diff["added"] or dir_diff["removed"] or dir_diff["renamed"]):
        return ""

    parts = []
    if dir_diff["added"]:
        parts.append(f"✨ +{len(dir_diff['added'])} thư mục mới")
    if dir_diff["removed"]:
        parts.append(f"🗑️ -{len(dir_diff['removed'])} thư mục đã xoá")
    if dir_diff["renamed"]:
        parts.append(f"🔀 {len(dir_diff['renamed'])} thư mục đổi tên")

    return "📝 *Thay đổi thư mục so với lần quét trước: " + ", ".join(parts) + "* — xem chi tiết tại `docs/CHANGELOG.md`\n\n"


def generate_tree(dir_diff):
    tree_content = generate_smart_tree(".")
    with open("docs/info.md", "w", encoding="utf-8") as f:
        time_str = now_hanoi().strftime("%d/%m/%Y %H:%M:%S")

        f.write("# 📂 CẤU TRÚC HỆ THỐNG\n")
        f.write(f"⏱️ *Cập nhật tự động lúc: {time_str} (Giờ Hà Nội)*\n\n")
        f.write(build_recent_dir_changes_note(dir_diff))
        f.write("```text\n🗺️ Root/\n")
        f.write(tree_content)
        f.write("\n```\n")


# ==========================================
# MAIN: chạy đúng thứ tự
# ==========================================

def main():
    os.makedirs("docs", exist_ok=True)

    # 0) Chụp ảnh cây thư mục hiện tại + so sánh với lần chạy trước
    #    (phải làm trước generate_changelog vì changelog cần dir_diff để
    #    ghi nhận thư mục thêm/xoá/đổi tên — git không thấy được điều này)
    old_dirs, old_children = load_previous_snapshot()
    new_dirs, new_children = scan_directory_tree(".")
    dir_diff = diff_directory_changes(old_dirs, old_children, new_dirs, new_children)

    # 1) Changelog trước (đọc working tree hiện tại, trước khi commit)
    generate_changelog(dir_diff)

    # 2) Cây thư mục sau (chụp lại trạng thái mới nhất, gồm cả CHANGELOG.md)
    generate_tree(dir_diff)

    # 3) Lưu snapshot mới làm baseline cho lần chạy kế tiếp
    save_snapshot(new_dirs, new_children)


if __name__ == "__main__":
    main()
