import subprocess
import shutil
from utils import *
from urllib.parse import urlparse
import os, json

REQUIRED_KEYS_SINGLE = ["project", "caravel_test", "module_test", "wrapper_proof", "openlane", "gds"]


class Project(object):

    def __init__(self, args, repo, commit, system_config):
        self.args = args
        self.system_config = system_config
        self.repo = repo
        self.commit = commit

        project_dir = self.system_config['configuration']['project_directory']

        # the project's directory is made by joining project dir to last part of the repo url 
        parsed = urlparse(repo)
        self.directory = os.path.join(project_dir, parsed.path.rpartition('/')[-1])

        if args.clone_repos:
            self.clone_repo()

        yaml_file = os.path.join(self.directory, 'info.yaml')
        self.config = parse_config(yaml_file, REQUIRED_KEYS_SINGLE)
        self.id = int(self.config['caravel_test']['id'])

        self.gds_filename = os.path.join(self.config['gds']['directory'], self.config['gds']['gds_filename'])
        self.lef_filename = os.path.join(self.config['gds']['directory'], self.config['gds']['lef_filename'])
        self.lvs_filename = os.path.join(self.config['gds']['directory'], self.config['gds']['lvs_filename'])
        self.title = self.config['project']['title'],

    def __str__(self):
        return "%2d %-30s : %s" % (self.id, self.title, self.directory)

    def run_tests(self):
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

        if self.args.test_all or self.args.test_interface:
            self.test_interface()

        if self.args.test_all or self.args.test_lvs:
            self.test_lvs()

        if self.args.test_all or self.args.test_tristate_num:
            self.test_tristate_num()

        if self.args.test_all or self.args.test_ports:
            self.validate_ports()

        if self.args.test_all or self.args.test_tristate_z:
            self.test_tristate_z()

    def clone_repo(self):
        clone_repo(self.repo, self.commit, self.directory, self.args.force_delete)

    def get_git_version(self):
        exit("deprecated")
        git_version = subprocess.check_output(['git', '-C', self.directory, 'log', '--pretty=format:%h', '-n', '1']).decode('utf-8')
        return git_version

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

        # instantiate inside user project wrapper
        macro_verilog = instantiate_module(conf["module_name"], conf["instance_name"], self.id, self.system_config['wrapper']['instance'])
        user_project_wrapper_path = os.path.join(self.system_config['caravel']['rtl_dir'], "user_project_wrapper.v")
        add_instance_to_upw(macro_verilog, user_project_wrapper_path, self.system_config['wrapper']['upw_template'])

        # setup includes
        includes_path = os.path.join(self.system_config['caravel']['rtl_dir'], "uprj_netlists.v")
        add_verilog_includes([self], includes_path, self.system_config['wrapper']['includes_template'], gl)

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

    # only valid if the LVS test passes
    def test_interface(self):
        conf = self.config["gds"]
        powered_v_filename = os.path.join(self.directory, conf["directory"], conf["lvs_filename"])

        with open(powered_v_filename) as fh:
            powered_v = fh.read()
        
        with open(self.system_config["wrapper"]["interface"]) as fh:
            for io in fh.readlines():
                if io.strip() not in powered_v:
                    logging.error("io port [%s] not found in %s" % (io.strip(), powered_v_filename))
                    exit(1)
            
        logging.info("module interface pass")

    def test_gds(self):
        if 'waive_gds' in self.config['project']:
            logging.info("skipping GDS in this test due to %s" % self.config['project']['waive_gds'])
            return

        conf = self.config["gds"]
        gds_file        = os.path.abspath(os.path.join(self.directory, conf["directory"], conf["gds_filename"]))
        import gdspy
        gdsii = gdspy.GdsLibrary(infile=gds_file)
        toplevel = gdsii.top_level()[0]
        width = self.system_config["tests"]["gds"]["width"]
        height = self.system_config["tests"]["gds"]["height"]

        # correct size
        if not (toplevel.get_bounding_box() == [[0,0],[width,height]]).all():
            logging.error("%s is the wrong size %s" % (gds_file, toplevel.get_bounding_box()))
            exit(1)

        # nothing on metal 5
        if self.system_config["tests"]["gds"]["metal5_id"] in toplevel.get_layers():
            logging.error("%s has layers on metal5" % gds_file)
            exit(1)

        logging.info("GDS pass")

    # not a great test, as tristate could be in use elsewhere.
    # better to parse the cells and check outputs of the tristates are correct)
    # only valid if the LVS test passes
    def test_tristate_num(self):
        conf = self.config["gds"]
        powered_v_filename = os.path.join(self.directory, conf["directory"], conf["lvs_filename"])

        count = 0
        tristate_cell = 'sky130_fd_sc_hd__ebufn_' # 1 or 2 is fine
        with open(powered_v_filename) as fh:
            for line in fh.readlines():
                if tristate_cell in line:
                    count += 1

        if count != self.system_config["tests"]["tristates"]:
            logging.error("wrong number of tristates [%s] %d in %s" % (tristate_cell, count, powered_v_filename))
            exit(1)

        logging.info("tristate test pass")

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

        os.system("yosys -qp 'read_verilog %s; hierarchy -top %s ; proc; json -o %s x:*' -DUSE_POWER_PINS=1 -DMPRJ_IO_PADS=38" % (sources, top, json_file))
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
