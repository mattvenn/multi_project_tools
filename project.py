import subprocess
import gdspy
import shutil
from utils import *
from codegen.caravel_codegen import generate_openlane_files
import os, json

REQUIRED_KEYS_SINGLE = ["project", "caravel_test", "module_test", "wrapper_proof", "openlane", "final"]
REQUIRED_KEYS_SHARED = ["project", "final"]

class BaseProject(object):

    def clone_repo(self):
        clone_repo(self.repo, self.commit, self.directory, self.args.force_delete)

    def get_module_source_paths(self, absolute=True, caravel=False):
        paths = []
        for path in self.config['source']:
            if absolute:
                paths.append(os.path.abspath(os.path.join(self.directory, path)))
            elif caravel:
                paths.append(os.path.join('rtl', os.path.basename(self.directory), path))
            else:
                paths.append(path)
        return paths    

    def copy_project_files_to_caravel(self):
        # RTL
        src = self.directory
        dst = os.path.join(self.system_config['caravel']['rtl_dir'], os.path.basename(self.directory))
        try_copy_tree(src, dst, self.args.force_delete)

        # TEST
        if "caravel_test" in self.config and "waive_caravel" not in self.config['project']:
            src = os.path.join(self.directory, self.config["caravel_test"]["directory"])
            dst = os.path.join(self.system_config['caravel']['test_dir'], self.config["caravel_test"]["directory"])
            try_copy_tree(src, dst, self.args.force_delete)

    def get_macro_pos(self):
        x, y, orient = self.pos.split(' ')
        return(float(x), float(y), orient)

    # parse the macro.cfg file and find our entry, return x, y position
    def get_macro_pos_from_caravel(self):
        logging.error("out of date")
        exit(1)

        macro_inst_file = os.path.join(self.system_config['caravel']['root'], 'openlane', 'user_project_wrapper', 'macro.cfg')
        with open(macro_inst_file) as f:
            for macro in f.readlines():
                # name, x, y, orientation
                instance_name, x, y, orientation = macro.split(' ')
                if instance_name == self.instance_name:
                    return(float(x), float(y))
        logging.error("couldn't find position for %s in %s" % (self.instance_name, macro_inst_file))
        exit(1)

    def get_gds_size(self):
        # openram size is cached to save time and because it won't change
        if 'size' in self.config:
            return self.config['size']['width'], self.config['size']['height']
        
        conf = self.config["final"]
        gds_file        = os.path.abspath(os.path.join(self.directory, conf["directory"], conf["gds_filename"]))
        gdsii = gdspy.GdsLibrary(infile=gds_file)
        toplevel = gdsii.top_level()[0]
        return toplevel.get_bounding_box()[1]

    # some project won't have these yet, and they aren't specced in the yaml, so test to see if they are there
    # for example sdc/ sdf/ spef/
    def get_optional_file(self, filetype):
        conf = self.config["final"]
        filename = os.path.abspath(os.path.join(self.directory, conf["directory"], filetype, "%s.%s" % (self.module_name, filetype)))
        if os.path.exists(filename):
            return filename
        return None
            
    def test_module(self):
        pass

    def prove_wrapper(self):
        pass

    def test_caravel(self):
        pass

    def test_gds(self):
        pass

    def test_lvs(self):
        pass

    def test_ports(self):
        pass

    def test_tristate_z(self):
        pass

    def test_tristate_driver(self):
        pass

    def test_git_match(self):
        if 'waive_git' in self.config['project']:
            logging.info("skipping git test due to %s" % self.config['project']['waive_git'])
            return

        self.gitsha = get_git_sha(self.directory)
        if self.gitsha != self.commit:
            logging.error("gitsha on disk %s doesn't match config %s for %s" % (self.gitsha, self.commit, self))
            exit(1) 
        else:
            logging.info("git pass")

    def run_tests(self):
        # print out info about the project
        if self.args.dump_hash:
            logging.info("%-30s %-20s %s %s" % (self.author, self.title, self.gitsha, self.repo))
        else:
            logging.info(self)

        if self.args.test_all or self.args.test_module:
            self.test_module()

        if self.args.test_all or self.args.prove_wrapper:
            self.prove_wrapper()

        if self.args.test_all or self.args.test_caravel:
            self.test_caravel()

        if self.args.test_all or self.args.test_gds:
            self.test_gds()

        # currently broken, waiting on testing a new netgen
        if self.args.test_all or self.args.test_lvs:
            self.test_lvs()

        if self.args.test_all or self.args.test_ports:
            self.validate_ports()

        if self.args.test_all or self.args.test_tristate_z:
            self.test_tristate_z()

        if self.args.test_all or self.args.test_tristate_driver:
            self.test_tristate_driver()

        if self.args.test_all or self.args.test_git:
            self.test_git_match()

    def count_cells(self):
        # hack for now, add the summary.csv file to the final files
        powered_verilog = os.path.abspath(os.path.join(self.directory, self.config["final"]["directory"], self.config["final"]["lvs_filename"]))
        cmd = "grep sky130_ %s | awk '{ print $1 }'  | grep -v fill | grep -v decap  | wc -l" % powered_verilog
        try:
            result = subprocess.getoutput(cmd)
        except subprocess.CalledProcessError as e:
            logging.error(e)
            exit(1)
   
        return int(result)

class SharedProject(BaseProject):

    def __init__(self, args, repo, directory, commit, pos, system_config):
        self.args = args
        self.system_config = system_config
        self.repo = repo # the repo on github
        self.commit = commit # not strictly a commit, could be a branch
        self.pos = pos
        self.directory = directory


        if args.clone_shared_repos:
            self.clone_repo()

        self.gitsha = get_git_sha(self.directory)

        yaml_file = os.path.join(self.directory, 'info.yaml')
        self.config = parse_config(yaml_file, REQUIRED_KEYS_SHARED)

        self.module_name = self.config['project']['module_name']
        self.author = self.config['project']['author']
        self.gds_filename = os.path.join(self.config['final']['directory'], self.config['final']['gds_filename'])
        self.lef_filename = os.path.join(self.config['final']['directory'], self.config['final']['lef_filename'])
        self.title = self.config['project']['title']
        self.instance_name = self.module_name

    def get_top_module(self):
        return self.module_name

    def copy_gl(self):
        pass

    def run_tests(self):
        # print out info about the project
        if self.args.dump_hash:
            logging.info("%-30s %-20s %s %s" % (self.author, self.title, self.gitsha, self.repo))
        else:
            logging.info(self)

        if self.args.test_all or self.args.test_module:
            self.test_module()

        if self.args.test_all or self.args.test_lvs:
            self.test_lvs()

        if self.args.test_all or self.args.test_git:
            self.test_git_match()

    def __str__(self):
        return "shared %-26s : %s" % (self.title, self.directory)

class Project(BaseProject):

    def __init__(self, args, repo, directory, commit, pos, required_interfaces, system_config):
        self.args = args
        self.system_config = system_config
        self.repo = repo # the repo on github
        self.commit = commit # not strictly a commit, could be a branch
        self.pos = pos
        self.directory = directory


        if args.clone_repos:
            self.clone_repo()

        if not os.path.exists(self.directory):
            logging.error("project directory %s doesn't exist. Use --clone-repos to clone it" % self.directory)
            exit(1)

        self.gitsha = get_git_sha(self.directory)

        yaml_file = os.path.join(self.directory, 'info.yaml')
        self.config = parse_config(yaml_file, REQUIRED_KEYS_SINGLE)
        self.id = int(self.config['caravel_test']['id'])
        self.module_name = self.config['caravel_test']['module_name']
        self.instance_name = self.module_name + "_" + str(self.id)

        self.interfaces = required_interfaces + self.config['interfaces'] 
        
        self.gds_filename = os.path.join(self.config['final']['directory'], self.config['final']['gds_filename'])
        self.lef_filename = os.path.join(self.config['final']['directory'], self.config['final']['lef_filename'])
        self.lvs_filename = os.path.join(self.config['final']['directory'], self.config['final']['lvs_filename'])
        self.title = self.config['project']['title']
        self.author = self.config['project']['author']

    def __str__(self):
        return "%2d %-30s : %s" % (self.id, self.title, self.directory)



    # hack - better to add this to the info.yaml but for now we do it by searching all the source files. not all are called wrapper.v
    def get_top_module(self):
        paths = self.get_module_source_paths(absolute=False)
        top_instance = 'module %s' % self.config['caravel_test']['module_name']
        # now check each source for the top_name
        for path in paths:
            abs_path = os.path.abspath(os.path.join(self.directory, path))
            with open(abs_path) as fh:
                if top_instance in fh.read():
                    return path
        else:
            logging.error("couldn't find top module for %s" % self)
            exit(1)


    def test_module(self):
        if 'waive_module_test' in self.config['project']:
            logging.info("skipping module test due to %s" % self.config['project']['waive_module_test'])
            return

        conf = self.config["module_test"]
        cwd = os.path.join(self.directory, conf["directory"])
        cmd = ["make", "-f", conf["makefile"], conf["recipe"]]
        logging.info("attempting to run %s in %s" % (cmd, cwd))
        try:
            subprocess.run(cmd, cwd=cwd, check=True)
        except subprocess.CalledProcessError as e:
            logging.error(e)
            exit(1)

        logging.info("test pass")

        

    def prove_wrapper(self):
        # TODO need to also check properties.sby - could have a few things to cksum and make wrapper_cksum able to check a few files
        if 'waive_formal' in self.config['project']:
            logging.info("skipping formal test due to %s" % self.config['project']['waive_formal'])
            return
        conf = self.config["wrapper_proof"]
        cwd = os.path.join(self.directory, conf["directory"])
        try:
            sby_cmd = self.system_config['tools']['sby']
        except KeyError:
            sby_cmd = 'sby'

        cmd = [sby_cmd, "-f", conf["sby"]]
        logging.info("attempting to run %s in %s" % (cmd, cwd))
        try:
            subprocess.run(cmd, cwd=cwd, check=True)
        except subprocess.CalledProcessError as e:
            logging.error(e)
            exit(1)

        logging.info("proof pass")

    def copy_gl(self):
        src = os.path.join(self.directory, self.config['final']['directory'], self.config['final']['lvs_filename'])
        dst = os.path.join(self.system_config['caravel']['gl_dir'], os.path.basename(self.config['final']['lvs_filename']))
        shutil.copyfile(src, dst)

    def test_caravel(self):
        if 'waive_caravel' in self.config['project']:
            logging.info("skipping caravel test due to %s" % self.config['project']['waive_caravel'])
            return

        conf = self.config["caravel_test"]

        # set up env
        test_env = os.environ.copy()
        test_env["GCC_PATH"]    = self.system_config['env']['GCC_PATH']
        test_env["GCC_PREFIX"]  = self.system_config['env']['GCC_PREFIX']
        test_env["PDK_PATH"]    = self.system_config['env']['PDK_PATH']
        test_env["PDK_ROOT"]    = self.system_config['env']['PDK_ROOT']
        test_env["PDK"]         = self.system_config['env']['PDK']
        test_env["CARAVEL_ROOT"]    = os.path.join(self.system_config['caravel']['root'], 'caravel')

        test_env["DESIGNS"] =         self.system_config['caravel']['root']
        test_env["TARGET_PATH"] =     self.system_config['caravel']['root']
        test_env["MCW_ROOT"] =        os.path.join(self.system_config['caravel']['root'], self.system_config['caravel']['mgmt_root'])
        test_env["CORE_VERILOG_PATH"] = os.path.join(self.system_config['caravel']['mgmt_root'], 'verilog')


        cwd = os.path.join(self.system_config['caravel']['test_dir'], conf["directory"])
        cmd = ["make", conf["recipe"]]

        # if gl, make sure the gatelevel netlist is in the correct place, & use the gl_recipe
        if self.args.gate_level:
            cmd = ["make", conf["gl_recipe"]]

        logging.info("attempting to run %s in %s" % (cmd, cwd))

        # run makefile
        try:
            subprocess.run(cmd, cwd=cwd, env=test_env, check=True)
        except subprocess.CalledProcessError as e:
            logging.error(e)
            exit(1)

        logging.info("caravel test pass")


    def test_gds(self):
        if 'waive_gds' in self.config['project']:
            logging.info("skipping GDS in this test due to %s" % self.config['project']['waive_gds'])
            return

        conf = self.config["final"]
        gds_file        = os.path.abspath(os.path.join(self.directory, conf["directory"], conf["gds_filename"]))
        gdsii = gdspy.GdsLibrary(infile=gds_file)
        toplevel = gdsii.top_level()[0]


        # nothing on metal 5
        if self.system_config["configuration"]["gds"]["metal5_id"] in toplevel.get_layers():
            logging.error("%s has layers on metal5" % gds_file)
            exit(1)

        logging.info("GDS pass")

    def test_lvs(self):
        if 'waive_lvs' in self.config['project']:
            logging.info("skipping LVS in this test due to %s" % self.config['project']['waive_lvs'])
            return

        module_name = self.config['caravel_test']['module_name']
        conf = self.config["final"]
        # given
        lvs_test_dir    = 'lvstest'
        try_mkdir(lvs_test_dir, self.args.force_delete)

        # copy the gds and verilog to local directory
        gds_file        = os.path.abspath(os.path.join(self.directory, conf["directory"], conf["gds_filename"]))
        powered_verilog = os.path.abspath(os.path.join(self.directory, conf["directory"], conf["lvs_filename"]))
        shutil.copyfile(gds_file, os.path.join(lvs_test_dir, os.path.basename(conf["gds_filename"])))
        shutil.copyfile(powered_verilog, os.path.join(lvs_test_dir, os.path.basename(conf["lvs_filename"])))
        gds_file = os.path.basename(conf["gds_filename"])
        powered_verilog = os.path.basename(conf["lvs_filename"])

        # generated files
        ext_file        = module_name + ".ext"
        log_file        = module_name + ".log"
        spice_file      = module_name + '.spice'
        netgen_log_file = module_name + '.netgen_log'
        netgen_json     = module_name + '.json'
        extract_tcl     = 'extract.tcl'

        # config files
        pdk_path        = self.system_config['env']['PDK_PATH']
        openlane_root   = self.system_config['env']['OPENLANE']
        logging.info("using PDK %s and OpenLANE %s" % (pdk_path, openlane_root))

        # env
        test_env                       = os.environ.copy()
        test_env["MAGIC_EXT_USE_GDS"]  = "1"
        test_env["PDKPATH"]            = pdk_path

        netgen_setup_file = os.path.join(pdk_path, 'libs.tech', 'netgen', 'sky130A_setup.tcl')
        cwd = lvs_test_dir

        # create tcl script for magic
        tcl_contents = """
        gds read %s;
        load %s -dereference

        extract do local;
        extract no capacitance;
        extract no coupling;
        extract no resistance;
        extract no adjust;
        extract unique;
        extract;
        ext2spice lvs;
        ext2spice %s;
        feedback save %s;
        exit;
        """ % (gds_file, module_name, ext_file, log_file)

        with open(os.path.join(lvs_test_dir, extract_tcl), 'w') as tcl:
            tcl.write(tcl_contents)

        magic_rcfile = os.path.join(pdk_path, 'libs.tech', 'magic', 'sky130A.magicrc')
        cmd = ['magic', '-rcfile', magic_rcfile, '-noc', '-dnull', extract_tcl]
        logging.info(' '.join(cmd))

        subprocess.run(cmd, cwd=cwd, env=test_env, check=True)

        left_side = '%s %s' % (spice_file, module_name)
        right_side = '%s %s' % (powered_verilog, module_name)
        # only way to get this quoted stuff to work was to use shell=True in the subprocess call
        cmd = 'netgen -batch lvs "%s" "%s" %s %s -json' % (left_side, right_side, netgen_setup_file, netgen_log_file)

        logging.info(cmd)
        subprocess.run(cmd, env=test_env, cwd=cwd, check=True, shell=True)

        lvs_count_cmd = os.path.join(openlane_root, 'scripts', 'count_lvs.py')
        cmd = [lvs_count_cmd, '--file', netgen_json]
        logging.info(cmd)

        # lvs count command doesn't return valid exit codes
        try:
            result = subprocess.run(cmd, cwd=cwd, capture_output=True)
        except subprocess.CalledProcessError as e:
            logging.error(e)
            exit(1)

        # so search for string in output
        if 'Total errors = 0' in str(result.stdout):
            logging.info("LVS passed")
        else:
            logging.error(result.stdout)
            exit(1)

    def test_tristate_z(self):
        # env
        test_env                       = os.environ.copy()
        test_env["POWERED_VERILOG"]    = powered_verilog = os.path.abspath(os.path.join(self.directory, self.config["final"]["directory"], self.config["final"]["lvs_filename"]))
        test_env["TOPLEVEL"]           = self.config["caravel_test"]["module_name"]
        test_env["PDK_ROOT"]           = self.system_config["env"]["PDK_ROOT"]

        if "custom_cells_file" in self.config:
            test_env["CUSTOM_CELLS_FILE"] = os.path.abspath(os.path.join(self.directory, self.config["custom_cells_file"]))

        cmd = ["make", "clean", "test"]
        tool_dir = os.path.dirname(os.path.realpath(__file__))
        cwd = os.path.join(tool_dir, "buffertest")

        logging.info("attempting to run %s in %s" % (cmd, cwd))

        # run makefile
        try:
            subprocess.run(cmd, cwd=cwd, env=test_env, check=True)
        except subprocess.CalledProcessError as e:
            logging.error(e)
            exit(1)

        logging.info("tristate z test pass")

    def test_tristate_driver(self):
        conf = self.config["final"]
        powered_verilog = os.path.abspath(os.path.join(self.directory, conf["directory"], conf["lvs_filename"]))
        cmd = "yosys -qp 'read_liberty -lib merged.lib; read_verilog -sv " + powered_verilog + "; select -set tristate_wires t:sky130_fd_sc_hd__ebufn_* %co:[Z] x:* %i; select -assert-none @tristate_wires %co:* x:* %d'"
        try:
            result = subprocess.getoutput(cmd)
            if result != "":
                logging.error(result)
                exit(1)

        except subprocess.CalledProcessError as e:
            logging.error(e)
            exit(1)

    def validate_ports(self):
        if 'waive_ports_test' in self.config['project']:
            logging.info("skipping ports test due to %s" % self.config['project']['waive_ports_test'])
            return
        # assume first source is top, bad idea
        sources = ""
        for source_file in self.config['source']:
            sources += os.path.join(self.directory, source_file)
            sources += " "

        top = self.config['caravel_test']['module_name']

        # use yosys to parse the verilog and dump a list of ports
        json_file = '/tmp/ports.json'

        os.system("yosys -qp 'read_verilog -sv %s; hierarchy -top %s ; proc; json -o %s x:*' -DUSE_POWER_PINS=1 -DMPRJ_IO_PADS=38" % (sources, top, json_file))
        with open(json_file) as fh:
            ports = json.load(fh)
        
        module_ports = ports['modules'][self.config['caravel_test']['module_name']]['ports']

        # check required ports
        for port_type, port_def in self.system_config['interfaces']['required'].items(): 
            for port_name, bits in port_def.items():
                # assert port is there
                if port_name not in module_ports:
                    logging.error("required port %s not in interface" % port_name)
                    exit(1)
                # and it's the correct length
                if len(module_ports[port_name]['bits']) != bits:
                    logging.error("required port %s is wrong size" % port_name)
                    exit(1)

                # delete it
                del module_ports[port_name]

        # for all the optional ports defined in the projects yaml
        for optional_port in self.config['interfaces']: 
            # look up its definition
            for port_name, bits in self.system_config['interfaces']['optional'][optional_port].items():
                # assert port is there
                if port_name not in module_ports:
                    logging.error("optional port %s was set but %s is not in interface" % (optional_port, port_name))
                    exit(1)
                # and it's the correct length
                if len(module_ports[port_name]['bits']) != bits:
                    logging.error("optional port %s is wrong size" % (port_name))
                    exit(1)
            
                # delete it
                del module_ports[port_name]

        # module def should now be empty
        if len(module_ports) != 0:
            logging.error("additional interfaces found in module")
            logging.error(module_ports)
            exit(1)

        logging.info("test ports pass")
