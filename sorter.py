from math import floor
from PIL import Image as img
import os
from shutil import move,copy
from progBar import progBar
from threading import Thread
from pillow_heif import register_heif_opener
from datetime import datetime
register_heif_opener()
maxDepth:int = 3
files:list[str] = []
permitedFileTypes = ["jpg", "JPG","png","PNG","HEIC","heic","JPEG","jpeg"]
dates:list[list[str]] = []
precision:bool = False
highPrecision:bool = False
makeCopy: bool = False
debug:bool = False
useFiles = False

def loadFiles(path: str, depth = 0) ->list[str]:
  out:list[str] = []
  for f in os.listdir(path):
    if os.path.isfile(path + "/" + f):
      out.append(path + "/" + f)
    else:
      if(depth <= maxDepth):
        out.extend(loadFiles(path + "/" + f,depth + 1))
  return out

def init(skip:bool = False, move = None, fileData = None, Debug = False):
  global precision,highPrecision,files,makeCopy,debug,useFiles
  if(skip):
    path = "./";
    precision= True
    highPrecision = True
  else:
    path = input("hvor er billederne, tryk enter for auto: ") or "./"
    precision = input("skal der opdeles efter måned?\ny for ja alt andet for nej: ") == "y"
    if(precision):
      highPrecision = input("skal der opdeles efter dag?\ny for ja alt andet for nej: ") == "y"
  if(move == None):
    makeCopy = input("skal billederne kopires hvis ikke flyttes de?\ny for ja alt andet for nej: ") == "y"
  if(fileData == None):
    useFiles = input("å mindre præcise datoer benytes?\ny for ja alt andet for nej") == "y"
    pass
  debug = Debug
  print("finder alle filer")
  files = loadFiles(path)
  print(f"fandt {len(files)} filer")

def check():
  global files
  print("registrere filer")
  toBeRemoved:list[int] = []
  prog = progBar(len(files),disable=debug)
  for j,f in enumerate(files):
    accept = False
    for i in permitedFileTypes:
      if(f.endswith(i)):
        accept = True
        break
    if(not accept):
      toBeRemoved.append(j)
    prog.incriment()
  print()
  print(f"filer {len(files)} registreret")
  print("fjerner alle ugyldige filer")
  prog = progBar(len(toBeRemoved),disable=debug)
  for i in toBeRemoved[::-1]:
    files.remove(files[i])
    prog.incriment()
  print()
  print(f"der er {len(files)} gyldige billeder")

def findDate():
  global files, dates
  pics:list[tuple(str)] = []
  prog = progBar(len(files),disable=debug)
  print("finder datoer")
  miss = 0
  for path in files:
    d = getDate(path,prog)
    if(d == None):
      miss += 1
    else:
      dates.append(d)
  print()
  print(f"fandt datoer til {len(dates)} billeder")
  print(f"der var {miss} billeder uden dato anmærkninger")

def getDate(picPath:str, prog:progBar) -> tuple[str]:
  args = [img.open(picPath),picPath,prog]
  extension:str = picPath[::-1].split(".",1)[0][::-1].lower()
  out:tuple[str]
  if(extension == "jpg" or "heic" or "jpeg"):
    out = getDate_jpg(*args)
  if(extension == "png"):
    out = getDate_png(*args)
  if(fileDate):
    return fileDate(picPath)
  if(out == None and debug):
    printData(picPath)
  return out

def getDate_jpg(pic:img ,picPath:str, prog:progBar) -> tuple[str]:
  exifData = pic.getexif();
  out:tuple(str,list[str])
  if(exifData):
    if(exifData.get(36867)):
      data = exifData.get(36867)
      if isinstance(data, bytes):
        data = data.decode()
      out = (picPath,data)
    elif(exifData.get(306)):
      data = exifData.get(306)
      if isinstance(data, bytes):
        data = data.decode()
      out = (picPath,data)
    elif(exifData.get(36868)):
      data = exifData.get(36868)
      if isinstance(data, bytes):
        data = data.decode()
      out = (picPath,data)
    elif(exifData.get(50971)):
      data = exifData.get(50971)
      if isinstance(data, bytes):
        data = data.decode()
      out = (picPath,data)
    elif(exifData.get(29)):
      data = exifData.get(29)
      if isinstance(data, bytes):
        data = data.decode()
      out = (picPath,data)
    else:
      out = None
  else:
    out = None
  prog.incriment()
  return out

def getDate_png(pic:img ,picPath:str, prog:progBar) -> tuple[str]:
  pic.load()
  return getDate_jpg(pic ,picPath, prog)

def movePictures():
  global dates, precision
  prog = progBar(len(dates),disable=debug)
  if(not makeCopy):
    print(f"flytter {len(dates)} billeder")
  else:
    print(f"kopiere {len(dates)} billeder")
  # movePic(prog,dates)
  t:list[Thread] = []
  for i in range(0,10):
    t.append(Thread(name=f"mover:{i}",target=movePic,args=[prog,dates[floor(len(dates)/i) if i != 0 else 0:floor(len(dates)/(i+1))]]))
  for i in t:
    i.start()
  for i in t:
    i.join()
  print("\ndone!")

def movePic(prog:progBar, dates:list[list[str]]):
  for i in dates:
    name = i[0].split("/")[-1]
    year = i[1].split(":")[0]
    month = i[1].split(":")[1]
    day = i[1].split(":")[2]
    if(len(day) > 2):
      day = day.split(" ")[0]
    newPath:str
    if(precision and highPrecision):
      newPath = f"./{year}/{month}/{day}/{name}"
    elif(precision):
      newPath = f"./{year}/{month}/{name}"
    else:
      newPath = i[0],f"./{year}/{name}"
    makeFile(newPath, i[0],not makeCopy)
    prog.incriment()

def makeFile(newPath:str, orgPath:str, delete:bool):
  if(orgPath == newPath):
    return
  if (not os.path.exists(newPath)):
    b = os.makedirs(newPath[::-1].split("/",1)[1][::-1],mode = 0o777,exist_ok=True)
    f = open(newPath,'a')
    f.close()
  else:
    makeFile(newPath[::-1].split(".",1)[1][::-1] + "(1)." + newPath[::-1].split(".",1)[0][::-1],newPath,True)
    makeFile(newPath,orgPath,delete)
  if(delete):
    move(orgPath,newPath)
  else:
    copy(orgPath,newPath)

def printData(picPath:str):
  from PIL.ExifTags import TAGS
  i = img.open(picPath)
  print(picPath)
  for tag in i.getexif():
    data = i.getexif().get(tag)
    if isinstance(data, bytes):
      data = data.decode()
    print(f"{tag}:{TAGS.get(tag,tag)}:{data}")

def fileDate(picPath) -> tuple[str]:
  time = min(min(datetime.fromtimestamp(os.stat(picPath).st_atime),datetime.fromtimestamp(os.stat(picPath).st_ctime)),datetime.fromtimestamp(os.stat(picPath).st_mtime))
  return (picPath,time.strftime("%Y") + ":" + time.strftime("%m") + ":" + time.strftime("%d"))

init(True,True,True,False)
check()
findDate()
movePictures()

while(True):
  input("luk vinduet for at slukke program")