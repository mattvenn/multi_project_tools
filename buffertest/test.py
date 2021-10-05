import cocotb
from cocotb.triggers import Timer

@cocotb.test()
async def test_output_z(dut):

    # power up
    dut.vccd1 <= 1
    dut.vssd1 <= 0

    # not active
    dut.active <= 0

    for i in range(10):
        await Timer(1, units="ns")

        # all outputs that exist must be z
        if getattr(dut, "io_oeb", None):
            assert str(dut.io_oeb.value)        == 'z' * 38
        if getattr(dut, "io_out", None):
            assert str(dut.io_out.value)        == 'z' * 38
        if getattr(dut, "la_data_out", None):
            assert str(dut.la_data_out.value)   == 'z' * 32
        if getattr(dut, "wbs_ack_o", None):
            assert str(dut.wbs_ack_o.value)     == 'z'
        if getattr(dut, "wbs_dat_o", None):
            assert str(dut.wbs_dat_o.value)     == 'z' * 32
