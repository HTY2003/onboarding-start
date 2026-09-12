<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

This design is a SPI Mode 0 peripheral for 16 outputs.
Each output can be individually set to always-on (high), always-off (low) or PWM output. However, all PWM outputs share the same duty cycle and phase.

## How to test

To use the peripheral, initiate a 16-bit SPI Mode 0 read transaction.

### Command Format

Commands are formatted as such: `<R/W bit (1b)> <Address (7b)> <Data (8b)>`

* R/W bit is set to 1 for writes and 0 for reads. There is nothing to read from this device, so setting this to 0 will end in a NOP.
* Valid addresses range from `0x00` to `0x04`. Using anything outside this range will end in a NOP.
* Data will be used to update the design's internal registers as described below.

### Register Map

| Addr | Register | Description | Reset Value |
|------|----------|-------------|--------------|
| 0x00 | `en_reg_out_7_0` | Enable outputs on `uo_out[7:0]` | 0x00 |
| 0x01 | `en_reg_out_15_8` | Enable outputs on `uio_out[7:0]` | 0x00 |
| 0x02 | `en_reg_pwm_7_0` | Enable PWM for `uo_out[7:0]` | 0x00 |
| 0x03 | `en_reg_pwm_15_8` | Enable PWM for `uio_out[7:0]` | 0x00 |
| 0x04 | `pwm_duty_cycle` | PWM Duty Cycle (`0x00`=0%, `0xFF`=100%) | 0x00 |

### Output Behavior

| Output Enable Bit | PWM Enable Bit | Result |
|--------------------|--------------|--------|
| 0 | X | Output `0` |
| 1 | 0 | Output `1` |
| 1 | 1 | Output PWM |

**Note:** Output Enable Takes Precedence over PWM Mode

## External hardware

To use this design, you will need an device with an SPI controller.
