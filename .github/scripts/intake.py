#!/usr/bin/env python3
# version: 1.0.0 | 2026-11-15 | NHẬN HÀNG cho kho Sileo: đọc repo/inbox/<lô>, kiểm tra, phân loại, đặt đúng kệ debs/dylibs, ghi chú + ghi sổ
# .github/scripts/intake.py
"""
KHO SILEO NHẬN HÀNG  (chạy ở workflow Auto-sync-feather-sileo, TRƯỚC main.py)

  Bên gửi (publish.py) chỉ chuyển hàng tới địa chỉ:  repo/inbox/<lô>/manifest.json + các tệp.
  Bên gửi KHÔNG biết kho sắp xếp ra sao. Mọi quyết định về vị trí nằm ở đây:

    kiểm tra  ─ manifest hợp lệ · tệp đủ · sha256 khớp · đúng định dạng (.deb / .dylib)
    phân loại ─ deb | dylib
    đặt tên   ─ <gói>_<phiên bản>_<kiến trúc>.deb | .dylib   (đọc từ control của .deb, không tin tên tệp)
    đặt kệ    ─ repo/debs/<tweak>/…      repo/dylibs/<tweak>/…      (<tweak> = đoạn cuối của bundle id)
    ghi chú   ─ v<phiên bản>.txt cạnh tệp  ("Có gì mới" cho Sileo / Cydia)
    ghi sổ    ─ repo/data/intake/ledger.jsonl  (mỗi tệp một dòng: nhãn, kệ, sha256, nguồn, kết quả)
    dọn hộp   ─ lô xong thì xoá khỏi inbox; lô lỗi → repo/inbox/_rejected/<lô>/ + REASON.txt

  Các lô xử lý theo thứ tự tên (tiền tố thời gian + số thứ tự: 1-debs trước 2-dylibs).
  Sau khi xong, main.py chạy như cũ và dựng index từ repo/debs, repo/dylibs.

Chạy từ thư mục gốc của repo:  python3 .github/scripts/intake.py [--strict]
  --strict: có lô bị từ chối thì thoát mã 1 (mặc định 0 để không chặn các lô tốt).
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

__version__ = "1.0.0"

INBOX = os.path.join("repo", "inbox")
SHELVES = {"debs": os.path.join("repo", "debs"), "dylibs": os.path.join("repo", "dylibs")}
LEDGER = os.path.join("repo", "data", "intake", "ledger.jsonl")
REJECTED = os.path.join(INBOX, "_rejected")
RE_DYLIB = re.compile(r"^(?P<id>.+)_(?P<ver>[^_]+)_(?P<arch>iphoneos-arm(?:64e?)?)\.dylib$")
ARCH_LABEL = {"iphoneos-arm64": "rootless", "iphoneos-arm": "rootful", "iphoneos-arm64e": "arm64e"}


class Reject(Exception):
    pass


def log(msg):
    print(msg, flush=True)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tweak_folder(package):
    """com.kyic.autoac → autoac (đúng quy ước hiện có của kho)."""
    return re.sub(r"[^a-z0-9._-]+", "-", package.split(".")[-1].lower()).strip("-") or "tweak"


def deb_control(path):
    r = subprocess.run(["dpkg-deb", "-f", path], capture_output=True, text=True)
    if r.returncode != 0:
        raise Reject(f"không đọc được control của {os.path.basename(path)}: {(r.stderr or '').strip()[:120]}")
    fields = {}
    for line in r.stdout.splitlines():
        if line[:1] not in (" ", "\t") and ":" in line:
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields


def safe_name(name):
    if not name or name != os.path.basename(name) or name.startswith("."):
        raise Reject(f"tên tệp không hợp lệ: {name!r}")
    return name


def read_manifest(batch):
    path = os.path.join(batch, "manifest.json")
    if not os.path.isfile(path):
        raise Reject("thiếu manifest.json")
    try:
        with open(path, encoding="utf-8") as fh:
            m = json.load(fh)
    except ValueError as e:
        raise Reject(f"manifest.json không đọc được: {e}")
    if m.get("schema") != 1:
        raise Reject(f"schema manifest không hỗ trợ: {m.get('schema')!r}")
    if m.get("stage") not in SHELVES:
        raise Reject(f"stage không hợp lệ: {m.get('stage')!r} (cần debs hoặc dylibs)")
    if not isinstance(m.get("files"), list) or not m["files"]:
        raise Reject("manifest không có tệp nào")
    return m


def place(src, dest_dir, canonical):
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, canonical)
    new = sha256_file(src)
    if os.path.exists(dest):
        status = "unchanged" if sha256_file(dest) == new else "replaced"
    else:
        status = "added"
    if status != "unchanged":
        shutil.copy2(src, dest)
    return dest, status, new


def process_batch(batch):
    m = read_manifest(batch)
    stage, results, notes_for = m["stage"], [], {}
    for entry in m["files"]:
        name = safe_name(entry.get("name", ""))
        src = os.path.join(batch, name)
        if not os.path.isfile(src):
            raise Reject(f"thiếu tệp {name}")
        digest = sha256_file(src)
        if entry.get("sha256") and entry["sha256"] != digest:
            raise Reject(f"{name}: sha256 không khớp (tệp hỏng khi chuyển)")
        if os.path.getsize(src) == 0:
            raise Reject(f"{name}: tệp rỗng")

        if stage == "debs":
            if not name.endswith(".deb"):
                raise Reject(f"{name}: lô debs chỉ nhận .deb")
            ctl = deb_control(src)
            pkg, ver, arch = ctl.get("Package"), ctl.get("Version"), ctl.get("Architecture")
            if not (pkg and ver and arch):
                raise Reject(f"{name}: control thiếu Package/Version/Architecture")
            canonical, label = f"{pkg}_{ver}_{arch}.deb", ARCH_LABEL.get(arch, arch)
            folder, kind = tweak_folder(pkg), "deb"
        else:
            if not name.endswith(".dylib"):
                raise Reject(f"{name}: lô dylibs chỉ nhận .dylib")
            match = RE_DYLIB.match(name)
            if not match:
                raise Reject(f"{name}: tên dylib phải là <gói>_<phiên bản>_<kiến trúc>.dylib")
            pkg, ver, arch = m.get("package") or match["id"], match["ver"], match["arch"]
            canonical, label = name, "dylib"
            folder, kind = tweak_folder(pkg), "dylib"

        dest, status, digest = place(src, os.path.join(SHELVES[stage], folder), canonical)
        notes_for[(stage, folder, ver)] = True
        results.append({"kind": kind, "folder": folder, "file": canonical, "dest": dest.replace(os.sep, "/"),
                        "version": ver, "arch": arch, "label": label, "sha256": digest, "status": status})

    notes = (m.get("notes") or "").strip()
    if notes:                                                   # "Có gì mới" dùng chung cho mọi kiến trúc của phiên bản
        for (st, folder, ver) in notes_for:
            with open(os.path.join(SHELVES[st], folder, f"v{ver}.txt"), "w", encoding="utf-8") as fh:
                fh.write(notes + "\n")
    return m, results


def ledger_append(batch_name, m, results):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    src = m.get("source") or {}
    with open(LEDGER, "a", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps({"ts": now, "batch": batch_name, "project": m.get("project", ""), "title": m.get("title", ""),
                                 "ecosystems": m.get("ecosystems", []), "source_run": src.get("run_url", ""),
                                 **r}, ensure_ascii=False) + "\n")


def reject(batch, reason):
    name = os.path.basename(batch)
    dest = os.path.join(REJECTED, name)
    os.makedirs(REJECTED, exist_ok=True)
    shutil.rmtree(dest, ignore_errors=True)
    shutil.move(batch, dest)
    with open(os.path.join(dest, "REASON.txt"), "w", encoding="utf-8") as fh:
        fh.write(reason + "\n")
    print(f"::error::Lô {name} bị từ chối: {reason}")


def summary(lines):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")


def set_output(key, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{key}={value}\n")


def main(strict=False):
    if not os.path.isdir(INBOX):
        log("📭 Chưa có hộp nhận (repo/inbox) — không có gì để nhận.")
        return 0
    batches = sorted(d for d in os.listdir(INBOX)
                     if os.path.isdir(os.path.join(INBOX, d)) and not d.startswith(("_", ".")))
    if not batches:
        log("📭 Hộp nhận trống.")
        return 0
    rows, received, rejected = [], 0, 0
    for name in batches:
        batch = os.path.join(INBOX, name)
        log(f"📥 Nhận lô {name}")
        try:
            m, results = process_batch(batch)
        except Reject as e:
            reject(batch, str(e))
            rejected += 1
            rows.append(f"| `{name}` | — | ❌ {str(e)[:90]} |")
            continue
        ledger_append(name, m, results)
        shutil.rmtree(batch, ignore_errors=True)
        received += len(results)
        for r in results:
            log(f"   {'✅' if r['status'] != 'unchanged' else '＝'} {r['status']:<9} {r['dest']}  [{r['label']}]")
            rows.append(f"| `{name}` | `{r['dest']}` | {r['status']} · {r['label']} |")
    summary(["## 📥 Nhận hàng vào kho", "", "| Lô | Kệ | Kết quả |", "|----|----|---------|"] + rows)
    set_output("received", str(received))
    set_output("rejected", str(rejected))
    log(f"✅ Đã nhận {received} tệp, từ chối {rejected} lô.")
    return 1 if (strict and rejected) else 0


if __name__ == "__main__":
    if "--version" in sys.argv:
        print(__version__)
        sys.exit(0)
    sys.exit(main("--strict" in sys.argv))
