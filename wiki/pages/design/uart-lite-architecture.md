---
title: UART-Lite 架構與頂層整合
type: design
created: 2026-07-09
updated: 2026-07-09
sources:
  - sources/archive/uart-lite-spec.md
implements: [REQ-UART-012, REQ-UART-013]
rtl: rtl/uart_lite_top.v
tb: verif/tb_uart_lite.v
status: ok
tags: [uart, architecture, spec-to-rtl]
---

# UART-Lite 架構

實作 [uart-lite-requirements](../specs/uart-lite-requirements.md) 的模組分解與頂層整合。

## 方塊圖

```
                    ┌─────────────── uart_lite_top ───────────────┐
  tx_valid ────────▶│  ┌───────────┐                              │
  tx_data[7:0] ────▶│  │  uart_tx  │──────────────────────────────│──▶ txd
  tx_ready ◀────────│  └───────────┘                              │
                    │                                             │
  rx_valid ◀────────│  ┌───────────┐                              │
  rx_data[7:0] ◀────│  │  uart_rx  │◀─────────────────────────────│◀── rxd
  rx_ferr ◀─────────│  └───────────┘                              │
                    │                                             │
  clk, rst ────────▶│──▶ 兩個子模組共用                            │
  baud_div[15:0] ──▶│──▶ 兩個子模組共用                            │
                    └─────────────────────────────────────────────┘
```

## 模組分解

| 模組 | 職責 | 設計頁 |
|------|------|--------|
| `uart_tx` | 訊框傳送、valid/ready 握手、位元計時 | [uart-tx](uart-tx.md) |
| `uart_rx` | 輸入同步、起始偵測、中點取樣、frame error | [uart-rx](uart-rx.md) |
| `uart_lite_top` | 純接線，無自有邏輯（本頁即其設計頁） | 本頁 |

TX 與 RX **各自擁有位元計時計數器**、不共用 baud tick：RX 的取樣相位必須對齊
自己偵測到的起始緣（[REQ-UART-008](../specs/uart-lite-requirements.md)），
與 TX 的相位無關；共用 tick 反而引入耦合。

## 頂層接線（uart_lite_top）

| Port | 方向 | 寬度 | 接往 |
|------|------|------|------|
| clk, rst | in | 1 | 兩個子模組（REQ-UART-012：單時脈域、同步高有效重置） |
| baud_div | in | 16 | 兩個子模組 |
| tx_valid, tx_data[7:0] | in | 1 / 8 | uart_tx |
| tx_ready, txd | out | 1 | uart_tx |
| rxd | in | 1 | uart_rx |
| rx_valid, rx_data[7:0], rx_ferr | out | 1 / 8 / 1 | uart_rx |

TX 與 RX 之間無任何連線（REQ-UART-013：全雙工獨立運作）。

## 時脈與重置策略（全專案約定）

- 單一時脈域 `clk`，所有循序邏輯 `always @(posedge clk)`。
- 同步重置、高有效 `rst`；重置時所有 FSM 回 IDLE、txd 拉高。
- 這是 [CLAUDE.md](../../../CLAUDE.md) Verilog-2001 規則的預設，各模組設計頁不再覆寫。
