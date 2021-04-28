# Multi project specification - DRAFT

Project provides an info.yaml file at the top level directory.
See example specs in the [project index](../index.md)

## Information

    project: 
      title: "RGB Mixer"
      description: "reads 3 encoders and generates PWM signals to drive an RGB LED"
      author: "Matt Venn"       
      picture: doc/schematic.jpg
      github: https://github.com/mattvenn/wrapped_rgb_mixer/tree/caravel-mpw2
      license: LICENSE

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
      id: 0                                 # ID of your project, 
      module_name: "wrapped_rgb_mixer"      # module name for instantiation inside user project wrapper
      instance_name: "wrapped_rgb_mixer"    # instance name for instantiation inside user project wrapper

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

GDS, LEF and post synth netlist files. These are used to check size, layers and LVS. With LVS correct, module interface can be verified and number of tristate buffers verified.

    gds:
      directory: "gds"          # directory containing the following files:
      gds_filename: "wrapped_rgb_mixer.gds"
      lef_filename: "wrapped_rgb_mixer.lef"
      lvs_filename: "wrapped_rgb_mixer.lvs.powered.v"

