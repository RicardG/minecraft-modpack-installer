# Builds the python executable package
# It's like a build pipeline, but terrible.
$venv_folder = "build-env"
python -m venv $venv_folder
cd $venv_folder
.\Scripts\Activate.ps1
pip install pyinstaller
cp "..\InstallModPack.py" .
pyinstaller ".\InstallModPack.py" --onefile
cp ".\dist\InstallModPack.exe" ..
deactivate
cd ..
rm -r -force $venv_folder 