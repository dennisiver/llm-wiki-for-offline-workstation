# Spec-to-RTL Flow — 以 llm-wiki 為核心的硬體設計流程

本文件說明如何用這個 wiki 把硬體 spec 一路帶到可驗證的 Verilog-2001 RTL。操作規則的正式定義在 [CLAUDE.md](../CLAUDE.md)（「Spec-to-RTL Flow」章節）；本文件解釋**為什麼這樣設計**與**怎麼日常使用**。

## 1. 核心思想：wiki 是 spec 與 RTL 之間的編譯層

直接把 spec 丟給 LLM 寫 RTL 有三個問題：spec 太長（本地 27B 模型的 context 裝不下整份 spec + 全部 RTL）、不可追溯（哪行 RTL 對應哪條需求說不清）、改版災難（spec v1.1 來了只能全部重來）。

llm-wiki 的做法是把 spec **編譯**成兩級中間表示：

```
sources/uart-lite-spec.md          原始 spec（不可變）
        │  Spec-Ingest：逐條抽出需求、給永久 ID
        ▼
wiki/pages/specs/…requirements.md  編號需求（REQ-UART-001…）＝「spec 的 IR」
        │  Design：模組分解、ports/FSM 定契約
        ▼
wiki/pages/design/…               架構頁 + 模組設計頁 ＝「RTL 的生成契約」
        │  RTL-Gen：只讀設計頁，絕不回頭讀 spec
        ▼
rtl/*.v + verif/tb_*.v            產物（可由設計頁重生）
```

每一級只依賴上一級，好處：

- **裝得下**：產生 `uart_tx.v` 時只需要讀 `design/uart-tx.md` 一頁（幾百行 context），不用讀整份 spec。
- **可追溯**：RTL 檔頭 → 設計頁 → `implements: [REQ-…]` → 需求頁 → spec 章節，機器可驗證（`scripts/trace_check.py`）。
- **改版可控**：spec v1.1 進來時 diff 需求頁，被波及的設計頁自動標 `needs-review`，影響範圍一目瞭然（見 §3）。

## 2. 日常操作（對 agent 說的話）

| 你說 | LLM 做的事 | commit |
|------|-----------|--------|
| 「ingest」（inbox 有 spec） | spec → 需求頁，逐條編 REQ ID | `spec: …` |
| 「design uart-lite」 | 需求頁 → 架構頁 + 模組設計頁 | `design: …` |
| 「rtl uart_tx」 | 設計頁 → `rtl/uart_tx.v`，更新 filelist | `rtl: …` |
| 「verify uart-lite」 | 產自檢 testbench + 模擬 script | `verify: …` |
| 「lint」 | 一般健檢 + `trace_check.py` 追溯檢查 | `lint: …` |
| 「flow uart-lite」 | 半自動：design → rtl → verify 一口氣串完（見下） | 各階段照常 |
| （貼上模擬失敗 log） | 判斷是設計頁錯還是實作錯，從對的層級修起 | 視情況 |

### 半自動模式（flow <block>）

需求單純、不想逐階段下指令時，用 `flow <block>` 串接 Design → RTL-Gen → Verify。與逐步執行的差別只有「不用每階段等你下指令」，紀律不變：

- **Spec-Ingest 永遠不在 flow 裡**——spec 解讀必須人審後才有需求頁，flow 從需求頁起跑。
- **啟動 gate**：需求頁有未清的 `⚠️ 待釐清` / `🔶` 就不啟動，先請你裁決。歧義不許自動流過。
- **每階段照常各自 commit**，git 歷史與手動逐步完全相同；中途卡住（需求資訊不足、追溯缺口）就停在該階段報告，已完成的 commit 保留。
- **大型 block 一次只 flow 一個子系統**；模擬仍由你執行——flow 結束時的產出是「等待模擬的完整 RTL + TB」，不是「已驗證的設計」。

關鍵紀律（LLM 被 CLAUDE.md 約束，人也要配合）：

- **不要手改 RTL 了事**。發現 bug 時，如果根因在設計（FSM 少一個狀態、握手定義錯），先改設計頁再重生 RTL；否則 wiki 與 RTL 漂移，下次重生就把修正蓋掉了。
- **spec 的歧義停在需求頁**。spec 沒定義的行為標 `⚠️ 待釐清`，由人裁決後補進需求頁，才往下流到設計。

## 3. Spec 改版的影響分析

```
spec v1.1 進 inbox
   │ Spec-Ingest（diff 模式）
   ▼
需求頁：REQ-UART-004 內文變更，標 🔶；REQ-UART-013 新增
   │ 自動：implements 含 REQ-UART-004 的設計頁 → status: needs-review
   ▼
trace_check.py 列出：design/uart-tx.md needs-review、REQ-UART-013 是孤兒
   │ 人審設計頁 → 更新 → status: ok → 重生受影響的 RTL → 重跑模擬
   ▼
🔶 清除，lint 乾淨，commit
```

REQ ID 永不重編是這一切的前提——ID 是 spec 版本之間、wiki 與 RTL 之間唯一穩定的錨點。

## 4. 驗證：商用模擬器（VCS / Questa / Xcelium）

- LLM 產出：自檢 testbench（`verif/tb_*.v`，結尾必印 `TEST PASSED` / `TEST FAILED`）、`verif/filelist.f`、三種工具的 run script（`verif/sim/`）。
- **模擬由使用者執行**（license 環境各站不同，LLM 不碰）：

```bash
# repo 根目錄執行，三選一
bash verif/sim/run_vcs.sh
bash verif/sim/run_questa.sh
bash verif/sim/run_xrun.sh
```

- 失敗時把 log 貼給 agent 分析。RTL 與 TB 都是純 Verilog-2001，在開源模擬器（Icarus Verilog）上行為一致，範例已用 iverilog 驗證過會 PASS——商用工具上若有差異，通常是 timescale 或 lint 嚴格度，不是行為。

## 5. 追溯資料模型

`scripts/trace_check.py` 依兩個機器可讀約定運作：

1. **需求頁的表格**（欄位順序固定）：`| ID | 需求 | Spec 出處 | Status |`
2. **設計頁的 frontmatter**：`implements: [REQ-…]`、`rtl:`、`tb:`、`status:`

```bash
python3 scripts/trace_check.py check    # 追溯健檢（lint 時執行；有缺口 exit 1）
python3 scripts/trace_check.py matrix   # 重生 wiki/pages/notes/traceability-matrix.md
```

check 抓的缺口：孤兒需求、implements 引用不存在的 REQ、`rtl:`/`tb:` 斷鏈、filelist 與 `rtl/` 不一致、`needs-review` 未清、需求頁殘留 `🔶`。

## 6. 完整範例：uart-lite

repo 內附一條走完整 flow 的範例（8N1 UART，可程式 baud divisor，valid/ready 握手）：

| 層 | 檔案 |
|----|------|
| Spec | `sources/archive/uart-lite-spec.md` |
| 需求 | `wiki/pages/specs/uart-lite-requirements.md`（REQ-UART-001…012） |
| 設計 | `wiki/pages/design/uart-lite-architecture.md`、`design/uart-tx.md`、`design/uart-rx.md` |
| RTL | `rtl/uart_tx.v`、`rtl/uart_rx.v`、`rtl/uart_lite_top.v` |
| 驗證 | `verif/tb_uart_lite.v`（loopback + frame error 自檢）、`verif/filelist.f`、`verif/sim/run_*.sh` |
| 追溯 | `wiki/pages/notes/traceability-matrix.md` |

`wiki/log.md` 裡有這條範例每個階段的紀錄，就是日後真實專案的 log 長相。

## 7. 大型 design 的分解（以 MIPI CSI-2 RX 為例）

uart-lite 是單層分解（一張架構頁、兩張模組頁）；CSI-2 這種量級套用 [CLAUDE.md](../CLAUDE.md)「大型 block 的分解規則」，wiki 會長成兩層：

```
specs/
├── csi2-dphy-requirements.md      REQ-DPHY-*   （PPI 介面、lane 對齊）
├── csi2-packet-requirements.md    REQ-PKT-*    （header/ECC/CRC/VC）
└── csi2-pixel-requirements.md     REQ-PIXEL-*  （解包、line/frame timing）

design/
├── csi2-rx-architecture.md            頂層：只分解到三個子系統 + CDC
├── csi2-rx-interfaces.md              介面唯一權威（IF-PKT-STREAM、IF-PIXEL-BUS…）
├── csi2-lane-layer-architecture.md    子系統架構頁
│   ├── ppi-if.md / lane-deskew.md / lane-merger.md
├── csi2-packet-layer-architecture.md
│   ├── pkt-parser.md / payload-crc.md / vc-demux.md
└── csi2-pixel-layer-architecture.md
    ├── pixel-unpack.md / frame-fsm.md / cdc-fifo.md
```

流程上的差異：

- **RTL-Gen 的輸入多一項**：該模組設計頁 + 所屬子系統架構頁的接線章節 + 介面定義頁中用到的介面。context 仍然有界——不管 design 多大，單次生成讀的都是這三小份。
- **Verify 分三層**：模組 TB（例：`tb_pkt_parser` 注入 ECC 單/雙位元錯誤）→ 子系統 TB（packet layer 餵合成 packet 流）→ top 整合 TB（全鏈路影像 frame）。
- **下指令的粒度不變**：`design csi2-packet-layer`、`rtl pkt_parser`——一次一個子系統/模組，每層產物審過再往下，與小 design 完全相同的節奏。

介面定義頁是這個量級的關鍵新元素：模組 A 的輸出與模組 B 的輸入若各寫各的，RTL 生成時兩邊不一致要到子系統模擬才炸出來；集中定義後，設計頁只引用介面名，`trace_check.py` 之外人工 review 也只需要看一頁。

## 8. 反向流程：Reverse-Ingest（匯入既有 Verilog design 並修改）

正向流程從 spec 出發、從零設計；現實中更常見的是**已經有一包現成的 design**（例如一份 MIPI IP），想在不大改的前提下修改——新增或不確定的部分參考 spec，其餘盡量維持原設計。操作規則的正式定義在 [CLAUDE.md](../CLAUDE.md) 操作 7，這裡說明資料模型與日常用法。

### 8.1 目錄模型：凍結 baseline vs 工作副本

```
sources/archive/mipi-csi2-rx/        凍結的原始碼（不可變，含 .version 版本標籤）
sources/archive/mipi-csi2-rx-v1.0/   被新版取代的舊版（永久封存）
rtl/mipi-csi2-rx/                    工作副本——Design-Revise 後 RTL-Gen 覆寫的對象
wiki/pages/design/mipi-csi2-rx/      逆向重建的架構頁＋模組設計頁（專案子目錄）
```

隨時可以 `diff -ru sources/archive/mipi-csi2-rx/ rtl/mipi-csi2-rx/` 看「原廠版 vs 目前改到哪」。設計頁的專案子目錄慣例對 spec 設計的大型 block 同樣適用——按專案分、不按來源分，`origin: reverse-engineered` frontmatter 才是機器可讀的來源標記。

### 8.2 日常用法

| 你說 | 發生什麼 | commit |
|------|----------|--------|
| 「reverse-ingest mipi-csi2-rx」（inbox 有整包 .v） | `verilog_map.py` 解析真實階層 → 逆向重建設計頁（as-is、不比對 spec）→ 原始碼凍結 + 工作副本落地 | `reverse-ingest: …` |
| 「design-revise pkt_parser：…你的想法…」 | 只針對改動範圍查 spec 給建議；衝突標 ⚠️ 不阻擋；每輪各自 commit | `design: … revise` |
| 「rtl pkt_parser」 | 依設計頁重生工作副本；行為唯設計頁是問，風格可參考 baseline（diff 雜訊小） | `rtl: …` |
| 「reverse-ingest mipi-csi2-rx」（archive 已存在） | 更新模式：舊版封存 → `verilog_map.py diff` 結構比對 → 逐檔三方判斷（你改過的檔案絕不自動覆蓋） | `reverse-ingest: … update` |

### 8.3 兩條核心紀律

1. **匯入時輕量**：不預先逐模組比對 spec。查 spec、標 `deviates`、跨域分析都是**按需**發生（Design-Revise touch 到、或你明確要求核對時）。維持原設計的部分不會被主動挑毛病。
2. **as-is 原則**：設計頁忠實記錄 RTL 實際行為，模組邊界跟真實階層走（與 spec 功能域分法不同是常態）。行為變更只能經由顯式的 Design-Revise，不能是記錄過程的副作用——否則重生 RTL 時行為會被默默改掉。

### 8.4 工具

```bash
python3 scripts/verilog_map.py map rtl/mipi-csi2-rx/          # 階層樹＋模組清單
python3 scripts/verilog_map.py ports rtl/mipi-csi2-rx/ pkt_parser   # 單模組 ports
python3 scripts/verilog_map.py diff <舊版目錄> <新版目錄>      # 版本結構差異
```

regex 啟發式解析、純標準函式庫。**不解析 generate 區塊**——本 flow 生成的 RTL 一律禁用 generate（重複結構明確展開為具名 instance，除錯時波形可直接對應），原廠 baseline 若用了 generate 會收到「階層不保證完整」的警告，該部分需人工確認；經 Design-Revise 重生後即為展開形式，警告自然消失。
