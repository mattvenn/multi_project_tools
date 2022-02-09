from utils import *
import subprocess
import copy
from project import Project, SharedProject
from codegen.caravel_codegen import generate_openlane_files
from codegen.allocator import allocate_macros

REQUIRED_KEYS_GROUP = ["interfaces", "openram_support", "configuration", "docs", "projects"]
REQUIRED_KEYS_LOCAL = ["project_directory", "caravel", "env", "lvs"]

def merge_two_dicts(x, y):
    z = x.copy()   # start with keys and values of x
    z.update(y)    # modifies z with keys and values of y
    return z

class Collection(object):

    def __init__(self, args):
        self.args = args
        project_config = parse_config(args.config, REQUIRED_KEYS_GROUP)
        try:
            local_config = parse_config(args.local_config, REQUIRED_KEYS_LOCAL)
        except FileNotFoundError:
            logging.error("%s local config not found. Copy matt_local.yaml to local.yaml and adjust as necessary" % args.local_config)
            exit(1)

        self.config = merge_two_dicts(project_config, local_config)
        self.projects = []

        if not (0 < len(self.config['projects']) <= 16):
            logging.error("bad number of projects - must be > 0 and <= 16")
            exit(1)

        # build the list of projects
        for project_info in self.config['projects'].values():
            repo = project_info["repo"]
            commit = project_info["commit"]
            
            required_interfaces = list(self.config['interfaces']['required'].keys())
            project = Project(args, repo, commit, required_interfaces, self.config)

            # if --project is given, skip others
            if self.args.project is not None:
                if self.args.project != project.id:
                    continue

            # start from a given project if --from is given
            if self.args.test_from is not None:
                if project.id < self.args.test_from:
                    continue

            # append
            self.projects.append(project)
   

        self.shared_projects = []
        for project_info in self.config['openram_support']['projects'].values():
            repo = project_info["repo"]
            commit = project_info["commit"]
            project = SharedProject(args, repo, commit, self.config)
            self.shared_projects.append(project)
            logging.info(project)
            
        # fill space with duplicated projects
        if args.fill and args.fill > len(self.projects):
            num_real_projects = len(self.projects)
            # make the copies
            for i in range(len(self.projects), args.fill):
                dup_project = copy.deepcopy(self.projects[i % num_real_projects])
                dup_project.id = i
                # instance names are generated now
                #      dup_project.config['caravel_test']['instance_name'] += str(dup_project.id)
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
            **self.config['interfaces']['required'], 
            **self.config['interfaces']['optional']
        }

    def run_tests(self):
        for project in self.projects + self.shared_projects:
            project.run_tests()

    # TODO refactor so project konws how to copy gds and lef, then do the same as rtl, gl, test etc.
    def copy_all_gds(self):
        macros_dir = os.path.join(self.config['caravel']['root'], 'openlane', 'user_project_wrapper', 'macros', 'lef')
        lef_dir = os.path.join(self.config['caravel']['root'], 'openlane', 'user_project_wrapper', 'macros', 'lef')
        gds_dir = os.path.join(self.config['caravel']['root'], 'openlane', 'user_project_wrapper', 'macros', 'gds')
        # macros directory might not exist
        os.makedirs(macros_dir, exist_ok=True)

        try_mkdir(lef_dir, self.args.force_delete)
        try_mkdir(gds_dir, self.args.force_delete)

        for project in self.projects + self.shared_projects:
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

    def copy_all_project_files_to_caravel(self):
        ### copy out rtl ###
        for project in self.projects + self.shared_projects:
            project.copy_project_files_to_caravel()

    def annotate_image(self):
        final_gds_file = os.path.join(self.config['caravel']['root'], 'gds', 'user_project_wrapper.gds.gz')
        # dump a 2000x2000 image with klayout to pics/multi_macro.png, check the dump_pic.rb file
        cmd = "klayout -l caravel.lyp %s -r dump_pic.rb -c klayoutrc" % final_gds_file
        logging.info(cmd)
        os.system(cmd)
        image_file = os.path.join('pics', 'multi_macro.png')
        from PIL import Image, ImageFont, ImageDraw
        font_author = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans.ttf", 27)
        font_title = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans.ttf", 22)
        img = Image.open(image_file)
        draw = ImageDraw.Draw(img)

        px_per_um = self.config['docs']['px_per_um']
        macro_border = self.config['docs']['macro_border']
        user_width = self.width * px_per_um
        user_height = self.height * px_per_um

        x_offset = (2000 - user_width) / 2
        y_offset = (2000 - user_height) / 2

        logging.info("annotating image")
        for project in self.projects + self.shared_projects:
            logging.info(project)
            macro_x, macro_y = project.get_macro_pos_from_caravel()
            x = x_offset + macro_x * px_per_um - macro_border
            y = 2000 - (y_offset + macro_y * px_per_um - macro_border) # flip, gds is bottom left 0,0, png is top left 0,0
            # takes a while
            macro_w, macro_h = project.get_gds_size()
            macro_w = macro_w * px_per_um + 2*macro_border
            macro_h = macro_h * px_per_um + 2*macro_border

            draw.text((x,y-macro_h-70), project.author, (0,0,0), font=font_author)
            draw.text((x,y-macro_h-40), project.title, (0,0,0), font=font_title)

            draw.line((x,           y          , x + macro_w, y          ), fill=(0,0,0), width=2)
            draw.line((x + macro_w, y          , x + macro_w, y - macro_h), fill=(0,0,0), width=2)
            draw.line((x + macro_w, y - macro_h, x          , y - macro_h), fill=(0,0,0), width=2)
            draw.line((x          , y - macro_h, x          , y          ), fill=(0,0,0), width=2)

        annotated_image_file = os.path.join('pics', 'multi_macro_annotated.png')
        img.save(annotated_image_file)


    def get_macro_pos_from_caravel(self):
        for project in self.projects + self.shared_projects:
            print(project.get_macro_pos_from_caravel())

    def create_openlane_config(self):
        logging.warning("macros.cfg is not currently being automatically generated - please make sure this file is up to date")

        macro_inst_file = os.path.join(self.config['caravel']['root'], 'openlane', 'user_project_wrapper', 'macro.cfg')
        # macro placement is broken. For now, if there is no file just put the openram stuff in place
        if not os.path.exists(macro_inst_file):
            if self.args.openram:
                logging.warning("creating basic macros.cfg with openram support")
                with open(macro_inst_file, "w") as f:
                    f.write(f"openram_1kB 344 475.5 N\n")
                    f.write(f"wb_openram_wrapper 1085 480 N\n")
                    f.write(f"wb_bridge_2way 1340 480 N\n")

        ### generate user wrapper and include ###
        user_project_wrapper_path = os.path.join(self.config['caravel']['rtl_dir'], "user_project_wrapper.v")
        user_project_includes_path = os.path.join(self.config['caravel']['rtl_dir'], "user_project_includes.v")
        caravel_includes_path =      os.path.join(self.config['caravel']['rtl_dir'], "uprj_netlists.v")
        openlane_config_path = os.path.join(self.config['caravel']['root'], 'openlane', 'user_project_wrapper', "obstruction.tcl")
        generate_openlane_files(
            self.projects, 
            self.shared_projects,
            self.interface_definitions, 
            user_project_wrapper_path, 
            user_project_includes_path,
            caravel_includes_path,
            openlane_config_path,
            self.args.openram,
            self.args.gate_level,
            self.config
        )


        # copy the local config.tcl file 
        src = 'config.tcl'
        dst = os.path.join(self.config['caravel']['root'], 'openlane', 'user_project_wrapper', 'config.tcl')
        logging.info(f"copying {src} to {dst}")
        shutil.copyfile(src, dst)

            
    """ totally broken
    def allocate_macros(self):
        # allocate macros and generate macro.cfg
        allocation = allocate_macros(
            design_size_x = self.width,
            design_size_y = self.height,
            h_edge = 344,
            v_edge = 464,
            macro_snap = self.config['configuration']['macro_snap'],
            projects = self.projects,
            allocation_policy = "legacy",
            openram = self.args.openram
        )
        return allocation
    """

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
            fh.write("* Github: %s\n" % project.repo)
            fh.write("* commit: %s\n" % project.gitsha)
            fh.write("* Description: %s\n\n" % conf["description"])
            fh.write("![%s](%s)\n\n" % (conf["title"], pic_dst))

        logging.info("wrote index.md")
