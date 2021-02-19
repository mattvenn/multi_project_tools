import yaml
import logging
import os
import shutil
from utils import *
from project import Project

REQUIRED_KEYS_GROUP = [ "projects", "caravel", "wrapper" ]

class Collection():

    def __init__(self, args):
        self.args = args
        self.config = parse_config(args.config, REQUIRED_KEYS_GROUP)
        self.projects = []

        if not (len(self.config['projects']) > 0 and len(self.config['projects']) <= 16):
            logging.error("bad number of projects - must be > 0 and <= 16")
            exit(1)

        for project_dir in self.config['projects']:
            if self.args.directory is not None:
                if self.args.directory != project_dir:
                    logging.info("skipping %s" % project_dir)
                    continue
            self.projects.append(Project(args, project_dir, self.config))
             
    def run_tests(self):
        for project in self.projects:

            if self.args.test_all or self.args.test_module:
                project.test_module()

            if self.args.test_all or self.args.prove_wrapper:
                project.prove_wrapper()

            if self.args.test_all or self.args.wrapper_cksum:
                project.wrapper_cksum()

            if self.args.test_all or self.args.test_caravel:
                project.test_caravel()

            if self.args.test_all or self.args.test_gds:
                project.test_gds()

            if self.args.test_all or self.args.test_interface:
                project.test_interface()

    def copy_gds(self):
        for project in self.projects:
            src = os.path.join(project.directory, project.gds_filename)
            dst = os.path.join(self.config['caravel']['root'], 'openlane', 'user_project_wrapper', 'macros', 'gds', os.path.basename(project.gds_filename))
            logging.info("copying %s to %s" % (src, dst))
            shutil.copyfile(src, dst)

            src = os.path.join(project.directory, project.lef_filename)
            dst = os.path.join(self.config['caravel']['root'], 'openlane', 'user_project_wrapper', 'macros', 'lef', os.path.basename(project.lef_filename))
            logging.info("copying %s to %s" % (src, dst))
            shutil.copyfile(src, dst)

    def create_openlane_config(self):
        num_macros = len(self.projects)
        logging.info("create macro config for user_project_wrapper with %d projects" % num_macros)

        width = 2920
        height =  3520

        macro_w = 300
        macro_h = 300

        h_space = width / 4
        v_space = height / 4

        obs_border = 30

        macro_inst_file  = os.path.join(self.config['caravel']['root'], 'openlane', 'user_project_wrapper', 'macro_placement.tcl')
        macro_obst_file  = os.path.join(self.config['caravel']['root'], 'openlane', 'user_project_wrapper', 'obstruction.tcl')
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
                
                module_name     = self.projects[macro_count].config['caravel_test']['module_name']
                instance_name   = self.projects[macro_count].config['caravel_test']['instance_name']
                proj_id         = self.projects[macro_count].config['caravel_test']['id']

                y = (v_space - macro_h) / 2 + v_space * row
                x = (h_space - macro_w) / 2 + h_space * column
                macro_inst.write("add_macro_placement %s %d %d N\n" % (instance_name, x, y))
                macro_obst.write ("met5 %d %d %d %d,\n" % (x - obs_border, x - obs_border, macro_w + obs_border, macro_h + obs_border))
                macro_obst.write ("met4 %d %d %d %d,\n" % (x - obs_border, x - obs_border, macro_w + obs_border, macro_h + obs_border))

                macro_verilog += instantiate_module(module_name, instance_name, proj_id)

        macro_obst.write('li1  0     0     2920 3520"\n')

        user_project_wrapper_path = os.path.join(self.config['caravel']['rtl_dir'], "user_project_wrapper.v")
        add_instance_to_upw(macro_verilog, user_project_wrapper_path)

