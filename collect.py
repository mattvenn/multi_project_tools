import yaml
import logging
import os
from test_repo import instantiate_module, add_instance_to_upw
import shutil

REQUIRED_KEYS_GROUP = [ "projects" ]
CARAVEL_DIR = "/home/matt/work/asic-workshop/caravel-mph"

def copy_gds(config):
    for project_dir, project_config in zip(config['projects'], config['project_configs']):
        src = os.path.join(project_dir, project_config['gds']['directory'], project_config['gds']['gds_filename'])
        dst = os.path.join(CARAVEL_DIR, 'openlane', 'user_project_wrapper', 'macros', 'gds', project_config['gds']['gds_filename'])
        logging.info("copying %s to %s" % (src, dst))
        shutil.copyfile(src, dst)

        src = os.path.join(project_dir, project_config['gds']['directory'], project_config['gds']['lef_filename'])
        dst = os.path.join(CARAVEL_DIR, 'openlane', 'user_project_wrapper', 'macros', 'lef', project_config['gds']['lef_filename'])
        logging.info("copying %s to %s" % (src, dst))
        shutil.copyfile(src, dst)
        
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

    macro_inst_file  = os.path.join(CARAVEL_DIR, 'openlane', 'user_project_wrapper', 'macro_placement.tcl')
    macro_obst_file  = os.path.join(CARAVEL_DIR, 'openlane', 'user_project_wrapper', 'obstruction.tcl')
    logging.info("creating instantiation file %s" % macro_inst_file)
    logging.info("creating obstruction file %s" % macro_obst_file)
    macro_inst    = open(macro_inst_file, 'w') 
    macro_obst    = open(macro_obst_file, 'w') 
    macro_verilog = ""

    macro_obst.write('set ::env(GLB_RT_OBS)  "')
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
            macro_obst.write ("met5 %d %d %d %d,\n" % (x - obs_border, x - obs_border, macro_w + obs_border, macro_h + obs_border))
            macro_obst.write ("met4 %d %d %d %d,\n" % (x - obs_border, x - obs_border, macro_w + obs_border, macro_h + obs_border))

            macro_verilog += instantiate_module(module_name, instance_name, proj_id)

    macro_obst.write('li1  0     0     2920 3520"\n')

    add_instance_to_upw(macro_verilog)

