# Wiki 目錄

每個 wiki 頁面一行摘要，依分類排列。LLM 回答任何問題前先讀這個檔案。
（格式規範見 [CLAUDE.md](../CLAUDE.md)）

## Concepts

（尚無頁面）

## Entities

（尚無頁面）

## Specs

- [uart-lite-requirements](pages/specs/uart-lite-requirements.md) — UART-Lite 的 13 條編號需求（REQ-UART-001…013），自 spec v1.0 編譯

## Design

- [uart-lite-architecture](pages/design/uart-lite-architecture.md) — UART-Lite 方塊圖、模組分解與頂層接線（uart_lite_top）
- [uart-tx](pages/design/uart-tx.md) — 傳送器設計頁：valid/ready 握手、FSM、位元計時（rtl/uart_tx.v 的生成契約）
- [uart-rx](pages/design/uart-rx.md) — 接收器設計頁：兩級同步、起始中點複檢、中點取樣、frame error（rtl/uart_rx.v 的生成契約）

## Notes

- [traceability-matrix](pages/notes/traceability-matrix.md) — REQ ↔ 設計頁 ↔ RTL ↔ TB 追溯總表（trace_check.py 產生，勿手改）
