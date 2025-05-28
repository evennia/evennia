# 协议

```
            Internet│ Protocol
            ┌─────┐ │ | 
┌──────┐    │Text │ │  ┌──────────┐    ┌────────────┐   ┌─────┐
│Client◄────┤JSON ├─┼──┤outputfunc◄────┤commandtuple◄───┤msg()│
└──────┘    │etc  │ │  └──────────┘    └────────────┘   └─────┘
            └─────┘ │
                    │Evennia
```

_协议_ 描述了 Evennia 如何通过网络向客户端发送和接收数据。每种连接类型（如 telnet、ssh、webclient 等）都有其自己的协议。一些协议也可能有变体（如纯文本 Telnet 与 Telnet SSL）。

请参阅 [Message Path](./Messagepath.md) 以了解数据如何在 Evennia 中流动的全貌。

在 Evennia 中，`PortalSession` 代表客户端连接。会话被告知使用特定的协议。发送数据时，会话必须提供一个“Outputfunc”来将通用的 `commandtuple` 转换为协议能够理解的形式。对于传入的数据，服务器还必须提供合适的 [Inputfuncs](../Components/Inputfuncs.md) 来处理发送到服务器的指令。

## 添加新协议

Evennia 有一个插件系统，可以将协议作为新的“服务”添加到应用程序中。

要向 Portal 或 Server 添加你自己的新服务（例如你自己的自定义客户端协议），请扩展 `mygame/server/conf/server_services_plugins` 和 `portal_services_plugins`。

要扩展 Evennia 查找插件的位置，请使用以下设置：
```python
# 添加到服务器
SERVER_SERVICES_PLUGIN_MODULES.append('server.conf.my_server_plugins')
# 或者，如果你想添加到 Portal
PORTAL_SERVICES_PLUGIN_MODULES.append('server.conf.my_portal_plugins')
```

> 添加新的客户端连接时，你很可能只需要向 Portal 插件文件中添加新内容。

插件模块必须包含一个函数 `start_plugin_services(app)`，其中 `app` 参数指的是 Portal/Server 应用程序本身。这在服务器或 Portal 启动时被调用。它必须包含所有需要的启动代码。

示例：

```python
# mygame/server/conf/portal_services_plugins.py

# 这里定义了新的 Portal Twisted 协议
class MyOwnFactory( ... ):
   # [...]

# 一些配置
MYPROC_ENABLED = True # 方便的关闭标志，避免每次都编辑设置
MY_PORT = 6666

def start_plugin_services(portal):
    "这是在启动期间由 Portal 调用的"
    if not MYPROC_ENABLED:
        return
    # 输出以在启动时列出其他服务
    print(f"  myproc: {MY_PORT}")

    # 一些设置（简单示例）
    factory = MyOwnFactory()
    my_service = internet.TCPServer(MY_PORT, factory)
    # 所有 Evennia 服务必须有唯一名称
    my_service.setName("MyService")
    # 添加到主 portal 应用程序
    portal.services.addService(my_service)
```

一旦定义了模块并在设置中定位，只需重新加载服务器，你的新协议/服务就应该与其他服务一起启动。

### 编写你自己的协议

```{important}
这被认为是一个高级主题。
```

从头编写一个稳定的通信协议不是我们在这里要讨论的内容，这不是一项简单的任务。好消息是 Twisted 提供了许多常见协议的实现，准备好进行适配。

在 Twisted 中编写协议实现通常涉及创建一个从已经存在的 Twisted 协议类和 `evennia.server.session.Session`（多重继承）继承的类，然后重载该特定协议使用的方法以将它们链接到 Evennia 特定的输入。

这里有一个示例来展示这个概念：

```python
# 在稍后通过 PORTAL_SERVICE_PLUGIN_MODULES 添加到系统的模块中

# 伪代码
from twisted.something import TwistedClient
# 此类用于 Portal 和 Server 会话
from evennia.server.session import Session 

from evennia.server.portal.portalsessionhandler import PORTAL_SESSIONS

class MyCustomClient(TwistedClient, Session): 

    def __init__(self, *args, **kwargs): 
        super().__init__(*args, **kwargs)
        self.sessionhandler = PORTAL_SESSIONS

    # 这些是我们必须知道 TwistedClient 用于通信的方法。名称和参数可能因不同的 Twisted 协议而异。
    def onOpen(self, *args, **kwargs):
        # 假设这是客户端首次连接时调用的

        # 我们需要初始化会话并连接到 sessionhandler。工厂通过 Twisted 父类可用

        client_address = self.getClientAddress()  # 以某种方式获取客户端地址

        self.init_session("mycustom_protocol", client_address, self.factory.sessionhandler)
        self.sessionhandler.connect(self)

    def onClose(self, reason, *args, **kwargs):
        # 当客户端连接断开时调用
        # 链接到 Evennia 等效项
        self.disconnect(reason)

    def onMessage(self, indata, *args, **kwargs): 
        # 随着传入数据调用
        # 根据需要在此处转换        
        self.data_in(data=indata) 

    def sendMessage(self, outdata, *args, **kwargs):
        # 用于发送数据
        # 根据需要修改        
        super().sendMessage(self, outdata, *args, **kwargs)

     # 这些是 Evennia 方法。它们必须全部存在并且看起来完全像这样。上面的 twisted 方法调用它们，反之亦然。这将协议连接到 Evennia 内部。
     
     def disconnect(self, reason=None): 
         """
         连接关闭时调用。
         这也可以由 Evennia 直接调用以手动关闭连接。
         在此处进行任何清理。
         """
         self.sessionhandler.disconnect(self)

     def at_login(self): 
         """
         当此会话通过服务器进行身份验证时调用（如果适用）
         """    

     def data_in(self, **kwargs):
         """
         进入服务器的数据应通过此方法。它应将数据传递到 `sessionhandler.data_in`。这将由 sessionhandler 调用，并使用从协议中找到的适当 send_* 方法获取的数据。
         """
         self.sessionhandler.data_in(self, text=kwargs['data'])

     def data_out(self, **kwargs):
         """
         从服务器发出的数据应通过此方法。它应交给协议的发送方法，无论它叫什么。
         """
         # 我们假设我们有一个 'text' outputfunc
         self.onMessage(kwargs['text'])

     # 'outputfuncs' 被定义为 `send_<outputfunc_name>`。从代码中，它们被调用为 `msg(outfunc_name=<data>)`。

     def send_text(self, txt, *args, **kwargs): 
         """
         发送文本，例如使用 `session.msg(text="foo")`
         """
         # 我们利用了
         self.data_out(text=txt)

     def send_default(self, cmdname, *args, **kwargs): 
         """
         处理所有没有显式 `send_*` 方法来处理的 outputfuncs。
         """
         self.data_out(**{cmdname: str(args)})

```

这里的原则是重写 Twisted 特定的方法以将输入/输出重定向到 Evennia 特定的方法。

### 发送数据

要通过此协议发送数据，你需要获取其会话，然后你可以例如：

```python
session.msg(text="foo")
```

消息将通过系统传递，以便 sessionhandler 将找出会话并检查它是否有 `send_text` 方法（它有）。然后它将把 "foo" 传递给该方法，在我们的例子中，这意味着通过网络发送 "foo"。

### 接收数据

仅仅因为协议存在，并不意味着 Evennia 知道如何处理它。必须存在一个 [Inputfunc](../Components/Inputfuncs.md) 来接收它。在上面示例的 `text` 输入的情况下，Evennia 已经处理了此输入——它会将其解析为命令名称及其输入。因此，要处理它，你只需在接收会话（和/或它所控制的对象/角色）上添加一个带有命令的 cmdset。如果没有，你可能需要添加你自己的 Inputfunc（请参阅 [Inputfunc](../Components/Inputfuncs.md) 页面以了解如何执行此操作）。

这些在所有协议中可能并不那么明确，但原则是存在的。这四个基本组件——无论它们如何访问——链接到 *Portal Session*，这是不同低级协议和 Evennia 之间的实际公共接口。
