# OpenRAM

Using OpenRAM isn't very straight forward yet.

* build pdk with OpenRAM support
* add https://github.com/embelon/wrapped_wb_openram_shim/tree/mpw3 to projects.yaml
* use --openram option when creating the openlane config or testing the ram

## Install the PDK with OpenRAM support on

From caravel_user_project setup as usual, instead of running make pdk, I do this:

    export SRAM_INSTALL=yes
    make pdk

## What --openram does

### RTL

* OpenRAM included in the uprj_netlist.v
* OpenRAM instantiated in user_project_wrapper.v
* add extra wires
* connects the shim and wires it up to OpenRAM 

## Hardening

* add OpenRAM to macro - at the moment this is manually placed in the bottom right corner
* OpenRAM doesn't play very well with OpenLANE, and one of the work arounds to get a good result is to add an obstruction layer on MET4 around it
* run make user_project_wrapper as normal
* If you get DRC errors or your precheck fails, you can try the following:
    *  

