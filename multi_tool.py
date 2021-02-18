#!/usr/bin/env python3
import argparse
import logging
from collect import *
from test_repo import *

def parse_config(config_file, required_keys):
    with open(config_file, 'r') as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            logging.error(exc)
   
    for key in required_keys:
        if key not in config:
            logging.error("key %s not found" % key)
            exit(1)

    logging.info("config %s pass" % config_file)
    return config

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="test a project repo")
    subparsers = parser.add_subparsers(help='help for subcommand', dest="command")

    parser_single = subparsers.add_parser('single', help='tests for a single repo')
    parser_group  = subparsers.add_parser('group', help='utilities for working with a group of projects')

    parser_single.add_argument('--directory', help="directory that defines the project", action='store', required=True)
    parser_single.add_argument('--test-module', help="run the module's test", action='store_const', const=True)
    parser_single.add_argument('--prove-wrapper', help="check the wrapper proof", action='store_const', const=True)
    parser_single.add_argument('--wrapper-cksum', help="check the wrapper md5sum is what it should be", action='store_const', const=True)
    parser_single.add_argument('--test-caravel', help="check the caravel test", action='store_const', const=True)
    parser_single.add_argument('--test-gds', help="check the gds", action='store_const', const=True)
    parser_single.add_argument('--test-interface', help="check the module's interface using powered Verilog", action='store_const', const=True)
    parser_single.add_argument('--test-all', help="run all the checks", action='store_const', const=True)

    parser_group.add_argument('--config', help="the config file listing all project directories", required=True)
    parser_group.add_argument('--create-config', help="create the OpenLANE configs for user project wrapper", action='store_const', const=True)
    parser_group.add_argument('--copy-gds', help="copy the projects GDS and LEF files", action='store_const', const=True)
    parser_group.add_argument('--test-all', help="run all the tests on each project", action='store_const', const=True)

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

    if args.command == 'single':
        # get rid of any trailing /
        directory = os.path.normpath(args.directory)
        yaml_file = os.path.join(directory, 'info.yaml')
        config = parse_config(yaml_file, REQUIRED_KEYS_SINGLE )

        if args.test_module:
            test_module     (config, directory)

        if args.prove_wrapper:
            prove_wrapper   (config, directory)

        if args.wrapper_cksum:
            wrapper_cksum   (config, directory)

        if args.test_caravel:
            test_caravel    (config, directory)

        if args.test_gds:
            test_gds        (config, directory)

        if args.test_interface:
            test_interface  (config, directory)

        if args.test_all:
            test_all        (config, directory)

    elif args.command == 'group':
        config = parse_config(args.config, REQUIRED_KEYS_GROUP)
        config['project_configs'] = []
        # parse and store all the separate project's configs
        for project_dir in config['projects']:
            yaml_file = os.path.join(project_dir, 'info.yaml')
            config['project_configs'].append(parse_config(yaml_file, REQUIRED_KEYS_SINGLE))

        if not (len(config['projects']) > 0 and len(config['projects']) <= 16):
            logging.error("bad number of projects - must be > 0 and <= 16")
            exit(1)

        # create all the OpenLane config for the user project wrapper
        if args.create_config:
            create_config(config)

        # copy gds to correct place
        if args.copy_gds:
            copy_gds(config)

        # runs each project's tests
        if args.test_all:
            for project_config in config['project_configs']:
                test_all(project_config, project_dir)

    else:
        logging.info("provide either single or group subcommand")
