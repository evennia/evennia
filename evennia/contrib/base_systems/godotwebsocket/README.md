# Godot Websocket

Contribution by ChrisLR, 2022

This contrib allows you to connect a Godot Client directly to your mud,
and display regular text with color in Godot's RichTextLabel using BBCode.
You can use Godot to provide advanced functionality with proper Evennia support.


## Installation

You need to add the following settings in your `settings.py` and restart evennia.

```python
PORTAL_SERVICES_PLUGIN_MODULES.append('evennia.contrib.base_systems.godotwebsocket.webclient')
GODOT_CLIENT_WEBSOCKET_PORT = 4008
GODOT_CLIENT_WEBSOCKET_CLIENT_INTERFACE = "127.0.0.1"
```

This will make evennia listen on the port 4008 for Godot.
You can change the port and interface as you want.


## Usage

The tl;dr of it is to connect using a Godot Websocket using the port defined above.
It will let you transfer data from Evennia to Godot, allowing you
to get styled text in a RichTextLabel with bbcode enabled or to handle
the extra data given from Evennia as needed.


This section assumes you have basic knowledge on how to use Godot.
You can read the following url for more details on Godot Websockets
and to implement a minimal client or look at the full example at the bottom of this page.

https://docs.godotengine.org/en/stable/tutorials/networking/websocket.html

The rest of this document will be for Godot 4.
Note that some of the code shown here is partially taken from official Godot Documentation

A very basic setup in godot would require

- One RichTextLabel Node to display the Evennia Output, ensure bbcode is enabled on it.
- One Node for your websocket client code with a new Script attached.
- One TextEdit Node to enter commands
- One Button Node to press and send the commands
- Controls for the layout, in this example I have used
  Panel
   VBoxContainer
     RichTextLabel
     HBoxContainer
       TextEdit
       Button

I will not go over how layout works but the documentation for them is easily accessible in the godot docs.


Open up the script for your client code.

We need to define the url leading to your mud, use the same values you have used in your Evennia Settings.
Next we write some basic code to get a connection going.
This will connect when the Scene is ready, poll and print the data when we receive it and close when the scene exits.
```
extends Node

# The URL we will connect to.
var websocket_url = "ws://127.0.0.1:4008"
var socket := WebSocketPeer.new()

func _ready():
	if socket.connect_to_url(websocket_url) != OK:
		print("Unable to connect.")
		set_process(false)


func _process(_delta):
	socket.poll()
	match socket.get_ready_state():
		WebSocketPeer.STATE_OPEN:
			while socket.get_available_packet_count():
				print(socket.get_packet().get_string_from_ascii())
		
		WebSocketPeer.STATE_CLOSED:
			var code = socket.get_close_code()
			var reason = socket.get_close_reason()
			print("WebSocket closed with code: %d, reason %s. Clean: %s" % [code, reason, code != -1])
			set_process(false)

func _exit_tree():
	socket.close()

```

At this point, you can start your evennia server, run godot and it should print a default reply.
After that you need to properly handle the data sent by evennia.
To do this, we will add a new function to dispatch the messages properly.

Here is an example
```
func _handle_data(data):
	print(data)  # Print for debugging
	var data_array = JSON.parse_string(data)
	# The first element can be used to see if its text
	if data_array[0] == 'text':
		# The second element contains the messages
		for msg in data_array[1]:
			write_to_rtb(msg)

func write_to_rtb(msg):
	output_label.append_text(msg)
```

The first element is the type, it will be `text` if it is a message
It can be anything you would provide to the Evennia `msg` function.
The second element will be the data related to the type of message, in this case it is a list of text to display.
Since it is parsed BBCode, we can add that directly to a RichTextLabel by calling its append_text method.

If you want anything better than fancy text in Godot, you will have
to leverage Evennia's OOB to send extra data.

You can [read more on OOB here](https://www.evennia.com/docs/latest/OOB.html#oob).


Now to send data, we connect the Button pressed Signal to a method,
read the label input and send it via the websocket, then clear the label.
```
func _on_button_pressed():
	var msg = text_edit.text
	var msg_arr = ['text', [msg], {}]
	var msg_str = JSON.stringify(msg_arr)
	socket.send_text(msg_str)
	text_edit.text = ""
```



## Known Issues

- Sending SaverDicts and similar objects straight from Evennia .DB will cause issues,
  cast them to dict() or list() before doing so.


## Full Example Script
```
extends Node

# The URL we will connect to.
var websocket_url = "ws://127.0.0.1:4008"
var socket := WebSocketPeer.new()

@onready var output_label = $"../Panel/VBoxContainer/RichTextLabel"
@onready var text_edit = $"../Panel/VBoxContainer/HBoxContainer/TextEdit"


func _ready():
	if socket.connect_to_url(websocket_url) != OK:
		print("Unable to connect.")
		set_process(false)

func _process(_delta):
	socket.poll()
	match socket.get_ready_state():
		WebSocketPeer.STATE_OPEN:
			while socket.get_available_packet_count():
				var data = socket.get_packet().get_string_from_ascii()
				_handle_data(data)
		
		WebSocketPeer.STATE_CLOSED:
			var code = socket.get_close_code()
			var reason = socket.get_close_reason()
			print("WebSocket closed with code: %d, reason %s. Clean: %s" % [code, reason, code != -1])
			set_process(false)

func _handle_data(data):
	print(data)  # Print for debugging
	var data_array = JSON.parse_string(data)
	# The first element can be used to see if its text
	if data_array[0] == 'text':
		# The second element contains the messages
		for msg in data_array[1]:
			write_to_rtb(msg)

func write_to_rtb(msg):
	output_label.append_text(msg)

func _on_button_pressed():
	var msg = text_edit.text
	var msg_arr = ['text', [msg], {}]
	var msg_str = JSON.stringify(msg_arr)
	socket.send_text(msg_str)
	text_edit.text = ""

func _exit_tree():
	socket.close()

```
