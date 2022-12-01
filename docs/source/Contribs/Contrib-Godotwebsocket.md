# Godot Websocket

Contribution by ChrisLR, 2022

This contrib allows you to connect a Godot Client directly to your mud,
and display regular text with color in Godot's RichTextLabel using BBCode.
You can use Godot to provide advanced functionality with proper Evennia support.


## Installation

You need to add the following settings in your settings.py and restart evennia.

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
and to implement a minimal client.

https://docs.godotengine.org/en/stable/tutorials/networking/websocket.html

The rest of this document will be for Godot 3, an example is left at the bottom
of this readme for Godot 4.


At the top of the file you must change the url to point at your mud.
```
extends Node

# The URL we will connect to
export var websocket_url = "ws://localhost:4008"

```


You must also remove the protocol from the `connect_to_url` call made
within the `_ready` function.

```
func _ready(): 
    # ...
    # Change the following line from this
    var err = _client.connect_to_url(websocket_url, ["lws-mirror-protocol"])
    # To this
    var err = _client.connect_to_url(websocket_url)
    # ...
```

This will allow you to connect to your mud.
After that you need to properly handle the data sent by evennia.
To do this, you should replace your `_on_data` method.
You will need to parse the JSON received to properly act on the data.
Here is an example
```
func _on_data():
    # The following two lines will get us the data from Evennia.
	var data = _client.get_peer(1).get_packet().get_string_from_utf8()
	var json_data = JSON.parse(data).result
	# The json_data is an array
	
	# The first element informs us this is simple text
	# so we add it to the RichTextlabel
	if json_data[0] == 'text':
		for msg in json_data[1]: 			label.append_bbcode(msg)
	
	# Always useful to print the data and see what we got.
	print(data)
```

The first element is the type, it will be `text` if it is a message
It can be anything you would provide to the Evennia `msg` function.
The second element will be the data related to the type of message, in this case it is a list of text to display.
Since it is parsed BBCode, we can add that directly to a RichTextLabel by calling its append_bbcode method.

If you want anything better than fancy text in Godot, you will have
to leverage Evennia's OOB to send extra data.

You can [read more on OOB here](https://www.evennia.com/docs/latest/OOB.html#oob).

In this example, we send coordinates whenever we message our character.

Evennia
```python
caller.msg(coordinates=(9, 2))
```

Godot
```
func _on_data():
    ...
	if json_data[0] == 'text':
		for msg in json_data[1]: 			label.append_bbcode(msg)
	
	# Notice the first element is the name of the kwarg we used from evennia.
	elif json_data[0] == 'coordinates':
		var coords_data = json_data[2]
		player.set_pos(coords_data)
		
    ...
```

A good idea would be to set up Godot Signals you can trigger based on the data
you receive, so you can manage the code better.

## Known Issues

- Sending SaverDicts and similar objects straight from Evennia .DB will cause issues,
  cast them to dict() or list() before doing so.

- Background colors are only supported by Godot 4.

## Godot 3 Example

This is an example of a Script to use in Godot 3.
The script can be attached to the root UI node.

```
extends Node

# The URL to connect to, should be your mud.
export var websocket_url = "ws://127.0.0.1:4008"

# These are references to controls in the scene
onready var parent = get_parent()
onready var label = parent.get_node("%ChatLog")
onready var txtEdit = parent.get_node("%ChatInput")

onready var room = get_node("/root/World/Room")

# Our WebSocketClient instance
var _client = WebSocketClient.new()

var is_connected = false

func _ready():
	# Connect base signals to get notified of connection open, close, errors and messages
	_client.connect("connection_closed", self, "_closed")
	_client.connect("connection_error", self, "_closed")
	_client.connect("connection_established", self, "_connected")
	_client.connect("data_received", self, "_on_data")
	print('Ready')

	# Initiate connection to the given URL.
	var err = _client.connect_to_url(websocket_url)
	if err != OK:
		print("Unable to connect")
		set_process(false)

func _closed(was_clean = false):
	# was_clean will tell you if the disconnection was correctly notified
	# by the remote peer before closing the socket.
	print("Closed, clean: ", was_clean)
	set_process(false)

func _connected(proto = ""):
	is_connected = true
	print("Connected with protocol: ", proto)

func _on_data():
	# This is called when Godot receives data from evennia
	var data = _client.get_peer(1).get_packet().get_string_from_utf8()
	var json_data = JSON.parse(data).result
	# Here we have the data from Evennia which is an array.
	# The first element will be text if it is a message
	# and would be the key of the OOB data you passed otherwise.
	if json_data[0] == 'text':
		# In this case, we simply append the data as bbcode to our label.
		for msg in json_data[1]: 			label.append_bbcode(msg)
	elif json_data[0] == 'coordinates':
		# Dummy signal emitted if we wanted to handle the new coordinates
		# elsewhere in the project.
		self.emit_signal('updated_coordinates', json_data[1])

	
	# We only print this for easier debugging.
	print(data)

func _process(delta):
	# Required for websocket to properly react
	_client.poll()

func _on_button_send():
	# This is called when we press the button in the scene
	# with a connected signal, it sends the written message to Evennia.
	var msg = txtEdit.text
	var msg_arr = ['text', [msg], {}]
	var msg_str = JSON.print(msg_arr)
	_client.get_peer(1).put_packet(msg_str.to_utf8())

func _notification(what):
	# This is a special method that allows us to notify Evennia we are closing.
	if what == MainLoop.NOTIFICATION_WM_QUIT_REQUEST:
		if is_connected:
			var msg_arr = ['text', ['quit'], {}]
			var msg_str = JSON.print(msg_arr)
			_client.get_peer(1).put_packet(msg_str.to_utf8())
		get_tree().quit() # default behavior

```

## Godot 4 Example

This is an example of a Script to use in Godot 4.
Note that the version is not final so the code may break.
It requires a WebSocketClientNode as a child of the root node.
The script can be attached to the root UI node.

```
extends Control

# The URL to connect to, should be your mud.
var websocket_url = "ws://127.0.0.1:4008"

# These are references to controls in the scene
@onready
var label: RichTextLabel = get_node("%ChatLog")
@onready
var txtEdit: TextEdit = get_node("%ChatInput")
@onready
var websocket = get_node("WebSocketClient")

func _ready():
	# We connect the various signals
	websocket.connect('connected_to_server', self._connected)
	websocket.connect('connection_closed', self._closed)
	websocket.connect('message_received', self._on_data)
	
	# We attempt to connect and print out the error if we have one.
	var result = websocket.connect_to_url(websocket_url)
	if result != OK:
		print('Could not connect:' + str(result))


func _closed():
	# This emits if the connection was closed by the remote host or unexpectedly
	print('Connection closed.')
	set_process(false)

func _connected():
	# This emits when the connection succeeds.
	print('Connected!')

func _on_data(data):
	# This is called when Godot receives data from evennia
	var json_data = JSON.parse_string(data)
	# Here we have the data from Evennia which is an array.
	# The first element will be text if it is a message
	# and would be the key of the OOB data you passed otherwise.
	if json_data[0] == 'text':
		# In this case, we simply append the data as bbcode to our label.
		for msg in json_data[1]: 			# Here we include a newline at every message.
			label.append_text("\n" + msg)
	elif json_data[0] == 'coordinates':
		# Dummy signal emitted if we wanted to handle the new coordinates
		# elsewhere in the project.
		self.emit_signal('updated_coordinates', json_data[1])

	# We only print this for easier debugging.
	print(data)

func _on_button_pressed():
	# This is called when we press the button in the scene
	# with a connected signal, it sends the written message to Evennia.
	var msg = txtEdit.text
	var msg_arr = ['text', [msg], {}]
	var msg_str = JSON.stringify(msg_arr)
	websocket.send(msg_str)

```

----

<small>This document page is generated from `evennia/contrib/base_systems/godotwebsocket/README.md`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
