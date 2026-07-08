#!/usr/bin/env python3
"""離線 wiki 全文搜尋 — SQLite FTS5，只依賴 Python 標準函式庫。

用法：
    python3 scripts/wiki_search.py index                 # 重建索引
    python3 scripts/wiki_search.py search "關鍵字" [-n 10]

索引檔存於 .wiki-index.db（不進版控，可隨時重建）。
索引範圍：wiki/ 與 sources/ 下的所有 .md 檔。
"""

import argparse
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / ".wiki-index.db"
INDEX_DIRS = ["wiki", "sources"]


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS pages USING fts5("
        "path, title, body, tokenize='unicode61')"
    )
    return conn


def extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
        if line.startswith("title:"):
            return line.split(":", 1)[1].strip()
    return fallback


def build_index() -> None:
    conn = connect()
    conn.execute("DELETE FROM pages")
    count = 0
    for d in INDEX_DIRS:
        base = REPO_ROOT / d
        if not base.is_dir():
            continue
        for md in sorted(base.rglob("*.md")):
            rel = md.relative_to(REPO_ROOT).as_posix()
            try:
                text = md.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                print(f"skip {rel}: {e}", file=sys.stderr)
                continue
            conn.execute(
                "INSERT INTO pages (path, title, body) VALUES (?, ?, ?)",
                (rel, extract_title(text, md.stem), text),
            )
            count += 1
    conn.commit()
    conn.close()
    print(f"indexed {count} files -> {DB_PATH.name}")


def search(query: str, limit: int) -> None:
    if not DB_PATH.exists():
        sys.exit("索引不存在，請先執行: python3 scripts/wiki_search.py index")
    conn = connect()
    rows = conn.execute(
        "SELECT path, title, snippet(pages, 2, '>>', '<<', ' … ', 12) "
        "FROM pages WHERE pages MATCH ? ORDER BY bm25(pages) LIMIT ?",
        (query, limit),
    ).fetchall()
    conn.close()
    if not rows:
        print("(沒有結果)")
        return
    for path, title, snip in rows:
        print(f"{path}  [{title}]")
        print(f"    {' '.join(snip.split())}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("index", help="重建全文索引")
    p_search = sub.add_parser("search", help="搜尋 wiki 與來源")
    p_search.add_argument("query")
    p_search.add_argument("-n", "--limit", type=int, default=10)
    args = parser.parse_args()

    if args.cmd == "index":
        build_index()
    else:
        search(args.query, args.limit)


if __name__ == "__main__":
    main()
