#!/usr/bin/env python3
import yaml
import argparse
import os

REQUIRED_KEYS = [ "description", "owner", "caravel_test_makefile", "module_test_makefile", "openlane_config" ]

def yaml_test():
    yaml_file = os.path.join(args.directory, 'info.yaml')
    with open(yaml_file, 'r') as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            exit(1)
   
    for key in REQUIRED_KEYS:
        assert key in config, "key %s not found" % key

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="multi project collect")
    parser.add_argument('--directory', help="directory that defines the project", action='store', required=True)
    parser.add_argument('--check-yaml', help="checks all keys are present in yaml file", action='store_const', const=True)
    args = parser.parse_args()

    if args.check_yaml:
        yaml_test()

