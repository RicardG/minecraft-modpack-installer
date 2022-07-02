extends ModulePane

onready var o_java_result :RichTextLabel = $VBoxContainer/JavaResult


func _ready() -> void:
	#_check_java()
	call_deferred("_check_java")

func _check_java() -> void:
	var output := []
	var exit_code := OS.execute("java", ["-version"], true, output, true)
	if exit_code == 0:
		o_java_result.bbcode_text = "[code]%s[/code][color=green]Java is installed![/color]\n" % output[0]
		_completed()
	else:
		o_java_result.bbcode_text = "[color=red]You do not have Java[/color]\nJava is required both to run Minecraft and the Forge/Fabric installers. Go install it @ [url]https://www.java.com/en/download/[/url]\n"
		_invalid()


func _on_ButtonCheckJava_pressed() -> void:
	_check_java()


func _on_JavaResult_meta_clicked(meta :String) -> void:
	if OS.shell_open(meta) != OK:
		push_error("Issue opening Java link")
