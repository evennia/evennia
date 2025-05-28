# API 摘要

[evennia](api/evennia-api.md) - 库源代码树
- [evennia.accounts](evennia.accounts) - 代表玩家的离线实体
- [evennia.commands](evennia.commands) - 处理所有输入。也包含默认命令
- [evennia.comms](evennia.comms) - 游戏内频道和消息传递
- [evennia.contrib](evennia.contrib) - 社区贡献的游戏特定工具和代码
- [evennia.help](evennia.help) - 游戏内帮助系统
- [evennia.locks](evennia.locks) - 限制对各种系统和资源的访问
- [evennia.objects](evennia.objects) - 所有游戏内实体，如房间、角色、出口等
- [evennia.prototypes](evennia.prototypes) - 使用字典自定义实体
- [evennia.scripts](evennia.scripts) - 所有离线游戏对象
- [evennia.server](evennia.server) - 核心服务器和门户程序，以及网络协议
- [evennia.typeclasses](evennia.typeclasses) - 核心数据库-Python 桥接
- [evennia.utils](evennia.utils) - 大量有用的编码工具和实用程序
- [evennia.web](evennia.web) - 网页客户端、网站和其他网页资源

## 快捷方式

Evennia 的“扁平化 API”提供了常用工具的快捷方式，只需导入 `evennia` 即可使用。
扁平化 API 在 `__init__.py` 中定义 [可在此处查看](github:evennia/__init__.py)

### 主要配置

- [evennia.settings_default](Setup/Settings-Default.md) - 所有设置 (在 `mygame/server/settings.py` 中修改/覆盖)

### 搜索函数

- [evennia.search_account](evennia.utils.search.search_account)
- [evennia.search_object](evennia.utils.search.search_object)
- [evennia.search_tag](evennia.utils.search.search_tag)
- [evennia.search_script](evennia.utils.search.search_script)
- [evennia.search_channel](evennia.utils.search.search_channel)
- [evennia.search_message](evennia.utils.search.search_message)
- [evennia.search_help](evennia.utils.search.search_help_entry)

### 创建函数

- [evennia.create_account](evennia.utils.create.create_account)
- [evennia.create_object](evennia.utils.create.create_object)
- [evennia.create_script](evennia.utils.create.create_script)
- [evennia.create_channel](evennia.utils.create.create_channel)
- [evennia.create_help_entry](evennia.utils.create.create_help_entry)
- [evennia.create_message](evennia.utils.create.create_message)

### 类型类 (Typeclasses)

- [evennia.DefaultAccount](evennia.accounts.accounts.DefaultAccount) - 玩家账户类 ([文档](Components/Accounts.md))
- [evennia.DefaultGuest](evennia.accounts.accounts.DefaultGuest) - 基础访客账户类
- [evennia.DefaultObject](evennia.objects.objects.DefaultObject) - 所有对象的基础类 ([文档](Components/Objects.md))
- [evennia.DefaultCharacter](evennia.objects.objects.DefaultCharacter) - 游戏内角色的基础类 ([文档](Components/Characters.md))
- [evennia.DefaultRoom](evennia.objects.objects.DefaultRoom) - 房间的基础类 ([文档](Components/Rooms.md))
- [evennia.DefaultExit](evennia.objects.objects.DefaultExit) - 出口的基础类 ([文档](Components/Exits.md))
- [evennia.DefaultScript](evennia.scripts.scripts.DefaultScript) - OOC 对象的基础类 ([文档](Components/Scripts.md))
- [evennia.DefaultChannel](evennia.comms.comms.DefaultChannel) - 游戏内频道的基础类 ([文档](Components/Channels.md))

### 命令 (Commands)

- [evennia.Command](evennia.commands.command.Command) - 基础 [Command](Components/Commands.md) 类。另请参阅 `evennia.default_cmds.MuxCommand`
- [evennia.CmdSet](evennia.commands.cmdset.CmdSet) - 基础 [CmdSet](Components/Command-Sets.md) 类
- [evennia.default_cmds](Components/Default-Commands.md) - 以属性方式访问所有默认命令类

- [evennia.syscmdkeys](Components/Commands.md#system-commands) - 以属性方式访问系统命令键

### 实用工具 (Utilities)

- [evennia.utils.utils](evennia.utils.utils) - 混合的有用实用程序
- [evennia.gametime](evennia.utils.gametime.TimeScript) - 服务器运行时间和游戏时间 ([文档](Components/Coding-Utils.md#game-time))
- [evennia.logger](evennia.utils.logger) - 日志工具
- [evennia.ansi](evennia.utils.ansi) - ANSI 颜色工具
- [evennia.spawn](evennia.prototypes.spawner.spawn) - 生成/原型系统 ([文档](Components/Prototypes.md))
- [evennia.lockfuncs](evennia.locks.lockfuncs) - 用于访问控制的默认锁定函数 ([文档](Components/Locks.md))
- [evennia.EvMenu](evennia.utils.evmenu.EvMenu) - 菜单系统 ([文档](Components/EvMenu.md))
- [evennia.EvTable](evennia.utils.evtable.EvTable) - 文本表格创建器
- [evennia.EvForm](evennia.utils.evform.EvForm) - 文本表单创建器
- Evennia.EvMore - 文本分页器
- [evennia.EvEditor](evennia.utils.eveditor.EvEditor) - 游戏内文本行编辑器 ([文档](Components/EvEditor.md))
- [evennia.utils.funcparser.Funcparser](evennia.utils.funcparser.FuncParser) - 函数的内联解析 ([文档](Components/FuncParser.md))

### 全局单例处理器 (Global singleton handlers)

- [evennia.TICKER_HANDLER](evennia.scripts.tickerhandler.TickerHandler) - 允许对象订阅计时器 ([文档](Components/TickerHandler.md))
- [evennia.MONITOR_HANDLER](evennia.scripts.monitorhandler.MonitorHandler) - 监控更改 ([文档](Components/MonitorHandler.md))
- [evennia.SESSION_HANDLER](evennia.server.sessionhandler.SessionHandler) - 管理所有会话的主要会话处理器

### 数据库核心模型 (用于更高级的查找)

- [evennia.ObjectDB](evennia.objects.models.ObjectDB)
- [evennia.accountDB](evennia.accounts.models.AccountDB)
- [evennia.ScriptDB](evennia.scripts.models.ScriptDB)
- [evennia.ChannelDB](evennia.comms.models.ChannelDB)
- [evennia.Msg](evennia.comms.models.Msg)
- evennia.managers - 包含所有数据库管理器的快捷方式

### 贡献 (Contributions)

- [evennia.contrib](Contribs/Contribs-Overview.md) 特定于游戏的贡献和插件

```{toctree}
:hidden:
api/evennia-api.md
