from utils import *
import subprocess
import copy
from project import Project, SharedProject
from codegen.caravel_codegen import generate_openlane_files
from codegen.allocator import allocate_macros
from layout_tool import LayoutTool, callback
from functools import partial

REQUIRED_KEYS_GROUP = ["interfaces", "openram_support", "configuration", "docs", "projects"]
REQUIRED_KEYS_LOCAL = ["project_directory", "caravel", "env"]

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
            pos = project_info["pos"]
            
            required_interfaces = list(self.config['interfaces']['required'].keys())
            project = Project(args, repo, commit, pos, required_interfaces, self.config)

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
        if self.args.openram:
            for project_info in self.config['openram_support']['projects'].values():
                repo = project_info["repo"]
                commit = project_info["commit"]
                pos = project_info["pos"]
                project = SharedProject(args, repo, commit, pos, self.config)
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
        lef_dir = os.path.join(self.config['caravel']['root'], 'lef')
        gds_dir = os.path.join(self.config['caravel']['root'], 'gds')

        for project in self.projects + self.shared_projects:
            # gds
            src = os.path.join(project.directory, project.gds_filename)
            dst = os.path.join(gds_dir, os.path.basename(project.gds_filename))
            logging.info("copying %s to %s" % (src, dst))
            shutil.copyfile(src, dst)

            # lef
            src = os.path.join(project.directory, project.lef_filename)
            dst = os.path.join(lef_dir, os.path.basename(project.lef_filename))
            logging.info("copying %s to %s" % (src, dst))
            shutil.copyfile(src, dst)

            # gl
            project.copy_gl()

            # spef, sdc, sdc files
            for optional_file_type in ["spef", "sdc", "sdf"]:
                filename = project.get_optional_file(optional_file_type)
                if filename is not None:
                    src = filename
                    dst = os.path.join(self.config['caravel']['root'], optional_file_type, os.path.basename(filename))
                    logging.info("copying optional file to %s" % dst)
                    shutil.copyfile(src, dst)


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
            macro_x, macro_y, orient = project.get_macro_pos()
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

    def get_macro_pos(self):
        for project in self.projects + self.shared_projects:
            logging.info(project.get_macro_pos())
        
    def get_macro_pos_from_caravel(self):
        for project in self.projects + self.shared_projects:
            logging.info(project.get_macro_pos_from_caravel())

    def create_openlane_config(self):
        self.generate_macro_cfg()
        self.generate_extra_lef_gds_tcl()

        ### generate user wrapper verilog and include files ###
        user_project_wrapper_path = os.path.join(self.config['caravel']['rtl_dir'], "user_project_wrapper.v")
        user_project_includes_path = os.path.join(self.config['caravel']['rtl_dir'], "user_project_includes.v")
        caravel_includes_path =      os.path.join(self.config['caravel']['includes_dir'], "includes.rtl.caravel_user_project")
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

    def generate_macro_cfg(self):
        macro_inst_file = os.path.join(self.config['caravel']['root'], 'openlane', 'user_project_wrapper', 'macro.cfg')
        logging.info("overwriting macros.cfg: %s" % macro_inst_file)
        with open(macro_inst_file, "w") as f:
            for project in self.projects + self.shared_projects:
                x, y, orient = project.get_macro_pos()
                f.write("%s %.2f %.2f %s\n" % (project.instance_name, x, y, orient))
            
    # want to put macros in top level dirs, so now need to generate a bit of tcl that adds the extra lef/def
    def generate_extra_lef_gds_tcl(self):
        extra_lef_gds_file = os.path.join(self.config['caravel']['root'], 'openlane', 'user_project_wrapper', 'extra_lef_gds.tcl')
        logging.info("creating extra_lef_gds tcl: %s" % extra_lef_gds_file)
        with open(extra_lef_gds_file, "w") as f:
            f.write('set ::env(EXTRA_LEFS) "')
            for project in self.projects + self.shared_projects:
                f.write("\\\n	$script_dir/../../lef/%s " % os.path.basename(project.lef_filename))
            f.write('"\n')

            f.write('set ::env(EXTRA_GDS_FILES) "')
            for project in self.projects + self.shared_projects:
                f.write("\\\n	$script_dir/../../gds/%s " % os.path.basename(project.gds_filename))
            f.write('"\n')

    def launch_layout_tool(self, downscale_factor):
        tool = LayoutTool(self, downscale_factor or 1)
        call = partial(callback, tool)
        print(call)
        tool.set_callback(call)
        tool.run()

    """
    * generate an index.md with a section for each project
        - title, author, description, link, picture
    * could also create the info.yaml file for efabless
    * tile all images for final image
    """
    def generate_docs(self):
        git_sha = get_git_sha(".")
        fh = open("index.md", 'w')
        fh.write("""
# Zero to ASIC Group submission MPW5

This ASIC was designed by members of the [Zero to ASIC course](https://zerotoasiccourse.com).

This submission was configured and built by the [multi project tools](https://github.com/mattvenn/multi_project_tools) at commit [%s](https://github.com/mattvenn/multi_project_tools/commit/%s).

    # clone all repos, and include support for shared OpenRAM
    ./multi_tool.py --clone-repos --clone-shared-repos --create-openlane-config --copy-gds --copy-project --openram

    # run all the tests
    ./multi_tool.py --test-all --force-delete

    # build user project wrapper submission
    cd $CARAVEL_ROOT; make user_project_wrapper

    # create docs
    ./multi_tool.py --generate-doc --annotate-image

![multi macro](pics/multi_macro_annotated.png)

# Project Index\n\n""" % (git_sha, git_sha))
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
