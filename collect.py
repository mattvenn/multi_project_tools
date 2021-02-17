import yaml
import logging
REQUIRED_KEYS_GROUP = [ "projects" ]


def create_config(config, args):
    num_macros = 8
    width = 2920
    height =  3520

    macro_w = 300
    macro_h = 300

    h_space = width / 4
    v_space = height / 4

    obs_border = 30

    macro_inst    = open("macro_placement.tcl", 'w') 
    macro_obs     = open("obstruction.tcl" , 'w') 
    macro_verilog = open("macro_verilog.v" , 'w') 

    macro_obs.write('set ::env(GLB_RT_OBS)  "')
    for column in range(4):
        for row in range(4):
            y = (v_space - macro_h) / 2 + v_space * row
            x = (h_space - macro_w) / 2 + h_space * column
            proj_id = row + column*4
            macro_inst.write("add_macro_placement proj_%d %d %d N\n" % (proj_id, x, y))
            macro_obs.write ("met5 %d %d %d %d,\n" % (x - obs_border, x - obs_border, macro_w + obs_border, macro_h + obs_border))
            macro_obs.write ("met4 %d %d %d %d,\n" % (x - obs_border, x - obs_border, macro_w + obs_border, macro_h + obs_border))

            macro_verilog.write("""
                wrapper proj_%d(
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
                    .active     (la_data_in[32+%d])
                    );
            """ % (proj_id, proj_id))

    macro_obs.write('li1  0     0     2920 3520"\n')

    logging.info("create macro config for user_project_wrapper with %d projects" % num_macros)
