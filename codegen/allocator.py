import itertools
from typing import Dict, Tuple
import logging

def allocate_macros(
    design_size_x: int,
    design_size_y: int,
    h_edge: int,
    v_edge: int,
    projects,
    allocation_policy: str
) -> Dict[int, Tuple[int, int]]:

    if allocation_policy == "legacy":
        return legacy_allocation(design_size_x, design_size_y, h_edge, v_edge, projects)

    logging.critical(f"unknown allocation policy {allocation_policy}")
    exit(1)

def legacy_allocation(
    design_size_x: int,
    design_size_y: int,
    x_edge: int,
    y_edge: int,
    projects,
) -> Dict[int, Tuple[int, int]]:
    
    allocation = {}

    macro_x = 360
    macro_y = 360

    x_space = (design_size_x  - 2 * x_edge - (4 * macro_x)) / 3
    y_space = (design_size_y  - 2 * y_edge - (4 * macro_y)) / 3

    for id_, (px, py) in enumerate(itertools.product(range(4), range(4))):
        allocation[id_] = (
            int(x_edge + (x_space + macro_x)  * px),
            int(y_edge + (y_space + macro_y)  * py)
        )
    
    return allocation