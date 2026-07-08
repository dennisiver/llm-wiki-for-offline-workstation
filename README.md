# llm-wiki-for-offline-workstation

一套可完全離線運作的 **LLM Wiki** 架構，改編自 [Andrej Karpathy 的 llm-wiki 模式](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)，專為無網路（air-gapped）或間歇性連線的工作站設計。

## 核心概念

傳統 RAG 在每次查詢時重新檢索原始文件；llm-wiki 反過來：**知識只編譯一次，之後持續維護**。LLM 逐步建立並維護一個持久的 wiki——一組結構化、互相連結的 Markdown 檔案。你負責蒐集來源和提問，LLM 負責所有的記帳工作（更新頁面、維護交叉連結、檢查矛盾）。

## 三層架構

```
┌─────────────────────────────────────────────────────┐
│  第 3 層：Schema（CLAUDE.md）                         │
│  規範 wiki 結構、慣例與工作流程 — 人與 LLM 共同制定    │
├─────────────────────────────────────────────────────┤
│  第 2 層：Wiki（wiki/）                               │
│  LLM 生成並維護的 Markdown 頁面 — LLM 寫、人讀        │
├─────────────────────────────────────────────────────┤
│  第 1 層：原始來源（sources/）                        │
│  文章、論文、筆記、資料檔 — 不可變，所有主張的依據     │
└─────────────────────────────────────────────────────┘
```

## 目錄結構

```
llm-wiki-for-offline-workstation/
├── CLAUDE.md              # Schema：wiki 維護規則（LLM 的操作手冊）
├── sources/               # 第 1 層：原始來源（唯讀，LLM 絕不修改）
│   ├── inbox/             #   新來源先放這裡，等待 ingest
│   └── archive/           #   已 ingest 的來源
├── wiki/                  # 第 2 層：LLM 維護的 wiki
│   ├── index.md           #   目錄：每頁一行摘要 + 分類（LLM 先讀這個）
│   ├── log.md             #   時間軸：ingest / query / lint 的追加式紀錄
│   └── pages/             #   wiki 頁面
│       ├── concepts/      #     概念頁
│       ├── entities/      #     實體頁（人、專案、工具…）
│       └── notes/         #     查詢產出、比較、綜合分析
├── scripts/
│   └── wiki_search.py     # 離線搜尋：SQLite FTS5（純 Python 標準函式庫）
└── docs/
    └── ARCHITECTURE.md    # 離線工作站的完整架構設計
```

## 三個核心操作

| 操作 | 說明 |
|------|------|
| **Ingest** | 把新來源放進 `sources/inbox/`，請 LLM 讀取、萃取重點、整合進現有 wiki（一份來源可能觸及 10–15 個頁面），完成後移到 `sources/archive/` |
| **Query** | 對 wiki 提問。LLM 先讀 `index.md` 找相關頁面，綜合出附引用的答案；有價值的答案可回存為新的 wiki 頁面，讓知識複利成長 |
| **Lint** | 定期健檢：找出矛盾、過時主張、孤兒頁面、缺漏的交叉連結 |

詳細流程規範在 [CLAUDE.md](CLAUDE.md)。

## 離線工作站的關鍵調整

相對於原始 gist（假設使用雲端 Claude），本架構做了以下調整，讓整套系統**零網路依賴**：

1. **本地 LLM 執行環境** — 使用 Ollama / llama.cpp 跑本地模型（如 Qwen 2.5、Llama 3.x），模型檔預先下載後可完全離線推論。
2. **離線搜尋** — `scripts/wiki_search.py` 用 SQLite FTS5 做全文檢索，只依賴 Python 標準函式庫，不需 pip、不需向量資料庫、不需 embedding API。頁數少時 LLM 直接讀 `index.md` + ripgrep 即可。
3. **來源蒐集分離** — 在有網路的機器上用 Obsidian Web Clipper 等工具把網頁轉成 Markdown（圖片下載到本地），透過 USB / 內網同步進離線工作站的 `sources/inbox/`。
4. **Git 版本控制** — 整個 wiki 是純文字檔，用本地 git 追蹤每次 ingest 與 lint 的變更，可隨時回溯 LLM 的每一次修改。
5. **Obsidian（可選）** — 完全離線可用的瀏覽介面：graph view 看頁面關聯、Dataview 查 frontmatter。

完整設計（元件選型、資料流、硬體建議、失效模式對策）見 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 快速開始

```bash
# 1. 準備本地 LLM（一次性，需在有網路時完成）
ollama pull qwen2.5:14b        # 或其他適合你硬體的模型

# 2. 放入第一份來源
cp ~/some-article.md sources/inbox/

# 3. 請 LLM ingest（用任何支援本地模型的 agent CLI）
#    prompt 範例：「請依照 CLAUDE.md 的規則，ingest sources/inbox/ 裡的新來源」

# 4. 建立搜尋索引並查詢（wiki 頁面多了之後）
python3 scripts/wiki_search.py index
python3 scripts/wiki_search.py search "你的關鍵字"
```
