# Multi project tools

A tool to help automate verification of sub projects and collect and harden them into the final submission.

* Project outputs isolated with tristate buffers
* Projects are activated by the Caravel logic analyser

Projects must conform to the [specification](docs/project_spec.md). 

See this [generated index page](index.md) for some example projects.

## Schematic

![schematic](docs/tristate_wrapper.jpg)

## Dependencies

* OpenLANE & PDK installed (tested with v0.9)
* projects.yaml file with correct paths
* netgen local install: https://github.com/RTimothyEdwards/netgen - TODO use the one in the OpenLANE docker
* gdspy: https://pypi.org/project/gdspy/

## Config file

[projects.yaml](projects.yaml) contains a list of projects and system wide config.

Some tests now require a recent OpenLANE (tested with v0.9). #TODO make a note why

## Test everything

     ./multi_tool.py --config projects.yaml  --test-all --force-delete

This command will run all the tests against all projects: 

* Check config file
* Runs a module test given Makefile and recipe
* Runs the Caravel simulation given Makefile and recipe
* Runs formal proof on wrapper tristated outputs
* Checks wrapper md5sum is correct (if doing an LVS with gds and powered Verilog, then is there any point in doing md5sum on wrapper?)
* Checks GDS is correct size
* Checks GDS nothing on layer metal 5
* Run LVS against powered Verilog and GDS - requires v0.9 OpenLANE/PDK
* Checks powered Verilog has correct number of tristate buffers
* Checks powered Verilog has correct module interface

This functionality is contained within the [Project class](project.py)

To choose a single project, provide the --directory argument.

## Generate OpenLANE config

    ./multi_tool.py --config projects.yaml  --copy-gds --create-openlane-config --generate-doc

This command will get everything ready for a complete system test and hardening of user_project_wrapper:

* Copy each project's GDS/LEF to the correct place in Caravel
* Generate OpenLANE configuration for user_project_wrapper (macro placement and obstructions)
* Instantiate all the projects inside user_project_wrapper.v
* Generate documentation in index.md

This functionality is contained within the [Collection class](collect.py)

## Done by hand

run OpenLANE to harden user_project_wrapper:

    cd $CARAVEL_ROOT/openlane ; make user_project_wrapper

![hardened user project wrapper](docs/mph-16designs.png)

The above was generated with config created by this command that duplicates 1 test design 16 times:

    ./multi_tool.py --project 0 --copy-gds  --create-openlane-config --duplicate 16 --force-delete

## TODO

* test with vga_clock - as it uses .hex files. will probably break the include system
* caravel test duplication is ugly
* template repository with everything in the right place and a default yaml
* if lvs fails, return code is pass
* fetch projects from a git ref
* check license
* one of the tests make a results.xml in local directory
