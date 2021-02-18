import yaml
import logging
import hashlib
import shutil
import os, sys
import subprocess

REQUIRED_KEYS_SINGLE = [ "project", "caravel_test", "module_test", "wrapper_proof", "wrapper_cksum", "openlane", "gds" ]
WRAPPER_MD5SUM = "0ec8fdff7ae891b1b156030a841d1800"
CARAVEL_TEST_DIR = "/home/matt/work/asic-workshop/caravel-mph/verilog/dv/caravel/user_proj_example/"
CARAVEL_RTL_DIR = "/home/matt/work/asic-workshop/caravel-mph/verilog/rtl/"

def test_all(config, directory):
    test_module     (config, directory)
    prove_wrapper   (config, directory)
    wrapper_cksum   (config, directory)
    test_caravel    (config, directory)
    test_gds        (config, directory)
    test_interface  (config, directory)

def test_module(config, directory):
    conf = config["module_test"]
    cwd = os.path.join(directory, conf["directory"])
    cmd = ["make", "-f", conf["makefile"], conf["recipe"]]
    logging.info("attempting to run %s in %s" % (cmd, cwd))
    try:
        subprocess.run(cmd, cwd=cwd, check=True)
    except subprocess.CalledProcessError as e:
        logging.error(e)
        exit(1)

    logging.info("test pass")

def prove_wrapper(config, directory):
    # TODO need to also check properties.sby - could have a few things to cksum and make wrapper_cksum able to check a few files
    conf = config["wrapper_proof"]
    cwd = os.path.join(directory, conf["directory"])
    cmd = ["sby", "-f", conf["sby"]]
    logging.info("attempting to run %s in %s" % (cmd, cwd))
    try:
        subprocess.run(cmd, cwd=cwd, check=True)
    except subprocess.CalledProcessError as e:
        logging.error(e)
        exit(1)

    logging.info("proof pass")

def wrapper_cksum(config, directory):
    conf = config["wrapper_cksum"]
    wrapper = os.path.join(directory, conf["directory"], conf["filename"])
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

def instantiate_module(module_name, instance_name, project_id):
    # read the data
    template = "module_instance.v"
    with open(template, 'r') as file :
        filedata = file.read()

    # replace the target strings
    filedata = filedata.replace('MODULE_NAME', module_name)
    filedata = filedata.replace('INSTANCE_NAME', instance_name)
    filedata = filedata.replace('PROJECT_ID', str(project_id))

    # return the string
    return filedata

def add_instance_to_upw(macro_verilog):
    # read the data
    upw_template = 'user_project_wrapper.sub.v'
    with open(upw_template, 'r') as file :
        filedata = file.read()

    # replace the target strings
    filedata = filedata.replace('MODULE_INSTANCES', macro_verilog)

    # overwrite the upw
    user_project_wrapper_path = os.path.join(CARAVEL_RTL_DIR, "user_project_wrapper.v")
    with open(user_project_wrapper_path, 'w') as file:
        file.write(filedata)

def cleanup(files):
    return
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

def test_caravel(config, directory):
    conf = config["caravel_test"]
    logging.info(conf)
    delete_later = []

    # copy src into caravel verilog dir
    src = directory
    dst = os.path.join(CARAVEL_RTL_DIR, os.path.basename(directory))
    try_copy(src, dst, delete_later)

    # instantiate inside user project wrapper
    macro_verilog = instantiate_module(conf["module_name"], conf["instance_name"], conf["id"])
    add_instance_to_upw(macro_verilog)

    # copy test inside caravel
    src = os.path.join(directory, conf["directory"])
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

def test_interface(config, directory):
    conf = config["gds"]
    powered_v_filename = os.path.join(directory, conf["directory"], conf["lvs_filename"])

    with open(powered_v_filename) as fh:
        powered_v = fh.readlines()
      
    with open("interface.txt") as fh:
        for io in fh.readlines():
            if io not in powered_v:
                logging.error("io port not found in %s: %s" % (powered_v_filename, io.strip()))
                exit(1)
        
    logging.info("module interface pass")

def test_gds(config, directory):
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


