#!/usr/bin/python3
#curse forge modpack installer by Ricard Grace
import sys
import json
import zipfile
import os
import urllib.request
import urllib.error
import re
import shutil
import subprocess
import time
import threading

tempDir = "modtemp"
manifestLoc = os.path.join(tempDir, "manifest.json")
modsLoc = os.path.join(tempDir, "mods")
minecraftProfLoc = os.path.join(os.getenv("APPDATA"), os.path.join(".minecraft", "launcher_profiles.json"))
downloadRetryCount = 2

def main():
    print("Minecraft modpack installer by Ricard Grace")

    #read in the manifest file that will be provided as the second arg, right?
    #do checking of input arguments
    if (len(sys.argv) < 2):
        print(sys.stderr, "This program needs to be run from the command line (Double clicking on it does not work!).\n\tExiting...")
        print("Usage: " + sys.argv[0] + " <mod.zip>")
        input("Press enter to continue...")
        sys.exit(2)

    if (not os.path.exists(sys.argv[1])):
        print(sys.stderr, f"Modpack file '{sys.argv[1]}' does not exist! Please check where it is located and try again.\n\tExiting...")
        sys.exit(2)

    nozip = False
    nodown = False
    noforge = False
    noprofile = False
    for i in range(2, len(sys.argv)):
        if (sys.argv[i] == "-nozip"):
            nozip = True
        elif (sys.argv[i] == "-nodown"):
            nodown = True
        elif (sys.argv[i] == "-noforge"):
            noforge = True
        elif (sys.argv[i] == "-noprofile"):
            noprofile = True

    if (not nozip):
        #delete the tempDir folder if it exists
        if (os.path.isdir(tempDir)):
            shutil.rmtree(tempDir)
            time.sleep(2)
        os.mkdir(tempDir)
        #the file we are given is a zip package
        #open the zip
        print("Unzipping " + sys.argv[1] + "...")
        zip_ref = zipfile.ZipFile(sys.argv[1], 'r')
        zip_ref.extractall(tempDir)
        zip_ref.close()
        print("\tDone!\n")

    #now to do file processing
    exists = os.path.isfile(manifestLoc)
    if (not exists):
        print(sys.stderr, "Manifest file cannot be found.\n\tExiting...")
        sys.exit(1)

    try:
        f = open(manifestLoc)
    except:
        print(sys.stderr, f"Could not open manifest file '{manifestLoc}'.\n\tExiting...")
        sys.exit(1)

    try:
        j = json.load(f)
    except:
        print(sys.stderr, f"File '{manifestLoc}' is not a valid json file!\n\tExiting...")
        sys.exit(1)
    finally:
        f.close()

    minecraftVersion = j["minecraft"]["version"]
    forgeVersion = re.findall(r'[0-9.]*$', j["minecraft"]["modLoaders"][0]["id"])[0]
    name = j["name"]
    modVersion = j["version"]
    gamedir = os.path.join(os.getenv("APPDATA"), ".minecraft", name)
    print("Installing Modpack '"+name+"'")
    print("\tVersion: " + modVersion)
    print("\tMinecraft: " + minecraftVersion)
    print("\tForge: " + forgeVersion)
    while (True):
        print("\nIs this correct? (y/n)")
        t = input()
        if (t in ("y", "Y")):
            break
        elif (t in ("n", "N")):
            print("\tExiting...")
            sys.exit(0)
        else:
            continue

    if (not nodown):
        while (True): #keep retrying until no errors
            #time to download all the mods
            #generate a list of mods we need to get and their urls
            print("\nGenerating mod urls...")
            fileList = []
            for mod in j["files"]:
                fileList.append((str(mod["projectID"]),str(mod["fileID"])))
            print("\tDone!")
            numMods = len(fileList)
            print(f"\tFound {numMods} mods")

            print("\nDownloading mods:")
            #create the folder we are going to store the mods in if it does not exist
            if (os.path.isdir(modsLoc)):
                #delete it and remake it
                shutil.rmtree(modsLoc)
                time.sleep(2)
            os.mkdir(modsLoc)

            #thread code here
            errorList = []
            modListLock = threading.Lock()
            errorListLock = threading.Lock()
            data = DownloadThreadData(fileList, errorList, modListLock, errorListLock)
            #spawn 4 threads
            for i in range(0, 4):
                thr = threading.Thread(target=DownloadModsThread, args=(data,))
                thr.daemon = True
                thr.start()

            #wait for all the threads to finish
            while (True):
                if (data.fileDone >= data.fileCount):
                    #then we have finished, display the exit message
                    print("Done!                                             ")
                    break
                else:
                    #display the progress message and then wait
                    time.sleep(0.1)
                    numBars = int(20*data.fileDone/data.fileCount)
                    progressString = "\t{0}/{1}\t[{2}{3}] {4}%".format(str(data.fileDone), str(data.fileCount), "|"*(numBars), " "*(20-numBars), str(int(100*data.fileDone/data.fileCount)))
                    print(progressString, end="\r")

            errorcount = len(errorList)
            if (errorcount > 0):
                print(sys.stderr, f"\nFailed to download {str(errorcount)} mods after {downloadRetryCount+1} tries!")
                for e in errorList:
                    print(sys.stderr, f"\t{e}")
                input("Press enter to retry download or close the installer to cancel...")
                continue
            #no error, so dont loop
            break

    if (not noforge):
        #all the mods have been acquired, now to get forge and install it
        forgename = 'forge-'+minecraftVersion+'-'+forgeVersion+'-installer.jar'
        forgeurl = 'https://files.minecraftforge.net/maven/net/minecraftforge/forge/'+minecraftVersion+'-'+forgeVersion+'/'+forgename
        print("\nDownloading " + forgename)
        try:
            rec = urllib.request.Request(forgeurl, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
            r = urllib.request.urlopen(rec)
        except (urllib.error.HTTPError, urllib.error.URLError) as err:
            print(err.fp.read())
            print(sys.stderr, f"Error downloading forge: {err.reason}\n\tExiting...")
            sys.exit(1)

        forgeF = open(os.path.join(tempDir, forgename), "wb")
        forgeF.write(r.read())
        forgeF.close()

        print("Running forge installer (It should come up as a seperate window)")
        ret = subprocess.run(["java", "-jar", os.path.join(tempDir, forgename)], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        if (ret.returncode != 0):
            print(sys.stderr, "Error during forge installation\n\tExiting...")
            sys.exit(1)

        input("Press enter when forge has finished installing to continue...\n")

    if (not noprofile):
        #now that forge has been installed, create a new profile based on the forge one
        profname = "modpack - " + name
        print("Adding/Replacing profile '"+profname+"'")
        if (not os.path.exists(minecraftProfLoc)):
            print(sys.stderr, f"Could not find your minecraft profile at '{minecraftProfLoc}' (is your minecraft installation at '%appdata%/.minecraft'?)\n\tExiting...")
            sys.exit(1)
        #find the forge version to ensure that it was actually installed
        forgevname = minecraftVersion+'-forge'+minecraftVersion+'-'+forgeVersion
        print("\tUsing forge version: " + forgevname)
        if (not os.path.isdir(os.path.join(os.getenv('APPDATA'), ".minecraft", "versions", forgevname))):
            #the old version name is not found, try the new name
            print("\tOld naming scheme not found, trying new naming scheme...")
            forgevname = minecraftVersion+'-forge'+'-'+forgeVersion
            if (not os.path.isdir(os.path.join(os.getenv('APPDATA'), ".minecraft", "versions", forgevname))):
                print(sys.stderr, f"Could not find required forge version: {forgevname} (did you install it?).\n\tExiting...")
                sys.exit(1)

        #the profile is where we expect it to be, make a new profile (or overwrite a previous one if the user is stupid enough to name their profile after a mod pack)
        profF = open(minecraftProfLoc, "r")
        profiles = json.load(profF)
        profF.close()
        #add the new profile
        if ("profiles" not in profiles):
            #create the profile dict
            profiles["profiles"] = {}
        profiles["profiles"][profname] = {}
        profiles["profiles"][profname]["name"] = profname
        profiles["profiles"][profname]["gameDir"] = gamedir
        profiles["profiles"][profname]["lastVersionId"] = forgevname
        #check how much memory the user wants to allocate
        print("How much memory do you expect this modpack to use (in GB)? Usually it will say on the modpack page the recommended value.")
        try:
            mem = float(input("Enter a number between 1.0 - 32.0 (default 4.0)\n"))
        except:
            mem = 4
            print("Could not detect a valid value. Setting memory to default of 4GB")
        if (mem < 1):
            mem = 4
            print("Invalid value! Setting memory to default of 4GB")
        elif (mem > 32):
            mem = 4
            print("Invalid value! Setting memory to default of 4GB")
        else:
            print("Using " + str(mem) + "GB of memory")

        mem = int(mem*1024)
        profiles["profiles"][profname]["javaArgs"] = "-Xms"+str(mem)+"m -Xmx"+str(mem)+"m -XX:+UseConcMarkSweepGC -XX:+UseParNewGC"
        profF = open(minecraftProfLoc, "w")
        json.dump(profiles, profF, indent=4)
        profF.close()

    #now to 'install' the modpack by copying over the mods folder and any folder spacified in the overrides
    print("\nInstalling mods")
    #make sure the directory we want to write to exists
    if (not os.path.exists(gamedir)):
        os.mkdir(gamedir)

    overridesloc = os.path.join(tempDir, "overrides")
    print("\tRemoving old files")
    #for each folder in the overides folder, delete the corresponding folder in the game directory
    overrideslist = os.listdir(overridesloc)
    for d in overrideslist:
        dpath = os.path.join(gamedir, d)
        if (os.path.isdir(os.path.join(overridesloc, d)) and os.path.exists(dpath)):
            #this is a directory which we are going to override. delete it
            shutil.rmtree(dpath)
    time.sleep(2)

    #make sure the mods folder is empty and exists
    gamemodsdir = os.path.join(gamedir, "mods")
    if (os.path.exists(gamemodsdir)):
        shutil.rmtree(gamemodsdir)
        time.sleep(2)
    #the mods folder does not exist, so make it
    os.mkdir(gamemodsdir)

    #now copy all the things
    print("\tInstalling base mods")
    if (os.path.exists(modsLoc)):
        #shutil.copy(modsLoc, gamedir)
        CopyReplaceFile(modsLoc, gamemodsdir)
    else:
        print(sys.stderr, f"Cannot find temp mod download folder (did you delete or move them after I downloaded them?)\n\tExiting...")
        sys.exit()

    print("\tInstalling overrides")
    #move contents of the overrides folder, not the folder itself
    #files = os.listdir(overridesloc)
    #for f in files:
        #shutil.copy(os.path.join(overridesloc, f), gamedir)
    CopyReplaceFile(overridesloc, gamedir)
    print("Done!")

    print("\nClean up temporary installation data? (y/n)\n(If this data is not cleaned up you can reinstall the modpack without redownloading by running \""+sys.argv[0]+" '"+sys.argv[1]+"' -nozip -nodown -noforge\")")
    while (True):
        t = input()
        if (t == "y" or t == "Y"):
            #cleanup then break
            print("\tRemoving '" +tempDir+"'")
            shutil.rmtree(tempDir)
            print("\tDone!")
            break
        elif (t == "n" or t == "N"):
            print("\tNo Cleanup")
            break
        else:
            continue


    print(name + " has been installed - Enjoy!")

#copy everything in srcpath to dstpath
#both paths are directories and exist
#creates directories as needed and replaces any existing files
#existing directories are merged into
def CopyReplaceFile(srcpath, dstpath):
    contents = os.listdir(srcpath)
    for file in contents:
        srcfilepath = os.path.join(srcpath, file)
        dstfilepath = os.path.join(dstpath, file)
        if (os.path.isdir(srcfilepath)):
            #recurse using this folder
            if (not os.path.exists(dstfilepath)):
                os.mkdir(dstfilepath)
            CopyReplaceFile(srcfilepath, dstfilepath)
        else:
            #this is a file we need to copy. Check if the dest exists and delete if needed
            if (os.path.exists(dstfilepath)):
                os.remove(dstfilepath)
            shutil.copy2(srcfilepath, dstfilepath)

class DownloadThreadData():
    def __init__(self, fileList, errorList, fileListLock, errorListLock):
        self.fileList = fileList
        self.errorList = errorList
        self.fileListLock = fileListLock
        self.errorListLock = errorListLock
        self.filePos = 0
        self.fileDone = 0
        self.fileCount = len(self.fileList)

def DownloadModsThread(data):
    while (True):
        #get the next mod in the list and download it
        with data.fileListLock:
            if (data.filePos >= data.fileCount):
                break
            else:
                #there is a mod to download, get it
                currFile = data.fileList[data.filePos]
                filePos = data.filePos
                data.filePos += 1
        #should only get here if there is actually a mod to download
        for i in range(downloadRetryCount):
            (error, resultString) = DownloadMod(currFile[0], currFile[1])
            if (not error):
                #no error, so dont retry
                break
        if (error):
            with data.errorListLock:
                data.errorList.append(f"(mod {filePos})\t{resultString}")
        #clear the line then display the result string to the user
        print(f"{' '*50}\r{resultString}")
        #print(' '*50, end='\r')
        #print(resultString)
        with data.fileListLock:
            data.fileDone += 1


#(error, reason)
def DownloadMod(projectID, fileID):
    #first acquire the download link from the curseforge interface
    interfaceurl = f"https://api.curse.tools/v1/cf/mods/{projectID}/files/{fileID}/download-url"
    (error, result) = downloadURL(interfaceurl)
    if (error):
        return (True, f"An issue was encountered when trying to retrieve a download link\n\t{result}")

    #result should contain the result object with the link to the mod file
    link = result.read().decode('utf-8')
    match = re.findall(r"(https?://)(.*[^\"}])", link)
    # match = re.sub("%2520", " ", match)
    # downloadLink = match[0][0] + urllib.parse.quote(match[0][1])
    # parsing sometimes messes up spaces
    downloadLink, error, result = None, None, None
    try:
        # see if the link contains unescaped spaces:
        index = match[0][1].find(" ")
        if index == -1:
            downloadLink = match[0][0] + match[0][1]
        else:
            downloadLink = match[0][0] + urllib.parse.quote(match[0][1])

    except IndexError:
        return True, f"An issue was encountered when trying to parse URL\n\t{link}\nFrom:\n\t{interfaceurl}"

    (error, result) = downloadURL(downloadLink)

    if error:
        return True, f"An issue was encountered when trying download a mod\n\t{result}"

    # we got the mod boyz, lets get to writing files!
    modName = re.findall(r'[^/]*$', result.geturl())[0]
    modName = urllib.parse.unquote(modName)
    # print(str(count) + "/" + str(num) + "\t" + modName)
    modName = re.sub(r'\\/:\*\?"<>\|', "-", modName)
    modF = open(os.path.join(modsLoc, modName), "wb")
    modF.write(result.read())
    modF.close()
    return (False, f"{modName}")

#given a url, will try and download it, returns (error, requestobject/string)
def downloadURL(url):
    if url is None:
        return True, "EMPTY URL"
    #im not a bot lol
    agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0'
    tries = 0

    while (tries < 3):
        try:
            rec = urllib.request.Request(url, headers={'User-Agent': agent})
            r = urllib.request.urlopen(rec)
            return (False, r)
        except urllib.error.HTTPError as e:
            return (True, f"HTTP ERROR {e.code}: {url}")
        except urllib.error.URLError as err:
            return (True, f"URL ERROR {err.reason}: {url}")
        except:
            tries += 1

    if (tries >= 3):
        return (True, f"Probably timed out: {url}")


if __name__ == '__main__':
    main()
