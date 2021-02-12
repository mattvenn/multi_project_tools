#!/usr/bin/env python3
import yaml
import argparse
import os, sys
import subprocess
import logging
import hashlib
import shutil

REQUIRED_KEYS = [ "project", "caravel_test", "module_test", "wrapper_proof", "wrapper_cksum", "openlane", "gds" ]
WRAPPER_MD5SUM = "0ec8fdff7ae891b1b156030a841d1800"
CARAVEL_TEST_DIR = "/home/matt/work/asic-workshop/caravel-mph/verilog/dv/caravel/user_proj_example/"
CARAVEL_RTL_DIR = "/home/matt/work/asic-workshop/caravel-mph/verilog/rtl/"

def parse_config():
    yaml_file = os.path.join(args.directory, 'info.yaml')
    with open(yaml_file, 'r') as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            logging.error(exc)
   
    for key in REQUIRED_KEYS:
        if key not in config:
            logging.error("key %s not found" % key)
            exit(1)

    logging.info("config pass")
    return config


def test_module():
    conf = config["module_test"]
    cwd = os.path.join(args.directory, conf["directory"])
    cmd = ["make", "-f", conf["makefile"], conf["recipe"]]
    logging.info("attempting to run %s in %s" % (cmd, cwd))
    try:
        subprocess.run(cmd, cwd=cwd, check=True)
    except subprocess.CalledProcessError as e:
        logging.error(e)
        exit(1)

    logging.info("test pass")

def prove_wrapper():
    # TODO need to also check properties.sby - could have a few things to cksum and make wrapper_cksum able to check a few files
    conf = config["wrapper_proof"]
    cwd = os.path.join(args.directory, conf["directory"])
    cmd = ["sby", "-f", conf["sby"]]
    logging.info("attempting to run %s in %s" % (cmd, cwd))
    try:
        subprocess.run(cmd, cwd=cwd, check=True)
    except subprocess.CalledProcessError as e:
        logging.error(e)
        exit(1)

    logging.info("proof pass")

def wrapper_cksum():
    conf = config["wrapper_cksum"]
    wrapper = os.path.join(args.directory, conf["directory"], conf["filename"])
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
    if md5sum != WRAPPER_MD5SUM:
        logging.error("md5sum %s doesn't match %s" % (md5sum, WRAPPER_MD5SUM))
        exit(1)

    logging.info("cksum pass")

def instantiate_project(template, output, module_name, instance_name, project_id):
    # read the data
    with open(template, 'r') as file :
        filedata = file.read()

    # replace the target strings
    filedata = filedata.replace('MODULE_NAME', module_name)
    filedata = filedata.replace('INSTANCE_NAME', instance_name)
    filedata = filedata.replace('PROJECT_ID', str(project_id))

    # overwrite the file
    with open(output, 'w') as file:
        file.write(filedata)

def cleanup(files):
    for file in files:
        logging.info("removing %s" % file)
        shutil.rmtree(file)

def try_copy(src, dst, delete_later):
    logging.info("copying %s to %s" % (src, dst))
    try:
        shutil.copytree(src, dst)
        delete_later.append(dst)
    except FileExistsError as e:
        logging.error(e)
        cleanup(delete_later)
        exit(1)

def test_caravel():
    conf = config["caravel_test"]
    logging.info(conf)
    delete_later = []

    # copy src into caravel verilog dir
    src = args.directory
    dst = os.path.join(CARAVEL_RTL_DIR, os.path.basename(args.directory))
    try_copy(src, dst, delete_later)

    # instantiate inside user project wrapper
    user_project_wrapper_template = os.path.join(CARAVEL_RTL_DIR, "user_project_wrapper.sub.v")
    user_project_wrapper_file = os.path.join(CARAVEL_RTL_DIR, "user_project_wrapper.v")
    instantiate_project(user_project_wrapper_template, user_project_wrapper_file, conf["module_name"], conf["instance_name"], conf["id"])

    # copy test inside caravel
    src = os.path.join(args.directory, conf["directory"])
    dst = os.path.join(CARAVEL_TEST_DIR, conf["directory"])
    try_copy(src, dst, delete_later)

    # set up env
    test_env = os.environ
    test_env["GCC_PATH"] = "/opt/riscv64-unknown-elf-gcc-8.3.0-2020.04.1-x86_64-linux-ubuntu14/bin/"
    test_env["GCC_PREFIX"] = "riscv64-unknown-elf"
    test_env["PDK_PATH"] = os.environ["PDKPATH"]

    cwd = os.path.join(CARAVEL_TEST_DIR, conf["directory"])
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

def test_interface():
    conf = config["gds"]
    powered_v_filename = os.path.join(args.directory, conf["directory"], conf["lvs_filename"])

    with open(powered_v_filename) as fh:
        powered_v = fh.readlines()
      
    with open("interface.txt") as fh:
        for io in fh.readlines():
            if io not in powered_v:
                logging.error("io port not found in %s: %s" % (powered_v_filename, io.strip()))
                exit(1)
        
    logging.info("module interface pass")

def test_gds():
    """
    need the LEF for this? will need the lef for final hardening
    check size
    nothing on metal 5,
    do a DRC,
    check 141 tristate buffers
    check number of io
    """

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="test a project repo")
    parser.add_argument('--directory', help="directory that defines the project", action='store', required=True)
    parser.add_argument('--test-module', help="run the module's test", action='store_const', const=True)
    parser.add_argument('--prove-wrapper', help="check the wrapper proof", action='store_const', const=True)
    parser.add_argument('--wrapper-cksum', help="check the wrapper md5sum is what it should be", action='store_const', const=True)
    parser.add_argument('--test-caravel', help="check the caravel test", action='store_const', const=True)
    parser.add_argument('--test-gds', help="check the gds", action='store_const', const=True)
    parser.add_argument('--test-interface', help="check the module's interface using powered Verilog", action='store_const', const=True)
    args = parser.parse_args()

    # get rid of any trailing /
    args.directory = os.path.normpath(args.directory)

    # setup log
    log_format = logging.Formatter('%(asctime)s - %(module)-20s - %(levelname)-8s - %(message)s')
    # configure the client logging
    log = logging.getLogger('')
    # has to be set to debug as is the root logger
    log.setLevel(logging.INFO)

    # create console handler and set level to info
    ch = logging.StreamHandler(sys.stdout)
    # create formatter for console
    ch.setFormatter(log_format)
    log.addHandler(ch)

    config = parse_config()

    if args.test_module:
        test_module()

    if args.prove_wrapper:
        prove_wrapper()

    if args.wrapper_cksum:
        wrapper_cksum()

    if args.test_caravel:
        test_caravel()

    if args.test_gds:
        test_gds()

    if args.test_interface:
        test_interface()
