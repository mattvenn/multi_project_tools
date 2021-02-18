import yaml
import logging
import os

REQUIRED_KEYS_GROUP = [ "projects" ]
CARAVEL_MACRO_DIR = "/home/matt/work/asic-workshop/caravel-mph/openlane/user_project_wrapper/macros/"

def copy_gds(config):
    for project_dir, project_config in zip(config['projects'], config['project_configs']):
        logging.info(project_dir)
        src = os.path.join(project_dir, project_config['gds']['directory'], project_config['gds']['gds_filename'])
        dst = os.path.join(CARAVEL_MACRO_DIR, 'gds')
        logging.info("copying %s to %s" % (src, dst))
        src = os.path.join(project_dir, project_config['gds']['directory'], project_config['gds']['lef_filename'])
        dst = os.path.join(CARAVEL_MACRO_DIR, 'lef')
        logging.info("copying %s to %s" % (src, dst))
        
def create_config(config):
    num_macros = len(config['project_configs'])

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
            proj_id = row + column*4

            if proj_id >= num_macros:
                continue
            
            # TODO id is calculated above but also exists in the caravel_test config
            module_name = config['project_configs'][proj_id]['caravel_test']['module_name']
            instance_name = config['project_configs'][proj_id]['caravel_test']['instance_name']

            y = (v_space - macro_h) / 2 + v_space * row
            x = (h_space - macro_w) / 2 + h_space * column
            macro_inst.write("add_macro_placement %s %d %d N\n" % (instance_name, x, y))
            macro_obs.write ("met5 %d %d %d %d,\n" % (x - obs_border, x - obs_border, macro_w + obs_border, macro_h + obs_border))
            macro_obs.write ("met4 %d %d %d %d,\n" % (x - obs_border, x - obs_border, macro_w + obs_border, macro_h + obs_border))

            # TODO this stub also exists in the user_project_wrapper.sub.v
            macro_verilog.write("""
                %s %s(
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
            """ % (module_name, instance_name, proj_id))


    macro_obs.write('li1  0     0     2920 3520"\n')

    logging.info("create macro config for user_project_wrapper with %d projects" % num_macros)
