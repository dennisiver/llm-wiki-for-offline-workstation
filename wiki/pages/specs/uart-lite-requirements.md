---
title: UART-Lite 需求（自 spec v1.0）
type: spec
created: 2026-07-09
updated: 2026-07-09
sources:
  - sources/archive/uart-lite-spec.md
tags: [uart, requirements, spec-to-rtl]
---

# UART-Lite 需求

自 [UART-Lite 設計規格書 v1.0](../../../sources/archive/uart-lite-spec.md) 編譯。
ID 永不重編；作廢需求標 `deprecated` 不刪列（規則見 [CLAUDE.md](../../../CLAUDE.md)）。

| ID | 需求 | Spec 出處 | Status |
|----|------|-----------|--------|
| REQ-UART-001 | 訊框格式 8N1：8 資料位元（LSB 先送）、無同位、1 停止位元；起始位元低電位、停止位元高電位 | §2.1 | ok |
| REQ-UART-002 | 序列線閒置時維持高電位；重置期間 txd 輸出高電位 | §2.2 | ok |
| REQ-UART-003 | 位元週期 = `baud_div`（16-bit 輸入）個時脈；合法範圍 `baud_div >= 4`；收發進行中不得變更 | §2.3 | ok |
| REQ-UART-004 | TX 採 valid/ready 握手，`tx_valid && tx_ready` 的時脈邊緣接受 `tx_data`；傳送中 `tx_ready` 為低、閒置時為高 | §3.1 | ok |
| REQ-UART-005 | TX 依序送出起始、8 資料（LSB 先）、停止位元，每位元 `baud_div` 個時脈 | §3.2 | ok |
| REQ-UART-006 | 停止位元結束後可背靠背接受下一筆，相鄰訊框間空隙不得超過 1 個時脈 | §3.2 | ok |
| REQ-UART-007 | rxd 為非同步輸入，須經兩級正反器同步後使用 | §4.1 | ok |
| REQ-UART-008 | 起始偵測：同步後 rxd 高轉低進入確認，於 `baud_div/2` 後中點複檢，仍為低才確認，否則視為雜訊回閒置 | §4.2 | ok |
| REQ-UART-009 | 資料位元一律於位元中點取樣 | §4.2 | ok |
| REQ-UART-010 | 成功訊框：`rx_valid` 單時脈脈波 + `rx_data` 提供位元組並保持到下一次 `rx_valid` | §4.3 | ok |
| REQ-UART-011 | 停止位元取樣為低：訊框作廢，不出 `rx_valid`，改出單時脈 `rx_ferr` 脈波 | §4.3 | ok |
| REQ-UART-012 | 單一時脈域；`rst` 同步高有效，重置後所有狀態機回到閒置 | §5 | ok |
| REQ-UART-013 | 頂層整合 TX、RX 各一，共用 `clk`/`rst`/`baud_div`，全雙工獨立運作 | §6 | ok |

設計分解見 [uart-lite-architecture](../design/uart-lite-architecture.md)；
追溯總表見 [traceability-matrix](../notes/traceability-matrix.md)。
