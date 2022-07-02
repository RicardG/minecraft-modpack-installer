extends ModulePane


func _on_RichTextLabel_meta_clicked(meta :String) -> void:
	if OS.shell_open(meta) != OK:
		push_error("Issue opening curseforge link")


func _on_ModpackSelected_toggled(state: bool) -> void:
	if state:
		_completed()
	else:
		_invalid()
