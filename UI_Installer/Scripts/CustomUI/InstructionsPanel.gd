tool
extends PanelContainer

export(String) var header := "Header Here"
export(String, MULTILINE) var bbcode := "Instructions Here"
onready var o_header :Label = $VBoxContainer/HeaderLabel
onready var o_description :RichTextLabel = $VBoxContainer/Description

func _ready() -> void:
	o_header.text = header
	o_description.bbcode_text = bbcode
