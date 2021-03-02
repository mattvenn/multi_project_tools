import yaml
import logging
import hashlib
import shutil
import os, sys
import subprocess
from utils import *

REQUIRED_KEYS_SINGLE = [ "project", "caravel_test", "module_test", "wrapper_proof", "wrapper_cksum", "openlane", "gds" ]

class Project():

    def __init__(self, args, directory, system_config):
        self.args = args
        self.system_config = system_config
        self.directory = os.path.normpath(directory)
        yaml_file = os.path.join(self.directory, 'info.yaml')
        self.config = parse_config(yaml_file, REQUIRED_KEYS_SINGLE )

        self.gds_filename = os.path.join(self.config['gds']['directory'], self.config['gds']['gds_filename'])
        self.lef_filename = os.path.join(self.config['gds']['directory'], self.config['gds']['lef_filename'])
        self.lvs_filename = os.path.join(self.config['gds']['directory'], self.config['gds']['lvs_filename'])

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

    def wrapper_cksum(self):
        conf = self.config["wrapper_cksum"]
        wrapper = os.path.join(self.directory, conf["directory"], conf["filename"])
        instance_lines = list(range(int(conf["instance_start"]), int(conf["instance_end"]+1)))
        logging.info("skipping instance lines %s" % instance_lines)

        wrapper_text = ""
        line_num = 1

        with open(wrapper) as fh:
            for line in fh.readlines():
                if line_num not in instance_lines:
                    wrapper_text += line
                else:
                    logging.info("skip %d: %s" % (line_num, line.strip()))
                line_num += 1
                
        md5sum = hashlib.md5(wrapper_text.encode('utf-8')).hexdigest()
        if md5sum != self.system_config['wrapper']['md5sum']:
            logging.error("md5sum %s doesn't match" % (md5sum))
            exit(1)

        logging.info("cksum pass")


    def test_caravel(self):
        conf = self.config["caravel_test"]
        delete_later = []

        # copy src into caravel verilog dir
        src = self.directory
        dst = os.path.join(self.system_config['caravel']['rtl_dir'], os.path.basename(self.directory))
        try_copy(src, dst, self.args.force_delete)

        # instantiate inside user project wrapper
        macro_verilog = instantiate_module(conf["module_name"], conf["instance_name"], conf["id"], self.system_config['wrapper']['instance'])
        user_project_wrapper_path = os.path.join(self.system_config['caravel']['rtl_dir'], "user_project_wrapper.v")
        add_instance_to_upw(macro_verilog, user_project_wrapper_path, self.system_config['wrapper']['upw_template'])

        # copy test inside caravel
        src = os.path.join(self.directory, conf["directory"])
        dst = os.path.join(self.system_config['caravel']['test_dir'], conf["directory"])
        try_copy(src, dst, self.args.force_delete)

        # set up env
        test_env = os.environ
        test_env["GCC_PATH"]    = self.system_config['env']['GCC_PATH']
        test_env["GCC_PREFIX"]  = self.system_config['env']['GCC_PREFIX']
        test_env["PDK_PATH"]    = self.system_config['env']['PDK_PATH']

        cwd = os.path.join(self.system_config['caravel']['test_dir'], conf["directory"])
        cmd = ["make", conf["recipe"]]
        logging.info("attempting to run %s in %s" % (cmd, cwd))

        # run makefile
        try:
            subprocess.run(cmd, cwd=cwd, env=test_env, check=True)
        except subprocess.CalledProcessError as e:
            logging.error(e)
            cleanup(delete_later)
            exit(1)

        cleanup(delete_later)
        logging.info("caravel test pass")

    def test_interface(self):
        conf = self.config["gds"]
        powered_v_filename = os.path.join(self.directory, conf["directory"], conf["lvs_filename"])

        with open(powered_v_filename) as fh:
            powered_v = fh.readlines()
          
        with open(self.system_config["wrapper"]["interface"]) as fh:
            for io in fh.readlines():
                if io not in powered_v:
                    logging.error("io port not found in %s: %s" % (powered_v_filename, io.strip()))
                    exit(1)
            
        logging.info("module interface pass")

    def test_gds(self):
       # gds_filename: "wrapper.gds"
       # lvs_filename: "wrapper.lvs.powered.v"
        """
        need the LEF for this? will need the lef for final hardening
        check size
        nothing on metal 5,
        do a DRC,
        check 141 tristate buffers
        check number of io
        """

    def test_lvs(self):
        module_name = self.config['caravel_test']['module_name']
        conf = self.config["gds"]
        # given
        lvs_test_dir    = 'lvstest'
        os.mkdir(lvs_test_dir)
        gds_file        = os.path.abspath(os.path.join(self.directory, conf["directory"], conf["gds_filename"]))
        powered_verilog = os.path.abspath(os.path.join(self.directory, conf["directory"], conf["lvs_filename"]))

        # generated files
        ext_file        = module_name + ".ext"
        log_file        = module_name + ".log"
        spice_file      = module_name + '.spice'
        netgen_log_file = module_name + '.netgen_log'
        netgen_json     = module_name + '.json'
        extract_tcl     = 'extract.tcl'

        # config files
        pdk_path        = self.system_config['env']['PDK_PATH']
        openlane_root   = self.system_config['openlane']['root']

        # env
        test_env                       = os.environ
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
        try:
            subprocess.run(cmd, cwd=cwd, check=True)
        except subprocess.CalledProcessError as e:
            logging.error(e)
            exit(1)

        logging.info("LVS passed")
        shutil.rmtree(lvs_test_dir)
