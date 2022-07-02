extends StepController

onready var o_button_next :Button = $ScrollContainer/VBoxContainer/NextTabFooter/HBoxContainer/ButtonNext
onready var o_step_tabs :TabContainer = $ScrollContainer/VBoxContainer/StepTabs
onready var o_footer :FooterPane = $ScrollContainer/VBoxContainer/NextTabFooter


func _on_ButtonNext_pressed() -> void:
	o_step_tabs.current_tab += 1
	completed_modules.clear()
	check_step_completed()


func _on_InstallerWindow_completed(_o :Control) -> void:
	o_footer.enable_footer(true)


func _on_InstallerWindow_invalid(_o :Control) -> void:
	o_footer.enable_footer(false)
