
// A *universal* address decoder. Works for any address range at any starting point.

// Checks if the address lies between the base and (higher, inclusive) bound of a range.

// Checks if the input address matches each possible address in the range,
// then outputs the bitwise OR of all these checks.  Some boolean algebra
// shows that it will always optimize down to a minimal form: any bits which
// iterate over their entire binary range become boolean "don't care", leaving
// the other bits to do the match. Thus, for aligned power of 2 address
// ranges, we get the minimal NOT-AND-gate decoder.

// This approach has one caveat: you may have to test, at synthesis time, up
// to all 2^N possible addresses, and store the matches into a vector 2^N bits
// long.  This could take a long time and AFAIK, Verilog implementations have
// a maximum vector width of a few million, so this decoder will break for
// address ranges more than 20-23 bits wide.

// Call it a synthesizer stress-test. ;)

// Even if your CAD tool can handle huge vectors, because we use an int as
// counter, this decoder cannot be guaranteed to work for address ranges
// exceeding 32 bits.

// However, this implementation yields the smallest, fastest logic.

`default_nettype none

module Address_Range_Decoder_Static
#(
    parameter       ADDR_WIDTH          = 0,
    parameter       ADDR_BASE           = 0,
    parameter       ADDR_BOUND          = 0
)
(
    input   wire                        enable,
    input   wire    [ADDR_WIDTH-1:0]    addr,
    output  reg                         hit 
);

    localparam ADDR_COUNT = ADDR_BOUND - ADDR_BASE + 1;
    localparam COUNT_ZERO = {ADDR_COUNT{1'b0}};

    initial begin
        hit = 1'b0;
    end

// --------------------------------------------------------------------

    integer                     i;
    reg     [ADDR_COUNT-1:0]    per_addr_match = COUNT_ZERO;

    // Check each address in base/bound range for match
    always @(*) begin
        for(i = ADDR_BASE; i <= ADDR_BOUND; i = i + 1) begin : addr_decode
            per_addr_match[i-ADDR_BASE] = (addr == i[ADDR_WIDTH-1:0]);
        end
    end

// --------------------------------------------------------------------

    reg hit_raw = 0;

    // Do any of them match, and are we enabled?
    always @(*) begin : is_hit
        hit_raw = | per_addr_match;
        hit     = hit_raw & enable;
    end 

endmodule

