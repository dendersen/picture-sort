import threading
import time
import os
from shutil import copy

class fileCacher:
    def __init__(self, files: list[str], destination: str, cacheID = 0, cacheSize: int = 100):
        self.files:list[tuple[str,int]] = [*zip(files,[-1]*len(files))]
        self.index:int = 0
        self.cache:list[str|None] = [None] * cacheSize
        self.inUse:list[bool] = [False] * cacheSize
        self.destination:str = destination
        self.ID:int = cacheID
        self.cacheSize:int = cacheSize
        self.cachers:threading.Thread = threading.Thread(target=self.__cacher, daemon=True)
        self.kill:bool = False
    
    def getFile(self, fileID: int) -> str:
        self.index = fileID
        if(fileID < 0 or fileID >= len(self.files)):
            raise IndexError("File ID out of range")
        return self.__getCachePath(fileID, True)
    
    def freeFile(self, fileID: int) -> None:
        if fileID < 0 or fileID >= len(self.files):
            raise IndexError("File ID out of range")
        loc = self.__getCacheIndex(fileID)
        if loc != -1:
            self.inUse[loc] = False
    
    def __cacher(self) -> None:
        cacheIndex = 0
        while True:
            print(f"Cache index {cacheIndex} for file {self.index} is being processed...")
            if self.kill:
                return
            if self.index >= len(self.files):
                self.index = 0
            index = self.index
            for i in range(cacheIndex, cacheIndex + self.cacheSize):
                if not self.inUse[i % self.cacheSize]:
                    cacheIndex = i % self.cacheSize
                    break
            if not self.inUse[cacheIndex]:
                self.inUse[index] = True
                
                oldCache = self.cache[index]
                
                os.remove(oldCache) if oldCache is not None else None
                
                print(f"Cache index {cacheIndex} for file {index} is free, copying file...")
                
                orgPath = self.files[index][0]
                
                self.cache[index] = orgPath
                
                newPath = os.path.join(self.destination, f"{self.ID}_{index}_{cacheIndex}_cache.{orgPath.split('/')[-1]}")
                
                if (not os.path.exists(newPath)): #see if file does not exist
                    os.makedirs(newPath[::-1].split("/",1)[1][::-1],mode = 0o777,exist_ok=True)# generate folders, NOT the file 
                    f = open(newPath,'a')# generate the file
                    f.close()
                
                copy(orgPath,newPath)
                
                print(f"Copied {orgPath} to {newPath}")
                
                self.files[index] = (orgPath, index)
                self.cache[index] = newPath
                self.inUse[index] = False
            self.index += 1
            time.sleep(0.01)  # Sleep to prevent busy waiting
    
    def __getOrig(self, fileID: int) -> str:
        return self.files[fileID][0]
    
    def __getCacheIndex(self, fileID: int) -> int:
        if fileID < 0 or fileID >= len(self.files):
            raise IndexError("File ID out of range")
        return self.files[fileID][1]
    
    def __getCachePath(self, fileID: int, setUse:bool = False) -> str:
        if fileID < 0 or fileID >= len(self.files):
            raise IndexError("File ID out of range")
        cache = self.__getCacheIndex(fileID)
        if cache != -1:
            if setUse:
                self.inUse[self.__getCacheIndex(fileID)] = True
            path = self.cache[cache]
            if path is not None:
                return path
        return self.__getOrig(fileID)
    
    def close(self) -> None:
        self.kill = True
        self.cachers.join()
        for i in self.cache:
            if i is not None and os.path.exists(i):
                os.remove(i)
