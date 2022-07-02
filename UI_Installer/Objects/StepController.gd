extends ModulePane
class_name StepController

export(int) var num_submodules := 1 #how many submodules need to be completed
export(NodePath) var module_parent_path
var completed_modules := {}


func _ready() -> void:
	var o_module_parent :Control = get_node(module_parent_path)
	for child in o_module_parent.get_children():
		child.connect("completed", self, "_submodule_completed")
		child.connect("invalid", self, "_submodule_invalid")
	call_deferred("check_step_completed")


func check_step_completed() -> void:
	if completed_modules.size() >= num_submodules:
		emit_signal("completed", self)
		print("step completed")
	else:
		emit_signal("invalid", self)
		print("step invalid")


func _submodule_completed(o :ModulePane) -> void:
	completed_modules[o] = true
	check_step_completed()


func _submodule_invalid(o :ModulePane) -> void:
	completed_modules.erase(o)
	check_step_completed()
