# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

from math import ceil
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Edge, Timer, First
from cocotb.types import LogicArray

async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

async def enable_uo_out_output(dut, ch):
    await send_spi_transaction(dut, 1, 0x00, (0x01 << ch))

async def enable_uo_out_pwm(dut, ch):
    await send_spi_transaction(dut, 1, 0x02, (0x01 << ch))

async def enable_uio_out_output(dut, ch):
    await send_spi_transaction(dut, 1, 0x01, (0x01 << ch))

async def enable_uio_out_pwm(dut, ch):
    await send_spi_transaction(dut, 1, 0x03, (0x01 << ch))

async def enable_uo_out_all_output(dut):
    await send_spi_transaction(dut, 1, 0x00, 0xFF)

async def enable_uo_out_all_pwm(dut):
    await send_spi_transaction(dut, 1, 0x02, 0xFF)

async def enable_uio_out_all_output(dut):
    await send_spi_transaction(dut, 1, 0x01, 0xFF)

async def enable_uio_out_all_pwm(dut):
    await send_spi_transaction(dut, 1, 0x03, 0xFF)

async def disable_uo_out_all_output(dut):
    await send_spi_transaction(dut, 1, 0x00, 0x00)

async def disable_uo_out_all_pwm(dut):
    await send_spi_transaction(dut, 1, 0x02, 0x00)

async def disable_uio_out_all_output(dut):
    await send_spi_transaction(dut, 1, 0x01, 0x00)

async def disable_uio_out_all_pwm(dut):
    await send_spi_transaction(dut, 1, 0x03, 0x00)

async def set_duty_cycle(dut, val):
    await send_spi_transaction(dut, 1, 0x04, val)

async def await_uo_out_1ch_rise(dut, ch, timeout_ns):
    await await_out_edge(dut, ch, timeout_ns, False, True)

async def await_uio_out_1ch_rise(dut, ch, timeout_ns):
    await await_out_edge(dut, ch, timeout_ns, True, True)

async def await_uo_out_1ch_fall(dut, ch, timeout_ns):
    await await_out_edge(dut, ch, timeout_ns, False, False)

async def await_uio_out_1ch_fall(dut, ch, timeout_ns):
    await await_out_edge(dut, ch, timeout_ns, True, False)

async def await_out_edge(dut, ch, timeout_ns, use_uio_out, wait_for_rise):
    start_time = cocotb.utils.get_sim_time(units="ns")

    while True:
        edge_coro = None
        if use_uio_out:
            old = (int(dut.uio_out.value) >> ch) & 0x1
            edge_coro = cocotb.start_soon(watch_uio_out_edge(dut))
        else:
            old = (int(dut.uo_out.value) >> ch) & 0x1
            edge_coro = cocotb.start_soon(watch_uo_out_edge(dut))

        timeout_timer = Timer(int(timeout_ns), 'ns')
        finished = await First(edge_coro, timeout_timer)
        if not edge_coro.done:
            edge_coro.cancel()

        assert finished is not timeout_timer, f"Expected edge within {timeout_ns} ns but signal did not change"

        if use_uio_out:
            new = (int(dut.uio_out.value) >> ch) & 0x1
        else:
            new = (int(dut.uo_out.value) >> ch) & 0x1

        if new == 0 and old == 1 and not wait_for_rise:
            break

        if new == 1 and old == 0 and wait_for_rise:
            break

        if cocotb.utils.get_sim_time(units="ns") - start_time > timeout_ns:
            assert False, f"Expected edge within {timeout_ns} ns but signal did not change"

async def watch_uo_out_edge(dut):
    await Edge(dut.uo_out)
    return True

async def watch_uio_out_edge(dut):
    await Edge(dut.uio_out)
    return True

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")

@cocotb.test()
async def test_pwm_freq(dut):
    dut._log.info("Start PWM frequency test")

    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")

    expected_freq = 3000
    typ_period_ns = 1e9 / expected_freq
    max_period_ns = ceil(typ_period_ns * 1.01 / 100) * 100
    min_period_ns = (typ_period_ns * 0.99) // 100 * 100
    timeout_ns    = typ_period_ns * 1.1

    # Set up PWM output with 50% Duty Cycle
    dut._log.info("Enable 50% Duty Cycle PWM output on all ch")
    await enable_uo_out_all_output(dut)
    await enable_uo_out_all_pwm(dut)
    await enable_uio_out_all_output(dut)
    await enable_uio_out_all_pwm(dut)
    await set_duty_cycle(dut, 0x80)

    # For each uo_out channel
    for i in range(8):
        # Collect rising edge times
        rise_edges = []

        for _ in range(4):
            await await_uo_out_1ch_rise(dut, i, timeout_ns)
            rise_edges.append(cocotb.utils.get_sim_time(units="ns"))

        # Check period between rising edges
        periods = [rise_edges[i+1] - rise_edges[i] for i in range(0, len(rise_edges)-1)]

        for p in periods:
            assert p >= min_period_ns, f"Expected PWM period of at least {min_period_ns} ns, got {p} ns"
            assert p <= max_period_ns, f"Expected PWM period of at most {max_period_ns} ns, got {p} ns"

        dut._log.info(f"PWM frequency for uo_out ch{i} OK")

    # For each uio_out channel
    for i in range(8):
        # Collect rising edge times
        rise_edges = []

        for _ in range(4):
            await await_uio_out_1ch_rise(dut, i, timeout_ns)
            rise_edges.append(cocotb.utils.get_sim_time(units="ns"))

        # Check period between rising edges
        periods = [rise_edges[i+1] - rise_edges[i] for i in range(0, len(rise_edges)-1)]

        for p in periods:
            assert p >= min_period_ns, f"Expected PWM period of at least {min_period_ns} ns, got {p} ns"
            assert p <= max_period_ns, f"Expected PWM period of at most {max_period_ns} ns, got {p} ns"

        dut._log.info(f"PWM frequency for uio_out ch{i} OK")

    dut._log.info("PWM frequency test completed successfully")

@cocotb.test()
async def test_pwm_duty(dut):
    dut._log.info("Start PWM Duty Cycle test")

    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")

    expected_freq   = 3000
    typ_period_ns   = 1e9 / expected_freq
    timeout_ns      = int(typ_period_ns * 1.1)

    # Set up PWM output
    dut._log.info("Enable PWM output on all chs")
    await enable_uo_out_all_output(dut)
    await enable_uo_out_all_pwm(dut)
    await enable_uio_out_all_output(dut)
    await enable_uio_out_all_pwm(dut)

    # Sweep through all duty cycles and check
    for i in range(256):
        dut._log.info(f"Set Duty Cycle to {i} / 255")
        await set_duty_cycle(dut, i)

        # Check for no edges if duty cycle is 0 or 255
        if i == 0 or i ==255:
            # Check uio_out output is constant
            assert dut.uo_out.value == i, f"Expected uo_out to be {i}, got {dut.uo_out.value}"

            edge_coro = cocotb.start_soon(watch_uo_out_edge(dut))
            timeout_timer = Timer(int(timeout_ns), 'ns')
            finished = await First(edge_coro, timeout_timer)
            if not edge_coro.done:
                edge_coro.cancel()

            assert finished is timeout_timer, f"Expected no change in uo_out within {timeout_ns} ns"

            # Check uio_out output is constant
            assert dut.uio_out.value == i, f"Expected uio_out to be {i}, got {dut.uio_out.value}"

            edge_coro = cocotb.start_soon(watch_uio_out_edge(dut))
            timeout_timer = Timer(int(timeout_ns), 'ns')
            finished = await First(edge_coro, timeout_timer)
            if not edge_coro.done:
                edge_coro.cancel()

            assert finished is timeout_timer, f"Expected no change in uio_out within {timeout_ns} ns"

        # Otherwise, check ON time is within 1% tolerance
        else:
            expected_on_ns = i / 255 * typ_period_ns
            max_on_ns = ceil(expected_on_ns * 1.01 / 100) * 100
            min_on_ns = (expected_on_ns * 0.99) // 100 * 100

            # Collect uo_out ch0 rising and falling edge times
            rise_edges = []
            fall_edges = []

            for _ in range(4):
                await await_uo_out_1ch_rise(dut, 0, timeout_ns)
                rise_edges.append(cocotb.utils.get_sim_time(units="ns"))
                await await_uo_out_1ch_fall(dut, 0, timeout_ns)
                fall_edges.append(cocotb.utils.get_sim_time(units="ns"))

            # Check ON duration of the signal
            on_times = [fall_edges[j] - rise_edges[j] for j in range(4)]

            for t in on_times:
                assert t >= min_on_ns, f"Expected uo_out ON time of at least {min_on_ns} ns, got {t} ns"
                assert t <= max_on_ns, f"Expected uo_out ON time of at most {max_on_ns} ns, got {t} ns"

            # Collect uio_out ch0 rising and falling edge times
            rise_edges = []
            fall_edges = []

            for _ in range(4):
                await await_uio_out_1ch_rise(dut, 0, timeout_ns)
                rise_edges.append(cocotb.utils.get_sim_time(units="ns"))
                await await_uio_out_1ch_fall(dut, 0, timeout_ns)
                fall_edges.append(cocotb.utils.get_sim_time(units="ns"))

            # Check ON duration of the signal
            on_times = [fall_edges[j] - rise_edges[j] for j in range(4)]

            for t in on_times:
                assert t >= min_on_ns, f"Expected uio_out ON time of at least {min_on_ns} ns, got {t} ns"
                assert t <= max_on_ns, f"Expected uio_out ON time of at most {max_on_ns} ns, got {t} ns"

        dut._log.info(f"PWM Duty Cycle {i} / 255 OK")

    dut._log.info("PWM Duty Cycle test completed successfully")

@cocotb.test()
async def test_output_control(dut):
    dut._log.info("Start Output Control test")

    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")

    expected_freq = 3000
    typ_period_ns = 1e9 / expected_freq
    timeout_ns = int(typ_period_ns * 1.1)

    for i in range(8):
        # Check that uo_out ch outputs 0 without toggling
        assert int(dut.uo_out[i]) == 0, f"Expected uo_out ch{i} to be 0, got {int(dut.uo_out[i])}"
        edge_coro = cocotb.start_soon(watch_uo_out_edge(dut))
        timeout_timer = Timer(int(timeout_ns), 'ns')
        finished = await First(edge_coro, timeout_timer)
        if not edge_coro.done:
            edge_coro.cancel()
        assert finished is timeout_timer, f"Expected no change in uo_out ch{i} within {timeout_ns} ns"

        # Enable output (but not PWM) for uo_out ch
        dut._log.info(f"Enable uo_out ch{i} output")
        await enable_uo_out_output(dut, i)

        # Check that uo_out ch outputs 1 without toggling
        assert int(dut.uo_out[i]) == 1, f"Expected uo_out ch{i} to be 1, got {int(dut.uo_out[i])}"

        edge_coro = cocotb.start_soon(watch_uo_out_edge(dut))
        timeout_timer = Timer(int(timeout_ns), 'ns')
        finished = await First(edge_coro, timeout_timer)
        if not edge_coro.done:
            edge_coro.cancel()

        assert finished is timeout_timer, f"Expected no change in uo_out ch{i} within {timeout_ns} ns"

        # Enable 50% duty cycle PWM output for uo_out ch
        dut._log.info(f"Enable uo_out ch{i} PWM and set 50% duty cycle")
        await enable_uo_out_pwm(dut, i)
        await set_duty_cycle(dut, 0x80)

        # Check that uo_out ch output toggles
        await await_uo_out_1ch_rise(dut, i, timeout_ns)
        await await_uo_out_1ch_fall(dut, i, timeout_ns)

        # Disable all uo_out channels
        dut._log.info(f"Disable uo_out ch{i} output")
        await disable_uo_out_all_output(dut)

        # Check that uo_out ch outputs 0 without toggling
        assert int(dut.uo_out[i]) == 0, f"Expected uo_out ch{i} to be 0, got {int(dut.uo_out[i])}"
        edge_coro = cocotb.start_soon(watch_uo_out_edge(dut))
        timeout_timer = Timer(int(timeout_ns), 'ns')
        finished = await First(edge_coro, timeout_timer)
        if not edge_coro.done:
            edge_coro.cancel()

        assert finished is timeout_timer, f"Expected no change in uo_out ch{i} within {timeout_ns} ns"

        dut._log.info(f"Output Control for uo_out ch{i} OK")

    for i in range(8):
        # Check that uio_out ch outputs 0 without toggling
        assert int(dut.uio_out[i]) == 0, f"Expected uio_out ch{i} to be 0, got {int(dut.uio_out[i])}"

        edge_coro = cocotb.start_soon(watch_uio_out_edge(dut))
        timeout_timer = Timer(int(timeout_ns), 'ns')
        finished = await First(edge_coro, timeout_timer)
        if not edge_coro.done:
            edge_coro.cancel()

        assert finished is timeout_timer, f"Expected no change in uio_out ch{i} within {timeout_ns} ns"

        # Enable output (but not PWM) for uio_out ch
        dut._log.info(f"Enable uio_out ch{i} output")
        await enable_uio_out_output(dut, i)

        # Check that uio_out ch outputs 1 without toggling
        assert int(dut.uio_out[i]) == 1, f"Expected uio_out ch{i} to be 1, got {int(dut.uio_out[i])}"

        edge_coro = cocotb.start_soon(watch_uio_out_edge(dut))
        timeout_timer = Timer(int(timeout_ns), 'ns')
        finished = await First(edge_coro, timeout_timer)
        if not edge_coro.done:
            edge_coro.cancel()

        assert finished is timeout_timer, f"Expected no change in uio_out ch{i} within {timeout_ns} ns"

        # Enable 50% duty cycle PWM output for uio_out ch
        dut._log.info(f"Enable uio_out ch{i} PWM and set 50% duty cycle")
        await enable_uio_out_pwm(dut, i)
        await set_duty_cycle(dut, 0x80)

        # Check that uio_out ch output toggles
        await await_uio_out_1ch_rise(dut, i, timeout_ns)
        await await_uio_out_1ch_fall(dut, i, timeout_ns)

        # Disable all uio_out channels
        dut._log.info(f"Disable uio_out ch{i} output")
        await disable_uio_out_all_output(dut)

        # Check that uio_out ch outputs 0 without toggling
        assert int(dut.uio_out[i]) == 0, f"Expected uio_out ch{i} to be 0, got {int(dut.uio_out[i])}"

        edge_coro = cocotb.start_soon(watch_uio_out_edge(dut))
        timeout_timer = Timer(int(timeout_ns), 'ns')
        finished = await First(edge_coro, timeout_timer)
        if not edge_coro.done:
            edge_coro.cancel()

        assert finished is timeout_timer, f"Expected no change in uio_out ch{i} within {timeout_ns} ns"

        dut._log.info(f"Output Control for uio_out ch{i} OK")

    dut._log.info("Output Control test completed successfully")
