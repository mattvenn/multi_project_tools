import subprocess
import gdspy
import shutil
from utils import *
from codegen.caravel_codegen import generate_openlane_files
from urllib.parse import urlparse
import os, json

REQUIRED_KEYS_SINGLE = ["project", "caravel_test", "module_test", "wrapper_proof", "openlane", "gds"]


class Project(object):

    def __init__(self, args, repo, commit, required_interfaces, system_config):
        self.args = args
        self.system_config = system_config
        self.repo = repo # the repo on github
        self.commit = commit # not strictly a commit, could be a branch

        project_dir = self.system_config['configuration']['project_directory']

        # the project's directory is made by joining project dir to last part of the repo url 
        parsed = urlparse(repo)
        self.directory = os.path.join(project_dir, parsed.path.rpartition('/')[-1])

        if args.clone_repos:
            self.clone_repo()

        self.gitsha = get_git_sha(self.directory)

        yaml_file = os.path.join(self.directory, 'info.yaml')
        self.config = parse_config(yaml_file, REQUIRED_KEYS_SINGLE)
        self.id = int(self.config['caravel_test']['id'])
        self.module_name = self.config['caravel_test']['module_name']

        if self.args.mpw2:
            self.interfaces = required_interfaces + ['gpio', 'la1', 'irq', 'clk2', 'wishbone']
        else:
            self.interfaces = required_interfaces + self.config['interfaces'] 
        
        self.gds_filename = os.path.join(self.config['gds']['directory'], self.config['gds']['gds_filename'])
        self.lef_filename = os.path.join(self.config['gds']['directory'], self.config['gds']['lef_filename'])
        self.lvs_filename = os.path.join(self.config['gds']['directory'], self.config['gds']['lvs_filename'])
        self.title = self.config['project']['title']
        self.author = self.config['project']['author']

    def __str__(self):
        return "%2d %-30s : %s" % (self.id, self.title, self.directory)

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

        # don't run this as part of test-all
        if self.args.test_caravel_gl:
            self.test_caravel(gl=True)

        if self.args.test_all or self.args.test_gds:
            self.test_gds()

        # currently broken, waiting on testing a new netgen
        if self.args.test_all or self.args.test_lvs:
            self.test_lvs()

        if self.args.test_all or self.args.test_ports:
            self.validate_ports()

        if self.args.test_all or self.args.test_tristate_z:
            self.test_tristate_z()

        if self.args.test_all or self.args.test_git:
            self.test_git_match()

    def clone_repo(self):
        clone_repo(self.repo, self.commit, self.directory, self.args.force_delete)

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

    def get_module_source_paths(self, absolute=True):
        paths = []
        for path in self.config['source']:
            if absolute:
                paths.append(os.path.abspath(os.path.join(self.directory, path)))
            else:
                paths.append(path)
        return paths    

    def test_module(self):
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

    def test_git_match(self):
        self.gitsha = get_git_sha(self.directory)
        if self.gitsha != self.commit:
            logging.error("gitsha on disk doesn't match config")
            exit(1) 
        else:
            logging.info("git pass")
        

    def prove_wrapper(self):
        # TODO need to also check properties.sby - could have a few things to cksum and make wrapper_cksum able to check a few files
        conf = self.config["wrapper_proof"]
        cwd = os.path.join(self.directory, conf["directory"])
        cmd = ["sby", "-f", conf["sby"]]
        logging.info("attempting to run %s in %s" % (cmd, cwd))
        try:
            subprocess.run(cmd, cwd=cwd, check=True)
        except subprocess.CalledProcessError as e:
            logging.error(e)
            exit(1)

        logging.info("proof pass")

    def copy_project_to_caravel_rtl(self):
        src = self.directory
        dst = os.path.join(self.system_config['caravel']['rtl_dir'], os.path.basename(self.directory))
        try_copy_tree(src, dst, self.args.force_delete)

    def copy_gl(self):
        dst = os.path.join(self.system_config['caravel']['gl_dir'], self.config['gds']['lvs_filename'])
        src = os.path.join(self.directory, self.config['gds']['directory'], self.config['gds']['lvs_filename'])
        shutil.copyfile(src, dst)
        
    def test_caravel(self, gl=False):
        conf = self.config["caravel_test"]

        # copy src into caravel verilog dir
        self.copy_project_to_caravel_rtl()

        # generate includes & instantiate inside user project wrapper
        # could this be removed and just do it in collect.py ?
        user_project_wrapper_path =  os.path.join(self.system_config['caravel']['rtl_dir'], "user_project_wrapper.v")
        caravel_includes_path =      os.path.join(self.system_config['caravel']['rtl_dir'], "uprj_netlists.v")
        user_project_includes_path = os.path.join(self.system_config['caravel']['rtl_dir'], "user_project_includes.v")

        interface_definitions = {
            **self.system_config['interfaces']['required'], 
            **self.system_config['interfaces']['optional']
        }

        generate_openlane_files(
            [self], 
            interface_definitions,
            user_project_wrapper_path, 
            user_project_includes_path,
            caravel_includes_path,
            self.args.openram
        )

        # copy test inside caravel
        src = os.path.join(self.directory, conf["directory"])
        dst = os.path.join(self.system_config['caravel']['test_dir'], conf["directory"])
        try_copy_tree(src, dst, self.args.force_delete)

        # set up env
        test_env = os.environ.copy()
        test_env["GCC_PATH"]    = self.system_config['env']['GCC_PATH']
        test_env["GCC_PREFIX"]  = self.system_config['env']['GCC_PREFIX']
        test_env["PDK_PATH"]    = self.system_config['env']['PDK_PATH']
        test_env["CARAVEL_ROOT"]    = os.path.join(self.system_config['caravel']['root'], 'caravel')

        cwd = os.path.join(self.system_config['caravel']['test_dir'], conf["directory"])
        cmd = ["make", conf["recipe"]]

        # if gl, use the gl_recipe
        if gl:
            cmd = ["make", conf["gl_recipe"]]

        logging.info("attempting to run %s in %s" % (cmd, cwd))

        # run makefile
        try:
            subprocess.run(cmd, cwd=cwd, env=test_env, check=True)
        except subprocess.CalledProcessError as e:
            logging.error(e)
            exit(1)

        logging.info("caravel test pass")

    def get_gds_size(self):
        conf = self.config["gds"]
        gds_file        = os.path.abspath(os.path.join(self.directory, conf["directory"], conf["gds_filename"]))
        gdsii = gdspy.GdsLibrary(infile=gds_file)
        toplevel = gdsii.top_level()[0]
        return toplevel.get_bounding_box()[1]

    def test_gds(self):
        if 'waive_gds' in self.config['project']:
            logging.info("skipping GDS in this test due to %s" % self.config['project']['waive_gds'])
            return

        conf = self.config["gds"]
        gds_file        = os.path.abspath(os.path.join(self.directory, conf["directory"], conf["gds_filename"]))
        gdsii = gdspy.GdsLibrary(infile=gds_file)
        toplevel = gdsii.top_level()[0]


        # nothing on metal 5
        if self.system_config["tests"]["gds"]["metal5_id"] in toplevel.get_layers():
            logging.error("%s has layers on metal5" % gds_file)
            exit(1)

        logging.info("GDS pass")

    def test_lvs(self):
        if 'waive_lvs' in self.config['project']:
            logging.info("skipping LVS in this test due to %s" % self.config['project']['waive_lvs'])
            return

        module_name = self.config['caravel_test']['module_name']
        conf = self.config["gds"]
        # given
        lvs_test_dir    = 'lvstest'
        try_mkdir(lvs_test_dir, self.args.force_delete)

        # copy the gds and verilog to local directory
        gds_file        = os.path.abspath(os.path.join(self.directory, conf["directory"], conf["gds_filename"]))
        powered_verilog = os.path.abspath(os.path.join(self.directory, conf["directory"], conf["lvs_filename"]))
        shutil.copyfile(gds_file, os.path.join(lvs_test_dir, conf["gds_filename"]))
        shutil.copyfile(powered_verilog, os.path.join(lvs_test_dir, conf["lvs_filename"]))
        gds_file = conf["gds_filename"]
        powered_verilog = conf["lvs_filename"]

        # generated files
        ext_file        = module_name + ".ext"
        log_file        = module_name + ".log"
        spice_file      = module_name + '.spice'
        netgen_log_file = module_name + '.netgen_log'
        netgen_json     = module_name + '.json'
        extract_tcl     = 'extract.tcl'

        # config files
        pdk_path        = self.system_config['lvs']['PDK_PATH']
        openlane_root   = self.system_config['lvs']['OPENLANE']
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
        elif 'Total errors = 6' in str(result.stdout) and 'unmatched pins = 6' in str(result.stdout):
            logging.info("LVS passed (waived 6 unconnected power pins)")
        else:
            logging.error(result.stdout)
            exit(1)

    def test_tristate_z(self):
        # env
        test_env                       = os.environ.copy()
        test_env["POWERED_VERILOG"]    = powered_verilog = os.path.abspath(os.path.join(self.directory, self.config["gds"]["directory"], self.config["gds"]["lvs_filename"]))
        test_env["TOPLEVEL"]           = self.config["caravel_test"]["module_name"]
        test_env["PDK_ROOT"]           = self.system_config["lvs"]["PDK_ROOT"]

        cmd = ["make", "clean", "test"]
        cwd = "buffertest"

        logging.info("attempting to run %s in %s" % (cmd, cwd))

        # run makefile
        try:
            subprocess.run(cmd, cwd=cwd, env=test_env, check=True)
        except subprocess.CalledProcessError as e:
            logging.error(e)
            exit(1)

        logging.info("tristate z test pass")

    def validate_ports(self):
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
