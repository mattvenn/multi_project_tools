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


def callback(class_ref, event,x,y,flags,param): 
    if event == cv2.EVENT_LBUTTONDOWN:
        if class_ref.pointerbound:
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
                        class_ref.pointerbound = name

    elif event == cv2.EVENT_MOUSEMOVE:
        if class_ref.pointerbound:
            class_ref.layout_info[class_ref.pointerbound]["design_location"] = (int(x), int(y))
            collision_map = {}
            for e in class_ref.layout_info.keys():
                collision_map[e] = False

            for ent_name, data in class_ref.layout_info.items():
                for o_name, odata in class_ref.layout_info.items():
                    if ent_name != o_name:
                        if check_collision(data, odata):
                            collision_map[ent_name] = True
                            collision_map[o_name] = True
            
            for ent_name, data in class_ref.layout_info.items():
                if collision_map[ent_name]:
                    class_ref.layout_info[ent_name]["design_color"] = (0.0, 0.0, 1.0)
                else:
                    class_ref.layout_info[ent_name]["design_color"] = (0.0, 1.0, 0.0)

            class_ref.update_image()
    pass


class LayoutTool():
    def __init__(self, collection, downscale):
        logging.info(f"launching layout tool. Found {len(collection.projects)} designs in collection")
        self.layout_info = {}
        self.callback = None
        self.scalar = downscale
        self.area_width = int(collection.config['configuration']['user_area_width'] // self.scalar)
        self.area_height = int(collection.config['configuration']['user_area_height'] // self.scalar)
        logging.info(f"layout tool canvas = {self.area_width}x{self.area_height}, using downscale = {self.scalar}")
        logging.info(f"pass --layout-tool-downscale=x if this does not fit on your screen")

        self.image_handle = np.ones((self.area_height, self.area_width, 3))

        for p in collection.projects:
            caravel_data = p.get_gds_size().tolist()
            # caravel_data = [256, 256]
            caravel_data = (
                int(caravel_data[0] // self.scalar),
                int(caravel_data[1] // self.scalar),
            )

            logging.info(f"parsed {p.module_name}, size is {caravel_data}")
            self.layout_info[p.module_name] = {
                "design_area": caravel_data,
                "design_location": (int(self.area_height//2), int(self.area_width//2)),
                "design_color": (0.0, 1.0, 0.0)
            }

            self.pointerbound = p.module_name


    def set_callback(self, fun):
        self.callback = fun

    def update_image(self):
        self.image_handle = np.ones((self.area_height, self.area_width, 3))
        for imname, data in self.layout_info.items():
            color = data["design_color"]
            
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
            
            sub_img = self.image_handle[data["design_location"][1]:data["design_location"][1] + data["design_area"][1], data["design_location"][0]:data["design_location"][0] + data["design_area"][0]]
            rect = np.ones(sub_img.shape) * color * 255.0
            cv2.addWeighted(sub_img, 0.85, rect, 0.15, 0, rect)
            self.image_handle[data["design_location"][1]:data["design_location"][1] + data["design_area"][1], data["design_location"][0]:data["design_location"][0] + data["design_area"][0]] = rect

            cv2.putText(self.image_handle, imname, data["design_location"], cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 1, cv2.LINE_AA)

        cv2.imshow("layout tool", self.image_handle)

    def run(self):
        self.update_image()
        cv2.namedWindow("layout tool")
        cv2.setMouseCallback("layout tool", self.callback)
        cv2.imshow("layout tool", self.image_handle)

        while True:
            cv2.waitKey(10)