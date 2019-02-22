
// Select some inputs from a consecutive, but not power-of-2 aligned,
// address range. This allows us to use the raw memory address to select some
// memory-mapped item.

`default_nettype none

module Translated_Addressed_Mux
#(
    parameter       WORD_WIDTH          = 0,
    parameter       ADDR_WIDTH          = 0, // Full address width
    parameter       INPUT_COUNT         = 0,
    parameter       INPUT_BASE_ADDR     = 0,
    parameter       INPUT_ADDR_WIDTH    = 0, // clog2(INPUT_COUNT)

    // Not for instantiation
    parameter       TOTAL_WIDTH = INPUT_COUNT * WORD_WIDTH
)
(
    // Only LSB used, but full width here for easy system integration
    // verilator lint_off UNUSED
    input   wire    [ADDR_WIDTH-1:0]    addr,
    // verilator lint_on  UNUSED
    input   wire    [TOTAL_WIDTH-1:0]   in, 
    output  wire    [WORD_WIDTH-1:0]    out
);

// --------------------------------------------------------------------------

    wire [INPUT_ADDR_WIDTH-1:0]  addr_translated;

    Address_Range_Translator 
    #(
        .ADDR_COUNT             (INPUT_COUNT),
        .ADDR_BASE              (INPUT_BASE_ADDR),
        .ADDR_WIDTH             (INPUT_ADDR_WIDTH),
        .REGISTERED             (0)
    )
    ART
    (
        .clock                  (1'b0),
        .raw_address            (addr[INPUT_ADDR_WIDTH-1:0]),
        .translated_address     (addr_translated)
    );         

    Addressed_Mux
    #(
        .WORD_WIDTH     (WORD_WIDTH),
        .ADDR_WIDTH     (INPUT_ADDR_WIDTH),
        .INPUT_COUNT    (INPUT_COUNT)
    )
    AM
    (
        .addr           (addr_translated),
        .in             (in),
        .out            (out)
    );

endmodule

