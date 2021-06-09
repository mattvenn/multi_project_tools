#!/usr/bin/env python3
import logging, sys, argparse
from collect import Collection

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="test a project repo")
    parser.add_argument('--force-delete', help='instead of aborting on existing files, delete them', action='store_const', const=True)
    subparsers = parser.add_subparsers(help='help for subcommand', dest="command")

    parser.add_argument('--config', help="the config file listing all project directories", default='projects.yaml')
    parser.add_argument('--project', help="just run for a single project, supply project ID", type=int)

    parser.add_argument('--test-module', help="run the module's test", action='store_const', const=True)
    parser.add_argument('--prove-wrapper', help="check the wrapper proof", action='store_const', const=True)
    parser.add_argument('--test-caravel', help="check the caravel test", action='store_const', const=True)
    parser.add_argument('--test-gds', help="check the gds", action='store_const', const=True)
    parser.add_argument('--test-lvs', help="check the gds against powered verilog", action='store_const', const=True)
    parser.add_argument('--test-interface', help="check the module's interface using powered Verilog", action='store_const', const=True)
    parser.add_argument('--test-tristate-num', help="check powered verilog has correct number of tristate buffers", action='store_const', const=True)
    parser.add_argument('--test-tristate-z', help="check outputs are z when not active", action='store_const', const=True)
    parser.add_argument('--test-all', help="run all the checks for each project", action='store_const', const=True)

    parser.add_argument('--create-openlane-config', help="create the OpenLANE configs for user project wrapper", action='store_const', const=True)
    parser.add_argument('--copy-gds', help="copy the projects GDS and LEF files", action='store_const', const=True)
    parser.add_argument('--generate-doc', help="generate a index.md file with information about each project", action='store_const', const=True)
    parser.add_argument('--fill', help="for testing, repeat the given projects this number of times", type=int)

    args = parser.parse_args()

    # setup log
    log_format = logging.Formatter('%(asctime)s - %(module)-10s - %(levelname)-8s - %(message)s')
    # configure the client logging
    log = logging.getLogger('')
    # has to be set to debug as is the root logger
    log.setLevel(logging.INFO)

    # create console handler and set level to info
    ch = logging.StreamHandler(sys.stdout)
    # create formatter for console
    ch.setFormatter(log_format)
    log.addHandler(ch)

    collection = Collection(args)

    # run any tests specified by arguments
    collection.run_tests()

    # create all the OpenLANE config for the user collection wrapper
    if args.create_openlane_config:
        collection.create_openlane_config()

    # copy gds to correct place
    if args.copy_gds:
        collection.copy_gds()

    if args.generate_doc:
        collection.generate_docs()
