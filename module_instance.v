    MODULE_NAME INSTANCE_NAME(
        `ifdef USE_POWER_PINS
        .vdda1(vdda1),  // User area 1 3.3V power
        .vdda2(vdda2),  // User area 2 3.3V power
        .vssa1(vssa1),  // User area 1 analog ground
        .vssa2(vssa2),  // User area 2 analog ground
        .vccd1(vccd1),  // User area 1 1.8V power
        .vccd2(vccd2),  // User area 2 1.8V power
        .vssd1(vssd1),  // User area 1 digital ground
        .vssd2(vssd2),  // User area 2 digital ground 
        `endif
    
        // interface as user_proj_example.v
        .wb_clk_i   (wb_clk_i),
        .wb_rst_i   (wb_rst_i),
        .wbs_stb_i  (wbs_stb_i),
        .wbs_cyc_i  (wbs_cyc_i),
        .wbs_we_i   (wbs_we_i),
        .wbs_sel_i  (wbs_sel_i),
        .wbs_dat_i  (wbs_dat_i),
        .wbs_adr_i  (wbs_adr_i),
        .wbs_ack_o  (wbs_ack_o),
        .wbs_dat_o  (wbs_dat_o),

        // only provide first 32 bits to reduce wiring congestion
        .la_data_in (la_data_in [31:0]),
        .la_data_out(la_data_out[31:0]),
        .la_oenb    (la_oenb[31:0]),

        // IOs
        .io_in      (io_in),
        .io_out     (io_out),
        .io_oeb     (io_oeb),

        // IRQs
        .irq        (user_irq),

        // Extra clock
        .user_clock2        (user_clock2),
        
        // active input, only connect tristated outputs if this is high
        .active     (la_data_in[32+PROJECT_ID])
        );

