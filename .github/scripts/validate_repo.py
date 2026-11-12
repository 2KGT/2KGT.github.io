#!/usr/bin/env python3
"""
validate_repo.py — Kiểm tra kho Sileo/Cydia/Zebra TRƯỚC khi push.
Chạy:  python3 .github/scripts/validate_repo.py [đường_dẫn_repo] [--notify]
(mặc định: thư mục gốc repo; --notify = gửi Telegram khi có lỗi)
Thoát mã 1 nếu có LỖI (❌). Cảnh báo (⚠️) không làm fail.
"""
import bz2, hashlib, json, os, re, sys
from collections import defaultdict

_args = [a for a in sys.argv[1:] if not a.startswith("--")]
ROOT = os.path.abspath(_args[0]) if _args else os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".."))
REPO = os.path.join(ROOT, "repo")
BASE = "https://2kgt.github.io/repo/"
errs, warns = [], []
E = lambda m: errs.append(m)
W = lambda m: warns.append(m)

def read_packages():
    for n in ("Packages", "Packages.bz2"):
        p = os.path.join(REPO, n)
        if os.path.exists(p):
            raw = bz2.open(p, "rt", encoding="utf-8").read() if n.endswith("bz2") else open(p, encoding="utf-8").read()
            return n, raw
    return None, ""

name, txt = read_packages()
if not txt:
    print("❌ Không tìm thấy Packages / Packages.bz2"); sys.exit(1)

# 1) Cú pháp APT nghiêm ngặt -----------------------------------------------------
stanzas, cur, ln = [], {}, 0
for i, line in enumerate(txt.split("\n"), 1):
    if not line.strip():
        if cur: stanzas.append(cur); cur = {}
        continue
    if line[0] in " \t":
        if not cur: E(f"Dòng {i}: tiếp nối nhưng chưa có field"); continue
        cur[last] += "\n" + line.strip(); continue
    m = re.match(r"^([A-Za-z][A-Za-z0-9\-]*):\s?(.*)$", line)
    if not m:
        E(f"{name} dòng {i}: SAI ĐỊNH DẠNG (dòng tiếp nối thiếu dấu cách đầu) → APT/Cydia/Zebra có thể bỏ cả file: {line[:70]!r}")
        continue
    last = m.group(1); cur[last] = m.group(2)
if cur: stanzas.append(cur)

need = ("Package", "Version", "Architecture", "Filename", "Size", "SHA256", "Description")
seen = defaultdict(list)
for s in stanzas:
    for k in need:
        if not s.get(k): E(f"{s.get('Package','?')}: thiếu field {k}")
    seen[(s.get("Package"), s.get("Architecture"), s.get("Version"))].append(s)
    if "Depends" not in s and "Depiction" not in s and "SileoDepiction" not in s:
        pass
for k, v in seen.items():
    if len(v) > 1: E(f"Trùng stanza {k}")

# 2) Kiến trúc / rootful-rootless -------------------------------------------------
archs = defaultdict(set); pkg_archs = set()
for s in stanzas:
    archs[s["Package"]].add(s["Architecture"]); pkg_archs.add(s["Architecture"])
only_rootless = [p for p, a in sorted(archs.items()) if "iphoneos-arm" not in a]
only_rootful  = [p for p, a in sorted(archs.items()) if not (a & {"iphoneos-arm64", "iphoneos-arm64e"})]
if only_rootless: W(f"{len(only_rootless)} package CHỈ có rootless (arm64/arm64e) → máy ROOTFUL (iphoneos-arm) KHÔNG thấy: {', '.join(only_rootless)}")
if only_rootful:  W(f"{len(only_rootful)} package CHỈ có rootful (arm) → máy ROOTLESS (Dopamine…) KHÔNG thấy: {', '.join(only_rootful)}")

# 3) Release ---------------------------------------------------------------------
rel = open(os.path.join(REPO, "Release"), encoding="utf-8").read() if os.path.exists(os.path.join(REPO, "Release")) else ""
if not rel: E("Thiếu file Release")
else:
    m = re.search(r"^Architectures:\s*(.*)$", rel, re.M)
    declared = set(m.group(1).split()) if m else set()
    for a in pkg_archs - declared:
        W(f"Release thiếu kiến trúc '{a}' trong Architectures (Packages có dùng)")
    if "SHA256:" not in rel and "MD5Sum:" not in rel:
        W("Release không có checksum Packages (không bắt buộc với Sileo, nhưng APT/Zebra kiểm tra)")
    if not re.search(r"^Date:", rel, re.M): W("Release không có Date")
    # checksum khớp?
    for fname, hx in re.findall(r"^ ([0-9a-f]{64}) +\d+ (\S+)$", rel, re.M)[::-1] if False else []:
        pass
    for h, size, fname in re.findall(r"^ ([0-9a-f]{64}) +(\d+) (\S+)$", rel, re.M):
        p = os.path.join(REPO, fname)
        if os.path.exists(p) and hashlib.sha256(open(p, "rb").read()).hexdigest() != h:
            E(f"Release: SHA256 của {fname} KHÔNG khớp file thật")

# 4) File .deb + depiction ---------------------------------------------------------
miss = defaultdict(list)
has_debs = os.path.isdir(os.path.join(REPO, "debs"))
if not has_debs:
    W("Không có thư mục repo/debs trong bản này → bỏ qua kiểm tra file .deb / hash / depiction")
for s in stanzas:
    fn = s.get("Filename", "")
    if has_debs and not fn.startswith("http"):
        p = os.path.join(REPO, fn)
        if not os.path.exists(p): E(f"{s['Package']} {s['Version']}: Filename không tồn tại → {fn}")
        else:
            if os.path.getsize(p) != int(s["Size"]): E(f"{s['Package']}: Size lệch ({os.path.getsize(p)} ≠ {s['Size']})")
            if hashlib.sha256(open(p, "rb").read()).hexdigest() != s["SHA256"]: E(f"{s['Package']}: SHA256 lệch → Sileo báo lỗi hash khi cài")
    for fld in ("SileoDepiction", "Depiction"):
        u = s.get(fld, "")
        if not u: miss[fld].append(s['Package']); continue
        if u.startswith(BASE) and os.path.isdir(os.path.join(REPO, "data")):
            if not os.path.exists(os.path.join(REPO, u[len(BASE):])): E(f"{s['Package']}: {fld} 404 → {u[len(BASE):]}")
    if "Depends" not in s: miss["Depends"].append(s['Package'])

for fld, why in (("Depiction", "Cydia/Installer không có trang mô tả"),
                 ("SileoDepiction", "Sileo không có trang chi tiết"),
                 ("Depends", "Sileo không tự cài dependency (ellekit/preferenceloader…)")):
    if miss[fld]:
        u = sorted(set(miss[fld]))
        W(f"{len(miss[fld])}/{len(stanzas)} stanza thiếu {fld} → {why} (vd: {', '.join(u[:3])}{'…' if len(u)>3 else ''})")

# 5) debs.json ↔ Packages + chất lượng "Có gì mới" ------------------------------------
dj = os.path.join(REPO, "debs.json")
if os.path.exists(dj):
    d = json.load(open(dj, encoding="utf-8"))
    latest = {}
    for s in stanzas:
        latest.setdefault(s["Package"], s)
    placeholder = total = 0
    for a in d.get("apps", []):
        bid = a["bundleIdentifier"]
        if bid not in archs: E(f"{bid} có trong debs.json nhưng KHÔNG có trong Packages (Sileo/Cydia sẽ không thấy)"); continue
        pk_desc = latest[bid]["Description"].split("\n")[0].strip()
        js_desc = (a.get("localizedDescription") or "").split("\n")[0].strip()
        if pk_desc and js_desc and pk_desc != js_desc:
            W(f"{bid}: mô tả debs.json ≠ Packages ('{js_desc[:40]}…' vs '{pk_desc[:40]}…')")
        for v in a.get("versions", []):
            total += 1
            if re.search(r"từ Kyic Store|^Cập nhật lên v", v.get("localizedDescription", "")): placeholder += 1
    if total and placeholder:
        W(f"'Có gì mới': {placeholder}/{total} phiên bản chỉ có câu mặc định (chưa có ghi chú thật)")

print(f"📦 {len(stanzas)} stanza | kiến trúc: {sorted(pkg_archs)} | {len(archs)} package")
for e in errs: print("❌", e)
for w in warns: print("⚠️ ", w)
print(f"\n{'❌ CÓ LỖI' if errs else '✅ Không có lỗi nghiêm trọng'}: {len(errs)} lỗi, {len(warns)} cảnh báo")

if errs and "--notify" in sys.argv:
    try:                                   # gửi Telegram (nếu đã cấu hình secrets)
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import notify
        notify.notify_validation_failed(errs, len(warns))
    except Exception as ex:
        print(f"⚠️  Không gửi được Telegram: {ex}")
sys.exit(1 if errs else 0)
