`default_nettype none

module spi_peripheral(
    input wire clk,
    input wire rst_n,

    // SPI Interface
    input wire COPI,    // Serial data output from controller
    input wire nCS,     // Negative chip select
    input wire SCLK,    // Serial Clock (Clock signal from controller)

    // PWM Inputs
    output reg [7:0] en_reg_out_7_0,      // Enable outputs on uo_out[7:0]
    output reg [7:0] en_reg_out_15_8,     // Enable outputs on uio_out[7:0]
    output reg [7:0] en_reg_pwm_7_0,      // Enable PWM for uo_out[7:0]
    output reg [7:0] en_reg_pwm_15_8,     // Enable PWM for uio_out[7:0]
    output reg [7:0] pwm_duty_cycle       // PWM Duty Cycle (0x00 = 0%, 0xFF = 100%)
);
    // SPI Interface "Key Features"
    reg read_write_bit;
    reg [6:0] address;
    reg [7:0] data;

    // CDC
    reg SCLK_sync1, SCLK_sync2;
    reg SCLK_delay_by_1;
    reg SCLK_rising_edge;
    
    reg COPI_sync1, COPI_sync2;

    reg nCS_sync1, nCS_sync2;
    reg nCS_delay_by_1;
    reg nCS_falling_edge;

    // Transaction state
    reg [4:0] transaction_bit_counter; // Indicate whether its reading the read_write bit, the address bits or the data bits
    reg transaction_active;
    reg transaction_ready;

    // Edge detection and delays
    assign SCLK_rising_edge = SCLK_sync2 & ~SCLK_delay_by_1;
    assign nCS_falling_edge = ~nCS_sync2 & nCS_delay_by_1;

    // Signal Synchronization (for CDC)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            read_write_bit <= 1'b0;
            address <= 7'b0;
            data <= 8'b0;

            SCLK_sync1 <= 1'b0; SCLK_sync2 <= 1'b0;
            COPI_sync1 <= 1'b0; COPI_sync2 <= 1'b0;
            nCS_sync1 <= 1'b0; nCS_sync2 <= 1'b0;

            transaction_bit_counter <= 4'b0;
            transaction_active <= 1'b0;
            transaction_ready <= 1'b0;

            en_reg_out_7_0 <= 8'b0;
            en_reg_out_15_8 <= 8'b0;
            en_reg_pwm_7_0 <= 8'b0;
            en_reg_pwm_15_8 <= 8'b0;
            pwm_duty_cycle <= 8'b0;

        end else begin
            SCLK_sync1 <= SCLK;
            SCLK_sync2 <= SCLK_sync1;

            COPI_sync1 <= COPI;
            COPI_sync2 <= COPI_sync1;

            nCS_sync1 <= nCS;
            nCS_sync2 <= nCS_sync1;

            ////////////////////////////////////////////////////////////////////////////////////
            // Edge detection and delays SCLK and nCS signal by one cycle
            SCLK_delay_by_1 <= SCLK_sync2;
            nCS_delay_by_1 <= nCS_sync2;

            ////////////////////////////////////////////////////////////////////////////////////
            // Transactions starts on nCS falling edge
            if (nCS_falling_edge) begin
                transaction_bit_counter <= 4'b0;
                transaction_active <= 1'b1;
                transaction_ready <= 1'b0;
            end

            // If the nCS signal goes high, end the transaction
            else if (nCS_sync2) begin
                transaction_active <= 1'b0;
                
                // Check if the correct number of bits (16) was received
                if (transaction_bit_counter == 16) begin
                    transaction_ready <= 1'b1;
                end
                
                // If the number of bits is not 16, the transaction is invalid
                else begin
                    transaction_ready <= 1'b0;    
                end
            end

            // Increment bit counter for every SCLK rising edge 
            else if (SCLK_rising_edge && transaction_active) begin
                if (transaction_bit_counter < 16) begin
                    transaction_bit_counter <= transaction_bit_counter + 1;
                end
            end

            ////////////////////////////////////////////////////////////////////////////////////
            // Data Capture
            if (SCLK_rising_edge && transaction_active) begin
                // R/W Bit (1b)
                if (transaction_bit_counter == 1) begin
                    read_write_bit <= COPI_sync2;
                end

                // Address (7b)
                else if ((transaction_bit_counter >= 2) && (transaction_bit_counter <= 8)) begin
                    address <= {address[5:0], COPI_sync2};
                end

                // Data (8b)
                else if ((transaction_bit_counter >= 9) && (transaction_bit_counter <= 16)) begin
                    data <= {data[6:0], COPI_sync2};
                end
            end

            ////////////////////////////////////////////////////////////////////////////////////
            // Update PWM Peripheral after receiving data
            if (address < 7'h04) begin
                // From Register Map
                case (address)
                    7'h00: en_reg_out_7_0 <= data;
                    7'h01: en_reg_out_15_8 <= data;
                    7'h02: en_reg_pwm_7_0 <= data;
                    7'h03: en_reg_pwm_15_8 <= data;
                    7'h04: pwm_duty_cycle <= data;
                    default: ;// Ignore if the address is something else
                endcase
            end
        end
    end

endmodule