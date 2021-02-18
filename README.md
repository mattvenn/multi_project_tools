# Multi project tools

Tools to help automate verification of sub projects and collect and harden them into the final submission.

## Test a single project repo

`multi_project.py single` needs a project's [info.yaml](info.yaml) file and can run the following tests:

* check config has correct keys
* runs a module test given Makefile and recipe
* runs the caravel simulation given Makefile and recipe
* runs formal proof on wrapper
* checks wrapper md5sum is correct
* TODO checks final gds is correct size, has correct io, has correct number of tristate buffers
    * run lvs against powered verilog and gds - check pass
    * search powered verilog for module interface and 

This functionality is contained within [test_repo.py](test_repo.py)

### wrapper md5sum

* if doing an LVS with gds and powered verilog, then is there any point in doing md5sum on wrapper?

## Tools for group submission with multiple projects

`multi_project.py group` needs a list of projects in a [collect.yaml](collect.yaml) file. It can do the following:

TODO what to do about project ids?

* run test_repo.py for each one
* copy gds and lef to correct place
* instantiate in user_project_wrapper
    * TODO actually use the generatred verilog
* build the OpenLANE config
    * TODO test it

This functionality is contained within [collect.py](collect.py)

## Done by hand

* run OpenLANE to harden user_project_wrapper
* TODO still haven't hardened upw. use mpw-one-c?
