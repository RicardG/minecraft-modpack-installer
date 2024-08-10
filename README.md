# Minecraft Curseforge Modpack Installer
Do you want to play a CurseForge modpack but do not want to be forced to sign up for a new account in order to download and install it? What if the whole installation process could be performed by a single Python script? What if the process could be completely automated? Then look no further, the solution is right here! Initially intended as a challenge project (and as a "I do not want to sign up for a new account for something which is freely available"), this script will take a modpack zip file, unpack it, read its manifest, download all the required mods and forge, install them, and create a new game profile in your Minecraft launcher. This script was developed with Windows OSes in mind but is likely to work 'as is' with other OSes which can run Python.

## How To Use
1. Go to CurseForge and find a Minecraft modpack you like the look of.
2. Download the modpack. This will give a zip file containing a manifest file along with any mod overrides.
3. Place the downloaded zip file in the same folder as this script `InstallModPack.py` (you have downloaded the script by now, right?).
4. Open your preferred console to the location of the script. (if you do not know what this means, open command prompt, copy the location of the folder the script is in and write in command prompt `cd <paste_location_here>`, replacing `<paste_location_here>` with the location).
5. Run the install script. Go to **5.1** if you have Python installed and want to run it directly from the source file or **5.2** if you want it to 'just work' without doing anything. In either case this utility only runs from a command line, if you double-click on it nothing will happen. Full help for the command structure and flags supported can be found by using the flag `-h` or at the bottom of this document
    1. The good news is all the required imports should be part of a standard installation of Python. If there are any missing then pip is your friend. Note: this script was developed and tested with Python 3.12 in mind, so no guarantees for anything before that. Run the script as you would a normal Python file `python InstallModPack.py <modpack.zip>` replacing `<modpack.zip>` with the name of the modpack zip file you just downloaded.
    2. (Windows Only) Run the executable package using `InstallModPack.exe <modpack.zip>` replacing `<modpack.zip>` with the name of the modpack zip file you just downloaded.
6. Follow the prompts in the console until the install completes.
7. Open your Minecraft launcher, a new profile called something like "modpack - mod_name_here" should be available to play.
8. Aaaaand you are done!

## Full Command Syntax
### Full Syntax
`InstallModPack.exe [-h] [-modpackname MODPACKNAME] [-tempfolder TEMPFOLDER] [-downloadthreads DOWNLOADTHREADS] [-minecraftpath MINECRAFTPATH] [-autoaccept] [-forgeheadless] [-memorymax MEMORYMAX] [-javaargs JAVAARGS] [-nounzip] [-nodownload] [-noforge] [-noprofile] [-version] modpack_file_path`

### Positional Arguments
`modpack_file_path`: The modpack zip file to install.

### Options/Flags
`-h`, `--help`: show this help message and exit

`-modpackname MODPACKNAME`, `-mn MODPACKNAME`: Custom name for the modpack profile in the Minecraft launcher. By default this will be 'modpack - <modpackname>'

`-tempfolder TEMPFOLDER`, `-tf TEMPFOLDER`: Change the temporary working/download folder. Anything in this folder could be overwritten or removed. By default it is 'modpack_install_temp'

`-downloadthreads DOWNLOADTHREADS`, `-th DOWNLOADTHREADS`: The number of threads to download mods with, for performance. Default is 4.

`-minecraftpath MINECRAFTPATH`, `-mp MINECRAFTPATH`: The location of your Minecraft install folder. Default is 'C:\Users\User\AppData\Roaming\.minecraft'

`-autoaccept`, `-y`: Auto-accept all confirmation prompts. It is recommended to use this in combination with other flags for full automation, customisation, and possibly headless installation (or use this script in a pipeline mayhaps? I would be very interested to know if you do use this script in a pipeline).

`-forgeheadless`, `-fh`: Run the forge installer in headless mode. This will make forge very sad :( but automation very happy :).

`-memorymax MEMORYMAX`, `-mm MEMORYMAX`: Sets the maximum memory for the modpack to this value in GB. Anything beyond 10GB Java does not know how to use effectively.

`-javaargs JAVAARGS`, `-ja JAVAARGS`: Sets the Java args to use with the modpack profile when launching. Only use if you know what you are doing. The inbuilt defaults in this installer should work well in most cases.

`-nounzip`, `-nz`: Do not unzip the modpack file and use a previous cached copy.

`-nodownload`, `-nd`: Do not download modpack files and use a previous cached copy.

`-noforge`, `-nf`: Do not download forge and use a previous cached copy.

`-noprofile`, `-np`: Do not modify minecraft profile. Usually you do not want this as this will prevent the modpack from appearing/updating in your Minecraft launcher.

`-version`, `-v`: show program's version number and exit