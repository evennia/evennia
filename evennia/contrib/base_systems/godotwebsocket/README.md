# Godot Websocket

_Contrib by ChrisLR 2022_


# Overview

This contrib allows you to connect a Godot Client directly to your mud,

and display regular text with color in Godot's RichTextLabel using BBCode.

You can use Godot to provide advanced functionality with proper Evennia support.


# How to make a basic install

### Evennia side
You need to add the following settings in your settings.py and restart evennia.

```python
PORTAL_SERVICES_PLUGIN_MODULES.append('evennia.contrib.base_systems.godotwebsocket.webclient')
GODOT_CLIENT_WEBSOCKET_PORT = 4008
GODOT_CLIENT_WEBSOCKET_CLIENT_INTERFACE = "127.0.0.1"
```

This will make evennia listen on the port 4008 for Godot.


### Godot side

This section assumes you have knowledge for using Godot and
will not go into details.

You can follow the minimal client tutorial at
https://docs.godotengine.org/en/stable/tutorials/networking/websocket.html


Then you need to change the websocket_url for your mud, like
```
# The URL we will connect to
export var websocket_url = "ws://localhost:4008"
```

Also remove the protocol from

```
var err = _client.connect_to_url(websocket_url, ["lws-mirror-protocol"])
```

to

```
var err = _client.connect_to_url(websocket_url)
```

This will allow you to connect to your mud.

After that you need to properly handle the data sent by evennia.

To do this, you should replace your `_on_data` method.

You will need to parse the JSON received to properly act on the data.

Here is an example
```
var data = _client.get_peer(1).get_packet().get_string_from_utf8()
var json_data = JSON.parse(data).result
if json_data[0] == 'text':
    for msg in json_data[1]:
        label.append_bbcode(msg)
```

The first element is the type, it will be `text` if it is a message

It can be anything you would provide to the Evennia `msg` function, more on that later.

The second element will be the data related to the type of message, in this case it is a list of text to display.

Since it is parsed BBCode, we can add that directly to a RichTextLabel by calling its append_bbcode method.

# Advanced usage

If you want anything better than fancy text in Godot, you will have

to leverage Evennia's OOB to send extra data.

You can [read more on OOB here](https://www.evennia.com/docs/latest/OOB.html#oob).

Example

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
	elif json_data[0] == 'coordinates':
		var coords_data = json_data[2]
		player.set_pos(coords_data)
		
    ...
```

A good idea would be to set up Godot Signals you can trigger based on the data

you receive, so you can manage the code better.

# Known Issues

Sending SaverDicts and similar objects straight from Evennia .DB will cause issues,

cast them to dict() or list() before doing so.


Godot 3.x Richtext does not support background colors, it will be supported

in Godot 4.x but the Websockets implementation changes in that version.