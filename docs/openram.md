# OpenRAM

Using OpenRAM isn't very straight forward yet.

* build pdk with OpenRAM support
* add https://github.com/embelon/wrapped_wb_openram_shim/tree/mpw3 to projects.yaml
* use --openram option when creating the openlane config or testing the ram

## Install the PDK with OpenRAM support on

From caravel_user_project setup as usual, instead of running make pdk, I do this:

    export INSTALL_SRAM=yes
    make pdk

## What --openram does

### RTL

* OpenRAM included in the uprj_netlist.v
* OpenRAM instantiated in user_project_wrapper.v
* add extra wires
* connects the shim and wires it up to OpenRAM 

## Hardening

* what was at position 0 move to the end
* add OpenRAM to macro at pos 0
* swaps anything in position 5 (next to OpenRAM) and exchange with the wishbone shim to keep them close
* OpenRAM doesn't play very well with OpenLANE, and one of the work arounds to get a good result is to add an obstruction layer on MET4,3,2 around it
* run make user_project_wrapper as normal
* you will get DRC errors that you can ignore
* Run the precheck, this will show if there are any real DRC errors to fix.

## Todo

* OpenRAM block gets placed with hardcoded co-ordinates in collect.py and also in config.tcl (for the obstruction layer)
