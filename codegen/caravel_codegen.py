from typing import List, Dict, Optional
from tabulate import tabulate
import shutil
import os
import logging

def generate_openlane_files(
    projects, 
    interface_definitions: Dict[str, Dict[str, int]],
    target_user_project_wrapper_path: Optional[str],
    target_user_project_includes_path: Optional[str],
    target_caravel_includes_path: Optional[str],
    openram,
    gl,
    config # this is getting silly now. These generators should be objects and get the config by default.
) -> None:

    ### user project wrapper ###
    user_project_wrapper_filename = "user_project_wrapper.v"

    logging.info(f"generating {user_project_wrapper_filename} locally")
    generate_openlane_user_project_wrapper(projects, interface_definitions, user_project_wrapper_filename, openram, config)

    if target_user_project_wrapper_path:
        logging.info(f"{user_project_wrapper_filename} to {target_user_project_wrapper_path}")
        shutil.move(user_project_wrapper_filename, target_user_project_wrapper_path)
    else:
        logging.info(f"leaving {user_project_wrapper_filename} here")
    
    ### user project includes ###
    ### used for blackboxing the projects for the openlane config.tcl
    user_project_includes_filename = "user_project_includes.v"

    logging.info(f"generating {user_project_includes_filename} locally")
    generate_openlane_user_project_include(projects, user_project_includes_filename)

    if target_user_project_includes_path:
        logging.info(f"{user_project_includes_filename} to {target_user_project_includes_path}")
        shutil.move(user_project_includes_filename, target_user_project_includes_path)
    else:
        logging.info(f"leaving {user_project_includes_filename} here")
    
    ### caravel includes ###
    ### for simulation
    caravel_includes_filename = "uprj_netlists.v"

    logging.info(f"generating {caravel_includes_filename} locally")
    generate_caravel_includes(projects, caravel_includes_filename, openram, gl)

    if target_caravel_includes_path:
        logging.info(f"{caravel_includes_filename} to {target_caravel_includes_path}")
        shutil.move(caravel_includes_filename, target_caravel_includes_path)
    else:
        logging.info(f"leaving {caravel_includes_filename} here")
    

def generate_openlane_user_project_include(projects, outfile):
    include_snippets: List[str] = []

    headers = ["project id", "title", "author", "repo", "commit"]
    table = [headers]
    for project in projects:
        table.append([project.id, project.title, project.author, project.repo, project.commit])

    for row in tabulate(
        table, 
        headers='firstrow', 
        tablefmt="pretty",
        colalign=("left" for _ in headers)
    ).split("\n"):
        include_snippets.append(f"// {row}")

    for project in projects:
        top_module = project.get_top_module()
        top_path = os.path.join(os.path.basename(project.directory), top_module)
        include_snippets.append(f"`include \"{top_path}\" // {project.id}")

    with open(outfile, "w") as f:
        f.write("\n".join(include_snippets))

def generate_caravel_includes(projects, outfile, openram, gl):
    with open("codegen/uprj_netlists.txt", "r") as f:
        filedata = f.read()

    gl_includes = ""
    project_includes = ""
    for project in projects:
        project_includes += ("// %s\n" % project)
        for path in project.get_module_source_paths(absolute=False):
            path = os.path.join(os.path.basename(project.directory), path)
            project_includes += ('	`include "%s"\n' % path)

        gl_includes += ('`include "%s"\n' % project.config['gds']['lvs_filename'])

    if openram:
        project_includes += ('	// include openram model\n')
        project_includes += ('	`include "libs.ref/sky130_sram_macros/verilog/sky130_sram_1kbyte_1rw1r_32x256_8.v"\n')
        project_includes += ('	// Wishbone bridge to split traffic into 2 streams: for user\n')
        project_includes += ('	// project and OpenRAM\n')
        project_includes += ('	`include "wb_bridge/src/wb_bridge_2way.v"\n')
        project_includes += ('	// Wishbone dual port wrapper for OpenRAM\n')
        project_includes += ('	`include "wb_openram_wrapper/src/wb_port_control.v"\n')
        project_includes += ('	`include "wb_openram_wrapper/src/wb_openram_wrapper.v"\n')


    # GL takes too long for all of Caravel, so just use the GL instead of all the normal RTL includes
    if gl == True:
        filedata = filedata.replace('RTL_INCLUDES', gl_includes)
    else:
        filedata = filedata.replace('RTL_INCLUDES', project_includes)

    with open(outfile, "w") as f:
        f.write(filedata)


def generate_openlane_user_project_wrapper(projects, interface_definitions, outfile, openram, config):
    verilog_snippets: List[str] = []

    ### generate header ###
    with open("codegen/caravel_iface_header.txt", "r") as f:
        for line in f.read().split("\n"):
            verilog_snippets.append(line)
    verilog_snippets.append("")

    ### include openram stuff ###
    if openram:
        with open("codegen/caravel_iface_openram.txt", "r") as f:
            for line in f.read().split("\n"):
                verilog_snippets.append(line)

    ### generate project includes ###

    verilog_snippets.append("    // start of user project module instantiation")
    for project in projects:
        verilog_snippets.append(
            generate_openlane_user_project_wrapper_instance(
                project.module_name,
                project.id,
                project.interfaces,
                interface_definitions,
                config,
                openram
            )
        )
    
    ### append footer ###
    verilog_snippets.append("    // end of module instantiation")
    verilog_snippets.append("")
    verilog_snippets.append("endmodule	// user_project_wrapper")
    verilog_snippets.append("`default_nettype wire")

    with open(outfile, "w") as f:
        f.write("\n".join(verilog_snippets))

def generate_openlane_user_project_wrapper_instance(
    macro_name: str,
    instance_name: str,    
    interfaces: List[str],
    interface_defs: Dict[str, Dict[str, int]],
    config,
    openram
) -> str:
    verilog_name = macro_name
    
    verilog_snippet: List[str] = []
    verilog_snippet.append(f"    {verilog_name} {verilog_name}_{instance_name}(")

    
    for macro_interface in interfaces:
        if macro_interface == "power":
            verilog_snippet.append("        `ifdef USE_POWER_PINS")

        for wire_name, width in interface_defs[macro_interface].items():
            dst_wire_name = wire_name
            if openram:
                # translate the signal names so the wb_bridge is used
                if wire_name in config['openram_support']['wb_uprj_bus']:
                    dst_wire_name = config['openram_support']['wb_uprj_bus'][wire_name]

            if wire_name == "active":
                verilog_snippet.append(f"        .{wire_name} ({dst_wire_name}[{instance_name}]),")
            elif width == 1:
                verilog_snippet.append(f"        .{wire_name} ({dst_wire_name}),")
            else:
                verilog_snippet.append(f"        .{wire_name} ({dst_wire_name}[{width - 1}:0]),")

        if macro_interface == "power":
            verilog_snippet.append("        `endif")

    # werilog likes complaining about trailing commas, remove the last one
    verilog_snippet[-1] = verilog_snippet[-1][:-1]

    verilog_snippet.append(f"    );")
    verilog_snippet.append("")

    return "\n".join(verilog_snippet)
