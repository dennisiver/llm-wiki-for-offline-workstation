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

### Query 補充：同一主題有多種來源的設計頁時

情境：查詢的主題同時有 spec 產生的頁面（`specs/`、spec-derived 設計頁）與 Reverse-Ingest 產生的設計頁（`origin: reverse-engineered`，見操作 7）。兩者性質不同——spec 頁講「應該怎樣」，逆向頁講「匯入的 RTL 實際怎樣」——**不可混為一談**：

1. 搜尋時兩種來源都納入，不偏廢。
2. 每個主張標明來源性質：「依 spec 規定」vs「依匯入的 `<project>` 實際 RTL 記錄」。
3. 兩者對同一件事說法不同時：已有 `deviates` 記錄（代表核對過）就直接引用該記錄；**從未核對過**（`implements`/`deviates` 皆空）就如實說「這兩份頁面尚未核對過是否一致」，分別列出兩邊說法，不擅自判斷是否衝突、不假裝一致。
4. 依問題性質決定優先引用：問 spec 規定 → `specs/` 優先；問實際實作 → 逆向設計頁優先；問題含糊 → 兩者並陳並標明是否核對過。

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

### 設計頁目錄慣例：大型 block 用專案子目錄

達到大型 block 門檻的 block（模組數 > ~5 或需求數 > ~30），**不論 spec 設計還是 Reverse-Ingest 匯入**，都在 `design/` 下開專案子目錄（例：`design/mipi-csi2-rx/`），該 block 的架構頁、介面定義頁、模組設計頁全放在裡面；小型 block（如 uart-lite）維持扁平檔名。子目錄按「屬於哪個專案」分——這是永久事實；不按「來源」分——那會隨 Design-Revise 而過時。`rtl/` 對應比照（`rtl/<project>/`）。兩種來源共用命名空間，建立子目錄前先做碰撞檢查（見操作 7 的碰撞規則，對正向 Design 同樣適用）。

### Design-Revise（既有設計頁的互動修改）

觸發：使用者對一張既有設計頁描述修改想法（例：「design-revise uart_tx：改成支援 2 個停止位元」）。不論該頁來自正向 Design 或 Reverse-Ingest（操作 7），流程相同：

1. 讀該設計頁＋所屬架構頁；針對**這次要修改/新增的範圍**主動搜尋相關的 `specs/` 需求頁作為建議依據。**只查與本次改動相關的 REQ，不對整個模組做全面稽核**——沒被 touch 的部分不主動挑毛病。
2. 把想法套進設計頁，**只動必要的地方**。「必要」不等於「單一檔案」：若改動牽涉共用介面定義頁或其他模組對本模組的假設，相關頁面必須一併更新以維持一致——該避免的是順手動與本次需求無關的部分。
3. 對本次改動涉及的 REQ 逐條檢查：
   - 與 REQ 衝突：標 `⚠️` 說明衝突與影響，**僅建議、不阻擋**（使用者可能刻意偏離 spec）；使用者決定接受偏離的，把該 REQ 記入 frontmatter `deviates`（欄位定義見操作 7）並在 ⚠️ 區塊寫接受理由。
   - 滿足了原本未連結的 REQ、或使某 REQ 失效：提出 `implements` 異動建議，使用者確認後才落筆。
4. 設計頁末尾維護「變更記錄」小節（日期、改了什麼、為什麼）。
5. 衝突已裁決設 `status: ok`，未裁決設 `needs-review`。
6. **每次有意義的修改各自 commit**：`design: <module> revise（一行摘要）`。
7. 使用者滿意後照操作 3 執行 `rtl <module>` 重生 RTL（逆向匯入模組適用其 baseline 風格補充規則）。

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
   - **禁止 `generate`/`genvar`**：重複結構（例：多條 lane 各一份邏輯）一律明確展開為具名 instance（`lane_deskew u_lane0 (...); lane_deskew u_lane1 (...);`），不用迴圈生成——除錯時波形才能直接對應到單一 instance。適用於所有經 RTL-Gen 產生/重生的檔案（匯入的原廠 baseline 若已用 generate，那是凍結來源、不改寫；其解析限制見操作 7）。
4. 新模組加進 `verif/filelist.f`（相對 repo 根目錄的路徑）。
   - 補充（filelist 的 `+incdir+` 慣例）：專案有 `.vh` header 或 `` `include `` 時，在該專案檔案清單前加一行 `+incdir+rtl/<project>/`（或 header 實際所在目錄）——VCS/Questa/Xcelium 的 `-f` 都原生支援此語法，`trace_check.py` 掃 filelist 時會自動跳過 `+` 開頭的行。
5. commit 訊息：`rtl: <module>`。

### RTL-Gen 對逆向匯入模組的補充：baseline 風格參考

對 `origin: reverse-engineered` 且 frontmatter 有 `baseline_rtl:` 的模組，重生 RTL 時**額外允許**讀取該凍結的原始檔案，用途**嚴格限定於風格**：訊號/變數命名慣例（如 `i_`/`o_` 前綴）、排版與 always block 分段方式、localparam/狀態機命名。目的：重生後與原廠版 diff 雜訊小，只有真正改變行為的地方有差異。

**行為（FSM 轉移、時序、握手、重置……）一律只依設計頁**——baseline 絕不能成為「設計頁沒寫、但原始碼有」的行為偷渡管道。對照風格時若發現原始碼有設計頁未記錄的行為，先回頭補設計頁（標 `⚠️ 待釐清` 或走 Design-Revise），不得默默照抄。

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

### 操作 6：Flow（半自動串接）

觸發：需求頁就緒後，使用者說「flow <block>」。把 Design → RTL-Gen → Verify 一口氣串完，用於需求單純、使用者不想逐階段下指令的場合。

1. **範圍**：不含 Spec-Ingest——spec 解讀必須人審，永遠獨立執行。flow 的起點是已存在的需求頁。
2. **啟動前檢查（gate）**：需求頁若有任何未清的 `⚠️ 待釐清` 或 `🔶`，**不啟動**，列出待裁決項請使用者處理。這是半自動與全自動的分界：歧義不許自動流過。
3. 依序執行，每階段照原規則各自 commit（`design:` → `rtl:` → `verify:`），歷史與手動逐步執行完全相同：
   - Design（架構頁 + 全部模組設計頁）→ 跑 `trace_check.py check`
   - RTL-Gen（全部模組 + filelist）
   - Verify（TB + 模擬 scripts）→ 再跑 `trace_check.py check`
4. **中途停下的條件**：設計頁寫不出來（需求資訊不足，需回補需求頁）；trace_check 出現缺口；任何需要設計決策但 spec 沒定義的情況。停下時報告已完成到哪個階段、卡住的原因、需要使用者裁決什麼。已完成階段的 commit 保留，不回滾。
5. **大型 block 限制**：達到「大型 block 分解規則」門檻的，flow 一次只跑**一個子系統**（例：`flow csi2-packet-layer`）；對整個 top 下 flow 時只產出頂層架構頁與介面定義頁，然後停下列出子系統清單。
6. 完成後輸出總結：新增頁面/RTL/TB 清單、追溯狀態、**提醒使用者執行模擬**（模擬仍由使用者跑，此界線不因 flow 而改變），並在 `log.md` 記一筆 `flow | <block>`。

### 操作 7：Reverse-Ingest（匯入既有 Verilog design）

觸發：使用者把一整包既有 Verilog 專案放進 `sources/inbox/<project>/`，說「reverse-ingest <project>」。目標：逆向重建設計頁作為之後 Design-Revise / RTL-Gen 的起點——**匯入時忠實記錄、盡量維持原設計，不預先比對 spec**。

1. 讀 `wiki/index.md` 掌握現有頁面。
2. 跑 `python3 scripts/verilog_map.py map sources/inbox/<project>/` 取得機器解析的模組階層（誰 instantiate 誰、各模組 ports）。LLM 在此骨架上補行為描述，**不自行從原始碼推斷階層**。工具對含 `generate` 的檔案會警告「階層樹不保證完整」——這些檔案的具現化須人工確認（工具不解析 generate 區塊；`ports <module>` 子指令可核對單一模組）。
3. **碰撞檢查**：建立 `design/<project>/`、`rtl/<project>/` 子目錄或任何新設計頁之前，先確認名稱未被使用（可能撞上既有 spec 設計的 block 或先前匯入的專案，雙向都可能）。已存在就**停下來問使用者要幫哪一邊改名**，不擅自選名、不靜默覆蓋。
4. 依「設計頁目錄慣例」建 `design/<project>/`：架構頁依真實階層畫（ASCII 方塊圖），每個模組一張設計頁，忠實記錄 as-is 行為。frontmatter 擴充欄位：

```yaml
origin: reverse-engineered
baseline_rtl: sources/archive/<project>/<file>.v   # 凍結原始碼，供 diff 與風格參考
implements: []    # 匯入時留白——不預先比對 spec
deviates: []      # RTL 行為與某 REQ 相抵觸且經使用者裁決後才記入
```

5. **不預先做 REQ 對照**：即使 wiki 已有相關 `specs/` 需求頁，匯入當下不逐模組比對、不預填 `implements`/`deviates`。比對只在按需時發生：Design-Revise touch 到該模組、或使用者明確要求「對照 XX 模組符不符合 spec」。屆時的鐵則：設計頁只寫 as-is，衝突經使用者裁決後記入 `deviates` 並在「⚠️ 與 spec 的差異」小節寫明（REQ、spec 要求、RTL 實作、影響）；三種出路（改 RTL 遵循 spec／接受偏離／spec 讓步改 REQ status）都由使用者裁決。
6. **階層與 spec 功能域分法不一致是常態**：模組邊界永遠依真實 RTL 階層，不為對齊 spec 功能域而切割/合併模組。一個模組橫跨多個 REQ 前綴、一條 REQ 由多模組承接都正常（`trace_check.py` 的「跨域模組」資訊性清單會列出，不影響檢查結果）。
7. 檔案落地：`sources/inbox/<project>/` 整包移入 `sources/archive/<project>/`（凍結，永不再改），同一批複製到 `rtl/<project>/`（工作副本，之後 Design-Revise → RTL-Gen 覆寫的對象）；在 `sources/archive/<project>/.version` 寫入版本標籤（問使用者，例 `v1.0`）。
8. 更新 `verif/filelist.f`（含必要的 `+incdir+`）、`wiki/index.md`、`wiki/log.md`。commit：`reverse-ingest: <project>`。

### 操作 7 更新模式：匯入同一專案的新版本

觸發：同一句「reverse-ingest <project>」，但 `sources/archive/<project>/` 已存在 → 自動切換為更新模式：

1. 讀 `.version` 得舊版標籤；問使用者新版標籤（不猜）。
2. 舊版整包改名封存：`sources/archive/<project>/` → `sources/archive/<project>-<舊版>/`（永久保留，不刪除）；新版落地為 `sources/archive/<project>/` 並更新 `.version`。
3. **結構化 diff**：`python3 scripts/verilog_map.py diff sources/archive/<project>-<舊版>/ sources/archive/<project>/` → 新增/移除模組、ports 變更、具現化數量變更；需要逐行差異再用 `diff -ru`。
4. **逐檔三方判斷**（本模式的核心）：對每個有變化的檔案，比對工作副本 `rtl/<project>/<file>` 與舊 baseline——
   - **工作副本＝舊 baseline**（使用者沒動過）：同步為新版內容；對應設計頁標 `status: needs-review` 並加註「🔶 baseline 已更新至 <新版>，設計頁尚未核對新版行為」。
   - **工作副本≠舊 baseline**（使用者改過、廠商也改了）：**不自動覆蓋**，標 `⚠️ 三方衝突待人工比對`，列出三個版本（舊 baseline／使用者修改版／新 baseline）請使用者決定合併方式。
5. 更新 `index.md`、`log.md`。commit：`reverse-ingest: <project> update <舊版> -> <新版>`。

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
- **不假設本機工具存在，動用前先確認**：`scripts/*.py`（`wiki_search.py`／`trace_check.py`／`verilog_map.py`／`pdf_to_md.py`）都需要 Python 3，`pdf_to_md.py` 額外需要 PyMuPDF——不同工作站不一定都裝好，用之前先確認（例如 `command -v python3`、`python3 -c "import fitz"`），不要假設文件寫過就一定在。缺少時**不擅自安裝任何東西**（含離線 wheel 的 `pip install`）——這是使用者的決定，不是 AI 自主行為；改用本機已確定存在的工具（`grep`/`diff`/直接讀檔）盡量完成任務，做不到的部分照鐵律列入「資料缺口」誠實回報給使用者，不要假裝完成或想辦法繞過去。
