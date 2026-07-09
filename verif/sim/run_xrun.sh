#!/bin/bash
# Cadence Xcelium — 在任何位置執行皆可，自動切到 repo 根目錄
set -e
cd "$(dirname "$0")/../.."

xrun -q \
     -f verif/filelist.f \
     verif/tb_uart_lite.v \
     -l verif/sim/xrun_sim.log

grep -q "TEST PASSED" verif/sim/xrun_sim.log
