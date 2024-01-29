from typing import Any
import cv2 as cv
import numpy as np
from unrealcv import client
import re
import json
import os
from tqdm import tqdm

class Color:
    """A utility class to parse color value 
    """
    reg_exp = re.compile(r'\(R=(.*),G=(.*),B=(.*),A=(.*)\)') #regexp 为一个pattern
    def __init__(self,color_str) :
        self.color_str = color_str
        try:
            match = self.reg_exp.findall(color_str)
            (self.R, self.G, self.B,self.A) = (int(match[0][0]),int(match[0][1]),int(match[0][2]),int(match[0][3]))
        except :
            (self.R, self.G, self.B,self.A) = (None, None, None,None)     
        # print (type(self.R))
        
    def __call__(self) :
        return (self.B,self.G,self.R,self.A)
        

def get_object_rbg(json_name: str = None):
    """select a path to save the object RBG

    Args:
        json_name (str, optional): if None it will one be output. Defaults to None.
    """
    client.connect()
    assert client.isconnected(), "UnrealCV server is not running!"
    scene_objects = client.request('vget /objects').split(' ')
    print('Number of objects in this scene:', len(scene_objects))
    tq_color = tqdm(scene_objects, desc="Creating Object-Color dict")
    id_color_dict = dict()
    for obj_id in tq_color:
        color = Color(client.request(f'vget /object/{obj_id}/color'))
        id_color_dict[obj_id] = color()
    if json_name:
        with open (f"{json_name}","w") as f:
            f.write(json.dumps(id_color_dict))   
    # print (id_color_dict.keys())
    client.disconnect()

class GetObjectMask:
    def __init__(self, id_color_json: str, object_mask_path: str, TestName: str):
        
        assert id_color_json, "Please input the created color_json!"
        assert object_mask_path, "You didn't input a groundtruth image."
        with open (id_color_json,'r') as f:
            self.id_color_dict :dict = json.load(f)
        self.object_mask = cv.imread(object_mask_path)
        re_index = re.compile(r"^.*/(?P<index>[0-9]*).png$")
        self.track_index = re_index.match(object_mask_path).group('index')
        self.TaskName = TestName
        
    def __call__(self):    
        # tq_mask = tqdm(self.id_color_dict.keys(), desc="Creating id...")
        
        class_list = ('duct', 'cable', 'pipe_t', 'pipe_else')
        count = 0
        for cabel_class in self.mask_classify:
            mask_di = np.zeros_like(self.object_mask[...,1])
            for obj in tqdm(cabel_class, f"Getting the musk of {count}"):
                color = self.id_color_dict[obj]
                mask_di = np.bitwise_or(mask_di, self.object_match_color(self.object_mask, color))
            ##TODO:写死的类型
            try:
                os.makedirs(f"{os.getcwd()}/{self.TaskName}/FinalResult/{self.track_index}")
            except Exception as e : 
                pass
            
            cv.imwrite(f"{os.getcwd()}/{self.TaskName}/FinalResult/{self.track_index}/{class_list[count]}.png", mask_di)
            count += 1
        # for obj_id in tq_mask:
        #     color = self.id_color_dict[obj_id]
        #     mask = self.object_match_color(self.object_mask, color)
        #     # try:
        #     if not (mask == 0).all():
        #         cv.imwrite(f"./{save_path}/{obj_id}.png", mask)
        #     # except FileExistsError as e:
        #         # print(e)
        #         # exit()
    
    
    def object_match_color(self, object_mask, target_color, tolerance = 10):
        # assert not object_mask.all(), "You did input a correct mask."
        
        match_region = np.ones(object_mask[...,0].shape, dtype = np.uint8)
        match_region[:,:] = 255
        
        for c in range(3):#B,G,R
            try:
                min_val = target_color[c] - tolerance
                max_val = target_color[c] + tolerance
                
                ret, channel_region_up = cv.threshold(object_mask[...,c], min_val, 255, type=cv.THRESH_BINARY)
                ret, channel_region_down = cv.threshold(object_mask[...,c], max_val, 255, type=cv.THRESH_BINARY_INV)
                channel_region = cv.bitwise_and(channel_region_up, channel_region_down)
                match_region = cv.bitwise_and(match_region, channel_region)
            except TypeError as e:
                    print(e)
        return match_region
    
    @property
    def mask_classify(self):
        """
        """
        # TODO: 此处的正则可能需要更多扩展性而不是写死在函数中
        reg_duct = re.compile(r'^Duct.*')
        reg_cable = re.compile(r'^Cable_.*')
        reg_pipe_t = re.compile(r'^Pipes_Pipe_Types_T.*') 
        reg_pipe_else = re.compile(r'^Pipes_Pipe_Types_[^T]+')
        reg_list = [reg_duct, reg_cable, reg_pipe_t, reg_pipe_else]
        classify_dict = [[], [], [], []]
        for mono in self.id_color_dict.keys():
            for index in range(4):
                match = reg_list[index].match(mono)
                if match:
                    classify_dict[index].append(mono)
                    continue
        # with open (f"./test_classify.json", 'w') as f :
        #     f.write(json.dumps(classify_dict))
        return classify_dict
    
if __name__ == "__main__":
    # get_object_rbg("2024.json")
    test_mask_output = GetObjectMask("./2024.json", "./7141/360/0.png", "7141")
    # test_mask_output("Mask")
    # test_mask_output.mask_classify()
    test_mask_output()