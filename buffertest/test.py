import cocotb
from cocotb.triggers import Timer

@cocotb.test()
async def test_output_z(dut):

    # power up
    dut.vccd1 <= 1
    dut.vssd1 <= 0

    # not active
    dut.active <= 0

    await Timer(1, units="ns")

    # all outputs must be z
    assert str(dut.io_oeb.value)        == 'z' * 38
    assert str(dut.io_out.value)        == 'z' * 38
    assert str(dut.la_data_out.value)   == 'z' * 32
    assert str(dut.wbs_ack_o.value)     == 'z'
    assert str(dut.wbs_dat_o.value)     == 'z' * 32
