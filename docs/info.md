<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

This is a SPI-controlled PWM peripheral. It operates at **10 MHz** and uses SPI communication at **\~100 KHz** to configure registers of the PWM.

In order to do so, the SPI peripheral takes in three signals :

- **SCLK (Serial Clock)**, Clock signal from the controller
- **nCS (Chip select)**, Signals whether or not to enable communication between the controller and the peripheral.
- **COPI (Controller Out Peripheral In)**, This essentially is the 16 bistream of data that the spi peripheral takes in and uses to configure the pwm peripheral.

and through COPI, the SPI peripheral writes data to the corresponding registers of the PWM peripheral. The available settings are :

- Enable Outputs
- Enable PWMs
- Set the Duty cycles

And the input 16 bitstream from COPI to the SPI peripheral is in the format :

- Read/Write (1 bit)
- Address (7 bit)
- Data (8 bit)

**Note:** Only write operations go through, read operations are ignored.

## How to test

Navigate to the /test directory and run Cocotb simulations with the test itself being written in the `test.py` file. In order to do so, run the MakeFile using command `make -B`. To see the waveform, run the generated `tb.vcd` file along with `tb.gtkw` with command `gtkwave tb.vcd tb.gtkw`.

## External hardware

This design relies on a clock source and an external SPI controller, and is comprised of a SPI Peripheral and PWM Peripheral.
