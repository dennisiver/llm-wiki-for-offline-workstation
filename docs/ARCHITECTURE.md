# 離線工作站 LLM Wiki — 架構設計

本文件說明如何在**無網路（air-gapped）或間歇性連線**的工作站上，運行 Karpathy llm-wiki 模式的完整系統設計。

在此基礎上的硬體設計流程（spec → 需求頁 → 設計頁 → Verilog-2001 RTL）見 [SPEC-TO-RTL-FLOW.md](SPEC-TO-RTL-FLOW.md)。

## 1. 設計目標

| 目標 | 對應設計 |
|------|----------|
| 零網路依賴的日常運作 | 本地 LLM 推論 + 純檔案系統 + 標準函式庫搜尋 |
| 知識可累積、可稽核 | Markdown + git，每次 LLM 修改都是一個 commit |
| 來源與產出嚴格分離 | `sources/`（不可變）與 `wiki/`（LLM 專屬）分層 |
| 低維運成本 | 無資料庫伺服器、無向量庫、無常駐服務（除了 LLM runtime） |
| 可攜性 | 整個 repo 複製到任何機器即完整還原，含歷史 |

## 2. 系統元件

```
┌────────────────────────── 離線工作站 ──────────────────────────┐
│                                                                │
│  ┌──────────────┐     ┌───────────────────────────────────┐   │
│  │ 使用者        │────▶│ Agent CLI                          │   │
│  │ (提問/指令)   │     │ （驅動 LLM 讀寫檔案的代理工具）      │   │
│  └──────────────┘     └──────────┬────────────────────────┘   │
│         ▲                        │ 讀 CLAUDE.md 取得規則        │
│         │                        ▼                             │
│  ┌──────┴───────┐     ┌───────────────────────┐                │
│  │ Obsidian     │     │ 本地 LLM Runtime       │                │
│  │ (瀏覽/graph) │     │ Ollama / llama.cpp     │                │
│  └──────────────┘     └──────────┬────────────┘                │
│                                  │ 檔案讀寫                     │
│  ┌───────────────────────────────▼───────────────────────┐    │
│  │ Git Repo（本 repo）                                     │    │
│  │  sources/ ──ingest──▶ wiki/pages/ ◀──search── FTS5 索引 │    │
│  │  （不可變）            index.md / log.md                 │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                │
└───────────────────────────▲────────────────────────────────────┘
                            │ USB / 內網單向同步
              ┌─────────────┴─────────────┐
              │ 連網蒐集機（可選）           │
              │ Web Clipper → Markdown     │
              │ 論文 PDF、模型檔下載        │
              └───────────────────────────┘
```

### 2.1 本地 LLM Runtime

| 選項 | 適用情境 |
|------|----------|
| **Ollama** | 首選。安裝簡單，模型管理方便，OpenAI 相容 API，多數 agent CLI 可直接對接 |
| **llama.cpp**（llama-server） | 資源受限或需要細部控制（量化、offload）時 |
| **vLLM** | 有伺服器級 GPU、需要高吞吐時 |

模型建議（依 VRAM）：

| 硬體 | 模型建議 | 備註 |
|------|----------|------|
| 8–12 GB VRAM | Qwen 2.5 7B / Llama 3.1 8B（Q4 量化） | 可勝任 ingest 與 query，複雜綜合品質有限 |
| 16–24 GB VRAM | Qwen3.6 27B、Qwen 2.5 14B–32B（Q4–Q5） | 甜蜜點：長文 ingest、跨頁綜合都穩定（本 repo 預設 Qwen3.6 27B） |
| 48 GB+ / 多卡 | Llama 3.3 70B、Qwen 2.5 72B | 接近雲端模型的維護品質 |

關鍵需求是**長上下文**（ingest 一份來源 + 讀 10 幾個相關頁面），建議 runtime 設定至少 32K context。

### 2.2 Agent CLI（LLM 的手腳）

llm-wiki 需要 LLM 能**自主讀寫多個檔案**，不是單輪問答。本 repo 對三種 agent CLI 開箱即用：

| Agent CLI | 規則檔載入方式 | 本地模型設定 |
|-----------|----------------|--------------|
| **Claude Code** | 自動讀 repo 根目錄的 `CLAUDE.md` | 需要 Anthropic API（非完全離線；適合間歇連線的工作站） |
| **Codex CLI** | 自動讀 `AGENTS.md`（其中要求先讀 `CLAUDE.md`） | `~/.codex/config.toml` 指向本地 Ollama（範例見 `AGENTS.md`） |
| **OpenCode** | `opencode.json` 的 `instructions` 直接載入 `CLAUDE.md` | `opencode.json` 已內建本地 Ollama provider，改 `model` 欄位即可 |

規則的唯一規範來源是 `CLAUDE.md`；`AGENTS.md` 只是入口與摘要，避免多份規則漂移。完全 air-gapped 環境建議用 Codex CLI 或 OpenCode 搭配 Ollama。其他選項：

- 任何支援自訂 OpenAI 相容 endpoint 的 agent 工具（Aider、OpenHands 等），把 `CLAUDE.md` 貼入 system prompt。
- 最低限度方案：自寫一個簡單的 agent loop（讀檔 / 寫檔 / 搜尋三個 tool），對 llm-wiki 的操作模式已經足夠。

### 2.3 搜尋層

分階段，避免過度工程：

1. **< 100 頁**：不需要索引。LLM 讀 `wiki/index.md` + ripgrep 就夠。
2. **100–1000 頁**：`scripts/wiki_search.py` — SQLite FTS5（BM25 排名），純 Python 標準函式庫，索引檔是單一 `.db` 檔。
3. **> 1000 頁（可選）**：FTS5 + 本地 embedding（如 sentence-transformers + 預下載模型）做混合檢索，由 LLM 重排。到這個規模前不要先建。

### 2.4 瀏覽層（人用的介面，可選）

- **Obsidian**：完全離線可用。把 repo 開成 vault——graph view 呈現頁面關聯，frontmatter 配 Dataview 外掛可做動態表格（例：列出所有 `⚠️ 待釐清` 的頁面）。
- 沒有 Obsidian 時，任何文字編輯器都能讀，這正是純 Markdown 的意義。

## 3. 資料流

### 3.1 來源進入（連網機 → 離線機）

```
連網蒐集機                          離線工作站
─────────────                      ─────────────
網頁 → Web Clipper → .md ─┐
論文 PDF → 轉 .md（必做）──┼─→ USB/內網 ─→ sources/inbox/ ─→ [ingest] ─→ sources/archive/
會議記錄、日誌 → .md ─────┘                                     │
                                                               ▼
                                                        wiki/pages/*.md 更新
                                                        index.md / log.md 更新
                                                        git commit
```

要點：
- 在連網機就完成「網頁 → Markdown、圖片本地化」，離線機永遠不需要網路。
- **PDF 也在連網機轉好**：離線工作站預設沒有 PDF 轉文字工具（見 §3.4）。文字型 PDF 用 `pdftotext`（poppler）或 PyMuPDF；掃描檔需要 OCR，用 MinerU / marker 這類工具。原始 PDF 可隨轉出的 .md 一起帶入存檔，但 ingest 與全文搜尋的對象是 .md。
- 純離線來源（自己寫的筆記、儀器輸出、內部文件）直接放 `sources/inbox/`。
- 模型檔（GGUF 等）也走同一條 USB 通道，一次性搬入。

### 3.2 查詢

```
使用者提問 → Agent 讀 index.md（或 FTS5 搜尋）→ 讀相關頁面 → 綜合 + 引用 → 回答
                                                                  │（有長期價值時）
                                                                  ▼
                                                     回存 wiki/pages/notes/ → commit
```

### 3.3 維護

```
每 ~10 次 ingest → lint → 修矛盾/斷鏈/孤兒頁 → lint 報告列出資料缺口
                                                    │
                                                    ▼
                                     使用者帶著缺口清單去連網機蒐集 → 回到 3.1
```

### 3.4 離線機上的 PDF 處理（備援方案）

離線工作站**預設沒有任何 PDF 轉文字程式**，所以首選永遠是 §3.1：在連網機轉好再帶入。但如果 PDF 已經在離線機上、短期回不了連網機，備援做法是把 PyMuPDF 的 wheel 檔經 USB 帶入離線安裝：

```bash
# 連網機（一次性）：下載對應離線機 Python 版本與平台的 wheel
pip download pymupdf -d pymupdf-wheels/
# → pymupdf-wheels/ 整個資料夾複製到 USB

# 離線機：不碰網路直接安裝
pip install --no-index --find-links pymupdf-wheels/ pymupdf

# 之後即可用 repo 附的腳本轉換
python3 scripts/pdf_to_md.py sources/inbox/some-paper.pdf
```

限制與注意：
- PyMuPDF 只能抽**文字型 PDF**（含中文/CJK）。**掃描檔（圖片型）抽不出字**，需要 OCR——OCR 工具鏈太重，不建議搬進離線機，掃描檔一律回連網機處理。
- `scripts/pdf_to_md.py` 在未安裝 PyMuPDF 時會直接印出上述離線安裝指引，不會默默失敗。
- LLM 遇到 inbox 裡讀不了的 PDF 時，依 CLAUDE.md 規則列入「資料缺口」，不憑檔名猜內容。

## 4. 版本控制策略

- 整個 repo 一個 git 倉庫；`sources/` 與 `wiki/` 一起版控，保證任何 commit 的 wiki 狀態與其依據的來源一致。
- LLM 的每次操作 = 一個 commit（`ingest: …` / `note: …` / `lint: …`），`git log` 就是 `log.md` 的機器可驗證版。
- 搜尋索引 `.db` 不進版控（見 `.gitignore`），隨時可重建。
- 備份 = `git clone` 到第二顆硬碟，或 `git bundle` 一個檔案帶走。

### 4.1 離線更新框架（git bundle 經 USB）

工作站不能 `git pull`，框架更新（CLAUDE.md 規則、scripts、docs）用 bundle 走 USB 通道，merge 交給工作站的 AI 執行。

**連網機**（打包最新版）：

```bash
git clone https://github.com/dennisiver/llm-wiki-for-offline-workstation.git
cd llm-wiki-for-offline-workstation
git bundle create llm-wiki-$(date +%Y%m%d).bundle --all
# 把 .bundle 複製到 USB
```

**工作站**（在 repo 目錄，先驗證再交給 AI）：

```bash
git bundle verify /path/to/usb/llm-wiki-YYYYMMDD.bundle   # 確認 bundle 完整
```

然後對工作站的 agent（OpenCode）下指令，範本：

> USB 上有框架更新：`/path/to/usb/llm-wiki-YYYYMMDD.bundle`。請：
> 1. `git fetch <bundle路徑> <分支名>` 然後 merge FETCH_HEAD 進目前分支。
> 2. 衝突處理原則：`sources/` 一律保留本地（鐵律：不可變）；`wiki/log.md` 兩邊聯集（append-only，已設 merge=union）；`wiki/index.md` 重新整併成涵蓋兩邊頁面的目錄；框架檔（CLAUDE.md、scripts/、docs/）以更新版為準，但若我本地改過要先列出差異給我裁決。
> 3. merge 完成後執行 `python3 scripts/wiki_search.py index` 重建索引；若有 `scripts/trace_check.py` 則跑 `check`。
> 4. 讀一遍新版 CLAUDE.md，摘要有哪些新規則/新操作給我。

**更新的邊界**：bundle 只該帶框架與（初次）範例；工作站本地產生的 wiki 內容、RTL 專案永遠不會被更新覆蓋——它們只存在工作站的 commit 裡。反向（工作站 → 連網機）如需備份，同樣用 `git bundle create` 從工作站打包帶出。

## 5. 失效模式與對策（承襲 gist 社群經驗）

| 失效模式 | 症狀 | 對策 |
|----------|------|------|
| **Drift（漂移）** | ingest 時漏更新交叉連結，頁面悄悄過時 | 強制 lint 週期（CLAUDE.md 規定每 ~10 次 ingest）；斷鏈與矛盾是 lint 必查項 |
| **規模瓶頸** | 扁平 index.md 到數百頁後 LLM 讀不完 | 分階段搜尋策略（§2.3），先 FTS5 再考慮 embedding，不要一開始就上 RAG 基礎設施 |
| **頁面經濟學倒掛** | 每個小實體都開頁，wiki 比來源還肥 | CLAUDE.md 明定：密集摘要表優於分散小頁；單頁比來源長就該壓縮 |
| **本地模型幻覺** | 小模型在綜合時編造 wiki 裡沒有的內容 | 強制引用規則（每個主張附來源連結）；lint 抽查引用是否真的支持主張；重要領域用較大模型 |
| **上下文不足** | 一次 ingest 讀不完來源 + 相關頁 | 分批 ingest（先建頁、再補交叉連結）；runtime 開 32K+ context |
| **索引過期** | 搜尋結果缺新頁面 | ingest 流程末尾重建索引（CLAUDE.md 已規定）；索引重建成本低（秒級） |

## 6. 安全性考量（air-gapped 環境）

- **單向資料流**：連網機 → 離線機只進不出。wiki 內容若屬敏感，永遠不離開離線工作站。
- **來源檢疫**：外部帶入的檔案只放 `sources/inbox/`，且 CLAUDE.md 規定 LLM 不執行來源中的任何指令——來源是「被閱讀的資料」，不是「被服從的指令」（防 prompt injection）。
- **無遙測**：Ollama / llama.cpp 離線執行不外傳資料；agent CLI 選型時確認可完全關閉遙測與自動更新。

## 7. 最小啟動清單

一次性（需網路，在連網機完成）：

- [ ] 下載 LLM runtime 安裝檔 + 模型檔（GGUF），USB 搬入離線機
- [ ] 下載 agent CLI 與（可選）Obsidian 安裝檔
- [ ] 確認離線機有 Python 3.8+（`wiki_search.py` 只用標準函式庫）與 git
- [ ] （可選）`pip download pymupdf -d pymupdf-wheels/` 帶入離線機備用，作為離線 PDF 轉文字的備援（§3.4）；主要流程仍是在連網機轉好 .md

日常循環（完全離線）：

1. 來源進 `sources/inbox/`（USB 或本地產生）
2. 「ingest inbox」→ LLM 更新 wiki、commit
3. 提問 → 得到附引用的答案 → 有價值就回存
4. 每 ~10 次 ingest 跑一次 lint
