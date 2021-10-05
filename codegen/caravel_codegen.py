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
) -> None:

    ### user project wrapper ###
    user_project_wrapper_filename = "user_project_wrapper.v"

    logging.info(f"generating {user_project_wrapper_filename} locally")
    generate_openlane_user_project_wrapper(projects, interface_definitions, user_project_wrapper_filename)

    if target_user_project_wrapper_path:
        logging.info(f"{user_project_wrapper_filename} to {target_user_project_wrapper_path}")
        shutil.move(user_project_wrapper_filename, target_user_project_wrapper_path)
    else:
        logging.info(f"leaving {user_project_wrapper_filename} here")
    
    ### user project includes ###
    user_project_includes_filename = "user_project_includes.v"

    logging.info(f"generating {user_project_includes_filename} locally")
    generate_openlane_user_project_include(projects, user_project_includes_filename)

    if target_user_project_includes_path:
        logging.info(f"{user_project_includes_filename} to {target_user_project_includes_path}")
        shutil.move(user_project_includes_filename, target_user_project_includes_path)
    else:
        logging.info(f"leaving {user_project_includes_filename} here")
    

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

def generate_openlane_user_project_wrapper(projects, interface_definitions, outfile):
    verilog_snippets: List[str] = []

    ### generate header ###
    with open("codegen/caravel_iface_header.txt", "r") as f:
        for line in f.read().split("\n"):
            verilog_snippets.append(line)
    verilog_snippets.append("")

    ### include caravel_interface.txt ###

    ### generate boilerplate verilog ###

    ### generate enable wires ###
    verilog_snippets.append("    // generate active wires")
    verilog_snippets.append("    wire [31: 0] active;")
    verilog_snippets.append("    assign active = la_data_in[31:0];")
    verilog_snippets.append("")

    ### split remaining 96 logic analizer wires into 3 chunks ###
    verilog_snippets.append("    // split remaining 96 logic analizer wires into 3 chunks")
    verilog_snippets.append("    wire [31: 0] la1_data_in, la1_data_out, la1_oenb;")
    verilog_snippets.append("    assign la1_data_in = la_data_in[63:32];")
    verilog_snippets.append("    assign la1_data_out = la_data_out[63:32];")
    verilog_snippets.append("    assign la1_oenb = la_oenb[63:32];")
    verilog_snippets.append("")

    verilog_snippets.append("    wire [31: 0] la2_data_in, la2_data_out, la2_oenb;")
    verilog_snippets.append("    assign la2_data_in = la_data_in[95:64];")
    verilog_snippets.append("    assign la2_data_out = la_data_out[95:64];")
    verilog_snippets.append("    assign la2_oenb = la_oenb[95:64];")
    verilog_snippets.append("")

    verilog_snippets.append("    wire [31: 0] la3_data_in, la3_data_out, la3_oenb;")
    verilog_snippets.append("    assign la3_data_in = la_data_in[127:96];")
    verilog_snippets.append("    assign la3_data_out = la_data_out[127:96];")
    verilog_snippets.append("    assign la3_oenb = la_oenb[127:96];")
    verilog_snippets.append("")

    ### generate project includes ###

    for project in projects:
        verilog_snippets.append(
            generate_openlane_user_project_wrapper_instance(
                project.title,
                project.id,
                project.interfaces,
                interface_definitions
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
    interface_defs: Dict[str, Dict[str, int]]
) -> str:
    verilog_name = macro_name.lower().replace(" ", "_")
    
    verilog_snippet: List[str] = []
    verilog_snippet.append(f"    wrapped_{verilog_name} wrapped_{verilog_name}_{instance_name}(")
    
    for macro_interface in interfaces:
        for wire_name, width in interface_defs[macro_interface].items():
            if wire_name == "active":
                verilog_snippet.append(f"        .{wire_name} ({wire_name}[{instance_name}]),")
            elif width == 1:
                verilog_snippet.append(f"        .{wire_name} ({wire_name}),")
            else:
                verilog_snippet.append(f"        .{wire_name} ({wire_name}[{width - 1}:0]),")

    # werilog likes complaining about trailing commas, remove the last one
    verilog_snippet[-1] = verilog_snippet[-1][:-1]

    verilog_snippet.append(f"    );")
    verilog_snippet.append("")

    return "\n".join(verilog_snippet)