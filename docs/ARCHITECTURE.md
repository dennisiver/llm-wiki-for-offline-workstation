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

### 4.1 離線更新框架

工作站不能 `git pull`，框架更新（`CLAUDE.md` 規則、`scripts/`、`docs/`）要靠實體媒介
（USB）帶進去，merge 交給工作站的 AI 執行。這個 repo 會持續長大（每次擴充規則、
每次匯入真實專案），升級是**反覆會發生的事**，所以流程整套寫在這裡、往後照做
即可，不用每次重新討論。

**主要方法：整包資料夾複製**（貼近實際操作——直接複製整個含 `.git` 的資料夾，
不需要額外打包）：

**連網機**：

```bash
git pull                          # 拿最新版（或先 git clone 一份）
# 把整個資料夾（含隱藏的 .git）複製到 USB
```

**工作站**：解壓/複製到暫存位置（**不要覆蓋**現有的工作目錄），例如
`~/transfer/llm-wiki-for-offline-workstation`，然後對 agent 下指令，範本
（直接複製貼上，改路徑即可）：

```
我從連網機帶入了新版的 llm-wiki repo 資料夾，解壓在：
~/transfer/llm-wiki-for-offline-workstation
我工作中的 repo 在：
~/llm-wiki-for-offline-workstation

請依序執行，每步完成後回報：

1. 前置檢查（在我工作中的 repo 裡）：
   - ls -a 確認有 .git；git log --oneline -3 看目前版本
   - git status 確認乾淨；有未 commit 的變更就先 commit
     （訊息：wip: 更新前存檔）

2. 打檢查點（比翻 git reflog 更好找的回滾點）：
   - git tag pre-update-$(date +%Y%m%d)

3. 把帶入的資料夾當 remote 合併：
   - git fetch ~/transfer/llm-wiki-for-offline-workstation <分支名>
   - git merge FETCH_HEAD

4. 若有衝突，依以下原則解決：
   - sources/ 一律保留本地版本（來源不可變）
   - wiki/log.md、CHANGELOG.md 兩邊聯集（已設 merge=union，通常自動解決）
   - wiki/index.md 重新整併，涵蓋兩邊所有頁面
   - 框架檔（CLAUDE.md、AGENTS.md、opencode.json、scripts/、docs/）以更新版
     為準；但若我本地改過這些檔案，先列出差異讓我裁決，不要直接蓋掉
   - 我本地建立的 wiki/pages/、rtl/<project>/、sources/archive/<project>/
     內容全部保留，這些更新版本來就沒有，不會被拿來比對

5. 合併完成後：
   - python3 scripts/wiki_search.py index 重建搜尋索引
   - python3 scripts/trace_check.py check 跑追溯健檢，有缺口列出來
   - git add -A && git commit（訊息：update: 框架更新至 YYYYMMDD）

6. 讀 CHANGELOG.md 裡這次合併新增的條目（不是整份重讀），摘要這次升級
   新增/變更了哪些規則與操作給我確認。

帶入的 ~/transfer/ 資料夾等我確認合併沒問題後才刪。
```

**為什麼合併通常不會衝突**：工作站本地做的任何真實專案工作（Reverse-Ingest
匯入的內容、Design-Revise 產生的新設計頁、自己 ingest 的來源）連網機的 repo
完全不知道、也**不會**知道——這是 §6 講的單向資料流鐵律，工作站的真實專案
資料永遠不回流。這些檔案在「帶入的新版」那邊根本不存在，git 合併時不會拿來
比對，自然不會衝突。唯一可能撞在一起的是使用者**手改過的框架檔**（例如調過
`opencode.json` 的 model 名稱）恰好這次升級也動了同一個檔案——範本裡的步驟 4
已經涵蓋這個情況。

**沒有 `.git` 的情況**（例如當初用 ZIP 下載解壓、不是 `git clone`）：這是一次性
遷移而非合併——`git clone` 帶入的資料夾成一個有完整歷史的新 repo，把工作站既有
的 `sources/`、`wiki/pages/` 內容搬進去，AI 應該先列清單問你「這些是你自己加的、
還是框架原有的」，不確定就問、不要猜。

**次要方法：git bundle**（repo 變得很大、想要單一壓縮檔案走 USB 時用）：

```bash
# 連網機
git bundle create llm-wiki-$(date +%Y%m%d).bundle --all

# 工作站
git bundle verify /path/to/usb/llm-wiki-YYYYMMDD.bundle   # 先驗證再用
```

驗證通過後，`git fetch` 的來源換成 bundle 檔案路徑即可，其餘步驟（打檢查點、
merge、衝突處理、驗證、讀 CHANGELOG）跟上面完全相同。

**升級內容參考**：`CHANGELOG.md` 記錄框架/規則層本身的演化（跟記錄 wiki *內容*
操作的 `wiki/log.md` 不同層級），每次合併後讀新增的條目，就知道這次升級帶來
什麼，不用臨時去 diff `CLAUDE.md` 猜。

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
- [ ] **盤點離線機實際有什麼工具，不要假設一定裝得上**：`python3 --version`、`git --version` 是否存在？本 repo 的 `scripts/*.py`（`wiki_search.py`／`trace_check.py`／`verilog_map.py`／`pdf_to_md.py`）全部需要 Python 3 才能跑。若這台工作站的政策不允許安裝任何直譯器/套件（含離線 wheel），如實記錄哪些工具用不了——日常操作時 AI 會改用本機已有的工具（grep/diff/直接讀檔）盡量完成，其餘列入資料缺口，不會假裝這些腳本可以跑。
- [ ] （可選，僅當 python3 + pip 確認可用時）`pip download pymupdf -d pymupdf-wheels/` 帶入離線機備用，作為離線 PDF 轉文字的備援（§3.4）；主要流程仍是在連網機轉好 .md

日常循環（完全離線）：

1. 來源進 `sources/inbox/`（USB 或本地產生）
2. 「ingest inbox」→ LLM 更新 wiki、commit
3. 提問 → 得到附引用的答案 → 有價值就回存
4. 每 ~10 次 ingest 跑一次 lint
