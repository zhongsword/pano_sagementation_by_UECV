import cv2 as cv
import numpy as np
import os
from py360convert import c2e
from py360convert.utils import xyzcube
import sys
from unrealcv import client
import re
from tqdm import tqdm
import json
import copy

class panorama():
    EqTglr = None
    
    def __init__(self,img :str):
        """create a cube from cube3x2 map.

        Args:
            img (str): path to map image. 
        """
        self.Cube3x2 = cv.imread(img)
        assert not self.Cube3x2.any == None , "Open image faile !" 
        self.face_wigth = int(np.shape(self.Cube3x2)[0]/2)
        index_list = [[1,1],[0,0],[1,2],[0,1],[0,2],[1,0]]#F R B L U D x index in cube3x2.
        self.horizon = xyzcube(face_w=self.face_wigth)
        a = self.face_wigth
        for i,index in enumerate(index_list) :
            self.horizon[:a,
                         i * a:(i + 1)*a,
                         :] = self.Cube3x2[a * (index[0]):a * (index[0]+1),
                                           a * index[1]:a * (index[1]+1),:]
            # self.horizon = cv.cvtColor(self.horizon,cv.COLOR_RGB2BGR)
        self.horizon[:a,2*a:3*a,:] = np.flip(self.horizon[:a,2*a:3*a,:],1)
        self.horizon[:a,1*a:2*a,:] = np.flip(self.horizon[:a,1*a:2*a,:],1)
        
    def OutputEtanger(self,SaveImage: str =None,Path: str=None):
        a = self.face_wigth
        Etanger = c2e(self.horizon,h=2*a,w=4*a,cube_format='horizon')
        Etanger = Etanger.astype(np.uint8)
        self.EqTglr=Etanger
        if SaveImage:
            cv.imwrite(f"{Path}/{SaveImage}.jpg",Etanger)    
        return Etanger

class Color:
    """A utility class to parse color value 
    """
    Regexp = re.compile('\(R=(.*),G=(.*),B=(.*),A=(.*)\)')#regexp 为一个pattern
    def __init__(self,color_str) :
        self.color_str = color_str
        try:
            match = self.Regexp.findall(color_str)
            (self.R, self.G, self.B,self.A) = (int(match[0][0]),int(match[0][1]),int(match[0][2]),int(match[0][3]))
        except :
            (self.R, self.G, self.B,self.A) = (None, None, None,None)     
        # print (type(self.R))
        
    def __call__(self) :
        return (self.B,self.G,self.R,self.A)

def GetObjectBitwiseMap(ObjectMask, TargetColor, tolerance=10):#Tolerance 容许的颜色偏离度
    """ Input a 360deg ObjectMask from UE4 , out only the target object Mask.

    Args:
        ObjectMask (ndarray in shape(...:3)): 
        TargetColor (tuple with 3 lenght): color described in RGB
        tolerance (int): RGB通道强度的容许误差.

    Returns:
        numpy_array(h, w, 1): bitwise map of the target object. 
    """
    assert not ObjectMask.all() == None, "You did input a correct GroundTruth."  
    # ObjectMask = ObjectMask.astype(np.uint8)
    # ObjectMask = cv.cvtColor(ObjectMask,cv.COLOR_BGR2RGB)
    MatchRegion = np.ones(ObjectMask[...,0].shape,dtype=np.uint8) #empty mask
    MatchRegion[:,:] = 255
    # print(ObjectMask[...,2])
    # print(MatchRegion)
    for c in range(3): #B,G,R 
        try:
            MinVal = TargetColor[c] - tolerance
            # print(MinVal)
            MaxVal = TargetColor[c] + tolerance
            # print(MaxVal)
            ret,ChannelRegionUp = cv.threshold(ObjectMask[...,c],MinVal,255,type=cv.THRESH_BINARY)
            # print(ChannelRegionUp.all() == 0)
            ret,ChannelRegionDown = cv.threshold(ObjectMask[...,c],MaxVal,255,type=cv.THRESH_BINARY_INV)
            ChannelRegionDown.all() == 0
            ChannelRegion = cv.bitwise_and(ChannelRegionUp,ChannelRegionDown)
            # print (ChannelRegion.all() == 0)
            MatchRegion = cv.bitwise_and(MatchRegion,ChannelRegion)
        except TypeError as e:
            print(e)
        # print(MatchRegion)
        # print(MatchRegion.all() == 0)
    # if :
    return MatchRegion
    # else :
        # return None


def GetObjectSemantic(save_name: str = None):
    """Take the ObjectName and its RBG in unrealcv.

    Args:
        JsonName (str, optional): Save the ObjectName with its Color in RGB format. Defaults to None.

    Returns:
        _type_: _description_
    """
    client.connect()
    assert client.isconnected() , "UnrealCV server is not running!"
    
    SceneObjects = client.request('vget /objects').split(' ')
    print('Number of objects in this scene:', len(SceneObjects))
    TqColor = tqdm(SceneObjects,desc="Creating Object-Color dict")
    IdColorDict = dict()
    for ObjId in TqColor:
        color = Color(client.request(f'vget /object/{ObjId}/color'))
        IdColorDict[ObjId] = color()
    if save_name:
        with open (f"{save_name}","w") as f:
            f.write(json.dumps(IdColorDict))   
    client.disconnect()
    return IdColorDict

def GetObjectMask(Id2ColorDict:dict, EquirecTangular, SavePath:str=None):
    """Iterate over ObjId, outputting every Objs bitmpas separately.

    Args:
        Id2ColorDict (dict): K-Vdic created by GetObjectSemantic().
        EquirecTangular (_type_): 360deg RBG ObjectMask.
        SavePath (str, optional): Dir to save all bitmap. Defaults to None.
    """
    assert not Id2ColorDict == None, "Please input the created Id2ColorDict!"
    assert not EquirecTangular.all() == None , "You didn't input a groundtruth image."
    # print(Id2ColorDict.keys())
    TqMask = tqdm(Id2ColorDict.keys(),desc="Creating Id2MaskDict!")
    Id2MaskDict = dict()
    for ObjId in TqMask:
        color = Id2ColorDict[ObjId]
        # try :
        mask = GetObjectBitwiseMap(EquirecTangular,color)
        # except :
        # mask = ObjectMatchColor(cv.imread(EquirecTangular),color)
        if SavePath:
            try:
                cv.imwrite(f"./{SavePath}/{ObjId}.jpg",mask)
                # Id2ColorDict[ObjId] = mask
            except:
                # Id2ColorDict[ObjId] = mask
                pass
        # else:    
            # Id2MaskDict[ObjId] = mask
    # return Id2MaskDict        

if __name__ == "__main__":
    GetObjectSemantic("./Test_2022_11_21/Obj-Rbg.json")



