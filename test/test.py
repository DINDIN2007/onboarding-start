# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import FallingEdge
from cocotb.triggers import with_timeout
from cocotb.triggers import Timer
from cocotb.triggers import First
from cocotb.triggers import ClockCycles
from cocotb.types import Logic
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

# Detects rising edge and returns the time that has elapsed since then
async def detect_rising_edge(dut, timeout):
    previous_signal = dut.uo_out.value.integer & 1
    starting_time = cocotb.utils.get_sim_time(units="ns")

    while cocotb.utils.get_sim_time(units="ns") - starting_time < timeout:
        await ClockCycles(dut.clk, 1)
        current_signal = dut.uo_out.value.integer & 1
        
        # If the signal goes low to high, there's a rising edge
        if previous_signal == 0 and current_signal == 1:
            return  cocotb.utils.get_sim_time(units="ns")
        previous_signal = current_signal
    
    return False

# Detects falling edge and returns the time that has elapsed since then
async def detect_falling_edge(dut, timeout):
    previous_signal = dut.uo_out.value.integer & 1
    starting_time = cocotb.utils.get_sim_time(units="ns")

    while cocotb.utils.get_sim_time(units="ns") - starting_time < timeout:
        await ClockCycles(dut.clk, 1)
        current_signal = dut.uo_out.value.integer & 1
        
        # If the signal goes high to low, there's a falling edge
        if previous_signal == 1 and current_signal == 0:
            return  cocotb.utils.get_sim_time(units="ns")
        previous_signal = current_signal
    
    return False

# Measure the time between two rising edges of the PWM signal (period = t_rising_edge2 - t_rising_edge1).
# Frequency = 1 / period.
@cocotb.test()
async def test_pwm_freq(dut):
    # Write your test here
    dut._log.info("PWM Frequency test started.")

    # Set the clock period to 100 ns or 10 MHz
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    sclk = 0; ncs = 1; bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    
    dut.rst_n.value = 0
    dut.ena.value = 1
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # Enable PWM output and PWM mode
    dut._log.info("Enabling PWM ouput and mode...")
    await send_spi_transaction(dut, 1, 0x00, 0x01) # Write 1 to enable output
    await send_spi_transaction(dut, 1, 0x02, 0x01) # Write 1 to enable PWM mode
    await send_spi_transaction(dut, 1, 0x04, 0x80) # Write 50% PWM Duty Cycle (128/255 to hex)
    await ClockCycles(dut.clk, 20000)

    # Measure the time between two rising edges of the PWM signal 
    start_time = await detect_rising_edge(dut, 1e7)
    assert start_time != False, f"Detecting Rising Edge Timed Out"
    end_time = await detect_rising_edge(dut, 1e7)
    assert end_time != False, f"Detecting Rising Edge Timed Out"

    period_time = end_time - start_time
    period_frequency = 1 / period_time * 1_000_000_000 # nanoseconds to seconds
    dut._log.info(f"Period: {period_time} ns")

    # Check if the PWM operates at the 3 kHZ ± 1% tolerance
    min_frequency = 2970
    max_frequency = 3030
    assert min_frequency <= period_frequency <= max_frequency, f"Frequency out of 3 kHZ ± 1% tolerance: {period_frequency:.2f} Hz"

    dut._log.info("PWM Frequency test completed successfully")

# Measure the time the signal is high (high_time = t_falling_edge - t_rising_edge).
# Duty Cycle = (high_time / period) * 100%
@cocotb.test()
async def test_pwm_duty(dut):
    # Write your test here
    dut._log.info("PWM Duty Cycle test started.")

    # Set the clock period to 100 ns or 10 MHz
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())
    
    # Reset
    sclk = 0; ncs = 1; bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    
    dut.rst_n.value = 0
    dut.ena.value = 1
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # Enable PWM output and PWM mode
    dut._log.info("Enabling PWM ouput and mode...")
    await send_spi_transaction(dut, 1, 0x00, 0x01) # Write 1 to enable output
    await send_spi_transaction(dut, 1, 0x02, 0x01) # Write 1 to enable PWM mode

    # Measure the time between two rising edges of the PWM signal 
    pwm_signal = dut.uo_out[0] # Change the index to whatever pin is enabled above

    ###########################################################################################################################################
    # Test 0% duty cycle edge case
    dut._log.info("Testing 0% duty cycle...")
    await send_spi_transaction(dut, 1, 0x04, 0x00) # Set 0% duty cycle
    await ClockCycles(dut.clk, 1000)
    assert pwm_signal.value == 0, f"Expected duty cycle: 0%, Measured duty cycle: {pwm_signal.value}"

    ###########################################################################################################################################
    # Test 50% duty cycle
    dut._log.info("Testing 50% duty cycle...")
    await send_spi_transaction(dut, 1, 0x04, 0x80)

    # Give the design time to stabilize
    await ClockCycles(dut.clk, 1000)

    # Find period (Frequency already tested above so no need to do it here)
    start_time = await detect_rising_edge(dut, 1e7)
    assert start_time != False, f"Detecting Rising Edge Timed Out"
    end_time = await detect_rising_edge(dut, 1e7)
    assert end_time != False, f"Detecting Rising Edge Timed Out"

    period_time = end_time - start_time

    high_start_time = await detect_rising_edge(dut, 1e7)
    assert high_start_time != False, f"Detecting Rising Edge Timed Out"
    high_end_time = await detect_falling_edge(dut, 1e7)
    assert high_end_time != False, f"Detecting Rising Edge Timed Out"

    high_end_time = cocotb.utils.get_sim_time(units="ns")

    high_time = high_end_time - high_start_time
    measured_duty_cycle = (high_time / period_time) * 100

    # Check if the PWM duty cycle for 50% is within ± 10% tolerance
    min_duty_cycle = 495
    max_duty_cycle = 505
    assert min_duty_cycle <= measured_duty_cycle * 10 <= max_duty_cycle, f"Expected duty cycle: 50%, Actual duty cycle: {measured_duty_cycle}%"
    dut._log.info(f"Intermediate value 50% test passed successfuly !")

    ###########################################################################################################################################
    # Test 100% duty cycle edge case
    dut._log.info("Testing 100% duty cycle...")
    await send_spi_transaction(dut, 1, 0x04, 0xFF) # Set 100% duty cycle
    await ClockCycles(dut.clk, 1000)
    assert pwm_signal.value == 1, f"Expected duty cycle: 100%, Measured duty cycle: {pwm_signal.value}"

    dut._log.info("PWM Duty Cycle test completed successfully")
