# Multi project tools

Tools to help automate verification of sub projects and collect and harden them into the final submission.

## Test a project repo

[test_repo.py](test_repo.py), reads a projects [info.yaml](info.yaml) file and runs the following tests:

* check config has correct keys
* runs a module test given Makefile and recipe
* TODO runs the caravel simulation given Makefile and recipe
* runs formal proof on wrapper
* checks wrapper md5sum is correct
* TODO checks final gds is correct size, has correct io, has correct number of tristate buffers

## Collect projects

Using a list of repositories:

* run test_repo.py for each one
* copy gds and lef to correct place
* instantiate in user_project_wrapper
* build the OpenLANE config

## Done by hand

* run OpenLANE to harden user_project_wrapper
