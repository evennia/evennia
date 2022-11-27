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


Then at the top of the file you must change the url to point at your mud.
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
		for msg in json_data[1]:
			label.append_bbcode(msg)
	
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
```gdscript
func _on_data():
    ...
	if json_data[0] == 'text':
		for msg in json_data[1]:
			label.append_bbcode(msg)
	
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