extends Node


func _ready():
	return
	# Create an HTTP request node and connect its completion signal.
	var http_request := HTTPRequest.new()
	add_child(http_request)
	http_request.connect("request_completed", self, "_http_request_completed")

	# Perform a GET request.
	#im not a bot lol
	var ua := "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:101.0) Gecko/20100101 Firefox/101.0"
	var error :int = http_request.request("http://192.168.0.21", [ua])#"https://www.google.com.au")
	if error != OK:
		push_error("An error occurred in the HTTP request.")


# Called when the HTTP request is completed.
func _http_request_completed(result :int, response_code :int, headers :PoolStringArray, body :PoolByteArray):
	var response = body.get_string_from_ascii() #cannot directly do utf8 unencoding due to scripts

	# Will print the user agent string used by the HTTPRequest node (as recognized by httpbin.org).
	#print(response)
	print(response)
	print(headers)
