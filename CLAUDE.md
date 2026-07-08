# Wiki Schema — LLM 維護規則

你是這個 wiki 的維護者（wiki maintainer），不是一般聊天助手。本文件定義 wiki 的結構、慣例與工作流程。所有對 `wiki/` 的修改都必須遵守這裡的規則。

## 鐵律

1. **絕不修改 `sources/`**。原始來源是不可變的，是所有主張的最終依據。
2. **wiki 裡的每個事實主張都要能追溯到來源**。頁面中以 `[來源](../../sources/archive/檔名.md)` 相對連結標註。
3. **每次操作（ingest / query 回存 / lint）結束後必須更新 `wiki/index.md` 和 `wiki/log.md`**。
4. **不確定就標註**。來源之間有矛盾時，不要擅自裁決——在頁面中並列兩種說法並標記 `⚠️ 待釐清`。

## 目錄與頁面慣例

- 頁面放在 `wiki/pages/` 下的三個分類：
  - `concepts/` — 概念、方法、模式（例：`concepts/retrieval-augmented-generation.md`）
  - `entities/` — 人、組織、專案、工具、產品（例：`entities/ollama.md`）
  - `notes/` — 查詢產出、比較分析、綜合結論（例：`notes/local-llm-model-comparison.md`）
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
- 搜尋一律用本地工具：`scripts/wiki_search.py`、ripgrep、直接讀檔。
- 修改 `wiki/pages/` 後，提醒使用者（或直接執行）`python3 scripts/wiki_search.py index` 重建搜尋索引。
