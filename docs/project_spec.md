# Multi project specification - DRAFT

Project provides an info.yaml file at the top level directory.
Here is an example configuration: https://github.com/mattvenn/wrapped_frequency_counter/blob/main/info.yaml

## Information

Project description, author, image, github repo, license.

## Caravel test

A test that runs within Caravel context. Must include a Makefile and firmware that activates the project and has a pass/fail test.

## Module test

More complete tests for the module. Must include a Makefile with pass/fail tests.

## Wrapper proof

Correctly configured sby configuration file and properties that verify tristate buffers are working correctly.
Unfortunately the formal tools can't deal with Z states yet, so the wrapper replaces tristates with muxes for the test.

## Wrapper checksum

Removing the module's name and instantiation, the wrapper md5sum should be correct. (Test may be removed)

## OpenLANE config

Configuration for re-hardening if required.

## Project source files

A list of all the source files. These are used in 2 contexts: simulation inside Caravel (files are included) and OpenLANE hardening (files are blackboxed).

## GDS

GDS, LEF and post synth netlist files. These are used to check size, layers and LVS. With LVS correct, module interface can be verified and number of tristate buffers verified.
