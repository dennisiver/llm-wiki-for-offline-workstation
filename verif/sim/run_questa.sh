#!/bin/bash
# Siemens Questa/ModelSim — 在任何位置執行皆可，自動切到 repo 根目錄
set -e
cd "$(dirname "$0")/../.."

vlib verif/sim/work
vlog -work verif/sim/work -f verif/filelist.f verif/tb_uart_lite.v

vsim -c -work verif/sim/work tb_uart_lite \
     -do "run -all; quit -f" \
     -l verif/sim/questa_sim.log

grep -q "TEST PASSED" verif/sim/questa_sim.log
