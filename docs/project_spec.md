# Multi project specification - updated for MPW3

Project provides an info.yaml file at the top level directory.
See example specs in the [project index](https://github.com/mattvenn/zero_to_asic_mpw3/blob/mpw3/README.md)

# Updates for MPW3

* Optional interface - use only the parts of the shared interface you need
* Don't require pin_config for OpenLANE
* Don't require 300x300um size. You can make it smaller, although it should be at least 200 um tall to pick up the power lines
* Remove github link in the project section
* LA0 is now used for selecting the active project, LA1 is used for communication between RISCV & your project - this means your firmware.c needs to change.

## Information

    project: 
      title: "RGB Mixer"
      description: "reads 3 encoders and generates PWM signals to drive an RGB LED"
      author: "Matt Venn"       
      picture: doc/schematic.jpg
      license: LICENSE

## Interfaces

Each project must have some required interfaces. See the example https://github.com/mattvenn/wrapped_project_template/blob/mpw3/wrapper.v

        power: {vccd1: 1, vssd1: 1}
        clock: {wb_clk_i: 1}
        active: {active: 1}

Then there are the optional interfaces. These can be turned on my commenting the ifdefs at the top of the file.

        gpio: {io_in: 38, io_out: 38, io_oeb: 38}
        la1: {la1_data_in: 32, la1_data_out: 32, la1_oenb: 32}
        la2: {la2_data_in: 32, la2_data_out: 32, la2_oenb: 32}
        la3: {la3_data_in: 32, la3_data_out: 32, la3_oenb: 32}
        irq: {user_irq: 3}
        clk2 : {user_clock2: 1}
        wishbone: {wb_rst_i: 1, wbs_stb_i: 1, wbs_cyc_i: 1, wbs_we_i: 1, wbs_sel_i: 4, wbs_dat_i: 32, wbs_adr_i: 32, wbs_ack_o: 1, wbs_dat_o: 32}

By having optional interfaces, you can use less pins, and make your design smaller.

## Caravel test

A test that runs within Caravel context. Must include a Makefile and firmware that activates the project and has a pass/fail test.

To create:

* make a new directory in caravel_user_project/verilog/dv/
* copy the firmware and Makefile from the example project
* adjust the tests for your application
* adjust the firmware to enable your design (setting the active pin in wrapper.v)
* make sure that there is a Makefile rule that runs the test with a pass/fail exit status

Then copy this directory to your project making sure to include:

* Makefile
* firmware
* testbench

Update the info.yaml config:

    caravel_test:
      recipe: "coco_test"                   # name of the recipe
      directory: "caravel_rgb_mixer"        # directory that contains the Makefile, firmware, testbench
      id: 0                                 # ID of your project - request this from Matt, 
      module_name: "wrapped_rgb_mixer"      # module name for instantiation inside user project wrapper

## Module test

More complete tests for the module. Must include a Makefile with pass/fail tests.

    module_test:
      recipe: "all"             # name of the recipe to run
      directory: "rgb_mixer"    # directory of the Makefile
      makefile: "Makefile"      # name of the Makefile

## Wrapper proof

Correctly configured sby configuration file and properties that verify tristate buffers are working correctly.
Unfortunately the formal tools can't deal with Z states yet, so the wrapper replaces tristates with muxes for the test.

    wrapper_proof:
      directory: "."            # directory containing the properties
      sby: "properties.sby"     # sby file correctly configured for your design

## OpenLANE config

Configuration for re-hardening if required.

    openlane:
      config: "config.tcl"

## Project source files

A list of all the source files. These are used in 2 contexts: simulation inside Caravel (files are included) and OpenLANE hardening (files are blackboxed).

    source:
        - wrapper.v
        - rgb_mixer/src/debounce.v
        - rgb_mixer/src/encoder.v
        - rgb_mixer/src/pwm.v
        - rgb_mixer/src/rgb_mixer.v

## GDS

GDS, LEF and post synth netlist files. These are used to layers and LVS. With LVS correct, module interface can be verified.

    gds:
      directory: "gds"          # directory containing the following files:
      gds_filename: "wrapped_rgb_mixer.gds"
      lef_filename: "wrapped_rgb_mixer.lef"
      lvs_filename: "wrapped_rgb_mixer.lvs.powered.v"

