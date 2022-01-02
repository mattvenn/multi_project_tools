import cocotb
from cocotb.triggers import Timer

@cocotb.test()
async def test_output_z(dut):

    # power up
    dut.vccd1.value = 1
    dut.vssd1.value = 0

    # not active
    dut.active.value = 0

    for i in range(10):
        await Timer(1, units="ns")

        # all outputs that exist must be z
        if getattr(dut, "io_oeb", None):
            assert str(dut.io_oeb.value)        == 'z' * 38
        if getattr(dut, "io_out", None):
            assert str(dut.io_out.value)        == 'z' * 38
        # la
        if getattr(dut, "la_data_out", None):
            assert str(dut.la_data_out.value)   == 'z' * 32
        # wb
        if getattr(dut, "wbs_ack_o", None):
            assert str(dut.wbs_ack_o.value)     == 'z'
        if getattr(dut, "wbs_dat_o", None):
            assert str(dut.wbs_dat_o.value)     == 'z' * 32
        # rambus
        if getattr(dut, "rambus_wb_clk_o", None):
            assert str(dut.rambus_wb_clk_o.value)     == 'z' * 1
        if getattr(dut, "rambus_wb_rst_o", None):
            assert str(dut.rambus_wb_rst_o.value)     == 'z' * 1
        if getattr(dut, "rambus_wb_stb_o", None):
            assert str(dut.rambus_wb_stb_o.value)     == 'z' * 1
        if getattr(dut, "rambus_wb_cyc_o", None):
            assert str(dut.rambus_wb_cyc_o.value)     == 'z' * 1
        if getattr(dut, "rambus_wb_we_o", None):
            assert str(dut.rambus_wb_we_o.value)      == 'z' * 1
        if getattr(dut, "rambus_wb_sel_o", None):
            assert str(dut.rambus_wb_sel_o.value)     == 'z' * 4
        if getattr(dut, "rambus_wb_dat_o", None):
            assert str(dut.rambus_wb_dat_o.value)     == 'z' * 32
        if getattr(dut, "rambus_wb_adr_o", None):
            assert str(dut.rambus_wb_adr_o.value)     == 'z' * 10


