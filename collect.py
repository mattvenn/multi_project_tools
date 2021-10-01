from utils import *
import subprocess
import copy
from project import Project
from codegen.caravel_codegen import generate_openlane_files
from codegen.allocator import allocate_macros

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
        for project_info in self.config['projects'].values():
            print(project_info)
            repo = project_info["repo"]
            commit = project_info["commit"]
            
            ifaces = project_info["interfaces"] + list(self.config["required_interfaces"].keys())

            project = Project(args, repo, commit, ifaces, self.config)
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
            
        self.macro_allocation = {}
        self.width = self.config['configuration']['user_area_width']
        self.height = self.config['configuration']['user_area_height']

        self.interface_definitions = {
            **self.config['interfaces'], 
            **self.config['required_interfaces']
        }

    def run_tests(self):
        for project in self.projects:
            project.run_tests()

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

    def annotate_image(self):
        image_file = os.path.join(self.config['caravel']['root'], 'pics', 'multi_macro.png')
        from PIL import Image, ImageFont, ImageDraw
        font_author = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans.ttf", 27)
        font_title = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans.ttf", 22)
        img = Image.open(image_file)
        draw = ImageDraw.Draw(img)

        # hack TODO better to base this off the relative size of the image and the die
        h_edge = 378
        v_edge = 280
        h_space = 122
        v_space = 185
        macro_h = 220
        macro_w = 220

        for column in range(4):
            for row in range(4):
                macro_count = (3-row) + column*4

                y = v_edge + (v_space + macro_h)  * row
                x = h_edge + (h_space + macro_w)  * column

                title = self.projects[macro_count].config['project']['title']
                author = self.projects[macro_count].config['project']['author']
                draw.text((x,y-70), author, (0,0,0), font=font_author)
                draw.text((x,y-40), title, (0,0,0), font=font_title)

                draw.line((x,           y          , x + macro_w, y          ), fill=(0,0,0), width=2)
                draw.line((x + macro_w, y          , x + macro_w, y + macro_h), fill=(0,0,0), width=2)
                draw.line((x + macro_w, y + macro_h, x          , y + macro_h), fill=(0,0,0), width=2)
                draw.line((x          , y + macro_h, x          , y          ), fill=(0,0,0), width=2)
#                draw.line((x + macro_w, y, x + macro_h, fill=128)
#                draw.line((macro_w, y + macro_h, fill=128)
#                draw.line((0, img.size[1], img.size[0], 0), fill=128)
        img.save("multi_macro_label.png")

    def create_openlane_config(self):
        ### generate user wrapper and include ###
        user_project_wrapper_path = os.path.join(self.config['caravel']['rtl_dir'], "user_project_wrapper.v")
        user_project_includes_path = os.path.join(self.config['caravel']['rtl_dir'], "user_project_includes.v")
        generate_openlane_files(
            self.projects, 
            self.interface_definitions, 
            user_project_wrapper_path, 
            user_project_includes_path
        )

        ### copy out rtl ###
        for project in self.projects:
            project.copy_project_to_caravel_rtl()

        # copy the local config.tcl file 
        src = 'config.tcl'
        dst = os.path.join(self.config['caravel']['root'], 'openlane', 'user_project_wrapper', 'config.tcl')
        print(f"copying {src} to {dst}")
        shutil.copyfile(src, dst)

        # allocate macros and generate macro.cfg
        allocation = allocate_macros(
            design_size_x = self.width,
            design_size_y = self.height,
            h_edge = 344,
            v_edge = 464,
            projects = self.projects,
            allocation_policy = "legacy"
        )

        macro_inst_file = os.path.join(self.config['caravel']['root'], 'openlane', 'user_project_wrapper', 'macro.cfg')
        with open(macro_inst_file, "w") as f:
            for project in self.projects:
                name = project.title
                alloc = allocation[project.id]
                verilog_name = "wrapped_" + name.lower().replace(" ", "_") + "_" + str(project.id)
                print(f"placing {verilog_name} @ {alloc}")
                f.write(f"{verilog_name} {alloc[0]} {alloc[1]} N\n")


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
