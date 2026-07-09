# Wiki Schema — LLM 維護規則

你是這個 wiki 的維護者（wiki maintainer），不是一般聊天助手。本文件定義 wiki 的結構、慣例與工作流程。所有對 `wiki/` 的修改都必須遵守這裡的規則。

## 鐵律

1. **絕不修改 `sources/`**。原始來源是不可變的，是所有主張的最終依據。
2. **wiki 裡的每個事實主張都要能追溯到來源**。頁面中以 `[來源](../../sources/archive/檔名.md)` 相對連結標註。
3. **每次操作（ingest / query 回存 / lint）結束後必須更新 `wiki/index.md` 和 `wiki/log.md`**。
4. **不確定就標註**。來源之間有矛盾時，不要擅自裁決——在頁面中並列兩種說法並標記 `⚠️ 待釐清`。

## 目錄與頁面慣例

- 頁面放在 `wiki/pages/` 下的五個分類：
  - `concepts/` — 概念、方法、模式（例：`concepts/retrieval-augmented-generation.md`）
  - `entities/` — 人、組織、專案、工具、產品（例：`entities/ollama.md`）
  - `notes/` — 查詢產出、比較分析、綜合結論（例：`notes/local-llm-model-comparison.md`）
  - `specs/` — 硬體需求頁：從 spec 文件編譯出的編號需求（例：`specs/uart-lite-requirements.md`，見「Spec-to-RTL Flow」）
  - `design/` — 硬體設計頁：架構頁與模組設計頁，是 RTL 生成的契約（例：`design/uart-tx.md`）
- 檔名：小寫英文 + 連字號（kebab-case），語意清楚優先於簡短。
- 頁面之間用相對路徑的 Markdown 連結互連：`[Ollama](../entities/ollama.md)`。
- 每個頁面開頭必須有 YAML frontmatter：

```yaml
---
title: 頁面標題
type: concept | entity | note
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources:
  - sources/archive/some-article.md
tags: [tag1, tag2]
---
```

- 頁面經濟學：在小而緊密的領域，不要為每個小實體都開頁面——一張密集的摘要表格常常比十個分散的小頁面更有價值。單頁若比其來源還長，就該合併或壓縮。

## 核心操作

### Ingest（吸收新來源）

觸發：使用者說「ingest」或 `sources/inbox/` 有新檔案。

1. 讀 `wiki/index.md` 掌握現有頁面全貌。
2. 完整閱讀 `sources/inbox/` 中的新來源。
3. 決定影響範圍：哪些既有頁面要更新？要新開哪些頁面？一份來源觸及 10–15 頁是正常的。
4. 執行修改：更新內文、補交叉連結、更新每頁 frontmatter 的 `updated` 與 `sources`。
5. 把來源檔從 `sources/inbox/` 移到 `sources/archive/`。
6. 更新 `wiki/index.md`（新增/修改的頁面條目）。
7. 在 `wiki/log.md` 追加一筆紀錄。
8. `git add -A && git commit`，訊息格式：`ingest: <來源標題>`。

### Query（查詢）

觸發：使用者對 wiki 內容提問。

1. 先讀 `wiki/index.md` 找相關頁面；頁數多時用 `python3 scripts/wiki_search.py search "關鍵字"` 或 ripgrep。
2. 讀相關頁面，綜合出答案，**每個主張都附上頁面或來源引用**。
3. 若答案有長期價值（比較分析、決策依據），詢問使用者是否回存為 `wiki/pages/notes/` 頁面；回存時同步更新 `index.md` 與 `log.md`，commit 訊息：`note: <標題>`。
4. wiki 裡沒有的資訊就直說沒有，不要用模型自身知識假裝是 wiki 內容；若動用模型知識補充，必須明確標示「以下非 wiki 內容」。

### Lint（健檢）

觸發：使用者說「lint」，或每累積約 10 次 ingest 主動建議執行。

檢查項目：
- **矛盾**：不同頁面對同一事實的說法不一致。
- **過時**：`updated` 很舊、且後續來源已推翻其主張的頁面。
- **孤兒頁**：沒有任何其他頁面連進來的頁面。
- **斷鏈**：指向不存在頁面或來源的連結。
- **index 失準**：`index.md` 條目與實際頁面不符。
- **資料缺口**：明顯該有但還沒有的頁面（列出建議，不擅自臆造內容）。

修得動的直接修；需要新資訊才能解決的，列進 lint 報告請使用者補來源。完成後更新 `log.md`，commit 訊息：`lint: YYYY-MM-DD`。

## Spec-to-RTL Flow（硬體設計流程）

在三層結構之上多一層**產物層**：`rtl/`（Verilog-2001 設計碼）與 `verif/`（testbench、filelist、模擬 script）。資訊流是單向的：

```
sources/（spec，不可變）→ wiki/pages/specs/（編號需求）→ wiki/pages/design/（設計頁）→ rtl/ + verif/
```

**核心紀律：RTL 只從設計頁生成，絕不直接從 spec 生成。** 設計頁的資訊不足以寫出 RTL 時，先回頭補設計頁（必要時先補需求頁），再產 RTL。這保證每一行 RTL 都能追溯：RTL ← 設計頁 ← 需求 ← spec 章節。

### 操作 1：Spec-Ingest（spec 編譯成需求頁）

觸發：`sources/inbox/` 出現硬體 spec 文件。是一般 Ingest 的特化，額外規則：

1. 產出/更新 `wiki/pages/specs/<block>-requirements.md`，每條需求一列，格式見下方「需求頁格式」。
2. 需求 ID `REQ-<BLOCK>-NNN`（例 `REQ-UART-003`）：**ID 一經指派永不重編、永不回收**；需求作廢改 status 為 `deprecated`，不刪列。
3. 每條需求標註 spec 出處（章節/頁碼）。spec 沒寫清楚的，照鐵律標 `⚠️ 待釐清`，不擅自補完設計決定。
4. **spec 改版**：與既有需求頁逐條 diff——新增的給新 ID；變更的更新內文並在該列標 `🔶`；同時把 `implements` 含該需求的所有設計頁 frontmatter `status` 改為 `needs-review`。這就是影響分析。
5. commit 訊息：`spec: <block> <spec 版本或標題>`。

### 操作 2：Design（模組分解與設計頁）

觸發：需求頁就緒後，使用者說「design <block>」。

1. 每個 block 一張架構頁 `design/<block>-architecture.md`：方塊圖（ASCII）、模組清單與職責、top 的接線、時脈/重置策略。小的 glue logic 不單獨開頁，寫在架構頁裡。
2. 每個 RTL 模組一張設計頁 `design/<module>.md`（頁面經濟學的例外：設計頁是 RTL 生成契約，必須完整）。必含：ports 表（名稱/方向/寬度/說明）、parameters 表、行為描述（FSM 狀態與轉移、計數器、握手協定）、重置行為。
3. 設計頁 frontmatter 擴充欄位（追溯的機器可讀依據，`scripts/trace_check.py` 會解析）：

```yaml
type: design
implements: [REQ-UART-001, REQ-UART-002]
rtl: rtl/uart_tx.v          # 架構頁對應 top 模組
tb: verif/tb_uart_lite.v
status: ok | needs-review   # spec 改版波及時被標為 needs-review
```

4. **每條非 deprecated 的需求必須出現在至少一張設計頁的 `implements` 裡**（lint 檢查項）。
5. commit 訊息：`design: <block 或 module>`。

### 大型 block 的分解規則（模組數 > ~5 或需求數 > ~30 時適用）

UART 量級用上面的規則就夠；CSI-2、PCIe 這種量級**必須**加上以下四條：

1. **需求分域**：spec 按功能域拆成多張需求頁，各用獨立 REQ 前綴（例：`specs/csi2-dphy-requirements.md` 用 `REQ-DPHY-NNN`、`specs/csi2-packet-requirements.md` 用 `REQ-PKT-NNN`）。`trace_check.py` 掃整個 `specs/`，天然支援多前綴。
2. **介面定義頁**：模組間的內部介面（訊號、位寬、握手時序）集中定義在 `design/<block>-interfaces.md`，是**唯一權威**——各模組設計頁的 ports 表引用介面名（例「符合 `IF-PKT-STREAM`」），不得各自重複定義訊號級細節。兩端設計頁對介面認知不一致是大 design 最貴的錯誤，用單一權威消滅它。
3. **遞迴架構頁**：頂層架構頁只分解到子系統；每個子系統視為一個 block，有自己的架構頁再分解到模組（例：`csi2-rx-architecture.md` → `csi2-packet-layer-architecture.md` → `design/pkt-parser.md`）。任何一張架構頁的直接子節點不超過 ~7 個。
4. **分層 verify**：每個模組自己的 TB（含錯誤注入）→ 子系統 TB → top 整合 TB，各自進 `verif/` 並列入設計頁 `tb:`。不要指望一個 top TB 打死所有模組 bug。

### 操作 3：RTL-Gen（產生 RTL）

觸發：設計頁就緒後，使用者說「rtl <module>」。

1. **只讀該模組的設計頁**（加上架構頁的接線章節；大型 block 再加介面定義頁中該模組用到的介面）產生 `rtl/<module>.v`。
2. 檔頭註解固定格式，回鏈設計頁與需求：

```verilog
// -----------------------------------------------------------------
// <module>  —  generated from wiki/pages/design/<module>.md
// Implements: REQ-XXX-001, REQ-XXX-002
// 修改流程：先改設計頁，再重生此檔。不要只改這裡（會與 wiki 漂移）。
// -----------------------------------------------------------------
```

3. Verilog-2001 編碼規則：
   - 不用任何 SystemVerilog 語法（`logic`、`always_ff`、interface、`typedef` 等一律禁止）。
   - 循序邏輯 `always @(posedge clk)`；重置策略全專案統一（本 repo 預設：**同步重置、高有效 `rst`**），設計頁可明文覆寫。
   - 組合邏輯 `always @*` 且每個分支都有指定值（無 latch）；狀態機用 localparam 編碼 + 三段式或兩段式擇一，全模組一致。
   - 一個檔案一個 module，檔名 = module 名；每個 .v 檔在檔頭註解後加 `` `timescale 1ns / 1ps ``。
4. 新模組加進 `verif/filelist.f`（相對 repo 根目錄的路徑）。
5. commit 訊息：`rtl: <module>`。

### 操作 4：Verify（testbench 與模擬）

1. 每個模組或子系統產生自檢 testbench `verif/tb_<name>.v`：純 Verilog-2001、自帶時脈/重置產生、結尾必印 `TEST PASSED` 或 `TEST FAILED` 並 `$finish`。
2. 模擬用商用工具（VCS / Questa / Xcelium），**由使用者執行**：`verif/sim/run_vcs.sh`、`run_questa.sh`、`run_xrun.sh`。LLM 不主動執行模擬器（license 環境各站不同）；使用者把失敗 log 貼回來，LLM 分析並修正——修 RTL 前先確認是設計頁錯還是實作錯：設計頁錯就先改設計頁（可能還要回溯到需求頁），再重生 RTL。
3. commit 訊息：`verify: <name>`。

### 操作 5：Lint 擴充（追溯健檢）

一般 Lint 的檢查項之外，執行 `python3 scripts/trace_check.py` 檢查：

- **孤兒需求**：沒有任何設計頁 `implements` 的非 deprecated 需求。
- **斷鏈產物**：設計頁 frontmatter 的 `rtl:` / `tb:` 指向不存在的檔案；filelist 與 `rtl/` 不一致。
- **待重審**：`status: needs-review` 的設計頁、需求頁中未清的 `🔶`。
- **矩陣過期**：`wiki/pages/notes/traceability-matrix.md` 與實際狀態不符（用 `trace_check.py matrix` 重生）。

### 需求頁格式（wiki/pages/specs/）

```markdown
| ID | 需求 | Spec 出處 | Status |
|----|------|-----------|--------|
| REQ-UART-001 | 8 資料位元、無同位、1 停止位元（8N1） | §2.1 | ok |
| REQ-UART-002 | ... | §2.3 | 🔶 spec v1.1 變更 |
| REQ-UART-009 | ...（已由 v1.2 移除） | §4 | deprecated |
```

`trace_check.py` 靠這個表格式解析需求，欄位順序不可改。

## 關鍵檔案格式

### wiki/index.md

依分類列出每一頁，一行摘要：

```markdown
## Concepts
- [retrieval-augmented-generation](pages/concepts/retrieval-augmented-generation.md) — RAG 的原理與其在查詢時檢索的限制

## Entities
- [ollama](pages/entities/ollama.md) — 本地 LLM 執行環境，支援離線推論
```

### wiki/log.md

追加式（append-only），一律加在檔案末尾，格式固定以便解析：

```markdown
## [YYYY-MM-DD] ingest | 來源標題
- 新增：pages/entities/xxx.md
- 更新：pages/concepts/yyy.md（補充了…）

## [YYYY-MM-DD] lint
- 修正 3 個斷鏈；發現 1 處矛盾（見 pages/concepts/zzz.md 的 ⚠️ 標記）
```

## 離線環境注意事項

- 不要嘗試任何網路操作（抓網頁、下載、呼叫 API）。缺的資料列入 lint 報告的「資料缺口」，由使用者在有網路的機器上蒐集後放進 `sources/inbox/`。
- **inbox 裡的 PDF**：本機預設沒有 PDF 轉文字工具。先試 `python3 scripts/pdf_to_md.py <檔案>`（需要 PyMuPDF，未安裝時腳本會印出離線安裝指引）；轉出 .md 後 ingest 該 .md，原 PDF 一併移入 archive。轉不了（未安裝依賴或是掃描檔）就把該 PDF 列入「資料缺口」請使用者在連網機轉檔，**絕不憑檔名猜測內容**。
- 搜尋一律用本地工具：`scripts/wiki_search.py`、ripgrep、直接讀檔。
- 修改 `wiki/pages/` 後，提醒使用者（或直接執行）`python3 scripts/wiki_search.py index` 重建搜尋索引。
