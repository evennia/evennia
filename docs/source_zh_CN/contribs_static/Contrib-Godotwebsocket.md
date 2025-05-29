# Godot Websocket

由 ChrisLR 贡献于 2022 年

此模块允许您将 Godot 客户端直接连接到您的 MUD，并在 Godot 的 RichTextLabel 中使用 BBCode 显示带颜色的常规文本。您可以使用 Godot 提供具有适当 Evennia 支持的高级功能。

## 安装

您需要在 `settings.py` 中添加以下设置并重启 Evennia。

```python
PORTAL_SERVICES_PLUGIN_MODULES.append('evennia.contrib.base_systems.godotwebsocket.webclient')
GODOT_CLIENT_WEBSOCKET_PORT = 4008
GODOT_CLIENT_WEBSOCKET_CLIENT_INTERFACE = "127.0.0.1"
```

这将使 Evennia 在端口 4008 上监听 Godot。您可以根据需要更改端口和接口。

## 用法

简而言之，就是使用 Godot Websocket 连接到上面定义的端口。这将允许您从 Evennia 向 Godot 传输数据，使您能够在启用 BBCode 的 RichTextLabel 中获取样式化文本，或根据需要处理来自 Evennia 的额外数据。

本节假设您具备基本的 Godot 使用知识。您可以阅读以下网址以获取有关 Godot Websockets 的更多详细信息，并实现一个最小客户端，或查看此页面底部的完整示例。

https://docs.godotengine.org/en/stable/tutorials/networking/websocket.html

本文档的其余部分将针对 Godot 4。请注意，这里显示的一些代码部分取自官方 Godot 文档。

在 Godot 中进行非常基本的设置需要：

- 一个 RichTextLabel 节点来显示 Evennia 输出，确保启用了 BBCode。
- 一个节点用于您的 websocket 客户端代码，并附加一个新脚本。
- 一个 TextEdit 节点用于输入命令。
- 一个按钮节点用于按下并发送命令。
- 布局控件，在本例中我使用了：
  - Panel
  - VBoxContainer
    - RichTextLabel
    - HBoxContainer
      - TextEdit
      - Button

我不会详细介绍布局的工作原理，但 Godot 文档中可以轻松获取相关文档。

打开您的客户端代码脚本。

我们需要定义通向您的 MUD 的 URL，使用您在 Evennia 设置中使用的相同值。接下来，我们编写一些基本代码以建立连接。这将在场景准备好时连接，在接收到数据时轮询并打印数据，并在场景退出时关闭连接。

```
extends Node

# 我们将连接的 URL。
var websocket_url = "ws://127.0.0.1:4008"
var socket := WebSocketPeer.new()

func _ready():
	if socket.connect_to_url(websocket_url) != OK:
		print("无法连接。")
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
			print("WebSocket 已关闭，代码: %d, 原因 %s. 清理: %s" % [code, reason, code != -1])
			set_process(false)

func _exit_tree():
	socket.close()
```

此时，您可以启动您的 Evennia 服务器，运行 Godot，它应该会打印一个默认回复。之后，您需要正确处理 Evennia 发送的数据。为此，我们将添加一个新函数以正确分派消息。

下面是一个示例：

```
func _handle_data(data):
	print(data)  # 用于调试的打印
	var data_array = JSON.parse_string(data)
	# 第一个元素可以用来查看是否是文本
	if data_array[0] == 'text':
		# 第二个元素包含消息
		for msg in data_array[1]:
			write_to_rtb(msg)

func write_to_rtb(msg):
	output_label.append_text(msg)
```

第一个元素是类型，如果是消息则为 `text`。它可以是您提供给 Evennia `msg` 函数的任何内容。第二个元素将是与消息类型相关的数据，在这种情况下，它是要显示的文本列表。由于它是解析过的 BBCode，我们可以通过调用 RichTextLabel 的 append_text 方法直接添加到它。

如果您希望在 Godot 中实现比花哨文本更好的功能，您将需要利用 Evennia 的 OOB 发送额外数据。

您可以在[这里](https://www.evennia.com/docs/latest/OOB.html#oob)阅读有关 OOB 的更多信息。

现在要发送数据，我们连接按钮按下信号到一个方法，读取标签输入并通过 websocket 发送，然后清除标签。

```
func _on_button_pressed():
	var msg = text_edit.text
	var msg_arr = ['text', [msg], {}]
	var msg_str = JSON.stringify(msg_arr)
	socket.send_text(msg_str)
	text_edit.text = ""
```

## 已知问题

- 直接从 Evennia .DB 发送 SaverDicts 和类似对象会导致问题，请在这样做之前将它们转换为 dict() 或 list()。

## 完整示例脚本

```
extends Node

# 我们将连接的 URL。
var websocket_url = "ws://127.0.0.1:4008"
var socket := WebSocketPeer.new()

@onready var output_label = $"../Panel/VBoxContainer/RichTextLabel"
@onready var text_edit = $"../Panel/VBoxContainer/HBoxContainer/TextEdit"

func _ready():
	if socket.connect_to_url(websocket_url) != OK:
		print("无法连接。")
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
			print("WebSocket 已关闭，代码: %d, 原因 %s. 清理: %s" % [code, reason, code != -1])
			set_process(false)

func _handle_data(data):
	print(data)  # 用于调试的打印
	var data_array = JSON.parse_string(data)
	# 第一个元素可以用来查看是否是文本
	if data_array[0] == 'text':
		# 第二个元素包含消息
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
