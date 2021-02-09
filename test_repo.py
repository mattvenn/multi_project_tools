#!/usr/bin/env python3
import yaml
import argparse
import os, sys
import subprocess
import logging
import hashlib

REQUIRED_KEYS = [ "project", "caravel_test", "module_test", "wrapper_proof", "wrapper_cksum", "openlane", "gds" ]
WRAPPER_MD5SUM = "0ec8fdff7ae891b1b156030a841d1800"

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

def test_caravel():
    """
    copy source into caravel
    instantiate inside user project wrapper
    copy test inside caravel
    run makefile
    """

def test_gds():
    """
    need the LEF for this?
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
    args = parser.parse_args()

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
