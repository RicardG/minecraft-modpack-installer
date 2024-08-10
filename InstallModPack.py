#!/usr/bin/python3
# CurseForge modpack installer by Ricard Grace
import sys
import json
import urllib.parse
import zipfile
import os
import urllib.request
import urllib.error
import re
import shutil
import subprocess
import base64
import time
import threading
import logging
import argparse
import random


# === BUILD INFO ===
APP_NAME: str = "Minecraft Modpack Installer"
APP_AUTHOR: str = "Ricard Grace"
APP_VERSION: str = "v2.0.0"

# === CONSTANTS ===
# PATHS
CWD: str = os.path.dirname(os.path.realpath(sys.argv[0]))
LOG_FILE: str = os.path.join(CWD, "modpack_installer_log.txt")
MINECRAFT_FPATH_DEFAULT: str = os.path.join(os.getenv("APPDATA", "/"), ".minecraft") # If APPDATA is not an environment variable this path will likely be invalid but will not cause a crash.
# URL DOWNLOAD
DOWNLOAD_TRIES_MAX: int = 3 # Attempt downloads up to this many times before giving up
DOWNLOAD_TIMEOUT: int = 5 # Timeouts for downloads
DOWNLOAD_RETRY_WAIT_MIN: int = 1 # Download retry min wait time
DOWNLOAD_RETRY_WAIT_SPREAD: int = 2 # Download retry random scatter time
DOWNLOAD_STEP_TRIES_MAX: int = 3 # Only allow running the entire download step this many times before failing
# FOLDER/FILE NAMES
MANIFEST_FILE: str = "manifest.json"
MINECRAFT_PROFILE_FILE: str = "launcher_profiles.json"
MINECRAFT_VERSIONS_FOLDER: str = "versions"
MODS_FOLDER: str = "mods"
MODPACK_OVERRIDES_FOLDER: str = "overrides"
# MISC
PROGRESS_BAR_SIZE: int = 40
REMOVE_SLEEP: float = 1.0
# MINECRAFT MEMORY
GB_TO_MB: int = 1024
MEMORY_MIN: float = 1.0
MEMORY_MAX: float = 32.0 # Anything beyond this is crazy. Especially since the benefits start to break down after 10GB.
# HTTP HEADERS
API_DOWNLOAD_HEADERS: dict[str, str] = {
    'Accept': 'application/json'
}
DEFAULT_DOWNLOAD_HEADERS: dict[str, str] = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0'
}
# ARGUMENT DEFAULTS
DEFAULT_INSTALL_TEMP: str = "modpack_install_temp"
DEFAULT_DOWNLOAD_THREADS: int = 4
DEFAULT_MEMORY_MAX: float = 4.0 # in GB
DEFAULT_JAVA_ARGS: str = "-XX:+UnlockExperimentalVMOptions -XX:+UseG1GC -XX:G1NewSizePercent=20 -XX:G1ReservePercent=20 -XX:MaxGCPauseMillis=50 -XX:G1HeapRegionSize=16M -Djava.net.preferIPv4Stack=true"
# PARAMETER NAMES
PARAM_MINECRAFT_PATH: str = "-minecraftpath"


def main(args: dict) -> int:
    """
    Does main really need an explanation?
    """
    # Give the user something nice to look at
    title: str = f"| {appVersionStr()} |"
    title_border: str = "="*len(title)
    print(f"{title_border}\n{title}\n{title_border}")

    # Do some checks/processing on arguments
    logging.info("Processing arguments...")
    fpath_modpack :str = os.path.realpath(args["fpath_modpack"])
    if not os.path.exists(fpath_modpack):
        print(f"Modpack file '{fpath_modpack}' does not exist! Please check where it is located and try again.\n\tExiting...", file=sys.stderr)
        logging.info(f"Failed to find input modpack file at path '{fpath_modpack}'")
        return 1
    fpath_install_temp: str = os.path.realpath(args["tempfolder"])
    fpath_minecraft: str = os.path.realpath(args["minecraftpath"])
    modpack_profile_name: str|None = args["modpackname"]
    no_unzip: bool = args["nounzip"]
    no_download: bool = args["nodownload"]
    no_forge: bool = args["noforge"]
    no_profile: bool = args["noprofile"]
    auto_accept: bool = args["autoaccept"]
    download_thread_count: int = max(args["downloadthreads"], 1)
    forge_installer_headless: bool = args["forgeheadless"]
    modpack_memory_max: float = args["memorymax"]
    modpack_java_args: str = args["javaargs"]

    # Unzip the supplied modpack zip file
    if not no_unzip:
        logInfo("Unzipping modpack zip...")
        try:
            unzipToDir(fpath_modpack, fpath_install_temp)
        except Exception as e:
            # Something happened. This is unrecoverable.
            print(f"Error while unzipping modpack file '{fpath_modpack}'", file=sys.stderr)
            raise e
        logInfo("> Done!")
    else:
        logInfo("Skipping modpack unzip due to flag...")

    # Read the contents of the manifest file
    logInfo("Reading modpack manifest...")
    fpath_manifest = os.path.join(fpath_install_temp, MANIFEST_FILE)
    try:
        manifest = readManifestFile(fpath_manifest)
    except Exception as e:
        # Something happened. This is unrecoverable.
        print(f"Error while reading manifest file '{fpath_manifest}'", file=sys.stderr)
        raise e
    logInfo("> Done!")

    # Parse the manifest file
    logInfo("Parsing manifest file...")
    try:
        minecraft_version: str = manifest["minecraft"]["version"]
        forge_version: str = re.findall(r'[0-9.]*$', manifest["minecraft"]["modLoaders"][0]["id"])[0]
        modpack_name: str = manifest["name"].strip()
        modpack_version: str = "Not Supplied"
        fpath_install: str = os.path.join(fpath_minecraft, modpack_name)
        if not modpack_profile_name:
            modpack_profile_name = f"modpack - {modpack_name}"
        modpack_profile_name = modpack_profile_name.strip()
        if "version" in manifest:
            modpack_version = manifest["version"]
    except Exception as e:
        # Something happened. This is unrecoverable.
        print(f"Error while parsing manifest file '{fpath_manifest}'", file=sys.stderr)
        raise e
    logInfo("> Done!")

    # Prompt the user with details of the installation and if they want to continue
    message=f"""Modpack Name: {modpack_name}
Modpack Version: {modpack_version}
Forge Version: {forge_version}
Minecraft Version: {minecraft_version}
Minecraft Path: {fpath_minecraft}

Modpack Install Location: {fpath_install}
Modpack Profile Name: {modpack_profile_name}"""
    prompt = "Details of modpack installation above. Continue? (y/n)"
    if showPromptYN(message, prompt, auto_accept):
        logInfo("Continuing with installation...")
    else:
        # Gracefully exit without error
        logInfo("Installation cancelled. Exiting...")  
        return 0

    # Start the process of downloading all the required mods.
    if not no_download:
        # Extract the mod list from the manifest file
        logInfo("Detecting mods...")
        mod_list: list[dict] = readManifestModList(manifest)
        logInfo(f"Detected {len(mod_list)} mods in modpack")

        # Run the download loop
        logInfo("Starting download loop...")
        if downloadModList(mod_list, fpath_install_temp, download_thread_count, auto_accept):
            logInfo(f"Successfully downloaded all mods.")
        else:
            logInfo("> Exiting install with download error.")
            return 1

        # Clear the progress bar
        print(f"{' '*int(PROGRESS_BAR_SIZE+30)}\r", end="")
    else:
        logInfo("Skipping mod download due to flag...")

    # Download and install forge
    if not no_forge:
        # TODO, get forge installer headless command
        # Download
        logInfo("Downloading forge installer...")
        try:
            forge_file = downloadForgeInstaller(minecraft_version, forge_version, fpath_install_temp)
        except Exception as e:
            logError("Failed to download forge")
            logInfo("> Exiting install with forge error.")
            return 1

        # Install
        logInfo(f"> Running forge installer '{forge_file}'...")
        if forge_installer_headless:
            print("\tRunning in headless mode due to flag. Please hold (puts on hold music)...")
        else:
            print("\tIt will show up in a seperate window. Follow the installation prompts then come back here.")
        # TODO, check for java installation
        try:
            runForgeInstaller(fpath_install_temp, forge_file, fpath_minecraft, forge_installer_headless)
        except Exception as e:
            logError("Failed to install forge")
            logInfo("> Exiting install with forge error")
            return 1
        logInfo("Detected forge installer closed without error")

        # Check the installed version of forge exists
        forge_install_name: str = isForgeVersionInstalled(fpath_minecraft, minecraft_version, forge_version)
        if not forge_install_name:
            # Could not find the forge installation...
            logError("Failed to find forge installation. Was it installed?")
            logInfo("> Exiting install with forge error")
            return 1

        logInfo(f"Found forge version '{forge_install_name}' - install successful!")
    else:
        logInfo("Skipping forge download and install due to flag...")

    if not no_profile:
        logInfo(f"Setting up modpack profile '{modpack_profile_name}'")

        # Check the minecraft profile file exists
        fpath_minecraft_profile: str = os.path.join(fpath_minecraft, MINECRAFT_PROFILE_FILE)
        if not os.path.isfile(fpath_minecraft_profile):
            logError(f"Failed to find minecraft profile file at '{fpath_minecraft_profile}'")
            print(f"Please check your minecraft installation location and set the '{PARAM_MINECRAFT_PATH}' parameter accordingly.")
            logInfo("> Exiting install with profile setup error")
            return 1

        # TODO make a backup in case we ruin it

        # Read the minecraft profile
        with open(fpath_minecraft_profile, "r") as f:
            try:
                minecraft_profiles: dict = json.load(f) # Must be a dict at top level
            except Exception as e:
                logging.exception("Failed to parse minecraft profile")
                logError("Failed to parse minecraft profile")
                print("Is your profile corruped? Minecraft install path incorrect?")
                logInfo("> Exiting install with profile error")
                return 1



        # Start updating the profile
        if "profiles" not in minecraft_profiles:
            minecraft_profiles["profiles"] = {}
        minecraft_profiles["profiles"][modpack_profile_name] = {}
        minecraft_profiles["profiles"][modpack_profile_name]["name"] = modpack_profile_name
        minecraft_profiles["profiles"][modpack_profile_name]["gameDir"] = fpath_install
        # Unfortunately need to do this again just in case
        forge_install_name: str = isForgeVersionInstalled(fpath_minecraft, minecraft_version, forge_version)
        minecraft_profiles["profiles"][modpack_profile_name]["lastVersionId"] = forge_install_name

        # Get memory allocation
        message = """Modpacks will sometimes specify a minimum or recommended
memory setting on the modpack page. You can use that value
or specify one yourself. Values between 1.0 & 32.0 GB are
allowed here. 
Note: Values above 10.0 GB generally do not do much in
terms of performance since Java has no idea how to use that
much memory effectively. If you are still unsure, 4.0 GB is
a good 'mid' value which will work with most lite to mid
sized modpacks. 6.0 - 8.0+ GB is generally required for 
larger modpacks.
Note 2: The memory argument can sometimes be ignored by the
launcher. It is worth checking the profile created to see
if it is going to respect the value in Java args."""
        prompt = "Choose how much memory to use for the modpack in GB. Decimals are allowed."
        user_memory: float = showPromptNum(message, prompt, auto_accept, modpack_memory_max)
        if user_memory < MEMORY_MIN:
            user_memory = MEMORY_MIN
            logInfo(f"Clamping memory to minimum of {MEMORY_MIN} GB.")
        elif user_memory > MEMORY_MAX:
            user_memory = MEMORY_MAX
            logInfo(f"Clamping memory to maximum of {MEMORY_MAX} GB.")
        logInfo(f"Setting modpack max memory to {user_memory} GB")

        # Convert to MB
        user_memory = int(user_memory * GB_TO_MB)

        # Set the args
        minecraft_profiles["profiles"][modpack_profile_name]["javaArgs"] = f"{modpack_java_args} -Xms{user_memory}m -Xmx{user_memory}m"
        # Also set the "memoryMax" value in case your launcher uses this.
        # The official launcher does not. I do not know what launcher you are using...
        minecraft_profiles["profiles"][modpack_profile_name]["memoryMax"] = user_memory

        # Write the profile
        with open(fpath_minecraft_profile, "w") as f:
            json.dump(minecraft_profiles, f, indent=4)        
    else:
        logInfo("Skipping profile setup due to flag...")

    # Do instalation by copying all the relevant mods over to the target directory
    logInfo("Copying mods to install directory")
    # Ensure the target directory exists
    if not generateFolder(fpath_install):
        logError("Failed to prepare install directory")
        logInfo("> Exiting with install error")
        return 1


    fpath_install_temp_overrides: str = os.path.join(fpath_install_temp, MODPACK_OVERRIDES_FOLDER)

    # Clear override folders in install location
    logInfo("Removing old installed overrides...")
    overrides: list[str] = os.listdir(fpath_install_temp_overrides)
    for override in overrides:
        fpath_install_temp_override: str = os.path.join(fpath_install_temp_overrides, override)
        logging.info(f"Processing override '{fpath_install_temp_override}'")
        if not os.path.isdir(fpath_install_temp_override):
            # Must be a directory to regenerate the directory.
            continue
        fpath_install_override: str = os.path.join(fpath_install, override)
        # Regenerate the target override directories
        if not regenerateFolder(fpath_install_override):
            logError("Failed to prepare install override directory")
            logInfo("> Exiting with install error")
            return 1

    # Make sure the mods folder is empty and exists
    logInfo("Removing old installed mods...")
    fpath_install_mods = os.path.join(fpath_install, MODS_FOLDER)
    if not regenerateFolder(fpath_install_mods):
            logError("Failed to prepare install override directory")
            logInfo("> Exiting with install error")
            return 1

    # Copy base mods (non-overrides) into install location
    logInfo("Installing base mods...")
    fpath_install_temp_mods = os.path.join(fpath_install_temp, MODS_FOLDER)
    if os.path.isdir(fpath_install_temp_mods):
        # Copy all the mods from the install temp to the install location
        copyReplaceFile(fpath_install_temp_mods, fpath_install_mods)
    else:
        # This should only occur due to user intervention (bad user) or from one of the skip flags being used incorrectly.
        logError("Mods in temporary install folder missing. Did you remove them?")
        logInfo("> Exiting install with installation error")
        return 1

    # Copy overrides
    logInfo("Installing overrides...")
    if os.path.isdir(fpath_install_temp_overrides):
        copyReplaceFile(fpath_install_temp_overrides, fpath_install)
    else:
        # This should only occur due to user intervention (bad user) or from one of the skip flags being used incorrectly.
        logError("Overrides in temporary install folder missing. Did you remove them?")
        logInfo("> Exiting install with installation error")
        return 1

    # INSTALLATION IS FINALLY COMPLETE!!!
    logInfo("Installation complete!")

    # Ask for post cleanup
    message = """Temporary installation files can allow for a quick
reinstall as long as they are not cleaned up (installing)
another mod will also clean them up. Can be useful for
doing a quick reinstall/repair/debugging without 
redownloading everything.
Note: Only useful in combination with certain flags when
running the installer."""
    query = "Clean up temporary installation data? (y/n)"
    if showPromptYN(message, query, auto_accept):
        # Do cleanup
        logInfo("Doing temporary install data cleanup...")
        removeFile(fpath_install_temp)

    logInfo("Everything done!")
    logInfo("> Exiting with success!")
    return 0


# ===========================
# HELPER FUNCTIONS BELOW HERE
# ===========================

# === Threading ===
class DownloadThreadData():
    def __init__(self, mod_list: list[dict], fpath_mods_temp: str):
        self.mod_list: list[dict] = mod_list
        self.error_list: list[str] = []
        self.mod_list_lock: threading.Lock = threading.Lock()
        self.error_list_lock: threading.Lock = threading.Lock()
        self.mod_list_position = 0
        self.mods_done = 0
        self.mods_total: int = len(self.mod_list)
        self.fpath_mods_temp = fpath_mods_temp


def downloadModList(mod_list: list[dict], fpath_install_temp: str, download_thread_count: int, auto_accept: bool=False) -> bool:
    """
    Runs the download loop with retries
    Returns if download was successful
    """
    download_successful = False
    for i in range(0, DOWNLOAD_STEP_TRIES_MAX): # Allow retries up to a max
        # Prepare where all the mods are going to be downloaded to
        logInfo("Preparing temporary download folder...")
        fpath_mods_temp = os.path.join(fpath_install_temp, MODS_FOLDER)
        if not regenerateFolder(fpath_mods_temp):
            logError(f"Failed to prepare download folder '{fpath_mods_temp}'")
            raise Exception("Failed to prepare download folder")

        # Prepare download threads
        logInfo("Downloading mods...")
        thread_data = DownloadThreadData(mod_list, fpath_mods_temp)
        download_threads: list[threading.Thread] = []

        # Spawn download threads
        for i in range(0, download_thread_count):
            thread = threading.Thread(target=downloadModsThread, args=(thread_data,))
            download_threads.append(thread)
            thread.daemon = True
            thread.start()

        # Wait for download threads to do their job and update progesss bar
        while True:
            if thread_data.mods_done >= thread_data.mods_total:
                # Everything appears to be downloaded.
                # Clear the progress bar
                print(f"{' '*int(PROGRESS_BAR_SIZE+30)}\r", end="")
                logInfo("All downloads complete. Waiting for threads to stop...")
                # The threads should kill themselves. Wait for them to end.
                for thread in download_threads:
                    thread.join()
                print("> Done!")
                break
            else:
                # Update the progress bar
                time.sleep(0.1)
                writeProgressBar(thread_data.mods_done, thread_data.mods_total)

        # Check for any download errors and offer retry
        download_error_count = len(thread_data.error_list)
        if download_error_count > 0:
            logError(f"Failed to download {download_error_count} mods after {DOWNLOAD_TRIES_MAX+1} tries!")
            for error_str in thread_data.error_list:
                print(f"\t{error_str}", file=sys.stderr)
            if showPromptYN("", "Retry download?", auto_accept):
                logInfo("> Retrying...")
                continue
            else:
                # The user has opted to cancel downloading
                return False
        else:
            # Download successful! Break retry loop
            download_successful = True
            break

    #check for max retries
    if not download_successful:
        logInfo("Max download retries reached, stopping download")
        return False

    # Everything is good
    return True


def downloadModsThread(thread_data: DownloadThreadData) -> None:
    """
    A function meant to be called from a thread which runs as a deamon.
    Consumes mods from the mod list and downloads them.
    Terminates it self when there are no more mods to download.
    """
    while True:
        # Get the next mod in the list and download it
        with thread_data.mod_list_lock:
            # Ensure there are still mods left to consume
            if thread_data.mod_list_position >= thread_data.mods_total:
                break
            # Get the next mod to consume
            mod_num: int = thread_data.mod_list_position
            mod: dict = thread_data.mod_list[mod_num]
            thread_data.mod_list_position += 1

        logging.info(f"Consuming mod {mod}...")

        # Download the mod. Retry handling is already done for us
        try:
            mod_name = downloadMod(mod["projectID"], mod["fileID"], thread_data.fpath_mods_temp)
            print(f"{' '*int(PROGRESS_BAR_SIZE+30)}\r", end="")
            logInfo(f"[MOD {mod_num:04}] Download successful: {mod_name}")
        except Exception as e:
            with thread_data.error_list_lock:
                thread_data.error_list.append(f"[ERROR MOD {mod_num}]\t{e}")
            print(f"{' '*int(PROGRESS_BAR_SIZE+30)}\r", end="")
            logError(f"[MOD {mod_num:04}] {e}")

        # Regardless of if we were actually successful, consider it done
        with thread_data.mod_list_lock:
            thread_data.mods_done += 1


# === Networking Ops ===
def downloadURL(url: str, headers: dict=DEFAULT_DOWNLOAD_HEADERS):
    """
    Attempts to download the given URL. The URL should already be quoted if needed.
    Retries download on error.
    Returns the open URL handle
    Raises exceptions on error.
    """
    last_error: Exception = Exception("Did not attempt download")
    for attempt in range(1, DOWNLOAD_TRIES_MAX+1):
        try:
            logging.info(f"Downloading '{url}' (Attempt {attempt})")
            request = urllib.request.Request(url, headers=headers)
            response: urllib.request._UrlopenRet = urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT)
            return response
        except urllib.error.HTTPError as e:
            last_error = Exception(f"HTTP ERROR {e.code}: {url}")
        except urllib.error.URLError as e:
            last_error = Exception(f"URL ERROR {e.reason}: {url}")
        except:
            last_error = Exception(f"UNKNOWN ERROR (probably timeout): {url}")

        # Wait a random amount of time before retrying
        time.sleep(DOWNLOAD_RETRY_WAIT_MIN + random.random()*DOWNLOAD_RETRY_WAIT_SPREAD)

    logging.error(f"Download exceeded maximum retries: {last_error}")
    raise last_error


def downloadMod(projectID: str, fileID: str, fpath_mods_temp: str) -> str:
    """
    Downloads and saves a single mod
    """
    mod_location_url: str = makeModLocationDownloadLink(projectID, fileID)

    try:
        response: urllib.request._UrlopenRet = downloadURL(mod_location_url, fixHeader(API_DOWNLOAD_HEADERS))
    except Exception as e:
        # Failed to download the url
        raise Exception(f"Failed to retrieve mod download location: {e}")

    # The response should contain the link to download the mod.
    link: str = json.loads(response.read().decode('utf-8'))["data"]
    match = re.findall(r"^(https?://)(.*)", link)
    if not match:
        raise Exception("Failed to extract mod download URL")

    # Check if CurseForge has decided to send already quoted data back to us so we do not quote again.
    url_http: str = match[0][0]
    url_address: str = match[0][1] 
    if not re.search(r'%[0-9A-Fa-f]{2}', url_address):
        # No quotes, so quote the address
        url_address = urllib.parse.quote(url_address)
    download_link: str = f"{url_http}{url_address}"

    try:
        response = downloadURL(download_link)
    except Exception as e:
        # Failed to retrieve the mod
        raise Exception(f"Failed to download mod: {e}")

    # Scrape the name of the mod from the download url
    # Note the final link may be different to what we requested due to redirection.
    match: list[str] = re.findall(r'[^/]*$', response.geturl())
    if not match:
        raise Exception("Failed to match mod name")
    mod_name: str = urllib.parse.unquote(match[0])
    # Replace any 'fancy' characters which are illegal in filenames
    mod_name = re.sub(r'\\/:\*\?"<>\|', "-", mod_name)

    # Write the bytes to file
    fpath_mod: str = os.path.join(fpath_mods_temp, mod_name)
    with open(fpath_mod, "wb") as f:
        f.write(response.read())

    # Return the name of the mod which was downloaded
    return mod_name


def fixHeader(headers: dict) -> dict:
    """
    Returns a copy of the given header object with them fixed
    """
    h:  dict = headers.copy()
    l = lambda x: base64.b64decode(x).decode("ascii")
    h.update([(l(b'eC1hcGkta2V5'), l(b'JDJhJDEwJGJMNGJJTDVwVVdxZmNPN0tRdG5NUmVha3d0ZkhiTktoNnYxdVRwS2x6aHdvdWVFSlFuUG5t'))])
    return h


def downloadForgeInstaller(minecraft_version: str, forge_version: str, fpath_install_temp: str) -> str:
    """
    Downloads and saves the specified forge version.
    Returns the name of the installer
    """
    forge_file: str = makeForgeInstallerFileName(minecraft_version, forge_version)
    forge_url: str = makeForgeInstallerDownloadLink(minecraft_version, forge_version)

    try:
        response_forge = downloadURL(forge_url)
    except Exception as e:
        logging.exception("Failed to download forge installer")
        raise Exception("Failed to download forge installer")

    # Write forge to install temp
    fpath_forge: str = os.path.join(fpath_install_temp, forge_file)
    with open(fpath_forge, "wb") as f:
        f.write(response_forge.read())

    return forge_file


# === Logging ===
def logInfo(message: str) -> None:
    """
    One liner for sending the same thing to the log file and console.
    Because effort...
    """
    logging.info(message)
    print(message)


def logWarn(message: str) -> None:
    """
    One liner for sending the same thing to the log file and console.
    Because effort...
    """
    logging.warning(message)
    print(f"[WARN] {message}", file=sys.stderr)


def logError(message: str) -> None:
    """
    One liner for sending the same thing to the log file and console.
    Because effort...
    """
    logging.error(message)
    print(f"[ERROR] {message}", file=sys.stderr)


# === Prompts ===
def showPromptYN(message: str, prompt: str, auto_accept: bool=False) -> bool:
    """
    Displays a message followed with a prompt and waits for user input (yes/no).
    Message: Longer description for context before the prompt.
    Prompt: The question to ask the user.
    Auto Accept: Do not wait for user input and always answer yes.

    Returns if the answer to the prompt was yes.
    """
    # Show the context message
    if message:
        border: str = max([len(x) for x in message.split("\n")])*"="
        print(f"{border}\n{message}\n{border}\n")

    # Show the prompt
    logging.info(f"Displaying prompt to user: {prompt}")
    print(prompt)

    # Collect input
    if auto_accept:
        logInfo("\tAuto-accept enabled. Accepting prompt...")
        return True
    else:
        while True:
            print("> ", end="")
            t: str = input()
            if t in ("y", "Y"):
                # Positive response
                logging.info("Prompt got positive response")
                return True
            elif t in ("n", "N"):
                # Negative response
                logging.info("Prompt got negative response")
                return False
            else:
                # Invalid response
                logging.info(f"Prompt got invalid response '{t}'. Repeating...")
                print(prompt)
                continue


def showPromptNum(message: str, prompt: str, auto_accept: bool=False, auto_value: float=0.0) -> float:
    """
    Displays a message followed with a prompt and waits for user input (numeric).
    Message: Longer description for context before the prompt.
    Prompt: The question to ask the user.
    Auto Accept: Do not wait for user input and always answer with auto_value.
    Auto Value: The default value to use. Also used as the auto accept value

    Returns a valid answer to the prompt
    """
    # Show the context message
    if message:
        border: str = max([len(x) for x in message.split("\n")])*"="
        print(f"{border}\n{message}\n{border}\n")

    # Show the prompt
    logging.info(f"Displaying prompt to user: {prompt}")
    print(prompt)

    # Collect input
    if auto_accept:
        logInfo(f"\tAuto-accept enabled. Using auto accept value = {auto_value}...")
        return auto_value
    else:
        while True:
            print("> ", end="")
            s: str = input()
            try:
                n: float = float(s)
                logging.info(f"Prompt got postive response '{n}'")
                return n
            except:
                # Invalid response
                logging.info(f"Prompt got invalid response '{s}'. Repeating...")
                print(prompt)
                continue


def writeProgressBar(progress_current: int, progress_max: int, max_bars: int=PROGRESS_BAR_SIZE) -> None:
    """
    Writes a progress bar to the console with the given size and percentage progress.
    progress_current: Current progress level.
    progress_max: How much is considered complete.
    max_bars: How many characters should be used to represent a full bar.
    """
    progress: float = progress_current/progress_max
    numBars = int(max_bars*progress)
    progressString: str = "\t{0}/{1}\t[{2}{3}] {4}%".format(str(progress_current), str(progress_max), "|"*(numBars), " "*(max_bars-numBars), str(int(100*progress)))
    print(progressString, end="\r")


# === File Parsing ===
def readManifestFile(fpath_manifest: str) -> dict:
    """
    Reads a modpack manifest file and returns the JSON data
    """
    logging.info(f"Reading manifest file '{fpath_manifest}'")
    # Ensure the source manifest exists
    if not os.path.isfile(fpath_manifest):
        logging.error(f"Bad file provided as manifest file. Path: '{fpath_manifest}'")
        raise Exception("Bad path for manifest file")

    # Read the manifest
    logging.info("Starting read")
    with open(fpath_manifest, "r") as f:
        manifest = json.load(f)

    # Ensure the decoded python object is what we are expecting
    manifest_type = type(manifest)
    if manifest_type is dict:
        # The manifest at the top level should contain only keys
        return manifest
    else:
        logging.error("Failed to decode manifest JSON")
        print("Failed to decode manifest JSON", file=sys.stderr)
        raise Exception("Failed to decode manifest JSON")


def readManifestModList(manifest: dict) -> list[dict]:
    """
    Gets the list of mods from a manifest JSON
    """
    output_list: list[dict] = []
    for mod in manifest["files"]:
        output_list.append({
            "projectID": str(mod["projectID"]), 
            "fileID": str(mod["fileID"])
            })
    return output_list


# === File Handling ===
def unzipToDir(fpath_source: str, fpath_dest: str) -> None:
    """
    Unzips a source file to the destination path.
    fpath_source: A file path to the zip file.
    fpath_dest: Path to the destination folder. This folder will be wiped before extraction.
    """
    logging.info(f"Unzipping '{fpath_source}' => {fpath_dest}")
    # Ensure the source file to unzip exists
    if not os.path.isfile(fpath_source):
        logError(f"Bad file provided as zip source '{fpath_source}'")
        raise Exception("Bad path for source zip file")

    if not regenerateFolder(fpath_dest):
        # Was not able to prepare unzip folder
        logError(f"Failed to prepare unzip location '{fpath_dest}'")
        raise Exception("Failed to prepare unzip location")

    # Actually unzip
    logging.info(f"Unzipping '{fpath_source}'")
    with zipfile.ZipFile(fpath_source, 'r') as f:
        f.extractall(fpath_dest)
    logging.info(f"Successfully unzipped")


def copyReplaceFile(fpath_src: str, fpath_dst: str) -> None:
    """
    Copies everything in the source path to the destination path.
    Overwrites any existing files and makes directories as needed.
    """
    # Get all the files
    contents: list[str] = os.listdir(fpath_src)
    for file in contents:
        fpath_src_file: str = os.path.join(fpath_src, file)
        fpath_dst_file: str = os.path.join(fpath_dst, file)
        if (os.path.isdir(fpath_src_file)):
            # This is actually a directory, recurse
            if (not os.path.exists(fpath_dst_file)):
                os.mkdir(fpath_dst_file)
            copyReplaceFile(fpath_src_file, fpath_dst_file)
        else:
            #this is a file we need to copy. Check if the dest exists and delete if needed
            logging.info(f"Copying file '{fpath_src_file}' => '{fpath_dst_file}'")
            if (os.path.exists(fpath_dst_file)):
                os.remove(fpath_dst_file)
            shutil.copy2(fpath_src_file, fpath_dst_file)


def removeFile(fpath_src: str) -> None:
    """
    Removes the specified file/folder tree
    """
    logging.info(f"Removing tree '{fpath_src}'")
    shutil.rmtree(fpath_src)
    # Wait for the OS to finish so we do not get inconsistent behaviour
    time.sleep(REMOVE_SLEEP)


def generateFolder(fpath_folder: str) -> bool:
    """
    Makes the specified folder if it does not exist
    """
    logging.info(f"Generating folder '{fpath_folder}'")
    if os.path.exists(fpath_folder):
        if os.path.isdir(fpath_folder):
            # There is already a folder here. Nothing to do.
            logging.info("Nothing to do. Folder already exists.")
            return True
        else:
            # A file is here
            logging.error(f"Cannot generate on top of non-folder '{fpath_folder}'")
            return False
    else:
        # No folder, make one
        os.mkdir(fpath_folder)
        logging.info("Successfully generated folder.")
        return True


def regenerateFolder(fpath_folder: str) -> bool:
    """
    Removes and remakes the specified folder (recursively).
    Returns if successful.
    """
    logging.info(f"Regenerating folder '{fpath_folder}'")
    if os.path.exists(fpath_folder):
        if not os.path.isdir(fpath_folder):
            # Trying to regenerate something other than a folder
            logging.error(f"Cannot regenerate non-folder '{fpath_folder}'")
            return False

        removeFile(fpath_folder)
    else:
        logging.info("Skipping folder deletion since it does not exist")

    # Make the folder
    os.mkdir(fpath_folder)
    logging.info("Successfully regenerated folder.")
    return True


# === Forge Ops ===
def runForgeInstaller(fpath_install_temp: str, forge_file: str, fpath_minecraft: str = "", headless: bool = False) -> None:
    """
    fpath_headless is the minecraft install path to use for a headless installation
    """
    fpath_forge_installer = os.path.join(fpath_install_temp, forge_file)
    command: list[str] = ["java", "-jar", fpath_forge_installer]
    if headless:
        if os.path.isdir(fpath_minecraft):
            logging.info("Running forge installer in headless mode...")
            command.extend(["--installClient", fpath_minecraft])
        else:
            logWarn("Forge headless path does not exist.")
    install_result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    if install_result.returncode != 0:
        logging.error("Forge installation failed. Stderr follows...")
        logging.error(install_result.stdout.decode())
        raise Exception(f"Forge install failed with exit code {install_result.returncode}")


def isForgeVersionInstalled(fpath_minecraft: str, minecraft_version: str, forge_version: str) -> str:
    """
    Returns the forge version name as it appears under versions if it is installed.
    Otherwise returns blank.
    """
    # Check v2 first
    forge_version_folder: str = makeForgeVersionFolderNameV2(minecraft_version, forge_version)
    fpath_forge_version_folder: str = os.path.join(fpath_minecraft, MINECRAFT_VERSIONS_FOLDER, forge_version_folder)
    logging.info(f"Checking for forge version at '{fpath_forge_version_folder}'")
    if not os.path.isdir(fpath_forge_version_folder):
        # Fallback to v1
        forge_version_folder: str = makeForgeVersionFolderNameV1(minecraft_version, forge_version)
        fpath_forge_version_folder: str = os.path.join(fpath_minecraft, MINECRAFT_VERSIONS_FOLDER, forge_version_folder)
        logging.info(f"[Fallback] Checking for forge version at '{fpath_forge_version_folder}'")
        if not os.path.isdir(fpath_forge_version_folder):
            # Could not find the forge installation...
            logging.info("Failed to find specified forge version")
            return ""

    return forge_version_folder


# === Path/Url Generators ===
def makeForgeInstallerDownloadLink(minecraft_version: str, forge_version: str) -> str:
    forge_file = makeForgeInstallerFileName(minecraft_version, forge_version)
    return f"https://files.minecraftforge.net/maven/net/minecraftforge/forge/{minecraft_version}-{forge_version}/{forge_file}"


def makeForgeInstallerFileName(minecraft_version: str, forge_version: str) -> str:
    return f"forge-{minecraft_version}-{forge_version}-installer.jar"


def makeModLocationDownloadLink(projectID: str, fileID: str) -> str:
    # Old API: https://addons-ecs.forgesvc.net/api/v2/addon/{projectID}/file/{fileID}/download-url
    return f"https://api.curseforge.com/v1/mods/{projectID}/files/{fileID}/download-url"


def makeForgeVersionFolderNameV1(minecraft_version: str, forge_version: str) -> str:
    return f"{minecraft_version}-forge{minecraft_version}-{forge_version}"


def makeForgeVersionFolderNameV2(minecraft_version: str, forge_version: str) -> str:
    return f"{minecraft_version}-forge-{forge_version}"


# === Misc ===
def appVersionStr() -> str:
    """
    What the script should call itself and its version
    """
    return f"{APP_NAME} {APP_VERSION} by {APP_AUTHOR}"


# ==================
# SCRIPT STARTS HERE
# ==================
if __name__ == '__main__':
    # Setup logging
    try:
        logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG, format="%(asctime)s %(levelname).3s: %(message)s", datefmt="%d/%m/%y %H:%M:%S", filemode="w")
        logging.info("Logging successfully setup connected.")
    except:
        print(f"Failed to setup logging. LOG_FILE={LOG_FILE} Crashing...", file=sys.stderr)
        sys.exit(1)

    logging.info("=== STARTING INSTALLER ===")

    # Process arguments
    try:
        arg_parser = argparse.ArgumentParser()
        # Required positional arguments.
        arg_parser.add_argument("fpath_modpack", metavar="modpack_file_path", type=str,
                                help="The modpack zip file to install.")
        # Possibly useful optional arguments.
        arg_parser.add_argument("-modpackname", "-mn",
                                help="Custom name for the modpack profile in the Minecraft launcher. By default this will be 'modpack - <modpackname>'")
        arg_parser.add_argument("-tempfolder", "-tf", default=DEFAULT_INSTALL_TEMP,
                                help=f"Change the temporary working/download folder. Anything in this folder could be overwritten or removed. By default it is '{DEFAULT_INSTALL_TEMP}'")
        arg_parser.add_argument("-downloadthreads", "-th", default=DEFAULT_DOWNLOAD_THREADS, type=int,
                                help=f"The number of threads to download mods with, for performance. Default is {DEFAULT_DOWNLOAD_THREADS}.")
        arg_parser.add_argument(PARAM_MINECRAFT_PATH, "-mp", default=MINECRAFT_FPATH_DEFAULT,
                                help=f"The location of your Minecraft install folder. Default is '{MINECRAFT_FPATH_DEFAULT}'")
        arg_parser.add_argument("-autoaccept", "-y", action="store_true",
                                help="Auto-accept all confirmation prompts. It is recommended to use this in combination with other flags for full automation, customisation, and possibly headless installation (or use this script in a pipeline mayhaps? I would be very interested to know if you do use this script in a pipeline).")
        arg_parser.add_argument("-forgeheadless", "-fh", action="store_true",
                                help="Run the forge installer in headless mode. This will make forge very sad :( but automation very happy :).")
        arg_parser.add_argument("-memorymax", "-mm", default=DEFAULT_MEMORY_MAX, type=float,
                                help="Sets the maximum memory for the modpack to this value in GB. Anything beyond 10GB Java does not know how to use effectively.")
        arg_parser.add_argument("-javaargs", "-ja", default=DEFAULT_JAVA_ARGS,
                                help="Sets the Java args to use with the modpack profile when launching. Only use if you know what you are doing. The inbuilt defaults in this installer should work well in most cases.")
        # Optional arguments which are only used if you know what you are doing.
        arg_parser.add_argument("-nounzip", "-nz", action="store_true",
                                help="Do not unzip the modpack file and use a previous cached copy.")
        arg_parser.add_argument("-nodownload", "-nd", action="store_true",
                                help="Do not download modpack files and use a previous cached copy.")
        arg_parser.add_argument("-noforge", "-nf", action="store_true",
                                help="Do not download forge and use a previous cached copy.")
        arg_parser.add_argument("-noprofile", "-np", action="store_true",
                                help="Do not modify minecraft profile. Usually you do not want this as this will prevent the modpack from appearing/updating in your Minecraft launcher.")
        # Inbuilt arguments.
        arg_parser.add_argument("-version", "-v", action="version", version=appVersionStr())

        # Actually do the parsing
        args: argparse.Namespace = arg_parser.parse_args()
        logging.info(f"Found args: {args}")
    except SystemExit:
        # Normal exit is an exception.
        sys.exit(0)
    except:
        print("Failed to parse args. Crashing...", file=sys.stderr)
        logging.exception("Failed to parse args. Crashing...")
        sys.exit(1)

    # Run the main loop
    r: int = 1
    try:
        logging.info("Running installer loop")
        r = main(vars(args))
        logging.info("=== ENDING INSTALLER ===")
    except:
        # Global exception handler so we have logs and a stack trace if anything goes wrong.
        print(f"FATAL CRASH. See {LOG_FILE} for details.")
        logging.exception("=== MAIN CRASH ===")
    sys.exit(r)
