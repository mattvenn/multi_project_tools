import yaml
import logging
import os
from test_repo import instantiate_module, add_instance_to_upw

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
    logging.info("create macro config for user_project_wrapper with %d projects" % num_macros)

    width = 2920
    height =  3520

    macro_w = 300
    macro_h = 300

    h_space = width / 4
    v_space = height / 4

    obs_border = 30

    macro_inst    = open("macro_placement.tcl", 'w') 
    macro_obs     = open("obstruction.tcl" , 'w') 
    macro_verilog = ""

    macro_obs.write('set ::env(GLB_RT_OBS)  "')
    for column in range(4):
        for row in range(4):
            macro_count = row + column*4

            if macro_count >= num_macros:
                continue
            
            module_name = config['project_configs'][macro_count]['caravel_test']['module_name']
            instance_name = config['project_configs'][macro_count]['caravel_test']['instance_name']
            proj_id = config['project_configs'][macro_count]['caravel_test']['id']

            y = (v_space - macro_h) / 2 + v_space * row
            x = (h_space - macro_w) / 2 + h_space * column
            macro_inst.write("add_macro_placement %s %d %d N\n" % (instance_name, x, y))
            macro_obs.write ("met5 %d %d %d %d,\n" % (x - obs_border, x - obs_border, macro_w + obs_border, macro_h + obs_border))
            macro_obs.write ("met4 %d %d %d %d,\n" % (x - obs_border, x - obs_border, macro_w + obs_border, macro_h + obs_border))

            macro_verilog += instantiate_module(module_name, instance_name, proj_id)

    macro_obs.write('li1  0     0     2920 3520"\n')

    add_instance_to_upw(macro_verilog)

