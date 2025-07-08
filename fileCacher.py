import threading
import time
import os
from shutil import copy

def loadFiles(path: str, depth = 0) ->list[str]:
    """
    Recursively loads all files in the given directory path and its subdirectories.
    has a depth limit set by a global variable.
    Args:
        path (str): The path to the directory to start loading files from.
        depth (int, optional): The current depth level of recursion. Defaults to 0.
    Returns:
        list[str]: A list of file paths.
    """
    out:list[str] = []
    for f in os.listdir(path): # find all paths in directory
        if os.path.isfile(path + "/" + f):
            out.append(path + "/" + f) # append files
    return out

class fileCacher:
    def __init__(self, files: list[str], destination: str = "C:/temp_sorter", cacheID = 0, cacheSize: int = 100):
        self.files:list[tuple[str,int]] = [*zip(files,[-1]*len(files))]
        self.index:int = 0
        self.cache:list[str|None] = [None] * cacheSize
        self.mutex:list[threading.Lock] = [threading.Lock() for _ in range(len(files))]
        self.destination:str = destination
        self.ID:int = cacheID
        self.cacheSize:int = cacheSize
        self.kill:bool = False
        
        
        self.cachers:threading.Thread = threading.Thread(target=self.__cacher, daemon=True)
        if not os.path.exists(destination):
            os.makedirs(destination, mode=0o777, exist_ok=True)  # Ensure destination exists
        for legacy_file in loadFiles(destination):
            os.remove(legacy_file)  # Remove old cache files
        self.cachers.start()
    
    def getFile(self, fileID: int) -> str:
        self.index = fileID
        if(fileID < 0 or fileID >= len(self.files)):
            raise IndexError("File ID out of range")
        return self.__getCachePath(fileID, True)
    
    def freeFile(self, fileID: int) -> None:
        if fileID < 0 or fileID >= len(self.files):
            raise IndexError("File ID out of range")
        if self.mutex[fileID].locked():
            self.mutex[fileID].release()
    def __cacher(self) -> None:
        cacheIndex = 0
        while True:
            if self.kill:
                return
            if self.index >= len(self.files):
                self.index = 0
            index = self.index
            for i in range(cacheIndex, cacheIndex + self.cacheSize):
                if not self.mutex[i % self.cacheSize].locked():  # Check if the cache index is free
                    cacheIndex = i % self.cacheSize
                    break

            if not self.mutex[index].acquire(timeout=0.1):  # Lock the current file index
                continue  # If the file is already being processed, skip to the next iteration

            oldIndex = -1
            for i, f in enumerate(self.files):
                if f[1] == cacheIndex:
                    oldIndex = i
                    break
            if self.files[index][1] != -1:  # if the file is already cached
                if oldIndex == -1:
                    continue  # No need to cache if the file is already cached
            
            
            if not self.mutex[oldIndex].acquire(timeout=0.1):  # Lock the old cache entry
                self.mutex[index].release()  # Release the current file index lock
                continue  # If the old cache entry is locked, skip to the next iteration
            oldCache = self.cache[cacheIndex]

            # Ensure the file is not in use before attempting to delete
            if oldCache is not None:
                try:
                    os.remove(oldCache)
                except PermissionError:
                    print(f"\nWarning: Could not remove cache file {oldCache} as it is in use. it will be skiped.") 
                    continue

            orgPath = self.files[index][0]

            self.cache[cacheIndex] = orgPath

            newPath = os.path.join(self.destination, f"{self.ID}_{index}_{cacheIndex}_cache.{orgPath.split('/')[-1]}")

            if not os.path.exists(newPath):  # see if file does not exist
                os.makedirs(newPath[::-1].split("/", 1)[1][::-1], mode=0o777, exist_ok=True)  # generate folders, NOT the file
                f = open(newPath, 'a')  # generate the file
                f.close()

            copy(orgPath, newPath)

            self.cache[cacheIndex] = newPath
            self.files[index] = (orgPath, cacheIndex)
            self.mutex[oldIndex].release()  # Release the old cache entry lock
            
            
            self.mutex[index].release()  # Release the current file index lock
            
            self.index += 1
            cacheIndex = (cacheIndex + 1) % self.cacheSize
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
        if setUse:
            if(not self.mutex[fileID].acquire(timeout=0.1)):  # Lock the cache entry
                return self.__getOrig(fileID)
        path =  self.cache[cache]
        return path if path is not None else self.__getOrig(fileID)
    def close(self) -> None:
        self.kill = True
        self.cachers.join()
        for i in self.cache:
            if i is not None and os.path.exists(i):
                os.remove(i)
