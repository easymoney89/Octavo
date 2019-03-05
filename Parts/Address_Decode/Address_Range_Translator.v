
// Translates a non-consecutive sequence of address bits into a consecutive
// one, so they can be used "as expected" with other addressed components
// (muxes, RAMs, etc...). ***Consumes no hardware.***

// Since address ranges might not start at power-of-2 boundaries and may not
// span power-of-2 size blocks, the Least-Significant bits might not
// necessarily be consecutive, exhaustive, and starting at zero: their order
// can be rotated by the offset to the nearest power-of-2 boundary. Thus, we
// construct a translation table that should hopefully optimize down to mere
// rewiring of inputs or internal logic.

// Typically, you'll need this alongside an Address_Range_Decoder module.

`default_nettype none

module Address_Range_Translator
#(
    parameter       ADDR_COUNT          = 0,
    parameter       ADDR_BASE           = 0,
    parameter       ADDR_WIDTH          = 0,
    parameter       REGISTERED          = 0
)
(
    // Clock is not always used, depending on REGISTERED parameter
    // verilator lint_off UNUSED
    input   wire                        clock,
    // verilator lint_on  UNUSED
    input   wire    [ADDR_WIDTH-1:0]    raw_address,
    output  reg     [ADDR_WIDTH-1:0]    translated_address
);

// --------------------------------------------------------------------------

    // ECL XXX *********  DO NOT MOVE! ************

    // Doing the obvious thing of placing a register at the output prevents
    // Quartus from reducing the translation table to simple LUT configuration
    // change or input rewiring, and creates a small RAM, which works too
    // slowly. It appears the translation table trick only works when
    // outputting straight into a RAM.

    reg     [ADDR_WIDTH-1:0]    cooked_address = 0;

    generate
        if (REGISTERED == 1) begin
            always @(posedge clock) begin
                cooked_address <= raw_address;
            end
        end
        else begin
            always @(*) begin
                cooked_address = raw_address;
            end
        end
    endgenerate

// --------------------------------------------------------------------------

    localparam ADDR_DEPTH = 2**ADDR_WIDTH;

    // Otherwise, it might end up as a Block RAM at random, and the logic
    // cannot get optimized.

    (* ramstyle = "logic" *) 
    reg     [ADDR_WIDTH-1:0]    translation_table [ADDR_DEPTH-1:0];

    // Translation table entry index.
    // When initializing j, we must zero-pad the narrow address 
    // up to integer width.

    integer j;
    localparam                  INTEGER_WIDTH   = 32;
    localparam                  PADSIZE         = INTEGER_WIDTH - ADDR_WIDTH;
    localparam [PADSIZE-1:0]    J_PADDING       = {PADSIZE{1'b0}};

    // Just a loop counter, over the number of addresses to translate.
    integer i;

    initial begin
        // In the case where ADDR_COUNT < ADDR_DEPTH, make sure all entries are defined
        // This happens for a single entry: ADDR_WIDTH is artificially kept at 1 instead of 0
        for(i = 0; i < ADDR_DEPTH; i = i + 1) begin
            translation_table[i] = 'h0;
        end

        // In the case of a single entry, the LSB (j) will be either 1 or zero,
        // but always translates to 0, thus this should optimize away.
        j = {J_PADDING, ADDR_BASE[ADDR_WIDTH-1:0]};
        for(i = 0; i < ADDR_COUNT; i = i + 1) begin
            translation_table[j] = i[ADDR_WIDTH-1:0];
            j = (j + 1) % ADDR_DEPTH; // Force wrap-around
        end
    end

// --------------------------------------------------------------------------

    always @(*) begin
        translated_address = translation_table[cooked_address];
    end

endmodule

