# sources/ — 原始來源（不可變）

- `inbox/`：新來源放這裡，等待 LLM ingest。
- `archive/`：已 ingest 的來源移到這裡，永久保存作為 wiki 主張的依據。

規則：
1. **LLM 絕不修改此目錄下的任何檔案內容**（ingest 完成後把檔案從 inbox 移到 archive 是唯一允許的操作）。
2. 建議格式：Markdown（網頁先在連網機用 Web Clipper 轉檔、圖片本地化後再帶入）。PDF 可放，但轉成 .md 的來源才能被全文搜尋。
3. 檔名：小寫 kebab-case，語意清楚，例：`2026-07-08-karpathy-llm-wiki.md`。
