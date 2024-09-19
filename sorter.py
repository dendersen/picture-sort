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

#constants
register_heif_opener()
maxDepth:int = 3
permittedFileTypes = ["jpg", "JPG","png","PNG","HEIC","heic","JPEG","jpeg"]
secondaryTypes = [
  "MOV","mov",
  "flv","FLV",
  "AVI","avi",
  "BMP","bmp",
  "GIF","gif",
  "ICO","ico",
  "AIFF","aiff",
  "MPEG_AUDIO","mpeg_audio",
  "REAL_AUDIO","real_audio",
  "SUN_NEXT_SND","sun_next_snd",
]

# global variables
# a list containing all the dates of the pictures and the path to the pictures
dates:list[list[str]] = []

# a list containing all the files to be sorted
files:list[str] = []

#flags
# if the files should be split into years
precision:bool = False

# if the files should be split into months
highPrecision:bool = False

# if the files should be copied instead of moved
makeCopy: bool = False

# if the program should print debug information
debug:bool = False

# if the program should use less precise dates
useFiles = False

# if the program should read all file types
readAllTypes = False

# if the program should remove duplicate images
antiDube = False

# if the program should use threads
threads = False

#use original folders
folders = False

#where the pictures where found
path = "./"

def init(skip:bool = False, move = None, fileData = None, readAll = None, Debug = False, RemoveDubes = None, Folders = None) -> None:
  """
  Initializes the sorting process for pictures.
  Args:
    skip (bool, optional): Flag to skip user input and use default values. Defaults to False.
    move (bool, optional): Flag to move pictures instead of making a copy. Defaults to None.
    fileData (bool, optional): Flag to allow less precise dates. Defaults to None.
    readAll (bool, optional): Flag to sort all files. Defaults to None.
    Debug (bool, optional): Flag to enable debug mode. Defaults to False.
    RemoveDubes (bool, optional): Flag to remove duplicate images. Defaults to None.
  Returns:
    None
  """
  global precision,highPrecision,files,makeCopy,debug,useFiles,readAllTypes,antiDube,threads,path
  #takes in arguments from the command line
  for i in range(1,len(sys.argv)):
    if(i == "-skip"): skip = True
    if(i == "-kopi"): move = False
    if(i == "-flyt"): move = True
    if(i == "--debug"): debug = True
    if(i == "-slet"): removeDubes = True
    if(i == "-file"): fileData = True
    if(i == "-all"): readAll = True
    if(i == "-threads"): threads = True
    if(i == "-folders"): folders = True
  
  
  if(skip):
    # default values
    path = "./"
    precision= True
    highPrecision = True
    makeCopy = True
    debug = False
    useFiles = True
    readAllTypes = False
    antiDube = False
    threads = False
    folders = True
  else:
    path = input("\n\nhvor er billederne, tryk enter for auto: ") or "./"
    
    precision = input("\n\nskal der opdeles efter måned?\ny for ja alt andet for nej: ") == "y"
    
    if(precision):
      highPrecision = input("\n\nskal der opdeles efter dag?\ny for ja alt andet for nej: ") == "y"
    else:
      highPrecision = input("\n\nskal der opdeles efter år\nvære en usorteret bunke\ny for ja alt andet for nej: ") == "y"
    
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
    
    if(Folders == None):
      folders = input("\n\nskal billederne sorteres i deres originale mapper?\ny for ja alt andet for nej: ") == "y"
  
  print("\n\nfinder alle filer")
  files = loadFiles(path)
  print(f"\nfandt {len(files)} filer")

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
    else:
      if(depth <= maxDepth): # if it isn't a file it must be a directory
        out.extend(loadFiles(path + "/" + f,depth + 1))
  return out

def check() -> None:
  """
  Check function is used to register files and remove invalid files from the list.
  Parameters:
  None
  Returns:
  None
  """
  
  global files
  print("\nregistrere filer")
  toBeRemoved:list[int] = []
  prog = progBar(len(files),disable=debug)
  for j,f in enumerate(files):
    if(
      ((not readAllTypes) and acceptedType(f)) or 
      (readAllTypes and not os.path.isdir(f))
    ):
      toBeRemoved.append(j)
    prog.incriment()
  print(f"\n\n{len(files)} filer registreret")
  print("fjerner alle ugyldige filer")
  prog = progBar(len(toBeRemoved),disable=debug)
  for i in toBeRemoved[::-1]:
    files.remove(files[i])
    prog.incriment()
  print(f"\nder er {len(files)} gyldige billeder")

def acceptedType(picPath:str) -> bool:
  """combines the two sets of accepted file types into one function
  this does  not  check if the file actually has exif data only if the file extension claims it can
  Args:
      picPath (str): a file path pointing towards the file that will be inspected
  Returns:
      bool: wether it is a valid file type or not
  """
  return picType(picPath) or secondaryType()

def picType(picPath:str) -> bool:
  """checks if the file is a picture file with potential exif information
  Args:
      picPath (str): the path to the file that will be inspected
  Returns:
      bool: wether the file is a picture file that can contain exif or not
  """
  for i in permittedFileTypes:
    if(picPath.endswith(i)):
      return True
  return False

def secondaryType(picPath:str) ->bool:
  """checks if the file is a picture, video or audio that may contain exif like information
  though not always supported by this program
  Args:
      picPath (str): the path to the file that will be inspected
  Returns:
      bool: wether the file is a potentially supported file
  """
  for i in secondaryTypes:
    if(picPath.endswith(i)):
      return True
  return False

def findDate() -> None:
  """finds the date of all the pictures in the files list
  and moves them to the dates list
  """
  global files, dates
  prog = progBar(len(files),disable=debug)
  print("\nfinder datoer")
  miss = 0
  for path in files:
    d = getDate(path)
    if(d == None):# no dates found
      miss += 1
    else:# dates found
      files.remove(path)
      dates.append(d)
    prog.incriment()
  print()
  print(f"\nfandt datoer til {len(dates)} billeder")
  print(f"der var {miss} billeder uden dato anmærkninger\nde vil ikke blive sorteret")

def getDate(picPath:str) -> tuple[str]:
  """
  Retrieves the date information from the given picture file.
  Parameters:
  picPath (str): The path of the picture file.
  Returns:
  tuple[str]: A tuple containing the date information extracted from the picture file.
  """
  
  if(picType(picPath)):
    args = [img.open(picPath),picPath]
  
  extension:str = picPath[::-1].split(".",1)[0][::-1].lower() 
  # flip, splits at first ".",gets first part, flip, this is the extension
  out:tuple[str] = None
  
  # finds out based on extension how the exif information should be read
  if(extension == "jpg" or extension ==  "heic" or extension ==  "jpeg"):
    out = getDate_jpg(*args)
  elif(extension == "png"):
    out = getDate_png(*args)
  elif(secondaryType(picPath)):
    out = exifRead(picPath)
  args[0].close()
  # if date extraction failed, try to get the date from the file itself
  if(out == None):
    out = fileDate(picPath)
  if(out == None and debug):
    printData(picPath)
  return out

def getDate_jpg(pic:img ,picPath:str) -> tuple[str]:
  """
  Retrieves the date from the EXIF data of an image with readily available EXIF.
  Parameters:
  - pic (img): The image object.
  - picPath (str): The file path of the image.
  Returns:
  - tuple[str]: A tuple containing the file path and the date extracted from the EXIF data.
          If the EXIF data does not contain the date, None is returned.
  """
  
  exifData = pic.getexif()
  out:tuple[str,list[str]]
  if(exifData): # if there is exif data
    if(exifData.get(36867)):# if there is a date time original
      data = exifData.get(36867)
      if isinstance(data, bytes):
        data = data.decode()
      out = (picPath,data)
    elif(exifData.get(306)):# if there is a date time
      data = exifData.get(306)
      if isinstance(data, bytes):
        data = data.decode()
      out = (picPath,data)
    elif(exifData.get(36868)):# if there is a date time digitized
      data = exifData.get(36868)
      if isinstance(data, bytes):
        data = data.decode()
      out = (picPath,data)
    elif(exifData.get(50971)):# if there is a subsec time
      data = exifData.get(50971)
      if isinstance(data, bytes):
        data = data.decode()
      out = (picPath,data)
    elif(exifData.get(29)):# if there is a date time original (old)
      data = exifData.get(29)
      if isinstance(data, bytes):
        data = data.decode()
      out = (picPath,data)
    else:# if there is no date time
      out = None
  else:# if there is no exif data
    out = None
  
  return out

def getDate_png(pic:img ,picPath:str) -> tuple[str]:
  """prepares and retrieves the date from EXIF information of an image, audio or video file that doesn't have readily available EXIF.

  Args:
  - pic (img): The image object.
  - picPath (str): The file path of the image.

  Returns:
  - tuple[str]: A tuple containing the file path and the date extracted from the EXIF data.
          If the EXIF data does not contain the date, None is returned.
  """
  pic.load()
  return getDate_jpg(pic ,picPath, prog)

def exifRead(picPath:str) -> tuple[str]:
  """
  Reads the metadata of the given picture file and extracts the relevant time information.
  Parameters:
    picPath (str): The file path of the picture.
  Returns:
    tuple[str]: A tuple containing the formatted picture path and the extracted time information.
  """
  
  parser = createParser(picPath)
  metadata:Metadata = extractMetadata(parser)
  data:dict = metadata.exportDictionary().get("Metadata")
  time:datetime = datetime.now()
  for key in data.keys():
    key:str
    if("date" in key.lower() or "modification" in key.lower() or "time" in key.lower()):
      time = min(time, datetime.fromisoformat(data.get(key)))
  return timeFormat(picPath,time)

def movePictures() -> None:
  """
  Moves or copies pictures based on the global variables 'dates', 'precision', 'makeCopy', and 'threads'.
  Parameters:
    None
  Returns:
    None
  """
  global dates, precision
  prog = progBar(len(dates),disable=debug)
  if(not makeCopy):
    print(f"\nflytter {len(dates)} billeder")
  else:
    print(f"\nkopiere {len(dates)} billeder")
  if(not threads):
    movePic(prog,dates)
  else:# WIP does not work
    t:list[Thread] = []
    step = ceil(len(dates)/10) 
    start = 0
    end = step
    for i in range(0,10):#generates threads
      t.append(Thread(name=f"mover: {start}/{min(end,len(dates))}",target=movePic,args=[prog,dates[start:min(end,len(dates))]]))
      start,end = end,end+step
    for i in t:#runs threads
      i.start()
    for i in t:#awaits threads
      i.join()
  print("\ndone!")

def movePic(prog:progBar, dates:list[list[str]]) -> None:
  """
  Moves pictures to a new location based on the given dates.
  Args:
    prog (progBar): An instance of the progBar class.
    dates (list[list[str]]): A list of lists containing picture information. 
    Each inner list should have two elements: the picture path and the date in the format "YYYY:MM:DD".
  Returns:
    None
  """
  global folders
  for i in dates:
    name:str = ""
    if(folders):
      name = i[0].split("/")[-1]# the file name
    else:
      name = i[0].removeprefix(path)# everything in the (relative) path after start path(still sorted in original folders)
    year = i[1].split(":")[0]
    month = i[1].split(":")[1]
    day = i[1].split(":")[2]
    
    if(len(day) > 2):
      day = day.split(" ")[0]
    newPath:str
    if(precision and highPrecision):# consider where to put the file
      newPath = f"./sorterede/{year}/{month}/{day}/{name}"
    elif(precision):
      newPath = f"./sorterede/{year}/{month}/{name}"
    elif(highPrecision):
      newPath = f"./sorterede/{name}"
    else:
      newPath = f"./sorterede/{year}/{name}"
    
    makeFile(newPath, i[0],not makeCopy)# save the file
    prog.incriment()

def makeFile(newPath:str, orgPath:str, delete:bool):
  """
  Create a file at the specified `newPath` by copying or moving the file from `orgPath`.
  Args:
    newPath (str): The path where the new file will be created.
    orgPath (str): The path of the original file to be copied or moved.
    delete (bool): A flag indicating whether to move the file.
  Returns:
    None
  Raises:
    None
  """
  
  if(orgPath == newPath):# can cause problems when writing to the same file, so avoid it (especially when moving)
    return
  
  if (not os.path.exists(newPath)): #see if file does not exist
    b = os.makedirs(newPath[::-1].split("/",1)[1][::-1],mode = 0o777,exist_ok=True)# generate folders, NOT the file 
    f = open(newPath,'a')# generate the file
    f.close()
  else:# if the file name exists move the old file to a new name and try again
    makeFile(newPath[::-1].split(".",1)[1][::-1] + "(1)." + newPath[::-1].split(".",1)[0][::-1],newPath,True)
    makeFile(newPath,orgPath,delete)
  
  try:# write to the new file
    if(delete):
      move(orgPath,newPath)
    else:
      copy(orgPath,newPath)
  except:# if the file could not be written to
    print(f"failure")
    printData(orgPath, "\t")

def printData(picPath:str, prefix = "") -> None:
  """
  Prints the data of an image file.
  Parameters:
  - picPath (str): The path of the image file.
  - prefix (str): Optional prefix to be added before each printed line.
  Returns:
  None
  """
  
  print(f"{prefix}{picPath}",end="\n\n")
  i = img.open(picPath)
  try:
    from PIL.ExifTags import TAGS
    i.load()
    print(picPath)
    exif = i.getexif()
    for tag in exif:
      data = exif.get(tag)
      if isinstance(data, bytes):
        data = data.decode()
      print(f"{prefix}{tag}:{TAGS.get(tag,tag)}:{data}")
  except:#if standard exif reading fails get all metadata instead
    parser = createParser(picPath)
    metadata:Metadata = extractMetadata(parser)
    data:dict = metadata.exportDictionary().get("Metadata")
    for key in data.keys():
      key:str
      print(f"{prefix}{key}:{data.get(key)}")
    
    if(data == None or len(data.keys()) == 0):
      print(f"\n{prefix}Data Search Failed")
  i.close()

def fileDate(picPath:str) -> tuple[str]:
  """
  Returns the date and time of the earliest timestamp associated with the given picture file.
  Parameters:
  picPath (str): The path of the picture file.
  Returns:
  tuple[str]: A tuple containing the formatted date and time.
  """
  
  time = min(min(
    datetime.fromtimestamp(os.stat(picPath).st_atime),
    datetime.fromtimestamp(os.stat(picPath).st_ctime)),
    datetime.fromtimestamp(os.stat(picPath).st_mtime)
  )
  return timeFormat(picPath,time)

def timeFormat(picPath:str, time:datetime)-> tuple[str]:
  """
  Formats the given time object into a string and appends it to the given picture path.
  Parameters:
  picPath (str): The path of the picture.
  time (datetime): The time object to be formatted.
  Returns:
  str: The formatted picture path with the time appended.
  Example:
  >>> timeFormat("/path/to/picture.jpg", datetime.datetime(2022, 10, 15, 12, 30, 45))
  '/path/to/picture.jpg,2022:10:15'
  """
  
  return (picPath,time.strftime("%Y") + ":" + time.strftime("%m") + ":" + time.strftime("%d"))

def removeDubes() -> None:
  """
  Removes duplicate images from the list of files.
  skips non image files
  Returns:
    None
  """
  
  if(not antiDube): return
  prog = progBar(len(files), disable=debug)
  dubes = []
  print("\nchecker for identiske billeder")
  for i in range(len(files)):
    prog.incriment("filer checket")
    if(img.isImageType(not files[i])): continue
    for j in range(i+1,len(files)):
      if(img.isImageType(not files[j])): continue
      img1 = img.open(files[i])
      img2 = img.open(files[j])
      if(
        (img1.size == img2.size) and #see that the images are the same size (for speed)
        (ImageChops.difference(img1,img2).getbbox() == None)):
        # get the difference and remove all black pixels 
        # if any non black pixels are left the images are not identical
        dubes.append(i)
        break
  print(f"\n{len(dubes)} identiske billeder fundet")
  prog = progBar(len(dubes), disable=debug)
  print("fjerner identiske billeder")
  for i in dubes[::-1]:
    prog.incriment()
    files.remove(files[i])
  print("identiske billeder er blevet fjernet")

init()
check()
removeDubes()
findDate()
movePictures()

#ending loop for debug and user being able to see know the program didn't crash but actually finished
while(True):
  print("\n\nluk vinduet eller tryk q for at slukke programet")
  print("tryk d for at se info om de filer der blev sorteret")
  print("tryk r for at se filer der ikke blev sorteret")
  user = input("luk vinduet eller tryk q for at slukke program: ")
  if(user == "q"): 
    exit()
  if(user == "d"):
    for i in dates:
      printData(i[1])
  if(user == "r"):
    for path in files:
      printData(path)