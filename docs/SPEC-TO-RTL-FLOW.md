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
| （貼上模擬失敗 log） | 判斷是設計頁錯還是實作錯，從對的層級修起 | 視情況 |

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
