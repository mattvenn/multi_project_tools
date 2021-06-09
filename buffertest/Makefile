VERILOG_SOURCES += wrapped_design.v
COMPILE_ARGS=-I $(PDK_ROOT)/sky130A/ 

# MODULE is the basename of the Python test file
MODULE = test

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim

test: wrapped_design.v results.xml
	! grep failure results.xml

wrapped_design.v:
	cat header.v $(POWERED_VERILOG) > wrapped_design.v

clean::
	rm -rf wrapped_design.v results.xml __pycache__ sim_build

.PHONY: clean all
