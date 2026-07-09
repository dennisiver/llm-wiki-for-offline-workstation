#!/bin/bash
# Synopsys VCS — 在任何位置執行皆可，自動切到 repo 根目錄
set -e
cd "$(dirname "$0")/../.."

vcs -full64 -q \
    -f verif/filelist.f \
    verif/tb_uart_lite.v \
    -o verif/sim/simv \
    -l verif/sim/vcs_compile.log

verif/sim/simv -l verif/sim/vcs_sim.log
grep -q "TEST PASSED" verif/sim/vcs_sim.log
