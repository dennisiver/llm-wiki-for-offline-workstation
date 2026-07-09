---
title: uart_rx 模組設計
type: design
created: 2026-07-09
updated: 2026-07-09
sources:
  - sources/archive/uart-lite-spec.md
implements: [REQ-UART-001, REQ-UART-003, REQ-UART-007, REQ-UART-008, REQ-UART-009, REQ-UART-010, REQ-UART-011, REQ-UART-012]
rtl: rtl/uart_rx.v
tb: verif/tb_uart_lite.v
status: ok
tags: [uart, rx, spec-to-rtl]
---

# uart_rx 模組設計

UART-Lite 接收器。所屬架構見 [uart-lite-architecture](uart-lite-architecture.md)，
需求見 [uart-lite-requirements](../specs/uart-lite-requirements.md)。

## Ports

| 名稱 | 方向 | 寬度 | 說明 |
|------|------|------|------|
| clk | in | 1 | 系統時脈 |
| rst | in | 1 | 同步重置，高有效（REQ-UART-012） |
| baud_div | in | 16 | 位元週期（時脈數），合法值 ≥ 4（REQ-UART-003） |
| rxd | in | 1 | 序列輸入，非同步（REQ-UART-007） |
| rx_valid | out | 1 | 成功收到一個位元組時的單時脈脈波（REQ-UART-010） |
| rx_data | out | 8 | 收到的位元組，保持到下一次 rx_valid |
| rx_ferr | out | 1 | frame error 單時脈脈波（REQ-UART-011） |

## 輸入同步（REQ-UART-007）

兩級正反器 `rxd_m → rxd_s`，重置值皆為 1（閒置高）。後續邏輯只用 `rxd_s`。

## FSM

狀態編碼 `localparam [1:0] S_IDLE=0, S_START=1, S_DATA=2, S_STOP=3`。

| 狀態 | 行為 | 轉移 |
|------|------|------|
| S_IDLE | 等 `rxd_s == 0`（起始緣）；偵測到即計數器歸零 | → S_START |
| S_START | 計到 `baud_div/2 - 1`（向下取整，即起始位元中點）複檢 `rxd_s`：仍為 0 → 確認起始，計數器歸零、`bit_idx` ← 0；為 1 → 雜訊，放棄（REQ-UART-008） | 0 → S_DATA；1 → S_IDLE |
| S_DATA | 每計滿 `baud_div` 個時脈即為該資料位元的中點（相位鎖定自中點複檢時刻）：`shreg ← {rxd_s, shreg[7:1]}`（LSB 先收，REQ-UART-001/009）、`bit_idx` + 1 | bit_idx==7 取樣後 → S_STOP |
| S_STOP | 計滿 `baud_div` 到停止位元中點取樣：`rxd_s == 1` → `rx_data ← shreg`、`rx_valid` 脈波；`== 0` → `rx_ferr` 脈波、資料作廢（REQ-UART-010/011）。取樣後即回閒置——停止位元後半段已可偵測下一個起始緣 | → S_IDLE |

## 計時與取樣相位

- 16-bit 計數器 `cnt`；中點複檢用 `baud_div >> 1`（無號右移，向下取整）。
- 相位基準：中點複檢那個時脈起，每 `baud_div` 個時脈就是下一位元的中點。
  兩級同步器造成的 1–2 時脈偏移在 `baud_div ≥ 4` 下仍落於位元內，可接受。

## 輸出時序

- `rx_valid`、`rx_ferr` 預設每時脈歸 0，僅在停止位元取樣的下一個時脈打一拍（單時脈脈波）。
- `rx_data` 為暫存器，只在成功訊框時更新（REQ-UART-010 的保持語意）。

## 重置行為

`rst` 為高的時脈：state ← S_IDLE、同步器輸出 ← 1、rx_valid/rx_ferr ← 0（REQ-UART-012）。
