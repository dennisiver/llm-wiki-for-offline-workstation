#!/usr/bin/env python3
"""離線 PDF → Markdown 轉換（備援方案，需要 PyMuPDF）。

首選流程是在連網機把 PDF 轉成 .md 再帶入（見 docs/ARCHITECTURE.md §3.1）。
本腳本是 PDF 已經在離線機上時的備援，依賴 PyMuPDF——
wheel 檔可在連網機下載後經 USB 離線安裝（見 docs/ARCHITECTURE.md §3.4）。

用法：
    python3 scripts/pdf_to_md.py sources/inbox/some-paper.pdf
    # 輸出 sources/inbox/some-paper.md（不覆蓋既有檔案，原 PDF 保留不動）

限制：只能抽文字型 PDF（含中文）。掃描檔（圖片型）抽不出字，
會警告並請你回連網機做 OCR。
"""

import sys
from pathlib import Path

OFFLINE_INSTALL_HINT = """\
錯誤：找不到 PyMuPDF（本腳本唯一的第三方依賴）。

離線安裝步驟：
  1. 連網機：pip download pymupdf -d pymupdf-wheels/
     （注意下載時指定離線機的 Python 版本與平台，必要時加
      --python-version 與 --platform 參數）
  2. 把 pymupdf-wheels/ 複製到 USB，帶到離線機
  3. 離線機：pip install --no-index --find-links pymupdf-wheels/ pymupdf
"""


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(f"用法：python3 {sys.argv[0]} <檔案.pdf>")

    try:
        import pymupdf  # PyMuPDF >= 1.24 的模組名（舊版為 fitz）
    except ImportError:
        try:
            import fitz as pymupdf
        except ImportError:
            sys.exit(OFFLINE_INSTALL_HINT)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.is_file():
        sys.exit(f"錯誤：找不到 {pdf_path}")
    out_path = pdf_path.with_suffix(".md")
    if out_path.exists():
        sys.exit(f"錯誤：{out_path} 已存在，不覆蓋。請先移走或改名。")

    doc = pymupdf.open(pdf_path)
    parts = [f"# {pdf_path.stem}\n\n> 轉自 `{pdf_path.name}`（scripts/pdf_to_md.py）\n"]
    empty_pages = 0
    for i, page in enumerate(doc, start=1):
        text = page.get_text().strip()
        if not text:
            empty_pages += 1
        parts.append(f"\n## 第 {i} 頁\n\n{text}\n")
    doc.close()

    out_path.write_text("".join(parts), encoding="utf-8")
    print(f"已輸出 {out_path}（{len(parts) - 1} 頁）")

    if empty_pages == len(parts) - 1:
        print(
            "警告：所有頁面都抽不出文字——這很可能是掃描檔（圖片型 PDF），\n"
            "需要 OCR，請回連網機處理（例如 MinerU / marker）。",
            file=sys.stderr,
        )
    elif empty_pages:
        print(
            f"警告：{empty_pages} 頁抽不出文字（可能是掃描頁或純圖片頁），"
            "請人工核對輸出。",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
