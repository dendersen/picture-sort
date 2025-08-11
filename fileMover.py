#!/usr/bin/python3

import requests
import os
from datetime import datetime
from threading import Thread
from progBar import progBar
f = open("API_KEY.txt", "r")
API_KEY = f.read().strip()
f.close()
BASE_URL = 'http://185.140.3.30:30041/api'  # replace as needed
FILE_PATH = "F:\\takeout_11-08-25"
MAX_THREADS = 25

def upload(files, destination, startIndex):
    for localIndex, file in enumerate(files):
        index = localIndex + startIndex
        if(os.path.isdir(file)):
            destination[index] = f"Skipping directory: {file}"
            continue
        stats = os.stat(file)

        headers = {
            'Accept': 'application/json',
            'x-api-key': API_KEY
        }

        data = {
            'deviceAssetId': f'{file}-{stats.st_mtime}',
            'deviceId': 'python',
            'fileCreatedAt': datetime.fromtimestamp(stats.st_mtime),
            'fileModifiedAt': datetime.fromtimestamp(stats.st_mtime),
            'isFavorite': 'false',
        }

        files = {
            'assetData': open(file, 'rb')
        }
        try:
            response = requests.post(
            f'{BASE_URL}/assets', headers=headers, data=data, files=files)
            destination[index] = response.json()

        except Exception as e:
            destination[index] = {'error': str(e)}

def addFilesFromDir(dir):
    files = []
    for file in [os.path.join(dir, f) for f in os.listdir(dir)]:
        if os.path.isdir(file):
            files.extend(addFilesFromDir(file))
        else:
            files.append(file)
    return files

def main():
    threads = []
    
    print("prepping ...")
    
    files = addFilesFromDir(FILE_PATH)
    responses = [None] * len(files)
    
    if(len(files) < MAX_THREADS):
        prog = progBar(len(files),prefix="starting")
        for index,file in enumerate(files):
            prog.incriment()
            thread = Thread(target=upload, args=(file, responses, index))
            threads.append(thread)
            responses.append(None)
            thread.start()
    else:
        filesPerThread = len(files) // MAX_THREADS
        prog = progBar(MAX_THREADS,prefix="starting")
        for t in range(0,MAX_THREADS):
            prog.incriment()
            thread = Thread(target=upload, args=(files[filesPerThread * t:filesPerThread * (t + 1)], responses, t * filesPerThread))
            threads.append(thread)
            responses.append(None)
            thread.start()
        if(len(files) > MAX_THREADS * filesPerThread):
            thread = Thread(target=upload, args=(files[MAX_THREADS * filesPerThread:], responses, MAX_THREADS * filesPerThread))
            threads.append(thread)
            responses.append(None)
            thread.start()
    prog.end()
    print("\n")
    
    prog = progBar(len(threads),prefix="running")
    for thread in threads:
        prog.incriment()
        thread.join()
    prog.end()
    print("\n")
    
    dup = 0
    unsupported = 0
    success = 0
    http_errors = 0
    none = 0
    
    for i, response in enumerate(responses):
        if response is not None:
            if(response.get('status') == "created"):
                success += 1
            elif(response.get('status') == 'duplicate'):
                dup += 1
            elif(response.get('status') == 'unsupported'):
                unsupported += 1
            elif(response.get("error") == "Bad Request"):
                unsupported += 1
            elif(response.get("error") is not None):
                http_errors += 1
            else:
                none += 1
            if(i < len(files)):
                print(f"Response for {files[i]}: {response}")
        else:
            if(i < len(files)):
                print(f"Response for {files[i]}: No response")
            http_errors += 1
    print(f"Summary:")
    print(f"  Successful: {success}")
    print(f"  Duplicates: {dup}")
    print(f"  Unsupported: {unsupported}")
    print(f"  HTTP Errors: {http_errors}")
    print(f"  noResponse: {none}")
    print(f"  Total: {success+dup+unsupported+http_errors+none}/{len(files)}")

main()