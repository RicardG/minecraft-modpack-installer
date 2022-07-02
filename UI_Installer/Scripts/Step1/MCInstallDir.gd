extends ModulePane

onready var o_folder_dialog :FileDialog = $FolderDialog
onready var o_install_dir :LineEdit = $VBoxContainer/HBoxContainer/MCInstallDir
onready var o_install_result :RichTextLabel = $VBoxContainer/InstallResult


func _ready() -> void:
	var s := (OS.get_environment("appdata") + "/.minecraft").replace("\\", "/")
	#_check_install_dir(s)
	call_deferred("_check_install_dir", s)


func _check_install_dir(dir :String) -> void:
	o_install_dir.text = dir
	o_folder_dialog.current_dir = dir
	#do checks
	var d := Directory.new()
	if !d.dir_exists(dir):
		o_install_result.bbcode_text = "[color=red]Directory does not exist[/color]\nPlease select a valid directory."
		_invalid()
	elif !d.file_exists(o_install_dir.text + "/launcher_profiles.json"):
		o_install_result.bbcode_text = "[color=red]Cannot find launcher profile[/color]\nPlease check where Minecraft is installed and select a valid directory (it is also possible you have never run Minecraft before)."
		_invalid()
	else:
		o_install_result.bbcode_text = "[color=green]Valid Minecraft installation[/color]"
		Global.install_directory = dir
		_completed()


func _on_FolderDialog_dir_selected(dir: String) -> void:
	_check_install_dir(dir)


func _on_ButtonOpenFolder_pressed() -> void:
	o_folder_dialog.popup_centered()
