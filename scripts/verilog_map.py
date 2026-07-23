#!/usr/bin/env python3
"""既有 Verilog design 的模組階層解析器 — 只依賴 Python 標準函式庫。

供 Reverse-Ingest 操作（見 CLAUDE.md「操作 7」）使用：在 LLM 逆向重建
架構頁/設計頁之前，先解析出「誰 instantiate 誰、每個模組的 ports」的機器
事實，降低大型 design 靠人工讀碼推斷階層的幻覺風險。不做語意分析，只做
結構抽取。

用法：
    python3 scripts/verilog_map.py map <目錄>              # 階層樹＋模組清單
    python3 scripts/verilog_map.py ports <目錄> <module>   # 單一模組的 ports
    python3 scripts/verilog_map.py diff <舊目錄> <新目錄>  # 兩版本的結構差異
                                                           # （新版 IP 匯入的影響分析）

限制：regex 啟發式解析，非完整 Verilog parser。**不解析 generate 區塊內的
具現化**——本 flow 生成的 RTL 一律禁止 generate（CLAUDE.md 編碼規則），但
匯入的原廠 baseline 可能用到：偵測到 generate/genvar 關鍵字會明確警告
「階層樹不保證完整」，不會靜默漏掉。
"""

import argparse
import re
import sys
from pathlib import Path

MODULE_RE = re.compile(
    r"\bmodule\s+(\w+)\s*(?:#\s*\((?:[^()]|\([^()]*\))*\))?\s*\((.*?)\)\s*;(.*?)\bendmodule\b",
    re.DOTALL,
)

# 模組本體內的具現化：<child_type> [#(...)] <instance_name> ( .port(...) ... );
# 只認 named port connection（.port(...)）開頭的括號，避免把 always/if 等誤判
KEYWORDS = {
    "if", "else", "begin", "end", "case", "endcase", "casez", "casex",
    "for", "while", "repeat", "forever", "always", "initial", "assign",
    "wire", "reg", "integer", "real", "time", "parameter", "localparam",
    "function", "endfunction", "task", "endtask", "generate", "endgenerate",
    "genvar", "input", "output", "inout", "signed", "posedge", "negedge",
    "or", "and", "not", "defparam", "specify", "endspecify",
}
INSTANCE_RE = re.compile(
    r"\b([A-Za-z_]\w*)\s*(?:#\s*\((?:[^()]|\([^()]*\))*\))?\s*([A-Za-z_]\w*)\s*\(\s*\."
)

PORT_RE = re.compile(
    r"\b(input|output|inout)\b\s*(?:reg|wire)?\s*(\[[^\]]+\])?\s*([A-Za-z_]\w*)"
)

GENERATE_RE = re.compile(r"\b(generate|genvar)\b")


def strip_comments(text):
    text = re.sub(r"//.*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return text


def parse_dir(root):
    """回傳 (modules, warnings)。
    modules = {name: {"file":…, "ports":[(dir,width,name)], "instances":[(type,inst)]}}
    """
    modules = {}
    warnings = []
    root = Path(root)
    files = sorted(root.rglob("*.v"))
    if not files:
        warnings.append(f"{root}: 目錄下找不到任何 .v 檔")
    for f in files:
        rel = f.relative_to(root).as_posix()
        text = strip_comments(f.read_text(encoding="utf-8", errors="replace"))
        if GENERATE_RE.search(text):
            warnings.append(
                f"{rel}: 含 generate/genvar——本工具不解析 generate 區塊內的具現化，"
                "此檔案相關的階層樹不保證完整，請人工確認"
            )
        found = list(MODULE_RE.finditer(text))
        if not found:
            warnings.append(f"{rel}: 找不到 module...endmodule，略過")
            continue
        for m in found:
            name, header, body = m.group(1), m.group(2), m.group(3)
            # Verilog-2001 ANSI style：ports 宣告在 header；non-ANSI 則在 body
            ports = PORT_RE.findall(header) or PORT_RE.findall(body)
            instances = [
                (child, inst) for child, inst in INSTANCE_RE.findall(body)
                if child not in KEYWORDS and inst not in KEYWORDS
            ]
            if name in modules:
                warnings.append(f"{rel}: module {name} 重複定義，以先出現者為準")
                continue
            modules[name] = {
                "file": rel,
                "ports": [(d, (w or "1").strip(), n) for d, w, n in ports],
                "instances": instances,
            }
    return modules, warnings


def print_warnings(warnings):
    if warnings:
        print("\n警告：")
        for w in warnings:
            print(f"  - {w}")


def cmd_map(root):
    modules, warnings = parse_dir(root)
    if not modules:
        print_warnings(warnings)
        sys.exit(f"{root}: 找不到任何 module")
    instantiated = {t for m in modules.values() for t, _ in m["instances"]}
    tops = [n for n in modules if n not in instantiated]

    print(f"掃描 {root}：{len(modules)} 個 module\n")

    def walk_inline(name, indent, seen):
        info = modules.get(name)
        if info is None:
            print(f"{name}  [未在掃描範圍內定義：外部模組或黑盒]")
            return
        print(f"{name}  ({info['file']}, {len(info['ports'])} ports)")
        if name in seen:
            pad = "  " * indent
            print(f"{pad}  ...（遞迴具現化，停止展開）")
            return
        pad = "  " * indent
        for child, inst in info["instances"]:
            print(f"{pad}  └─ {inst} : ", end="")
            walk_inline(child, indent + 2, seen | {name})

    if not tops:
        print("找不到明確的 top（所有模組都被具現化，可能互相引用）")
        tops = sorted(modules)
    for t in tops:
        print(f"{t}  ({modules[t]['file']}, {len(modules[t]['ports'])} ports)")
        for child, inst in modules[t]["instances"]:
            print(f"  └─ {inst} : ", end="")
            walk_inline(child, 2, {t})
        print()

    print("模組清單：")
    for name in sorted(modules):
        info = modules[name]
        role = "top" if name in tops else "sub"
        print(f"  [{role}] {name:<24} {info['file']}  "
              f"({len(info['ports'])} ports, {len(info['instances'])} instances)")
    print_warnings(warnings)


def cmd_ports(root, module):
    modules, warnings = parse_dir(root)
    info = modules.get(module)
    if info is None:
        print_warnings(warnings)
        sys.exit(f"找不到 module {module}（掃描範圍：{root}）")
    print(f"{module}（{info['file']}）ports：")
    for direction, width, name in info["ports"]:
        print(f"  {direction:<7} {width:<12} {name}")
    print_warnings(warnings)


def cmd_diff(old_root, new_root):
    """兩個版本目錄的結構差異——新版 IP 匯入（Reverse-Ingest 更新模式）的影響分析。"""
    old_mods, old_warn = parse_dir(old_root)
    new_mods, new_warn = parse_dir(new_root)
    old_names, new_names = set(old_mods), set(new_mods)

    changes = 0
    for name in sorted(new_names - old_names):
        print(f"新增模組：{name}（{new_mods[name]['file']}）")
        changes += 1
    for name in sorted(old_names - new_names):
        print(f"移除模組：{name}（原 {old_mods[name]['file']}）")
        changes += 1

    for name in sorted(old_names & new_names):
        o, n = old_mods[name], new_mods[name]
        o_ports, n_ports = set(o["ports"]), set(n["ports"])
        for d, w, p in sorted(n_ports - o_ports):
            print(f"ports 變更：{name} 新增 {d} {w} {p}")
            changes += 1
        for d, w, p in sorted(o_ports - n_ports):
            print(f"ports 變更：{name} 移除 {d} {w} {p}")
            changes += 1

        def inst_count(m):
            counts = {}
            for t, _ in m["instances"]:
                counts[t] = counts.get(t, 0) + 1
            return counts
        o_cnt, n_cnt = inst_count(o), inst_count(n)
        for t in sorted(set(o_cnt) | set(n_cnt)):
            if o_cnt.get(t, 0) != n_cnt.get(t, 0):
                print(f"具現化數量變更：{name} 內的 {t} "
                      f"{o_cnt.get(t, 0)} 個 → {n_cnt.get(t, 0)} 個")
                changes += 1

    if changes == 0:
        print("結構無差異（模組集合、ports、具現化數量皆相同）")
    else:
        print(f"\n共 {changes} 項結構差異")
    print_warnings(["[舊] " + w for w in old_warn] + ["[新] " + w for w in new_warn])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("map", help="印模組階層樹與清單")
    p.add_argument("dir")

    p = sub.add_parser("ports", help="印單一模組的 ports 清單")
    p.add_argument("dir")
    p.add_argument("module")

    p = sub.add_parser("diff", help="比較兩個版本目錄的結構差異")
    p.add_argument("old_dir")
    p.add_argument("new_dir")

    args = parser.parse_args()
    if args.cmd == "map":
        cmd_map(args.dir)
    elif args.cmd == "ports":
        cmd_ports(args.dir, args.module)
    else:
        cmd_diff(args.old_dir, args.new_dir)


if __name__ == "__main__":
    main()
