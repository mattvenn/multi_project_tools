from utils import *
import subprocess
import copy
from project import Project

REQUIRED_KEYS_GROUP = ["projects", "caravel", "wrapper", "lvs"]


class Collection(object):

    def __init__(self, args):
        self.args = args
        self.config = parse_config(args.config, REQUIRED_KEYS_GROUP)
        self.projects = []

        if not (0 < len(self.config['projects']) <= 16):
            logging.error("bad number of projects - must be > 0 and <= 16")
            exit(1)

        # if --project is given, skip others
        for project_dir in self.config['projects']:
            project = Project(args, project_dir, self.config)
            if self.args.project is not None:
                if self.args.project != project.id:
                    continue
            self.projects.append(project)
   
        # fill space with duplicated projects
        if args.fill and args.fill > len(self.projects):
            num_real_projects = len(self.projects)
            # make the copies
            for i in range(len(self.projects), args.fill):
                dup_project = copy.deepcopy(self.projects[i % num_real_projects])
                dup_project.id = i
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

    def sync_repos(self):
        for project in self.projects:
            project.sync_repo()

    def copy_gds(self):
        lef_dir = os.path.join(self.config['caravel']['root'], 'openlane', 'user_project_wrapper', 'macros', 'lef')
        gds_dir = os.path.join(self.config['caravel']['root'], 'openlane', 'user_project_wrapper', 'macros', 'gds')
        try_mkdir(lef_dir, self.args.force_delete)
        try_mkdir(gds_dir, self.args.force_delete)

        for project in self.projects:
            src = os.path.join(project.directory, project.gds_filename)
            dst = os.path.join(gds_dir, os.path.basename(project.gds_filename))
            logging.info("copying %s to %s" % (src, dst))
            shutil.copyfile(src, dst)

            src = os.path.join(project.directory, project.lef_filename)
            dst = os.path.join(lef_dir, os.path.basename(project.lef_filename))
            logging.info("copying %s to %s" % (src, dst))
            shutil.copyfile(src, dst)

            # gl
            project.copy_gl()

    def create_openlane_config(self):
        num_macros = len(self.projects)
        logging.info("create macro config for user_project_wrapper with %d projects" % num_macros)

        width = 2920
        height =  3520

        macro_w = self.config['tests']['gds']['width']
        macro_h = self.config['tests']['gds']['height']

        # area to leave around the edge for routing
        h_edge = 344 # was 344
        v_edge = 464 # was 464

        # calculate space between the macros
        h_space = (width  - 2 * h_edge - (4 * macro_w)) / 3
        v_space = (height - 2 * v_edge - (4 * macro_h)) / 3

        macro_inst_file  = os.path.join(self.config['caravel']['root'], 'openlane', 'user_project_wrapper', 'macro.cfg')
        includes_file    = os.path.join(self.config['caravel']['rtl_dir'], 'user_project_includes.v')

        logging.info("creating instantiation %s" % macro_inst_file)
        logging.info("creating includes      %s" % includes_file)

        macro_inst_fh    = open(macro_inst_file, 'w') 
        includes_fh      = open(includes_file,   'w')
        macro_verilog = ""

        for column in range(4):
            for row in range(4):
                macro_count = row + column*4

                if macro_count >= num_macros:
                    continue
                
                module_name     = self.projects[macro_count].config['caravel_test']['module_name']
                instance_name   = self.projects[macro_count].config['caravel_test']['instance_name']
                proj_id         = self.projects[macro_count].id

                y = v_edge + (v_space + macro_h)  * row
                x = h_edge + (h_space + macro_w)  * column

                # TODO HACK wrapped_qarma is bigger. should read the size out of the gds and centre it
                if module_name == "wrapped_qarma":
                    macro_inst_fh.write("%s %d %d N\n" % (instance_name, x - 30, y - 30))
                else:
                    macro_inst_fh.write("%s %d %d N\n" % (instance_name, x, y))

                macro_verilog += instantiate_module(module_name, instance_name, proj_id, self.config['wrapper']['instance'])

        user_project_wrapper_path = os.path.join(self.config['caravel']['rtl_dir'], "user_project_wrapper.v")
        add_instance_to_upw(macro_verilog, user_project_wrapper_path, self.config['wrapper']['upw_template'])

        for project in self.projects:

            # copy project to caravel rtl
            # couldn't get yosys to read include file to work unless the files are below Caravel root directory
            project.copy_project_to_caravel_rtl()

            # create include file - only need top module as everything is blackboxed in config.tcl
            includes_fh.write("// %s\n" % project)
            top_module = project.get_top_module()
            top_path = os.path.join(os.path.basename(project.directory), top_module)
            includes_fh.write('`include "%s"\n' % top_path)

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
            fh.write("* commit: %s\n" % project.get_git_version())
            fh.write("* Description: %s\n\n" % conf["description"])
            fh.write("![%s](%s)\n\n" % (conf["title"], pic_dst))

        logging.info("wrote index.md")
