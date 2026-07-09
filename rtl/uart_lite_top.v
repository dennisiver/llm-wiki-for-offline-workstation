// -----------------------------------------------------------------
// uart_lite_top  —  generated from wiki/pages/design/uart-lite-architecture.md
// Implements: REQ-UART-012, REQ-UART-013
// 修改流程：先改設計頁，再重生此檔。不要只改這裡（會與 wiki 漂移）。
// -----------------------------------------------------------------

`timescale 1ns / 1ps

module uart_lite_top (
    input             clk,
    input             rst,        // 同步重置，高有效
    input      [15:0] baud_div,   // 兩個子模組共用

    // TX 資料介面
    input             tx_valid,
    input      [7:0]  tx_data,
    output            tx_ready,
    output            txd,

    // RX 資料介面
    input             rxd,
    output            rx_valid,
    output     [7:0]  rx_data,
    output            rx_ferr
);

    // TX 與 RX 各自擁有位元計時，彼此無連線（REQ-UART-013 全雙工獨立）
    uart_tx u_tx (
        .clk      (clk),
        .rst      (rst),
        .baud_div (baud_div),
        .tx_valid (tx_valid),
        .tx_data  (tx_data),
        .tx_ready (tx_ready),
        .txd      (txd)
    );

    uart_rx u_rx (
        .clk      (clk),
        .rst      (rst),
        .baud_div (baud_div),
        .rxd      (rxd),
        .rx_valid (rx_valid),
        .rx_data  (rx_data),
        .rx_ferr  (rx_ferr)
    );

endmodule
