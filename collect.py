import yaml
import logging
import os
import copy
import shutil
from utils import *
from project import Project

REQUIRED_KEYS_GROUP = [ "projects", "caravel", "wrapper", "openlane" ]

class Collection():

    def __init__(self, args):
        self.args = args
        self.config = parse_config(args.config, REQUIRED_KEYS_GROUP)
        self.projects = []

        if not (len(self.config['projects']) > 0 and len(self.config['projects']) <= 16):
            logging.error("bad number of projects - must be > 0 and <= 16")
            exit(1)

        # if --project is given, skip others
        for project_dir in self.config['projects']:
            project = Project(args, project_dir, self.config)
            if self.args.project is not None:
                if self.args.project != project.id:
                    continue
            self.projects.append(project)
   
        # create duplicate projects, only works with --project for a single project
        if args.duplicate:
            # requires project id
            if self.args.project is None:
                logging.error("provide the project ID to duplicate with --project")

            # make the copies
            for i in range(args.duplicate):
                dup_project = copy.deepcopy(self.projects[0])
                dup_project.id += i + 1
                dup_project.config['caravel_test']['instance_name'] += str(dup_project.id)
                self.projects.append(dup_project)

        # assert ids are unique
        ids = [project.id for project in self.projects]
        if len(ids) != len(set(ids)):
            logging.error("not all project ids are unique: %s" % ids)
            exit(1)
             
    def run_tests(self):
        for project in self.projects:
            project.run_tests()

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
        includes_file    = os.path.join(self.config['caravel']['rtl_dir'], 'user_project_includes.v')

        logging.info("creating instantiation %s" % macro_inst_file)
        logging.info("creating obstruction   %s" % macro_obst_file)
        logging.info("creating includes      %s" % includes_file)

        macro_inst_fh    = open(macro_inst_file, 'w') 
        macro_obst_fh    = open(macro_obst_file, 'w') 
        includes_fh      = open(includes_file,   'w')
        macro_verilog = ""

        macro_obst_fh.write('set ::env(GLB_RT_OBS)  "')
        for column in range(4):
            for row in range(4):
                macro_count = row + column*4

                if macro_count >= num_macros:
                    continue
                
                module_name     = self.projects[macro_count].config['caravel_test']['module_name']
                instance_name   = self.projects[macro_count].config['caravel_test']['instance_name']
                proj_id         = self.projects[macro_count].id

                y = (v_space - macro_h) / 2 + v_space * row
                x = (h_space - macro_w) / 2 + h_space * column
                macro_inst_fh.write("add_macro_placement %s %d %d N\n" % (instance_name, x, y))
                macro_obst_fh.write ("met5 %d %d %d %d,\n" % (x - obs_border, y - obs_border, macro_w + obs_border, macro_h + obs_border))
                macro_obst_fh.write ("met4 %d %d %d %d,\n" % (x - obs_border, y - obs_border, macro_w + obs_border, macro_h + obs_border))

                macro_verilog += instantiate_module(module_name, instance_name, proj_id, self.config['wrapper']['instance'])

        macro_obst_fh.write('li1  0     0     2920 3520"\n')

        user_project_wrapper_path = os.path.join(self.config['caravel']['rtl_dir'], "user_project_wrapper.v")
        add_instance_to_upw(macro_verilog, user_project_wrapper_path, self.config['wrapper']['upw_template'])

        paths = []
        for project in self.projects:

            # copy project to caravel rtl
            # couldn't get yosys to read include file to work unless the files are below Caravel root directory
            project.copy_project_to_caravel_rtl()

            # create include file 
            includes_fh.write("// %s\n" % project)
            for path in project.get_module_source_paths(absolute=False):
                path = os.path.join(os.path.basename(project.directory), path)
                includes_fh.write('`include "%s"\n' % path)

        # copy the local config.tcl file 
        src = 'config.tcl'
        dst = os.path.join(self.config['caravel']['root'], 'openlane', 'user_project_wrapper', 'config.tcl')
        shutil.copyfile(src, dst)

    """
    * generate an index.md with a section for each project
        - title, author, description, link, picture
    * could also create the info.yaml file for efabless
    * tile all images for final image
    """
    def generate_docs(self):
        fh = open("index.md", 'w')
        fh.write("# Multi Project Index\n\n")
        fh.write("This index was made with [multi project tools](https://github.com/mattvenn/multi_project_tools)\n\n")
        try_mkdir(self.config["docs"]["pic_dir"], self.args.force_delete)
        for project in self.projects:
            conf = project.config["project"]
            # copy pic
            pic_src = os.path.join(project.directory, conf["picture"])
            pic_dst = os.path.join(self.config["docs"]["pic_dir"], os.path.basename(conf["picture"]))
            shutil.copyfile(pic_src, pic_dst)

            fh.write("## %s\n\n" % conf["title"])
            fh.write("* Author: %s\n" % conf["author"])
            fh.write("* Github: [%s](%s)\n" % (conf["github"], conf["github"]))
            fh.write("* Description: %s\n\n" % conf["description"])
            fh.write("![%s](%s)\n\n" % (conf["title"], pic_dst))

        logging.info("wrote index.md")
