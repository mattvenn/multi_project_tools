yosys -p 'read_liberty -lib ./merged.lib;  read_verilog -sv wrapped_picorv32.v ; prep -top wrapped_picorv32 ; dump w:wbs_dat_o %ci1 c:* %i t:sky*ebufn* %d'
