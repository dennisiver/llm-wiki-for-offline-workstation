# Changelog

記錄**框架/規則層本身**的演化——`CLAUDE.md`、`AGENTS.md`、`opencode.json`、
`scripts/`、`docs/` 的重大變動。追加式（append-only），新條目加在檔案末尾。

跟 `wiki/log.md` 分屬不同層級：`wiki/log.md` 記的是 wiki *內容* 的操作
（ingest/design/rtl/lint），這裡記的是**規則集本身**怎麼變。升級離線工作站時，
看這份檔案新增了哪些條目，就知道這次升級帶來什麼、不用臨時去 diff CLAUDE.md
猜。升級流程見 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §4.1。

## [2026-07-08] 初始架構

- 建立三層架構（sources / wiki / CLAUDE.md schema），改編自 Karpathy 的
  llm-wiki 模式，全系統零網路依賴。
- `scripts/wiki_search.py`：SQLite FTS5 全文搜尋，純 Python 標準函式庫。
- 新增 `AGENTS.md` + `opencode.json`，讓 Codex CLI 與 OpenCode 也能載入
  `CLAUDE.md` 規則（CLAUDE.md 維持唯一規範來源，不重複、不漂移）。
- 預設本地模型設為 Qwen3.6-27B（對齊實際工作站設定）。

## [2026-07-09] Spec-to-RTL Flow

- 新增硬體設計流程：spec → 編號需求頁（`specs/`）→ 模組設計頁（`design/`）→
  Verilog-2001 RTL + 自檢 testbench，全程可追溯。
- `scripts/trace_check.py`：追溯健檢與追溯矩陣產生。
- 附完整範例 uart-lite（8N1、可程式 baud divisor、valid/ready 握手），已用
  Icarus Verilog 模擬驗證 `TEST PASSED`。
- 大型 block（模組數 > ~5 或需求數 > ~30）的分解規則：REQ 多前綴分域、
  介面定義頁、遞迴架構頁、分層 verify（以 MIPI CSI-2 為例）。
- 半自動 `flow <block>` 指令，串接 Design → RTL-Gen → Verify，保留需求頁
  `⚠️`/`🔶` 未清時不啟動的 gate。
- `scripts/pdf_to_md.py`：PDF 轉 Markdown 備援（PyMuPDF，可離線安裝）。
- 離線框架更新程序初版（git bundle 經 USB）。

## [2026-07-10] 圖解總覽

- `docs/intro.html`：自包含單檔的架構與流程總覽，含與傳統 RAG 的比較，
  離線瀏覽器可直接開。

## [2026-07-23] Reverse-Ingest + Design-Revise

- 新增操作 7：Reverse-Ingest——匯入既有 Verilog design（例如既有的 MIPI IP），
  用 `scripts/verilog_map.py`（新增：`map`/`ports`/`diff` 三個子指令，純
  regex 解析）取得機器解析的模組階層，忠實重建設計頁（as-is，匯入當下**不**
  預先比對 spec）。
- 新增 Design-Revise：既有設計頁的互動修改，按需（新增功能或使用者明確要求時）
  參考 spec 給建議，衝突僅標 `⚠️` 不阻擋，接受的偏離記入新的 `deviates`
  frontmatter 欄位。
- 新版 IP 匯入的更新模式：`.version` 版本標籤、舊版封存、
  `verilog_map.py diff` 結構化比對、逐檔三方衝突判斷（使用者本地修改過的
  檔案絕不自動覆蓋）。
- 大型 block 一律用 `design/<project>/` 專案子目錄（不分 spec 生成或
  Reverse-Ingest 匯入），子目錄/檔案撞名會停下來問使用者要幫哪邊改名。
- RTL-Gen 新規則：禁止 `generate`/`genvar`，重複結構一律展開為具名
  instance；逆向匯入模組可參考 baseline 原始碼取風格/命名，行為仍唯設計頁
  是問。
- Query 操作補充：同一主題同時有 spec 生成與 Reverse-Ingest 生成的設計頁時，
  標明每個主張的來源性質，未核對過的地方不擅自判斷是否一致。
- `trace_check.py` 擴充：`deviates` 欄位解析（不算孤兒需求）、「跨域模組」
  資訊性清單，兩者皆不影響 exit code。
