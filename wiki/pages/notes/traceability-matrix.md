---
title: 追溯矩陣（REQ ↔ 設計頁 ↔ RTL ↔ TB）
type: note
created: 2026-07-09
updated: 2026-07-09
sources: []
tags: [traceability, spec-to-rtl, generated]
---

# 追溯矩陣

> 由 `python3 scripts/trace_check.py matrix` 產生，**不要手改**——改了下次重生就會被蓋掉。

| 需求 | Status | 設計頁 | RTL | Testbench |
|------|--------|--------|-----|-----------|
| REQ-UART-001 | ok | [uart-rx](../design/uart-rx.md)<br>[uart-tx](../design/uart-tx.md) | `rtl/uart_rx.v`<br>`rtl/uart_tx.v` | `verif/tb_uart_lite.v` |
| REQ-UART-002 | ok | [uart-tx](../design/uart-tx.md) | `rtl/uart_tx.v` | `verif/tb_uart_lite.v` |
| REQ-UART-003 | ok | [uart-rx](../design/uart-rx.md)<br>[uart-tx](../design/uart-tx.md) | `rtl/uart_rx.v`<br>`rtl/uart_tx.v` | `verif/tb_uart_lite.v` |
| REQ-UART-004 | ok | [uart-tx](../design/uart-tx.md) | `rtl/uart_tx.v` | `verif/tb_uart_lite.v` |
| REQ-UART-005 | ok | [uart-tx](../design/uart-tx.md) | `rtl/uart_tx.v` | `verif/tb_uart_lite.v` |
| REQ-UART-006 | ok | [uart-tx](../design/uart-tx.md) | `rtl/uart_tx.v` | `verif/tb_uart_lite.v` |
| REQ-UART-007 | ok | [uart-rx](../design/uart-rx.md) | `rtl/uart_rx.v` | `verif/tb_uart_lite.v` |
| REQ-UART-008 | ok | [uart-rx](../design/uart-rx.md) | `rtl/uart_rx.v` | `verif/tb_uart_lite.v` |
| REQ-UART-009 | ok | [uart-rx](../design/uart-rx.md) | `rtl/uart_rx.v` | `verif/tb_uart_lite.v` |
| REQ-UART-010 | ok | [uart-rx](../design/uart-rx.md) | `rtl/uart_rx.v` | `verif/tb_uart_lite.v` |
| REQ-UART-011 | ok | [uart-rx](../design/uart-rx.md) | `rtl/uart_rx.v` | `verif/tb_uart_lite.v` |
| REQ-UART-012 | ok | [uart-lite-architecture](../design/uart-lite-architecture.md)<br>[uart-rx](../design/uart-rx.md)<br>[uart-tx](../design/uart-tx.md) | `rtl/uart_lite_top.v`<br>`rtl/uart_rx.v`<br>`rtl/uart_tx.v` | `verif/tb_uart_lite.v` |
| REQ-UART-013 | ok | [uart-lite-architecture](../design/uart-lite-architecture.md) | `rtl/uart_lite_top.v` | `verif/tb_uart_lite.v` |
