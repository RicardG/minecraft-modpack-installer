extends Control
class_name ModulePane

signal completed #when this module is completed
signal invalid #when this module is invalid


func _completed() -> void:
	emit_signal("completed", self)


func _invalid() -> void:
	emit_signal("invalid", self)
