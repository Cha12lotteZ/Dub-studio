# Godot 4: add this script to a Node, then call speak("ข้อความ", {"character": "giant"}).
# Requires Dub Studio running (start.bat / start.sh) on the same computer.
extends Node

const BASE := "http://127.0.0.1:8000"
signal line_ready(stream: AudioStreamWAV)

func speak(text: String, opts: Dictionary = {}) -> void:
	var body := {"text": text, "character": "me", "mood": "normal", "atmosphere": "none"}
	body.merge(opts, true)
	var http := HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_done.bind(http))
	http.request(BASE + "/api/v1/speak", ["Content-Type: application/json"],
		HTTPClient.METHOD_POST, JSON.stringify(body))

func _on_done(result: int, code: int, _headers, data: PackedByteArray, http: HTTPRequest) -> void:
	http.queue_free()
	if result != HTTPRequest.RESULT_SUCCESS or code != 200:
		push_error("Dub Studio: %s" % data.get_string_from_utf8())
		return
	# The API returns 16-bit PCM WAV; skip the 44-byte header.
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_16_BITS
	wav.mix_rate = data.decode_u32(24)
	wav.stereo = data.decode_u16(22) == 2
	wav.data = data.slice(44)
	line_ready.emit(wav)
