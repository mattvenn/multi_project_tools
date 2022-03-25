import cv2
from utils import *
import numpy as np

def check_collision(ent1, ent2):
    def extract_points(ent):
        start = ent["design_location"]
        end = [
            ent["design_location"][0] + ent["design_area"][0],
            ent["design_location"][1] + ent["design_area"][1]
        ]

        # order matters here, check_single assumes start is at 0, end at 3.
        return [
            start,
            [ent["design_location"][0], ent["design_location"][1] + ent["design_area"][1]],
            [ent["design_location"][0] + ent["design_area"][0], ent["design_location"][1]],
            end
        ]

    def check_single(pont, entpoint):
        if pont[0] > entpoint[0][0] and pont[0] < entpoint[3][0]:
            if pont[1] > entpoint[0][1] and pont[1] < entpoint[3][1]:
                return True
        return False

    ent1_points = extract_points(ent1)
    ent2_points = extract_points(ent2)
    for p in ent1_points:
        if check_single(p, ent2_points):
            return True
    for p in ent2_points:
        if check_single(p, ent1_points):
            return True
    return False

# this is a pretty ugly hack.
# we want this callback to be a method of LayoutTool, so that no global variables can be used
# however, being a method of a class means that 
# 1 - first argument is this class
# 2 - it is somehow registered in class __dict__ field
# since opencv doesn't really allow to modify it's callback procedure, we will create this funciton
# the signature is of standard callback, with class_ref added.
# in collect.py/launch_layout_tool() you can see that this function is patched with LayoutTool reference
# meaning that this behaves _exactly_ like a method of LayoutTool with two exceptions:
# - you cannot call layout_tool_instance.callback()
# - instead of self. you need to use class_ref.
def callback(class_ref, event,x,y,flags,param): 
    if event == cv2.EVENT_LBUTTONDOWN:
        if class_ref.pointerbound:
            logging.info(f"dropped cell {class_ref.pointerbound}")
            class_ref.pointerbound = None
            class_ref.update_image()
        else:
            for name, data in class_ref.layout_info.items():
                start = data["design_location"]
                end = [
                    data["design_location"][0] + data["design_area"][0],
                    data["design_location"][1] + data["design_area"][1]
                ]

                if x > start[0] and x < end[0]:
                    if y > start[1] and y < end[1]:
                        if data["grabbable"]:
                            class_ref.pointerbound = name
                            logging.info(f"picked cell {class_ref.pointerbound}")

    elif event == cv2.EVENT_MOUSEMOVE:
        if class_ref.pointerbound:
            layout_state = "good"

            class_ref.layout_info[class_ref.pointerbound]["design_location"] = (int(x), int(y))
            class_ref.layout_info[class_ref.pointerbound + "__border"]["design_location"] = (
                int(x - class_ref.border_offsets // class_ref.scalar), 
                int(y - class_ref.border_offsets // class_ref.scalar)
            )
            
            collision_map = {}
            for e in class_ref.layout_info.keys():
                collision_map[e] = False

            for ent_name, data in class_ref.layout_info.items():
                    for o_name, odata in class_ref.layout_info.items():
                            if ent_name + "__border" != o_name and ent_name != o_name + "__border":
                                if ent_name != o_name:
                                    if check_collision(data, odata):
                                        collision_map[ent_name] = True
                                        collision_map[o_name] = True
            
            for ent_name, data in class_ref.layout_info.items():
                if "__border" in ent_name:
                    if collision_map[ent_name]:
                        class_ref.layout_info[ent_name]["design_color"] = class_ref.bad_color
                        if layout_state != "bad":
                            layout_state = "warning"
                        # if there is a bad color on border, we want to add warning to main
                        e = ent_name.replace("__border", "")
                        # but only if the color isn't already bad
                        if (class_ref.layout_info[e]["design_color"] == class_ref.good_color).all():
                            class_ref.layout_info[e]["design_color"] = class_ref.warning_color
                            if layout_state != "bad":
                                layout_state = "warning"
                    else:
                        class_ref.layout_info[ent_name]["design_color"] = class_ref.warning_color
                else:
                    if collision_map[ent_name]:
                        class_ref.layout_info[ent_name]["design_color"] = class_ref.bad_color
                        layout_state = "bad"
                    else:
                        class_ref.layout_info[ent_name]["design_color"] = class_ref.good_color

            class_ref.update_image()
    pass


class LayoutTool():
    def __init__(self, collection, downscale):
        logging.info(f"launching layout tool. Found {len(collection.projects)} designs in collection")
        self.callback = None
        self.scalar = downscale
        self.area_width = int(collection.config['configuration']['user_area_width'] // self.scalar)
        self.area_height = int(collection.config['configuration']['user_area_height'] // self.scalar)
        logging.info(f"layout tool canvas = {self.area_width}x{self.area_height}, using downscale = {self.scalar}")
        logging.info(f"pass --layout-tool-downscale=x if this does not fit on your screen")
 
        self.pointerbound = None

        # values for the color scheme, these should probably be in config?
        self.background_color = np.array([20, 18, 17]) / 255.0
        self.good_color = np.array([0.0, 1.0, 0.0])
        self.bad_color = np.array([0.0, 0.0, 1.0])
        self.warning_color = np.array([0.0, 1.0, 1.0])
        self.border_offsets = 25

        # this needs to change asap, will throw if a net isn't in this dict.
        self.line_colors = {
            "la1": np.array([0.0, 1.0, 0.0]),
            "gpio": np.array([1.0, 1.0, 0.0]),
            "wishbone": np.array([0.0, 1.0, 1.0]),
            "openram": np.array([1.0, 0.0, 1.0])
        }

        # line offsets, if two cells have same nets, they would get drawn on top of each other.
        # this prevents that.
        self.loffsets = {}
        for li, lt in enumerate(self.line_colors.keys()):
            self.loffsets[lt] = np.array([5, 5]) * li

        self.lines = []
        self.image_handle = np.ones((self.area_height, self.area_width, 3)) * self.background_color

        self.layout_info = {}
        for p in collection.projects + collection.shared_projects:
            size = p.get_gds_size()
            if isinstance(size, tuple):
                caravel_data = size
            else:
                caravel_data = p.get_gds_size().tolist()
            # this should stay, as it is used for debugging. get_gds_size() is _slow_
            # caravel_data = [256, 256]
            caravel_data = (
                int(caravel_data[0] // self.scalar),
                int(caravel_data[1] // self.scalar),
            )

            design_location = (
                int(p.get_macro_pos()[0] // self.scalar),
                int(p.get_macro_pos()[1] // self.scalar)
            )

            logging.info(f"parsed {p.instance_name}, size is {caravel_data}")
            instance_name = p.instance_name.replace("wrapped_", "")
            self.layout_info[instance_name] = {
                "grabbable": True,
                "interfaces": set(p.interfaces) - set(['power', 'clock', 'active']),
                "design_area": caravel_data,
                "design_location": design_location,
                "design_color": (0.0, 1.0, 0.0)
            }

            # we also append <name> + __border to show the border.
            caravel_data = (
                int(caravel_data[0] + ((2 * self.border_offsets) // self.scalar)),
                int(caravel_data[1] + ((2 * self.border_offsets) // self.scalar))
            )

            design_location = (
                int(p.get_macro_pos()[0] // self.scalar - self.border_offsets // self.scalar),
                int(p.get_macro_pos()[1] // self.scalar - self.border_offsets // self.scalar)
            )

            self.layout_info[instance_name + "__border"] = {
                "grabbable": False,
                "interfaces": set(),
                "design_area": caravel_data,
                "design_location": design_location,
                "design_color": (0.0, 1.0, 0.0)
            }

    def set_callback(self, fun):
        self.callback = fun

    def update_netmap(self):
        nets = set()
        self.lines = []
        for macro in self.layout_info.values():
            nets |= macro["interfaces"]

        # this runs union-find based minimal spanning tree over all nets.
        # possibly this shouldn't calculate the center-center distance, but minimum distance
        # between cells. Also this is only a rough estimate on how openlane will layout the connecting
        # wires, so it might get axed anyways
        for net in nets:
            users = {}
            unionfind = {}

            for macro in self.layout_info.keys():
                if "__border" not in macro:
                    unionfind[macro] = macro

            for macro_name, macro in self.layout_info.items():
                if net in macro["interfaces"]:
                    users[macro_name] = macro["design_location"]

            distances = []
            for name_a, position_a in users.items():
                for name_b, position_b in users.items():
                    if name_a != name_b:
                        distance = (position_a[0] - position_b[0])**2 + (position_a[1] - position_b[1])**2
                        distances.append((distance, name_a, name_b))

            picked = []
            for (d, a_name, b_name) in sorted(distances):
                if unionfind[a_name] != unionfind[b_name]:
                    picked.append((a_name, b_name))
                    prev_a = unionfind[a_name]
                    unionfind[a_name] = unionfind[b_name]
                    for own, ptr in unionfind.items():
                        if ptr == prev_a:
                            unionfind[own] = unionfind[b_name]

            for p in picked:
                self.lines.append((
                    (
                        int(self.layout_info[p[0]]['design_location'][0] + self.layout_info[p[0]]['design_area'][0]/2),
                        int(self.layout_info[p[0]]['design_location'][1] + self.layout_info[p[0]]['design_area'][1]/2)
                    ),
                    (
                        int(self.layout_info[p[1]]['design_location'][0] + self.layout_info[p[1]]['design_area'][0]/2),
                        int(self.layout_info[p[1]]['design_location'][1] + self.layout_info[p[1]]['design_area'][1]/2)
                    ),
                    net                
                ))

    def update_image(self):
        self.update_netmap()
        self.image_handle = np.ones((self.area_height, self.area_width, 3)) * self.background_color
        __imnames = self.layout_info.keys()
        imnames = []
        
        # since color mixing is weird, we make sure that borders are drawn before cells.
        for i in __imnames:
            if "__border" in i:
                imnames.append(i)

        for i in __imnames:
            if "__border" not in i:
                imnames.append(i)
        
        for imname in imnames:
            data = self.layout_info[imname]
            color = np.copy(data["design_color"])
            if not self.pointerbound:
                color *= 0.6
            elif not imname.startswith(self.pointerbound):
                color *= 0.6
            
            # draw outline with 100% opacity
            cv2.rectangle(
                self.image_handle, 
                data["design_location"],
                (
                    int(data["design_location"][0] + data["design_area"][0]),
                    int(data["design_location"][1] + data["design_area"][1]),    
                ),
                color,
                2
            )
            
            # since opaqueness is weird we do this stackoverflow licensed hack
            sub_img = self.image_handle[data["design_location"][1]:data["design_location"][1] + data["design_area"][1], data["design_location"][0]:data["design_location"][0] + data["design_area"][0]]
            rect = np.ones(sub_img.shape) * color
            cv2.addWeighted(sub_img, 0.55, rect, 0.45, 0, rect)

            text_position = (
                data["design_location"][0],
                data["design_location"][1] - 10
            )

            self.image_handle[data["design_location"][1]:data["design_location"][1] + data["design_area"][1], data["design_location"][0]:data["design_location"][0] + data["design_area"][0]] = rect
            if "__border" not in imname:
                cv2.putText(self.image_handle, imname, text_position, cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

        for lstart, lend, ltype in self.lines:
            offsets = self.loffsets[ltype]
            cv2.line(self.image_handle, np.array(lstart) + offsets, np.array(lend) + offsets, self.line_colors[ltype], thickness=2)


        cv2.imshow("layout tool", self.image_handle)

    def run(self):
        self.update_image()
        cv2.namedWindow("layout tool")
        cv2.setMouseCallback("layout tool", self.callback)
        cv2.imshow("layout tool", self.image_handle)
 
        while True:
            cv2.waitKey(10)