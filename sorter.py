from math import ceil
from PIL import Image as img
from PIL import ImageChops
import os
from shutil import move,copy
from progBar import progBar,sys
from threading import Thread
from pillow_heif import register_heif_opener
from datetime import datetime
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from hachoir.metadata.metadata import Metadata

register_heif_opener()
maxDepth:int = 3
files:list[str] = []
permittedFileTypes = ["jpg", "JPG","png","PNG","HEIC","heic","JPEG","jpeg"]
secondaryTypes = [
  "MOV","mov",
  "flv","FLV",
  "AVI","avi",
  "EXE","exe",
  "BMP","bmp",
  "GIF","gif",
  "ICO","ico",
  "PNG","png",
  "AIFF","aiff",
  "MPEG_AUDIO","mpeg_audio",
  "REAL_AUDIO","real_audio",
  "SUN_NEXT_SND","sun_next_snd",
]
dates:list[list[str]] = []
precision:bool = False
highPrecision:bool = False
makeCopy: bool = False
debug:bool = False
useFiles = False
readAllTypes = False
antiDube = False
threads = None

def init(skip:bool = False, move = None, fileData = None, readAll = None, Debug = False, RemoveDubes = None):
  global precision,highPrecision,files,makeCopy,debug,useFiles,readAllTypes,antiDube,threads
  for i in range(1,len(sys.argv)):
    if(i == "skip"): skip = True
    if(i == "kopi"): move = False
    if(i == "flyt"): move = True
    if(i == "debug"): debug = True
    if(i == "rent"): removeDubes = True
  if(skip):
    path = "./"
    precision= True
    highPrecision = True
    RemoveDubes = False
    threads = False
  else:
    path = input("\n\nhvor er billederne, tryk enter for auto: ") or "./"
    precision = input("\n\nskal der opdeles efter måned?\ny for ja alt andet for nej: ") == "y"
    if(precision):
      highPrecision = input("\n\nskal der opdeles efter dag?\ny for ja alt andet for nej: ") == "y"
    else:
      highPrecision = input("\n\nskal der opdeles efter år\nvære en usorteret bunke\ny for ja alt andet for nej: ") == "y"
  makeCopy = not move
  useFiles = fileData
  readAllTypes = readAll
  antiDube = RemoveDubes
  
  if(move == None):
    makeCopy = input("\n\nskal billederne kopires, hvis ikke flyttes de?\ny for ja alt andet for nej: ") == "y"
  if(fileData == None):
    useFiles = input("\n\nmå mindre præcise datoer benytes?\ny for ja alt andet for nej: ") == "y"
  if(fileData and readAll == None):
    readAllTypes = input("\n\nskal alle filer sorteres?\n(det garanteres ikke at filerne sorteres korrekt)\ny for ja alt andet for nej: ") == "y"
  debug = Debug
  if(RemoveDubes == None):
    antiDube = input("\n\nskal gentagende BILLEDER fjernes \n(baseret på billede ikke filnavn)\ny for ja alt andet for nej: ") == "y"
  if(threads == None):
    threads = input("\n\nWIP threads\nvil formentligt fejle\ny for ja alt andet for nej: ") == "y"
  print("\n\nfinder alle filer")
  files = loadFiles(path)
  print(f"\nfandt {len(files)} filer")

def loadFiles(path: str, depth = 0) ->list[str]:
  out:list[str] = []
  for f in os.listdir(path):
    if os.path.isfile(path + "/" + f):
      out.append(path + "/" + f)
    else:
      if(depth <= maxDepth):
        out.extend(loadFiles(path + "/" + f,depth + 1))
  return out

def check():
  global files
  print("\nregistrere filer")
  toBeRemoved:list[int] = []
  prog = progBar(len(files),disable=debug)
  for j,f in enumerate(files):
    accept = False
    if(not readAllTypes):
      accept = acceptedType(f)
    else:
      accept = not os.path.isdir(f)
    if(not accept):
      toBeRemoved.append(j)
    prog.incriment()
  print()
  print(f"\nfiler {len(files)} registreret")
  print("fjerner alle ugyldige filer")
  prog = progBar(len(toBeRemoved),disable=debug)
  for i in toBeRemoved[::-1]:
    files.remove(files[i])
    prog.incriment()
  print(f"\nder er {len(files)} gyldige billeder")

def acceptedType(picPath):
  return picType(picPath) or secondaryType()

def picType(picPath:str) -> bool:
  for i in permitedFileTypes:
    if(picPath.endswith(i)):
      return True
  return False

def secondaryType(picPath:str) ->bool:
  for i in secondaryTypes:
    if(picPath.endswith(i)):
      return True
  return False

def findDate():
  global files, dates
  prog = progBar(len(files),disable=debug)
  print("\nfinder datoer")
  miss = 0
  for path in files:
    d = getDate(path,prog)
    if(d == None):
      miss += 1
    else:
      dates.append(d)
  print()
  print(f"\nfandt datoer til {len(dates)} billeder")
  print(f"der var {miss} billeder uden dato anmærkninger")

def getDate(picPath:str, prog:progBar) -> tuple[str]:
  if(picType(picPath)):
    args = [img.open(picPath),picPath,prog]
  extension:str = picPath[::-1].split(".",1)[0][::-1].lower()
  out:tuple[str] = None
  if(extension == "jpg" or extension ==  "heic" or extension ==  "jpeg"):
    out = getDate_jpg(*args)
  elif(extension == "png"):
    out = getDate_png(*args)
  elif(secondaryType(picPath)):
    out = exifRead(picPath)
  else:
    return None
  if(out == None):
    out = fileDate(picPath)
  if(out == None and debug):
    printData(picPath)
  return out

def getDate_jpg(pic:img ,picPath:str, prog:progBar) -> tuple[str]:
  exifData = pic.getexif()
  out:tuple[str,list[str]]
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
    print(f"\nflytter {len(dates)} billeder")
  else:
    print(f"\nkopiere {len(dates)} billeder")
  if(not threads):
    movePic(prog,dates)
  else:
    t:list[Thread] = []
    step = ceil(len(dates)/10) 
    start = 0
    end = step
    for i in range(0,10):
      t.append(Thread(name=f"mover: {start}/{min(end,len(dates))}",target=movePic,args=[prog,dates[start:min(end,len(dates))]]))
      start,end = end,end+step
    for i in t:
      i.start()
    for i in t:
      i.join()
  print("\ndone!")

def movePic(prog:progBar, dates:list[list[str]]):
  for i in dates:
    name = i[0]
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
    elif(highPrecision):
      newPath = f"./sorterede/{name}"
    else:
      newPath = f"./{year}/{name}"
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
  try:
    if(delete):
      move(orgPath,newPath)
    else:
      copy(orgPath,newPath)
  except: pass

def printData(picPath:str):
  try:
    from PIL.ExifTags import TAGS
    i = img.open(picPath)
    print(picPath)
    for tag in i.getexif():
      data = i.getexif().get(tag)
      if isinstance(data, bytes):
        data = data.decode()
      print(f"{tag}:{TAGS.get(tag,tag)}:{data}")
  except:
    print("\nData Search Failed")

def fileDate(picPath:str) -> tuple[str]:
  time = min(min(datetime.fromtimestamp(os.stat(picPath).st_atime),datetime.fromtimestamp(os.stat(picPath).st_ctime)),datetime.fromtimestamp(os.stat(picPath).st_mtime))
  return timeFormat(picPath,time)

def timeFormat(picPath:str, time:datetime):
  return (picPath,time.strftime("%Y") + ":" + time.strftime("%m") + ":" + time.strftime("%d"))

def exifRead(picPath:str) -> tuple[str]:
  parser = createParser(picPath)
  metadata:Metadata = extractMetadata(parser)
  data:dict = metadata.exportDictionary().get("Metadata")
  time:datetime = datetime.now()
  for key in data.keys():
    key:str
    if("date" in key.lower() or "modification" in key.lower() or "time" in key.lower()):
      time = min(time, datetime.fromisoformat(data.get(key)))
  return timeFormat(picPath,time)

def removeDubes():
  if(not antiDube): return
  prog = progBar(len(files), disable=debug)
  dubes = []
  print("\nchecker for identiske billeder")
  for i in range(len(files)):
    prog.incriment("filer checket")
    for j in range(i+1,len(files)):
      img1 = img.open(files[i])
      img2 = img.open(files[j])
      if(
        (img1.size == img2.size) and 
        (ImageChops.difference(img1,img2).getbbox() == None)):
        dubes.append(i)
        break
  print("alle identiske billeder fundet")
  prog = progBar(len(dubes), disable=debug)
  print("\nfjerner identiske billeder")
  for i in dubes[::-1]:
    prog.incriment()
    files.remove(files[i])
  print("identiske billeder er blevet fjernet")

init()
check()
removeDubes()
findDate()
movePictures()

while(True):
  user = input("luk vinduet eller tryk q for at slukke program: ")
  if(user == "q"): break
  if(user == "d"):
    for i in files:
      printData(i)