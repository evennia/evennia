# 核心组件

这些就是构建 Evennia 的“建筑块”。本文件的文档补充了每个组件的 [API](../Evennia-API.md) 中的文档字符串，并且通常更为详细。

## 基础组件

这些是用于制作 Evennia 游戏的基础部分。大多数组件寿命较长，并存储在数据库中。

```{toctree} 
:maxdepth: 2
Portal-And-Server.md
Sessions.md
Typeclasses.md
Accounts.md
Objects.md
Characters.md
Rooms.md
Exits.md
Scripts.md
Channels.md
Msg.md
Attributes.md
Nicks.md
Tags.md
Prototypes.md
Help-System.md
Permissions.md
Locks.md
```

## 命令

Evennia 的命令系统处理用户发送到服务器的所有内容。

```{toctree} 
:maxdepth: 2

Commands.md
Command-Sets.md
Default-Commands.md
Batch-Processors.md
Inputfuncs.md
```

## 工具和实用程序

Evennia 提供了一组代码资源库，以帮助创建游戏。

```{toctree} 
:maxdepth: 2

Coding-Utils.md
EvEditor.md
EvForm.md
EvMenu.md
EvMore.md
EvTable.md
FuncParser.md
MonitorHandler.md
OnDemandHandler.md
TickerHandler.md
Signals.md
```

## Web 组件

Evennia 还是自己的 web 服务器，具有您可以扩展的网站和浏览器中的 Web 客户端。

```{toctree} 
:maxdepth: 2

Website.md
Webclient.md
Web-Admin.md
Webserver.md
Web-API.md
Web-Bootstrap-Framework.md
```
