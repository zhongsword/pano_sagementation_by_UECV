from unrealcv import client
import numpy as np
import os
import cv2 as cv
import json 
from py360convert.utils import xyzcube
from py360convert import c2e

class Camera360:
    def __init__(self, track: list, cwd, deg) :
        """
        take 360 deg image on object mask by the track.
        before using it please put a fusion camera in the unreal editor.
        
        Args:
            track (list): list(tuple(x,y,z,rx,ry,rz))
        """
        self.track = track
        self.cwd = cwd
        self.deg0 = deg
        pass
    
    def take_etan(self, index: int):
        """Use the unrealcv to posite the FusionCamera to take images saved in :
        path/to/6rotaion/camera{{id}}/index.png

        Args:
            index (int):index in the list of the track.

        Returns:
            numpy.array[h, w, 3]: A 360 image with semantic in RBG.
        """
        count = 0
        #F R B L U D 0F 1R 2B 3L 4U 5D
        for deg in [[0, 0+self.deg0, 0],\
                    [0, 90+self.deg0, 0],\
                    [0, 180+self.deg0, 0],\
                    [0, 270+self.deg0, 0],\
                    [90, 0+self.deg0, 0],\
                    [-90, 0+self.deg0, 0]]:
            res = client.request(f'vset /camera/1/rotation {deg[0]} {deg[1]} {deg[2]}')
            print(res)
            try: 
                # os.makedirs(os.getcwd() + f"/{self.cwd}/6rotation/camera{count}")
                os.makedirs(os.getcwd() + f"/{self.cwd}/360")
            # os.(os.getcwd() + f"{self.cwd}/6rotation/camera{count}")
            except : pass
            client.request(
                f'vget /camera/1/object_mask {os.getcwd()}/{self.cwd}/6rotation/camera{count}/{index}.png')
            count += 1
        picr = cv.imread(os.getcwd() + f'/{self.cwd}/6rotation/camera1/{index}.png')
        picb = cv.imread(os.getcwd() + f'/{self.cwd}/6rotation/camera2/{index}.png')
        picu = cv.imread(os.getcwd() + f'/{self.cwd}/6rotation/camera4/{index}.png')
        print(np.shape(picr))
        wigth = np.shape(picr)[0]
        picr = cv.flip(picr,1)
        picb = cv.flip(picb,1)
        picu = cv.flip(picu,0)
        cv.imwrite(os.getcwd() + f'/{self.cwd}/6rotation/camera1/{index}.png', picr)
        cv.imwrite(os.getcwd() + f'/{self.cwd}/6rotation/camera2/{index}.png', picb)
        cv.imwrite(os.getcwd() + f'/{self.cwd}/6rotation/camera4/{index}.png', picu)
        horizon = xyzcube(face_w=wigth)
        
        for i in range(6):
            horizon[:wigth,i*wigth:(i+1)*wigth,:] = cv.imread(os.getcwd() + f'/{self.cwd}/6rotation/camera{i}/{index}.png')
        equ_tangular = c2e(horizon, 2 * wigth, 4 * wigth, cube_format='horizon')
        equ_tangular = equ_tangular.astype(np.uint8)
        
        cv.imwrite(os.getcwd() + f'/{self.cwd}/360/{index}.png', equ_tangular)
        return equ_tangular
    
    def __call__(self,save_path):
        position_dict = dict()
        client.connect()
        if not client.isconnected():
            print('UnrealCV server is not running.')
            exit()
        for index, position in enumerate(self.track):
            client.request(f'vset /camera/1/location {position[0]} {position[1]} {position[2]}')
            self.take_etan(index)
            position_dict[index] = position
        client.disconnect()
        with open (os.getcwd() + f"/{self.cwd}/{save_path}", 'w') as f:
            f.write(json.dumps(position_dict))        
                
if __name__ == "__main__":
    test_position = [(10530, -690, 173)]
    test_camera = Camera360(test_position, "7141",  255.6)
    test_camera("test_track.json")
    
    # 7825, 109, 111 7.19
    
