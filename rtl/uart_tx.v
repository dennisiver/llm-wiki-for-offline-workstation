// -----------------------------------------------------------------
// uart_tx  —  generated from wiki/pages/design/uart-tx.md
// Implements: REQ-UART-001, REQ-UART-002, REQ-UART-003, REQ-UART-004,
//             REQ-UART-005, REQ-UART-006, REQ-UART-012
// 修改流程：先改設計頁，再重生此檔。不要只改這裡（會與 wiki 漂移）。
// -----------------------------------------------------------------

`timescale 1ns / 1ps

module uart_tx (
    input             clk,
    input             rst,       // 同步重置，高有效
    input      [15:0] baud_div,  // 位元週期（時脈數），合法值 >= 4
    input             tx_valid,
    input      [7:0]  tx_data,
    output            tx_ready,
    output reg        txd
);

    localparam [1:0] S_IDLE  = 2'd0,
                     S_START = 2'd1,
                     S_DATA  = 2'd2,
                     S_STOP  = 2'd3;

    reg [1:0]  state;
    reg [15:0] baud_cnt;
    reg [2:0]  bit_idx;
    reg [7:0]  shreg;

    wire bit_done = (baud_cnt == baud_div - 16'd1);

    assign tx_ready = (state == S_IDLE);

    always @(posedge clk) begin
        if (rst) begin
            state    <= S_IDLE;
            txd      <= 1'b1;   // 重置期間線路維持高（REQ-UART-002）
            baud_cnt <= 16'd0;
            bit_idx  <= 3'd0;
            shreg    <= 8'd0;
        end else begin
            case (state)
                S_IDLE: begin
                    txd <= 1'b1;
                    if (tx_valid) begin
                        shreg    <= tx_data;
                        txd      <= 1'b0;   // 起始位元自此邊緣開始
                        baud_cnt <= 16'd0;
                        state    <= S_START;
                    end
                end
                S_START: begin
                    if (bit_done) begin
                        baud_cnt <= 16'd0;
                        txd      <= shreg[0];   // 資料 LSB 先送
                        bit_idx  <= 3'd0;
                        state    <= S_DATA;
                    end else begin
                        baud_cnt <= baud_cnt + 16'd1;
                    end
                end
                S_DATA: begin
                    if (bit_done) begin
                        baud_cnt <= 16'd0;
                        if (bit_idx == 3'd7) begin
                            txd   <= 1'b1;      // 停止位元
                            state <= S_STOP;
                        end else begin
                            shreg   <= {1'b0, shreg[7:1]};
                            txd     <= shreg[1];
                            bit_idx <= bit_idx + 3'd1;
                        end
                    end else begin
                        baud_cnt <= baud_cnt + 16'd1;
                    end
                end
                S_STOP: begin
                    if (bit_done) begin
                        state <= S_IDLE;    // 下一時脈 tx_ready 即為高，
                    end else begin          // 背靠背間隙 <= 1 時脈（REQ-UART-006）
                        baud_cnt <= baud_cnt + 16'd1;
                    end
                end
                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
