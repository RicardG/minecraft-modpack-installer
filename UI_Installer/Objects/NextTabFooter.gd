extends PanelContainer
class_name FooterPane

onready var o_label_description := $HBoxContainer/LabelDescription
onready var o_button_next := $HBoxContainer/ButtonNext

func _ready() -> void:
	enable_footer(false)


func enable_footer(b :bool) -> void:
	o_label_description.visible = b
	o_button_next.disabled = !b
