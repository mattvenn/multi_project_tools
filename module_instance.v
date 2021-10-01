    MODULE_NAME INSTANCE_NAME(
        `ifdef USE_POWER_PINS
        .vccd1(vccd1),  // User area 1 1.8V power
        .vssd1(vssd1),  // User area 1 digital ground
        `endif
    
        // interface as user_proj_example.v
        .wb_clk_i   (wb_clk_i),

        // only provide first 32 bits to reduce wiring congestion
        .la_data_in (la_data_in [31:0]),
        .la_data_out(la_data_out[31:0]),
        .la_oenb    (la_oenb[31:0]),

        // IOs
        .io_in      (io_in),
        .io_out     (io_out),
        .io_oeb     (io_oeb),

        // active input, only connect tristated outputs if this is high
        .active     (la_data_in[32+PROJECT_ID])
        );

