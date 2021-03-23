# Minecraft Curseforge Modpack Installer
Do you want to play a curseforge modpack but do not want to be forced to sign up for a new account in order to download and install it? What if the whole installation process could be performed by a single Python script? Then look no further, the solution is right here! Initially intended as a challenge project (and as a "I do not want to sign up for a new account for something which is freely available"), this script will take a modpack zip file, unpack it, read its manifest, download all the required mods and forge, install them, and create a new game profile in your Minecraft launcher. NOTE: This script assumes you have a Windows machine and your Minecraft installation is in the usual place of: `%appdata%/.minecraft`. If not, you will need to exercise some coding skills and change the location of installation.

## How to use
1. Go to curse forge and find a Minecraft modpack you like the look of.
2. Click the files tab (near the top left of the page).
3. Click on the NAME of the version of the modpack you want to install. If you just want the latest one, then it will be the top one. Otherwise, find your prefered version and click it.
4. To the right of the file's name there should be a download button, click that and download the zip file.
5. Place the downloaded zip file in the same folder as the python script `InstallModPack.py` (you have downloaded the script by now, right?).
6. Open your preferred console to the location of the script. (if you do not know what this means, open command prompt, copy the location of the folder the script is in and write in command prompt `cd <paste location here>`).
7. Now you can run the install script. Take note of the name of the zip file you downloaded and run the following command in your console. If you don't have python installed already, you will need to go and install that first.\
`python InstallModPack.py <zip file name here>`
8. Follow the prompts in the console until the install completes.
9. Open your Minecraft launcher, a new profile called something like "modpack - modnamehere" should be available to play.
10. Aaaaand you are done!

If you wish to skip certain parts of the installation process (eg. you want to reinstall a modpack that was recently downloaded but you messed with the files and it does not work anymore), you can add any of the following flags after the run command\
`-nozip` Skips unzipping the specified modpack file and refreshing the temp folder (use when you already unzipped the mod before and want to perform a reinstall without having to redownload the mods).\
`-nodown` Skips downloading the required mods. This is usually used in combination with the above for a quick reinstall.\
`-noforge` Skips downloading and installation of forge. This can be used when you have already installed the required version of forge.\
`-noprofile` Skips setting up of a new Minecraft game profile for the modpack. Generally, you will not use this unless you know what you are doing.