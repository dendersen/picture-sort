from PIL import Image as img
from PIL.ExifTags import TAGS as tags
import os
from shutil import move,copy
from progBar import progBar

maxDepth:int = 3
files:list[str] = []
permitedFileTypes = ["jpg", "JPG","png","PNG"]
dates:list[list[str]] = []
precision:bool = False
highPrecision:bool = False
makeCopy: bool = False

def loadFiles(path: str, depth = 0) ->list[str]:
  out:list[str] = []
  for f in os.listdir(path):
    if os.path.isfile(path + "/" + f):
      out.append(path + "/" + f)
    else:
      if(depth <= maxDepth):
        out.extend(loadFiles(path + "/" + f,depth + 1))
  return out

def init(skip:bool = False):
  global precision,highPrecision,files,makeCopy
  if(skip):
    path = "./David";
    precision= True
    highPrecision = True
    makeCopy = True
  else:
    path = input("hvor er billederne, tryk enter for auto: ") or "./"
    precision = input("skal der opdeles efter måned?\ny for ja alt andet for nej: ") == "y"
    if(precision):
      highPrecision = input("skal der opdeles efter dag?\ny for ja alt andet for nej: ") == "y"
    makeCopy = input("skal billederne kopires hvis ikke flyttes de?\ny for ja alt andet for nej: ") == "y"
  print("finder alle filer")
  files = loadFiles(path)
  print(f"fandt {len(files)} filer")

def check():
  global files
  print("registrere filer")
  toBeRemoved:list[int] = []
  prog = progBar(len(files))
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
  prog = progBar(len(toBeRemoved))
  for i in toBeRemoved[::-1]:
    files.remove(files[i])
    prog.incriment()
  print()
  print(f"der er {len(files)} gyldige billeder")

def findDate():
  global files, dates
  pics:list[tuple(str,list[str])] = []
  prog = progBar(len(files))
  print("finder datoer")
  miss = 0
  for f in files:
    pic = img.open(f)
    exifData = pic.getexif();
    if(exifData):
      if(exifData.get(36867)):
        data = exifData.get(36867)
        if isinstance(data, bytes):
          data = data.decode()
        dates.append((f,exifData.get(36867)))
      elif(exifData.get(306)):
        data = exifData.get(306)
        if isinstance(data, bytes):
          data = data.decode()
        dates.append((f,exifData.get(306)))
      elif(exifData.get(36868)):
        data = exifData.get(36868)
        if isinstance(data, bytes):
          data = data.decode()
        dates.append((f,exifData.get(36868)))
      elif(exifData.get(50971)):
        data = exifData.get(50971)
        if isinstance(data, bytes):
          data = data.decode()
        dates.append((f,exifData.get(50971)))
      elif(exifData.get(29)):
        data = exifData.get(29)
        if isinstance(data, bytes):
          data = data.decode()
        dates.append((f,exifData.get(29)))
      else:
        miss += 1
    pic.close()
    prog.incriment()
  print()
  print(f"fandt datoer til {len(dates)} billeder")
  print(f"der var {miss} billeder uden dato anmærkninger")

def movePictures():
  global dates, precision
  prog = progBar(len(dates))
  if(not makeCopy):
    print(f"rykker {len(dates)} billeder")
  else:
    print(f"kopiere {len(dates)} billeder")
  for i in dates:
    name = i[0].split("/")[-1]
    year = i[1].split(":")[0]
    month = i[1].split(":")[1]
    day = i[1].split(":")[2]
    newPath:str
    if(precision and not highPrecision):
      newPath = f"./{year}/{month}/{day}/{name}"
    elif(precision):
      newPath = f"./{year}/{month}/{name}"
    else:
      newPath = i[0],f"./{year}/{name}"
    makeFile(newPath, i[0],not makeCopy)
    prog.incriment()
  print("done!")

def makeFile(newPath:str, orgPath:str, delete:bool):
  if (not os.path.exists(newPath)):
    b = os.makedirs(newPath[::-1].split("/",1)[1][::-1],mode = 0o777,exist_ok=True)
    f = open(newPath,'a')
    f.close()
  if(delete):
    move(orgPath,newPath)
  else:
    copy(orgPath,newPath)

init()
check()
findDate()
movePictures()
