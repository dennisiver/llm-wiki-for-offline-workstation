---
title: uart_tx 模組設計
type: design
created: 2026-07-09
updated: 2026-07-09
sources:
  - sources/archive/uart-lite-spec.md
implements: [REQ-UART-001, REQ-UART-002, REQ-UART-003, REQ-UART-004, REQ-UART-005, REQ-UART-006, REQ-UART-012]
rtl: rtl/uart_tx.v
tb: verif/tb_uart_lite.v
status: ok
tags: [uart, tx, spec-to-rtl]
---

# uart_tx 模組設計

UART-Lite 傳送器。所屬架構見 [uart-lite-architecture](uart-lite-architecture.md)，
需求見 [uart-lite-requirements](../specs/uart-lite-requirements.md)。

## Ports

| 名稱 | 方向 | 寬度 | 說明 |
|------|------|------|------|
| clk | in | 1 | 系統時脈 |
| rst | in | 1 | 同步重置，高有效（REQ-UART-012） |
| baud_div | in | 16 | 位元週期（時脈數），合法值 ≥ 4（REQ-UART-003） |
| tx_valid | in | 1 | 資料有效（REQ-UART-004） |
| tx_data | in | 8 | 待送位元組 |
| tx_ready | out | 1 | 高 = 可接受資料；`state == S_IDLE` 的組合輸出 |
| txd | out | 1 | 序列輸出（暫存器輸出，重置與閒置為高，REQ-UART-002） |

## Parameters

無。位元週期由 `baud_div` 埠動態設定（REQ-UART-003 規定收發中不得變更，由使用端保證）。

## FSM（兩段式：狀態暫存 + 輸出在同一個 always 內更新）

狀態編碼 `localparam [1:0] S_IDLE=0, S_START=1, S_DATA=2, S_STOP=3`。

| 狀態 | 行為 | 轉移 |
|------|------|------|
| S_IDLE | txd=1、tx_ready=1；`tx_valid` 為高時鎖存 `tx_data` 進移位暫存器 `shreg`，txd 拉低（起始位元開始）、位元計數器歸零 | → S_START |
| S_START | 計滿 `baud_div` 個時脈後：txd ← `shreg[0]`，`bit_idx` ← 0 | → S_DATA |
| S_DATA | 每計滿 `baud_div`：若 `bit_idx == 7` 則 txd ← 1（停止位元）；否則 `shreg` 右移一位、txd ← 移位前的 `shreg[1]`、`bit_idx` + 1。LSB 先送（REQ-UART-001/005） | bit_idx==7 → S_STOP |
| S_STOP | 計滿 `baud_div` 後回閒置；txd 維持 1。回到 S_IDLE 的下一個時脈 `tx_ready` 即為高，滿足背靠背間隙 ≤ 1 時脈（REQ-UART-006） | → S_IDLE |

## 計時

- 16-bit 計數器 `baud_cnt`，每狀態入口歸零，計到 `baud_div - 1` 視為一個位元週期結束。
- 起始位元的週期從 S_IDLE 接受資料、txd 拉低的那個時脈開始算（S_START 計數涵蓋整個起始位元）。

## 重置行為

`rst` 為高的時脈：state ← S_IDLE、txd ← 1、計數器/索引清零（REQ-UART-002/012）。
