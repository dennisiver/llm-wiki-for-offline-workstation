#!/usr/bin/env python3
"""Spec-to-RTL 追溯檢查 — 只依賴 Python 標準函式庫。

用法：
    python3 scripts/trace_check.py check    # 追溯健檢，有缺口 exit 1（lint 時執行）
    python3 scripts/trace_check.py matrix   # 重生 wiki/pages/notes/traceability-matrix.md

機器可讀約定（定義於 CLAUDE.md 的 Spec-to-RTL 章節）：
  - 需求頁（wiki/pages/specs/*.md）表格：| ID | 需求 | Spec 出處 | Status |
  - 設計頁（wiki/pages/design/*.md）frontmatter：implements / rtl / tb / status
"""

import re
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPECS_DIR = REPO_ROOT / "wiki" / "pages" / "specs"
DESIGN_DIR = REPO_ROOT / "wiki" / "pages" / "design"
FILELIST = REPO_ROOT / "verif" / "filelist.f"
MATRIX_PATH = REPO_ROOT / "wiki" / "pages" / "notes" / "traceability-matrix.md"

REQ_ROW = re.compile(r"^\|\s*(REQ-[A-Z0-9]+-\d+)\s*\|(.*)\|(.*)\|(.*)\|\s*$")


def parse_requirements():
    """回傳 {req_id: {"desc":…, "origin":…, "status":…, "page":…}}"""
    reqs = {}
    if not SPECS_DIR.is_dir():
        return reqs
    for page in sorted(SPECS_DIR.glob("*.md")):
        rel = page.relative_to(REPO_ROOT).as_posix()
        for line in page.read_text(encoding="utf-8").splitlines():
            m = REQ_ROW.match(line.strip())
            if m:
                rid, desc, origin, status = (g.strip() for g in m.groups())
                reqs[rid] = {
                    "desc": desc, "origin": origin,
                    "status": status, "page": rel,
                }
    return reqs


def parse_frontmatter(text):
    """極簡 YAML 子集：只解析本 repo frontmatter 用到的 key: value 與 inline list。"""
    fm = {}
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return fm
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^(\w+):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val.startswith("[") and val.endswith("]"):
            fm[key] = [v.strip() for v in val[1:-1].split(",") if v.strip()]
        else:
            fm[key] = val
    return fm


def parse_design_pages():
    """回傳 [{"page":…, "implements":[…], "rtl":…, "tb":…, "status":…}]"""
    pages = []
    if not DESIGN_DIR.is_dir():
        return pages
    for page in sorted(DESIGN_DIR.glob("*.md")):
        fm = parse_frontmatter(page.read_text(encoding="utf-8"))
        pages.append({
            "page": page.relative_to(REPO_ROOT).as_posix(),
            "implements": fm.get("implements", []),
            "rtl": fm.get("rtl", ""),
            "tb": fm.get("tb", ""),
            "status": fm.get("status", ""),
        })
    return pages


def run_check(reqs, designs):
    issues = []

    implemented = {}
    for d in designs:
        for rid in d["implements"]:
            implemented.setdefault(rid, []).append(d["page"])
            if rid not in reqs:
                issues.append(f"未知需求：{d['page']} implements {rid}，但沒有任何需求頁定義它")

    for rid, info in reqs.items():
        if info["status"] == "deprecated":
            continue
        if rid not in implemented:
            issues.append(f"孤兒需求：{rid}（{info['page']}）沒有任何設計頁承接")
        if "🔶" in info["status"] or "🔶" in info["desc"]:
            issues.append(f"待重審：{rid} 帶 🔶 標記（{info['page']}），spec 改版影響尚未消化")

    for d in designs:
        for key in ("rtl", "tb"):
            path = d[key]
            if path and not (REPO_ROOT / path).is_file():
                issues.append(f"斷鏈產物：{d['page']} 的 {key}: {path} 不存在")
        if d["status"] == "needs-review":
            issues.append(f"待重審：{d['page']} status 為 needs-review")

    rtl_files = {p.relative_to(REPO_ROOT).as_posix()
                 for p in (REPO_ROOT / "rtl").glob("*.v")} if (REPO_ROOT / "rtl").is_dir() else set()
    listed = set()
    if FILELIST.is_file():
        for line in FILELIST.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith(("#", "//", "+", "-")):
                listed.add(line)
                if not (REPO_ROOT / line).is_file():
                    issues.append(f"filelist 斷鏈：{line} 不存在")
    for missing in sorted(rtl_files - listed):
        issues.append(f"filelist 缺漏：{missing} 不在 {FILELIST.relative_to(REPO_ROOT)} 裡")

    return issues


def build_matrix(reqs, designs):
    impl_map = {}
    for d in designs:
        for rid in d["implements"]:
            impl_map.setdefault(rid, []).append(d)

    today = date.today().isoformat()
    lines = [
        "---",
        "title: 追溯矩陣（REQ ↔ 設計頁 ↔ RTL ↔ TB）",
        "type: note",
        "created: 2026-07-09",
        f"updated: {today}",
        "sources: []",
        "tags: [traceability, spec-to-rtl, generated]",
        "---",
        "",
        "# 追溯矩陣",
        "",
        "> 由 `python3 scripts/trace_check.py matrix` 產生，**不要手改**——改了下次重生就會被蓋掉。",
        "",
        "| 需求 | Status | 設計頁 | RTL | Testbench |",
        "|------|--------|--------|-----|-----------|",
    ]
    for rid in sorted(reqs):
        info = reqs[rid]
        ds = impl_map.get(rid, [])
        pages = "<br>".join(
            f"[{Path(d['page']).stem}](../design/{Path(d['page']).name})" for d in ds
        ) or "—"
        rtls = "<br>".join(sorted({f"`{d['rtl']}`" for d in ds if d["rtl"]})) or "—"
        tbs = "<br>".join(sorted({f"`{d['tb']}`" for d in ds if d["tb"]})) or "—"
        lines.append(f"| {rid} | {info['status']} | {pages} | {rtls} | {tbs} |")
    lines.append("")
    return "\n".join(lines)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("check", "matrix"):
        sys.exit(__doc__)
    reqs = parse_requirements()
    designs = parse_design_pages()

    if sys.argv[1] == "matrix":
        MATRIX_PATH.parent.mkdir(parents=True, exist_ok=True)
        MATRIX_PATH.write_text(build_matrix(reqs, designs), encoding="utf-8")
        print(f"已重生 {MATRIX_PATH.relative_to(REPO_ROOT)}"
              f"（{len(reqs)} 條需求、{len(designs)} 張設計頁）")
        return

    issues = run_check(reqs, designs)
    if issues:
        print(f"追溯檢查：{len(issues)} 個缺口")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    print(f"追溯檢查通過：{len(reqs)} 條需求、{len(designs)} 張設計頁、零缺口")


if __name__ == "__main__":
    main()
