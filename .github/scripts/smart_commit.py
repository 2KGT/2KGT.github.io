#!/usr/bin/env python3
"""
smart_commit.py — Chỉ commit & push khi có thay đổi THẬT.

Vấn đề: mỗi lần sync, một số file luôn đổi chỉ vì đồng hồ (dấu thời gian, ngày
của news, generated_at, CHANGELOG...) → workflow luôn commit → Pages build lại
vô ích, lịch sử commit đầy rác.

Cách hoạt động:
  1. git add -A, lấy danh sách file thay đổi so với HEAD.
  2. Mỗi file được xếp loại:
       • VOLATILE_PATHS   → bỏ qua (chỉ đổi theo thời gian)
       • .json            → so sánh SAU KHI bỏ các key thời gian (generated_at, news[].date)
       • repo/Release     → so sánh bỏ dòng Date:
       • .html            → so sánh sau khi chuẩn hoá dấu thời gian
       • còn lại          → thay đổi thật
  3. Không có thay đổi thật → KHÔNG commit (exit 0, committed=false).
     Có → commit TOÀN BỘ (kể cả file volatile) → rebase → push.

Đầu ra: in danh sách file được coi là "thay đổi thật" để bạn tinh chỉnh quy tắc;
ghi `committed=true|false` vào $GITHUB_OUTPUT.
"""
import json
import os
import re
import subprocess
import sys

# ── Quy tắc (chỉnh tại đây) ───────────────────────────────────────────────────
VOLATILE_PATHS = (".commit_msg", "repo/audit.log", "docs/")      # khớp theo tiền tố
UNTRACK = (".commit_msg", "repo/audit.log")                      # không cần nằm trong repo
VOLATILE_JSON_KEYS = {"generated_at"}                            # bỏ ở mọi cấp
VOLATILE_NEWS_KEYS = {"date"}                                    # news[].date đổi mỗi ngày
TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z|\d{2}:\d{2} \d{2}/\d{2}/\d{4}")


def git(*args, check=True):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        print(f"❌ git {' '.join(args)}\n{r.stderr}")
        sys.exit(r.returncode)
    return r


def old_text(path):
    r = subprocess.run(["git", "show", f"HEAD:{path}"], capture_output=True)
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


def new_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def _strip(obj, parent=None):
    if isinstance(obj, dict):
        drop = VOLATILE_JSON_KEYS | (VOLATILE_NEWS_KEYS if parent == "news" else set())
        return {k: _strip(v, k) for k, v in obj.items() if k not in drop}
    if isinstance(obj, list):
        return [_strip(x, parent) for x in obj]
    return obj


def is_real_change(status, path):
    if path.startswith(VOLATILE_PATHS):
        return False
    if status != "M":                       # file mới / bị xoá → thay đổi thật
        return True
    old, new = old_text(path), new_text(path)
    if old is None or new is None:
        return True
    if path.endswith(".json"):
        try:
            return _strip(json.loads(old)) != _strip(json.loads(new))
        except Exception:
            return True
    if path == "repo/Release":
        drop = lambda t: [l for l in t.splitlines() if not l.startswith("Date:")]
        return drop(old) != drop(new)
    if path.endswith(".html"):
        return TS_RE.sub("", old) != TS_RE.sub("", new)
    return True


def set_output(committed):
    out = os.getenv("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"committed={'true' if committed else 'false'}\n")


def main():
    branch = os.getenv("SMART_COMMIT_BRANCH", "main")
    git("config", "--local", "user.email", "action@github.com")
    git("config", "--local", "user.name", "GitHub Action")

    # Tệp trung gian (.commit_msg, audit.log) không nên nằm trong repo
    git("rm", "--cached", "--ignore-unmatch", "-r", "-q", *UNTRACK, check=False)
    git("add", "-A")

    diff = git("diff", "--cached", "--name-status", "--no-renames").stdout.strip()
    changes = [l.split("\t", 1) for l in diff.splitlines() if "\t" in l]
    if not changes:
        print("✅ Không có thay đổi nào để commit.")
        set_output(False)
        return

    real = [(s, p) for s, p in changes if is_real_change(s, p)]
    if not real:
        print(f"✅ {len(changes)} file chỉ đổi theo thời gian (dấu thời gian/CHANGELOG…) "
              "→ BỎ QUA commit, không build lại Pages.")
        git("reset", "-q", check=False)
        set_output(False)
        return

    print(f"📝 {len(real)} thay đổi thật / {len(changes)} file:")
    for s, p in real[:15]:
        print(f"   {s} {p}")
    if len(real) > 15:
        print(f"   … và {len(real) - 15} file khác")

    msg = "🔄 Tối ưu hóa hệ thống & Đồng bộ kho lưu trữ định kỳ"
    if os.path.exists(".commit_msg"):
        msg = open(".commit_msg", encoding="utf-8").read().strip() or msg
    git("commit", "-m", f"{msg} [skip ci]")
    # Các file sinh lại hoàn toàn mỗi lần chạy → khi xung đột, bản local (mới hơn) thắng.
    git("pull", "--rebase", "-X", "theirs", "origin", branch)
    git("push", "origin", f"HEAD:{branch}")
    print("✅ Đã push lên cloud.")
    set_output(True)


if __name__ == "__main__":
    main()
