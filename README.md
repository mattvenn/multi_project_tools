# Multi project tools

A tool to help automate verification of sub projects and collect and harden them into the final submission.

## Config file

[projects.yaml](projects.yaml) contains a list of projects and system wide config.

## Test everything

     ./multi_tool.py --config projects.yaml  --test-all --force-delete

This command will run all the tests against all projects: 

* check config has correct keys
* runs a module test given Makefile and recipe
* runs the caravel simulation given Makefile and recipe
* runs formal proof on wrapper
* checks wrapper md5sum is correct (if doing an LVS with gds and powered verilog, then is there any point in doing md5sum on wrapper?)
* TODO checks final gds is correct size, has correct io, has correct number of tristate buffers
    * run lvs against powered verilog and gds - check pass
    * search powered verilog for module interface

This functionality is contained within the [Project class](project.py)

To choose a single project, provide the --directory argument.

## Generate OpenLANE config

    ./multi_tool.py --config projects.yaml  --copy-gds --create-openlane-config

This command will get everything ready for a complete system test and hardening of user_project_wrapper:

* copy each project's GDS/LEF to the correct place
* generate OpenLANE configuration for user_project_wrapper (macro placement and obstructions)
* instantiate all the projects inside user_project_wrapper.v, 
* TODO build the include file for Caravel RTL and config

This functionality is contained within the [Collection class](collect.py)

## Done by hand

* run OpenLANE to harden user_project_wrapper: cd $CARAVEL_ROOT/openlane ; make user_project_wrapper

## TODO

* TODO still haven't hardened upw. use mpw-one-c?
* caravel test duplication is ugly
* include files for each project, add to project yaml - try to avoid duplication in the makefiles
* template repository with everything in the right place and a default yaml
