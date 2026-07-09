# 操作日誌

追加式紀錄：所有 ingest / query 回存 / lint 都在此留痕，新紀錄加在檔案末尾。
（格式規範見 [CLAUDE.md](../CLAUDE.md)）

## [2026-07-08] init
- 建立 wiki 骨架：index.md、log.md、pages/ 三分類目錄

## [2026-07-09] spec | UART-Lite 設計規格書 v1.0
- 新增：pages/specs/uart-lite-requirements.md（REQ-UART-001…013，13 條）
- 來源歸檔：sources/archive/uart-lite-spec.md

## [2026-07-09] design | uart-lite
- 新增：pages/design/uart-lite-architecture.md（模組分解：uart_tx / uart_rx / uart_lite_top）
- 新增：pages/design/uart-tx.md、pages/design/uart-rx.md（RTL 生成契約）
- 全部 13 條需求皆有設計頁承接（trace_check 通過）

## [2026-07-09] rtl | uart_tx, uart_rx, uart_lite_top
- 新增：rtl/uart_tx.v、rtl/uart_rx.v、rtl/uart_lite_top.v（Verilog-2001，自設計頁生成）
- 更新：verif/filelist.f

## [2026-07-09] verify | uart-lite
- 新增：verif/tb_uart_lite.v（loopback 4 bytes 背靠背 + frame error，自檢）
- 新增：verif/sim/run_vcs.sh、run_questa.sh、run_xrun.sh
- Icarus Verilog 12.0 預跑：TEST PASSED（修正一次 TB 握手 bug：send_byte 誤把忙碌當已接受）
- 新增：pages/notes/traceability-matrix.md（trace_check.py matrix 產生，零缺口）
