    MODULE_NAME INSTANCE_NAME(
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
        .la_oen     (la_oen[31:0]),

        // IOs
        .io_in      (io_in),
        .io_out     (io_out),
        .io_oeb     (io_oeb),
        
        // active input, only connect tristated outputs if this is high
        .active     (la_data_in[32+PROJECT_ID])
        );

