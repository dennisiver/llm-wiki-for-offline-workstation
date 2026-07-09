// -----------------------------------------------------------------
// tb_uart_lite  —  UART-Lite 自檢 testbench（純 Verilog-2001）
// 測項：
//   T1  TX→RX 回繞，4 bytes 背靠背傳送，逐一比對（REQ-UART-001/004/005/006/009/010）
//   T2  直接驅動 rxd 送出壞停止位元，預期 rx_ferr 且無 rx_valid（REQ-UART-011）
// 結尾必印 TEST PASSED / TEST FAILED（flow 約定，見 CLAUDE.md）
// -----------------------------------------------------------------

`timescale 1ns / 1ps

module tb_uart_lite;

    localparam integer DIV      = 8;            // baud_div：每位元 8 個時脈
    localparam integer BIT_NS   = DIV * 10;     // 位元週期（10ns 時脈）
    localparam integer N_BYTES  = 4;

    reg         clk;
    reg         rst;
    reg  [15:0] baud_div;

    reg         tx_valid;
    reg  [7:0]  tx_data;
    wire        tx_ready;
    wire        txd;

    reg         use_direct;     // 1 = rxd 由 TB 直接驅動（frame error 測試）
    reg         rxd_direct;
    wire        rxd = use_direct ? rxd_direct : txd;   // 回繞 mux

    wire        rx_valid;
    wire [7:0]  rx_data;
    wire        rx_ferr;

    uart_lite_top dut (
        .clk      (clk),
        .rst      (rst),
        .baud_div (baud_div),
        .tx_valid (tx_valid),
        .tx_data  (tx_data),
        .tx_ready (tx_ready),
        .txd      (txd),
        .rxd      (rxd),
        .rx_valid (rx_valid),
        .rx_data  (rx_data),
        .rx_ferr  (rx_ferr)
    );

    always begin
        clk = 1'b0; #5;
        clk = 1'b1; #5;
    end

    // ---------------- 接收監測 ----------------
    reg [7:0] expected [0:N_BYTES-1];
    integer   n_rx;
    integer   n_ferr;
    integer   errors;

    always @(posedge clk) begin
        if (rx_valid) begin
            if (n_rx < N_BYTES) begin
                if (rx_data !== expected[n_rx]) begin
                    $display("[%0t] ERROR: byte %0d 收到 %02x，預期 %02x",
                             $time, n_rx, rx_data, expected[n_rx]);
                    errors = errors + 1;
                end
            end else begin
                $display("[%0t] ERROR: 多收了一個 byte %02x（frame error 測試不該出 rx_valid）",
                         $time, rx_data);
                errors = errors + 1;
            end
            n_rx = n_rx + 1;
        end
        if (rx_ferr)
            n_ferr = n_ferr + 1;
    end

    // ---------------- 激勵 tasks ----------------

    // 送一個 byte：等 tx_ready 為高才換上新資料，接受後立即返回且
    // tx_valid 保持為高——連續呼叫即為背靠背傳輸（valid 不落下）。
    task send_byte;
        input [7:0] b;
        begin
            while (tx_ready == 1'b0) @(negedge clk);    // 等 TX 可接受
            tx_valid = 1'b1;
            tx_data  = b;
            @(negedge clk);     // 中間的 posedge 完成接受（valid && ready）
        end
    endtask

    // 直接驅動 rxd 送一個訊框，停止位元可指定（0 = 製造 frame error）
    task drive_frame_direct;
        input [7:0] b;
        input       stop_bit;
        integer     k;
        begin
            rxd_direct = 1'b0;              // 起始位元
            #(BIT_NS);
            for (k = 0; k < 8; k = k + 1) begin
                rxd_direct = b[k];          // LSB 先
                #(BIT_NS);
            end
            rxd_direct = stop_bit;          // 停止位元
            #(BIT_NS);
            rxd_direct = 1'b1;              // 回閒置
            #(2 * BIT_NS);
        end
    endtask

    // ---------------- 主流程 ----------------
    integer i;

    initial begin
        rst        = 1'b1;
        baud_div   = DIV[15:0];
        tx_valid   = 1'b0;
        tx_data    = 8'h00;
        use_direct = 1'b0;
        rxd_direct = 1'b1;
        n_rx       = 0;
        n_ferr     = 0;
        errors     = 0;

        expected[0] = 8'h55;
        expected[1] = 8'hA3;
        expected[2] = 8'h00;
        expected[3] = 8'hFF;

        repeat (5) @(negedge clk);
        rst = 1'b0;
        repeat (5) @(negedge clk);

        // T1：回繞、4 bytes 背靠背
        $display("[%0t] T1: loopback 送 %0d bytes（背靠背）", $time, N_BYTES);
        for (i = 0; i < N_BYTES; i = i + 1)
            send_byte(expected[i]);
        tx_valid = 1'b0;

        // 等全部收完（watchdog 顧超時）
        while (n_rx < N_BYTES) @(negedge clk);
        if (n_ferr != 0) begin
            $display("[%0t] ERROR: T1 不該出現 frame error（n_ferr=%0d）", $time, n_ferr);
            errors = errors + 1;
        end

        // T2：壞停止位元 → 預期恰一次 rx_ferr、無新 rx_valid
        repeat (4 * DIV) @(negedge clk);    // 等線路完全閒置
        use_direct = 1'b1;
        $display("[%0t] T2: 直接驅動 rxd，停止位元為 0（frame error）", $time);
        drive_frame_direct(8'h3C, 1'b0);
        repeat (2 * DIV) @(negedge clk);

        if (n_ferr != 1) begin
            $display("[%0t] ERROR: T2 預期 rx_ferr 恰 1 次，實得 %0d", $time, n_ferr);
            errors = errors + 1;
        end
        if (n_rx != N_BYTES) begin
            $display("[%0t] ERROR: T2 不該增加 rx_valid（n_rx=%0d）", $time, n_rx);
            errors = errors + 1;
        end

        if (errors == 0) $display("TEST PASSED");
        else             $display("TEST FAILED (%0d errors)", errors);
        $finish;
    end

    // watchdog：卡死時強制失敗收場
    initial begin
        #200000;
        $display("[%0t] ERROR: watchdog 超時", $time);
        $display("TEST FAILED (watchdog)");
        $finish;
    end

endmodule
