# Agent 規則 — Codex CLI / OpenCode 入口

> 本檔案由 **OpenAI Codex CLI** 與 **OpenCode** 自動載入。
> 本 wiki 的完整維護規則（Schema）只有一份，在 [CLAUDE.md](CLAUDE.md)——
> **執行任何 wiki 操作（ingest / query / lint）前，必須先完整閱讀 CLAUDE.md 並全文遵守。**
> 本檔案不重複其內容，以免兩份規則漂移。

## 鐵律（CLAUDE.md 的摘要，衝突時以 CLAUDE.md 為準）

1. 絕不修改 `sources/` 下任何檔案內容（ingest 後從 `inbox/` 移到 `archive/` 是唯一允許的操作）。
2. wiki 裡每個事實主張都要能追溯到來源，附相對連結引用。
3. 每次操作結束必須更新 `wiki/index.md` 與 `wiki/log.md`，並 git commit。
4. 離線環境：不做任何網路操作；搜尋用 `python3 scripts/wiki_search.py search "關鍵字"` 或 ripgrep。

---

## Codex CLI 離線設定

Codex CLI 的設定檔在 `~/.codex/config.toml`（全域，不在 repo 內）。指向本地 Ollama 的範例：

```toml
model = "qwen3.6:27b"
model_provider = "ollama"

[model_providers.ollama]
name = "Ollama (local)"
base_url = "http://localhost:11434/v1"
wire_api = "chat"
```

- 啟動後 Codex 會自動讀取 repo 根目錄的本檔案（AGENTS.md）。
- 離線注意：確認未啟用任何需要連網的功能（web search、自動更新檢查）。

## OpenCode 離線設定

repo 已附 [opencode.json](opencode.json)：

- `instructions` 直接載入 `CLAUDE.md` 作為規則（不經過本檔案的摘要，零漂移）。
- `provider` 指向本地 Ollama 的 OpenAI 相容端點。
- 依你的硬體修改 `model` 欄位即可（模型建議見 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §2.1）。

在 repo 根目錄執行 `opencode` 即自動套用。
