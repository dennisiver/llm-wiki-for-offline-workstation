// -----------------------------------------------------------------
// uart_rx  —  generated from wiki/pages/design/uart-rx.md
// Implements: REQ-UART-001, REQ-UART-003, REQ-UART-007, REQ-UART-008,
//             REQ-UART-009, REQ-UART-010, REQ-UART-011, REQ-UART-012
// 修改流程：先改設計頁，再重生此檔。不要只改這裡（會與 wiki 漂移）。
// -----------------------------------------------------------------

`timescale 1ns / 1ps

module uart_rx (
    input             clk,
    input             rst,       // 同步重置，高有效
    input      [15:0] baud_div,  // 位元週期（時脈數），合法值 >= 4
    input             rxd,       // 非同步序列輸入
    output reg        rx_valid,  // 單時脈脈波
    output reg [7:0]  rx_data,   // 保持到下一次 rx_valid
    output reg        rx_ferr    // frame error 單時脈脈波
);

    localparam [1:0] S_IDLE  = 2'd0,
                     S_START = 2'd1,
                     S_DATA  = 2'd2,
                     S_STOP  = 2'd3;

    // 兩級同步器（REQ-UART-007）
    reg rxd_m, rxd_s;
    always @(posedge clk) begin
        if (rst) begin
            rxd_m <= 1'b1;
            rxd_s <= 1'b1;
        end else begin
            rxd_m <= rxd;
            rxd_s <= rxd_m;
        end
    end

    reg [1:0]  state;
    reg [15:0] cnt;
    reg [2:0]  bit_idx;
    reg [7:0]  shreg;

    wire [15:0] half_div = {1'b0, baud_div[15:1]};      // baud_div/2 向下取整
    wire        at_half  = (cnt == half_div - 16'd1);
    wire        at_full  = (cnt == baud_div - 16'd1);

    always @(posedge clk) begin
        if (rst) begin
            state    <= S_IDLE;
            cnt      <= 16'd0;
            bit_idx  <= 3'd0;
            shreg    <= 8'd0;
            rx_valid <= 1'b0;
            rx_data  <= 8'd0;
            rx_ferr  <= 1'b0;
        end else begin
            rx_valid <= 1'b0;   // 預設歸零：兩者皆為單時脈脈波
            rx_ferr  <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (rxd_s == 1'b0) begin    // 起始緣
                        cnt   <= 16'd0;
                        state <= S_START;
                    end
                end
                S_START: begin                  // 中點複檢（REQ-UART-008）
                    if (at_half) begin
                        cnt <= 16'd0;
                        if (rxd_s == 1'b0) begin
                            bit_idx <= 3'd0;
                            state   <= S_DATA;
                        end else begin
                            state <= S_IDLE;    // 雜訊，放棄
                        end
                    end else begin
                        cnt <= cnt + 16'd1;
                    end
                end
                S_DATA: begin                   // 每 baud_div 到位元中點取樣
                    if (at_full) begin
                        cnt   <= 16'd0;
                        shreg <= {rxd_s, shreg[7:1]};   // LSB 先收
                        if (bit_idx == 3'd7)
                            state <= S_STOP;
                        else
                            bit_idx <= bit_idx + 3'd1;
                    end else begin
                        cnt <= cnt + 16'd1;
                    end
                end
                S_STOP: begin                   // 停止位元中點取樣後即回閒置
                    if (at_full) begin
                        cnt   <= 16'd0;
                        state <= S_IDLE;
                        if (rxd_s == 1'b1) begin
                            rx_data  <= shreg;
                            rx_valid <= 1'b1;   // 成功訊框（REQ-UART-010）
                        end else begin
                            rx_ferr  <= 1'b1;   // frame error（REQ-UART-011）
                        end
                    end else begin
                        cnt <= cnt + 16'd1;
                    end
                end
                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
