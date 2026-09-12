/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module spi_peripheral (
    input wire        clk,        // clock
    input wire        rst_n,      // reset_n - low to reset
    input wire        sclk_in,
    input wire        ncs_in,
    input wire        copi_in,
    output reg [7:0]  en_reg_out_7_0,
    output reg [7:0]  en_reg_out_15_8,
    output reg [7:0]  en_reg_pwm_7_0,
    output reg [7:0]  en_reg_pwm_15_8,
    output reg [7:0]  pwm_duty_cycle
);

  wire        sclk_rise;
  wire        ncs_rise;
  wire        ncs;
  wire        copi;
  wire        tsc_rdy;
  wire        tsc_off;
  wire        tsc_vld;
  wire [7:0]  addr;
  wire [7:0]  data;
 
  reg [2:0]   sclk_samples;
  reg [2:0]   ncs_samples;
  reg [1:0]   copi_samples;
  reg [4:0]   sclk_ctr;
  reg [15:0]  fifo;

  assign sclk_rise  = ~sclk_samples[2] & sclk_samples[1];
  assign ncs_rise   = ~ncs_samples[2] & ncs_samples[1];
  assign ncs        = ncs_samples[1];
  assign copi       = copi_samples[1];
  assign tsc_rdy    = ~ncs & sclk_rise;
  assign tsc_off    = ncs;
  assign tsc_vld    = ncs_rise && sclk_ctr == 5'b10000;
  assign addr       = fifo[15:8];
  assign data       = fifo[7:0];

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      sclk_samples  <= '0;
      ncs_samples   <= '1;
      copi_samples  <= '0;
    end
    else begin
      sclk_samples  <= {sclk_samples[1:0], sclk_in};
      ncs_samples   <= {ncs_samples[1:0], ncs_in};
      copi_samples  <= {copi_samples[0], copi_in};
    end
  end

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      fifo      <= '0;
      sclk_ctr  <= '0;
    end
    else begin
      if (tsc_rdy) begin
        fifo      <= {fifo[14:0], copi}; 
        sclk_ctr  <= sclk_ctr == 5'b10001 ? sclk_ctr : sclk_ctr + 1;
      end else if (tsc_off) begin
        sclk_ctr  <= 0;
      end
    end
  end

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      en_reg_out_7_0  <= '0;
      en_reg_out_15_8 <= '0;
      en_reg_pwm_7_0  <= '0;
      en_reg_pwm_15_8 <= '0;
      pwm_duty_cycle  <= '0;
    end
    else begin
      if (tsc_vld) begin
        case (addr)
          8'b10000000:  en_reg_out_7_0   <= data;
          8'b10000001:  en_reg_out_15_8  <= data;
          8'b10000010:  en_reg_pwm_7_0   <= data;
          8'b10000011:  en_reg_pwm_15_8  <= data;
          8'b10000100:  pwm_duty_cycle   <= data;
          default:      ;
        endcase
      end
    end
  end

endmodule
