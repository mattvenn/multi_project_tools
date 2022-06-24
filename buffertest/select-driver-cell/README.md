# Check that all outputs are driven by tristates

From wrapped_cpr.v line 24097:

     sky130_fd_sc_hd__ebufn_8 _2711_ (.A(net35),
        .TE_B(_1077_),
        .VGND(vssd1),
        .VNB(vssd1),
        .VPB(vccd1),
        .VPWR(vccd1),
        .Z(io_out[0]));

This is correct, the output of the trisate (Z) connects to io_out.

However in wrapped_picorv32.v line 281158:

     sky130_fd_sc_hd__ebufn_8 _21483_ (.A(\wb_picorv32_0.o_wb_data[11] ),
        .TE_B(_09556_),
        .VGND(vssd1),
        .VNB(vssd1),
        .VPB(vccd1),
        .VPWR(vccd1),
        .Z(net108));

The tristate is then followed by a buffer (line 315982):

     sky130_fd_sc_hd__buf_12 repeater108 (.A(wbs_dat_o[11]),
        .VGND(vssd1),
        .VNB(vssd1),
        .VPB(vccd1),
        .VPWR(vccd1),
        .X(net108));

Which breaks the tristate output. This is due to a bug in OpenLane with inout ports.

I'm trying to formulate a yosys select statement that will find all the outputs and assert they are of type ebuf.
This is close but doesn't work yet.

    yosys -p 'read_liberty -lib ./merged.lib;  read_verilog -sv wrapped_picorv32.v ; prep -top wrapped_picorv32 ; dump w:wbs_dat_o %ci1 c:* %i t:sky*ebufn* %d'
