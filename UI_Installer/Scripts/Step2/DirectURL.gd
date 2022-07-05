extends ModulePane

onready var o_url_result :RichTextLabel = $VBoxContainer/URLResult
onready var o_pack_url :LineEdit = $VBoxContainer/HBoxContainer/PackURL
onready var o_button_check_url :Button = $VBoxContainer/HBoxContainer/ButtonCheckURL
onready var o_http_request :HTTPRequest = $HTTPRequest

var modpack_url :String = ""
var modpack_url_name :String = ""


func _check_url(url :String) -> void:
	url = url.to_lower()
	var regex = RegEx.new()
	#https://www.curseforge.com/minecraft/modpacks/<packname>
	regex.compile("^https://www\\.curseforge\\.com/minecraft/modpacks/([^/]+)$")
	var result :RegExMatch = regex.search(url)
	
	if !result:
		#looks nothing like the URL structure
		o_url_result.bbcode_text = "[color=red]Invalid Modpack URL[/color]\nThe URL does not follow the basic CurseForge URL structure. It must be of the form https://www.curseforge.com/minecraft/modpacks/<packname>"
		emit_signal("invalid", self)
	else:
		#ask curseforge for this url to check if it exists
		o_button_check_url.disabled = true
		o_pack_url.editable = false
		print(url)
		#https://www.curseforge.com/minecraft/modpacks/rlcraft
		var error :int = o_http_request.request("https://www.curseforge.com/minecraft/modpacks/rlcraft", CONST.HEADERS)
		if error != OK:
			push_error("Error creating HTTP request (might already be busy).")
			end_request()
		else:
			o_url_result.bbcode_text = "[color=yellow]Checking URL with CurseForge[/color]"
			modpack_url = result.strings[0]
			modpack_url_name = result.strings[1]
			emit_signal("invalid", self)


func end_request() -> void:
	o_button_check_url.disabled = false
	o_pack_url.editable = true


func _on_PackURL_text_entered(new_text: String) -> void:
	_check_url(new_text)


func _on_ButtonCheckURL_pressed() -> void:
	_check_url(o_pack_url.text)


func _on_HTTPRequest_request_completed(result: int, response_code: int, headers: PoolStringArray, body: PoolByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS:
		push_error("Http request failed %s" % result)
	else:
		print(body.get_string_from_ascii())
	if response_code != 200:
		#the page does not exist
		o_url_result.bbcode_text = "[color=red]Invalid Modpack URL[/color]\nThe URL does not exist on CurseForge, please check it and try again."
		print(response_code)
		emit_signal("invalid", self)
	else:
		#the url seems valid
		Global.modpack_url = modpack_url
		Global.modpack_url_name = modpack_url_name
		o_url_result.bbcode_text = "[color=green]Valid Modpack URL[/color]\nModpack: %s" % Global.modpack_url_name
		emit_signal("completed", self)
	end_request()
