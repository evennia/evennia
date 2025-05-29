# Evennia 1.0 发行说明

以下是更改的摘要。完整列表请参见[更新日志](./Changelog.md)。

- 主要开发现在在 `main` 分支进行。`master` 分支仍然存在，但将不再更新。

## 最低要求

- 现在最低要求 Python 3.10。Ubuntu LTS 现在安装的是 3.10。Evennia 1.0 也在 Python 3.11 上进行了测试——这是 Linux/Mac 的推荐版本。Windows 用户可能希望继续使用 Python 3.10，除非他们愿意安装 C++ 编译器。
- Twisted 22.10+
- Django 4.1+

## 主要新功能

- Evennia 现在可以在 PyPi 上安装，使用命令 [pip install evennia](../Setup/Installation.md)。
- 全新改版的文档在 https://www.evennia.com/docs/latest。旧的 wiki 和 readmedocs 页面将关闭。
- Evennia 1.0 现在有一个 REST API，允许您使用 CRUD 操作 GET/POST 等访问游戏对象。更多信息请参见 [Web-API 文档][Web-API]。
- [Evennia & Discord 集成](../Setup/Channels-to-Discord.md)，实现 Evennia 频道和 Discord 服务器之间的集成。

- [脚本](../Components/Scripts.md)大修：脚本的计时器组件与脚本对象删除独立；现在可以在不删除脚本的情况下启动/停止计时器。`.persistent` 标志现在仅控制计时器是否在重载后存活——脚本必须像其他类型类实体一样用 `.delete()` 删除。这使得脚本作为通用存储实体更加有用。
- [FuncParser](../Components/FuncParser.md) 集中并大大改进了所有字符串内函数调用，例如 `say the result is $eval(3 * 7)` 和 `say the result is 21`。解析器完全取代了旧的 `parse_inlinefunc`。新解析器可以处理参数和关键字参数，也用于原型解析以及导演姿态消息传递，例如在字符串中使用 `$You()` 表示自己，并根据谁看到您而产生不同的结果。
- [频道](../Components/Channels.md) 新的频道系统使用 `channel` 命令和昵称。旧的 `ChannelHandler` 被移除，频道的自定义和操作大大简化。旧的命令语法命令现在作为一个贡献提供。
- [帮助系统](../Components/Help-System.md) 被重构。
  - 新的 `FileHelp` 系统允许您将游戏内帮助文件作为外部 Python 文件添加。这意味着在 Evennia 中有三种方式添加帮助条目：1）从命令代码自动生成。2）从游戏中的 `sethelp` 命令手动添加到数据库中。3）创建为 Evennia 加载并在游戏中可用的外部 Python 文件。
  - 我们现在使用 `lunr` 搜索索引以获得更好的 `help` 匹配和建议。还改进了主要帮助命令的默认列表输出。
  - 帮助命令现在使用 `view` 锁定来确定 cmd/entry 是否显示在索引中，并使用 `read` 锁定来确定是否可以读取。过去是 `view` 扮演后者的角色。
  - `sethelp` 命令现在在创建新条目时会警告是否遮蔽其他帮助类型。
  - 使 `help` 索引输出对 webclient/支持 MXP 的客户端可点击（由 davewiththenicehat 提供的 PR）。
- 重构 [Web](../Components/Website.md) 设置，使其结构更加一致，并更新到最新的 Django。`mygame/web/static_overrides` 和 `-template_overrides` 被移除。文件夹现在只是 `mygame/web/static` 和 `/templates`，并在后台自动处理数据复制。将 `app.css` 改为 `website.css` 以保持一致性。旧的 `prosimii-css` 文件被移除。
- [AttributeProperty](../Components/Attributes.md#using-attributeproperty)/[TagProperty](../Components/Tags.md) 以及 `AliasProperty` 和 `PermissionProperty`，允许以与 Django 字段相同的方式管理类型类上的属性、标签、别名和权限。这大大减少了在 `at_create_object` 钩子中分配属性/标签的需要。
- 旧的 `MULTISESSION_MODE` 被分为更小的设置，以更好地控制用户连接时发生的事情、是否应自动创建角色以及他们可以同时控制多少个角色。有关详细说明，请参见 [连接样式](../Concepts/Connection-Styles.md)。
- Evennia 现在支持自定义 `evennia` 启动器命令（例如 `evennia mycmd foo bar`）。将新命令添加为接受 `*args` 的可调用对象，作为 `settings.EXTRA_LAUNCHER_COMMANDS = {'mycmd': 'path.to.callable', ...}`。

## 贡献

`contrib` 文件夹结构从 0.9.5 版本发生了变化。所有贡献现在都在子文件夹中，并按类别组织。所有导入路径必须更新。请参见 [贡献概览](../Contribs/Contribs-Overview.md)。

- 新的 [Traits 贡献](../Contribs/Contrib-Traits.md)，从 Ainneve 项目转换并扩展而来。（whitenoise, Griatch）
- 新的 [Crafting 贡献](../Contribs/Contrib-Crafting.md)，添加了一个完整的制作子系统（Griatch）
- 新的 [XYZGrid 贡献](../Contribs/Contrib-XYZGrid.md)，添加了 x, y, z 网格坐标，带有游戏内地图和路径查找。通过自定义 evennia 启动器命令在游戏外部控制（Griatch）
- 新的 [命令冷却贡献](../Contribs/Contrib-Cooldowns.md)，用于更轻松地管理使用动态冷却时间的命令（owllex）
- 新的 [Godot 协议贡献](../Contribs/Contrib-Godotwebsocket.md)，用于从开源游戏引擎 [Godot](https://godotengine.org/) 编写的客户端连接到 Evennia（ChrisLR）。
- 新的 [name_generator 贡献](../Contribs/Contrib-Name-Generator.md)，用于根据语音规则构建基于真实世界或幻想的随机名称（InspectorCaracal）
- 新的 [Buffs 贡献](../Contribs/Contrib-Buffs.md)，用于管理临时和永久 RPG 状态增益效果（tegiminis）
- 现有的 [RPSystem 贡献](../Contribs/Contrib-RPSystem.md) 被重构并获得了速度提升（InspectorCaracal，其他贡献者）

## 翻译

- 新的拉丁语（la）翻译（jamalainm）
- 新的德语（de）翻译（Zhuraj）
- 更新的意大利语翻译（rpolve）
- 更新的瑞典语翻译

## 实用工具

- 新的 `utils.format_grid` 用于轻松地在块中显示长列表项。这现在用于默认的帮助显示。
- 添加 `utils.repeat` 和 `utils.unrepeat` 作为 TickerHandler 添加/删除的快捷方式，类似于 `utils.delay` 是 TaskHandler 添加的快捷方式。
- 添加 `utils/verb_conjugation` 用于自动动词变位（仅限英语）。这对于实现演员姿态表情以将字符串发送给不同目标非常有用。
- `utils.evmenu.ask_yes_no` 是一个辅助函数，可以轻松地向用户询问是/否问题并响应他们的输入。这补充了现有的 `get_input` 辅助函数。
- 新的 `tasks` 命令用于管理使用 `utils.delay` 启动的任务（由 davewiththenicehat 提供的 PR）。
- 向 `_Saver*` 结构添加 `.deserialize()` 方法，以帮助完全解耦结构与数据库，而无需单独导入。
- 添加 `run_in_main_thread` 作为希望从 Web 视图编写服务器代码的人的助手。
- 更新 `evennia.utils.logger` 以使用 Twisted 的新日志记录 API。Evennia API 没有变化，只是现在可以使用更标准的别名 logger.error/info/exception/debug 等。
- 使 `utils.iter_to_str` 格式化更漂亮的字符串，使用牛津逗号。
- 将 `create_*` 函数移到 db 管理器中，只保留 `utils.create` 作为包装函数（与 `utils.search` 一致）。否则没有 API 更改。

## 锁

- 新的 `search:` 锁类型用于完全隐藏对象，使其无法通过 `DefaultObject.search` (`caller.search`) 方法找到。（CloudKeeper）
- `holds()` 锁函数的新默认值——从默认的 `True` 更改为默认的 `False`，以防止丢弃无意义的东西（例如您不持有的东西）。

## 钩子更改

- 将所有 `at_before/after_*` 钩子更改为 `at_pre/post_*`，以在 Evennia 中保持一致性（旧名称仍然有效，但已被弃用）
- 在 `Objects` 上添加新的 `at_pre_object_leave(obj, destination)` 方法。
- 新的 `at_server_init()` 钩子在所有其他启动钩子之前调用，适用于所有启动模式。用于更通用的重写（volund）
- 在 Objects 上添加新的 `at_pre_object_receive(obj, source_location)` 方法。调用目标，模仿 `at_pre_move` 钩子的行为——返回 False 将中止移动。
- `Object.normalize_name` 和 `.validate_name` 添加到（默认情况下）强制使用拉丁字符作为角色名，并避免使用巧妙的 Unicode 字符进行潜在的漏洞利用（trhr）
- 使 `object.search` 支持 'stacks=0' 关键字 - 如果 ``>0``，方法将返回 N 个相同的匹配，而不是触发多重匹配错误。
- 为检查对象是否具有标签或标签添加 `tags.has()` 方法（由 ChrisLR 提供的 PR）
- 向 `Msg.db_receiver_external` 字段添加外部字符串 ID 消息接收器。
- 在 actor-stance 字符串中使用 `$pron()` 和 `$You()` 内联函数进行代词解析。

## 命令更改

- 将默认的多重匹配语法从 `1-obj`、`2-obj` 改为 `obj-1`、`obj-2`，这似乎是大多数人期望的。
- 使用辅助方法拆分 `return_appearance` 钩子，并使用模板字符串以便更容易重写。
- 在副本上执行命令，以确保 `yield` 不会导致交叉。添加 `Command.retain_instance` 标志以重用相同的命令实例。
- 如果目标名称不包含空格，则允许使用 `page/tell` 发送消息而不带 `=`。
- `typeclass` 命令现在将正确搜索目标对象的正确数据库表（避免错误地将 AccountDB 类型类分配给 Character 等）。
- 将 `script` 和 `scripts` 命令合并为一个，用于管理全局和对象上的脚本。将 `CmdScripts` 和 `CmdObjects` 移动到 `commands/default/building.py`。
- `channel` 命令替换了所有旧的频道相关命令，如 `cset` 等。
- 扩展 `examine` 命令的代码，使其更具可扩展性和模块化。显示属性类别和值类型（当不是字符串时）。
  - 添加使用 `examine` 命令检查 `/script` 和 `/channel` 实体的功能。
- 在使用 `set` 命令分配属性值时，添加对 `$dbref()` 和 `$search` 的支持。这允许从游戏中分配真实对象。
- 使 `type/force` 默认使用 `update` 模式而不是 `reset` 模式，并在使用重置模式时添加更详细的警告。

## 编码改进亮点

- 数据库 pickle 序列化器现在检查方法 `__serialize_dbobjs__` 和 `__deserialize_dbobjs__`，以允许自定义打包/解包嵌套的 dbobjs，以便存储在属性中。请参阅 [属性](../Components/Attributes.md) 文档。
- 将 `ObjectParent` 混合添加到默认游戏文件夹模板中，作为一种简单、现成的方法，可以轻松覆盖所有 ObjectDB 继承对象的功能。
- 新的单元测试父类，用于 Evenia 核心和 mygame 中。重构单元测试以始终遵循默认设置。

## 其他

- 统一管理器搜索方法，以始终返回查询集，而不是有时返回查询集，有时返回列表。
- Attribute/NAttribute 获得了统一的表示，使用接口，`AttributeHandler` 和 `NAttributeHandler` 现在具有相同的 API。
- 向 DefaultObject 的 ContentsHandler 添加 `content_types` 索引。（volund）
- 使大多数网络类（如协议和 SessionHandlers）可通过 `settings.py` 替换，以供修改爱好者使用。（volund）
- 现在可以在 `settings.py` 中替换 `initial_setup.py` 文件，以自定义初始游戏数据库状态。（volund）
- 使 IP 节流使用基于 Django 的缓存系统以实现可选持久性（由 strikaco 提供的 PR）
- 在 `settings.PROTOTYPE_MODULES` 给出的模块中，生成器现在将首先查找字典的全局列表 `PROTOTYPE_LIST`，然后再将模块中的所有字典加载为原型。
- 原型现在允许将 `prototype_parent` 直接设置为原型字典。这使得在模块中动态构建原型变得更容易。
- 使 `@lazy_property` 装饰器创建只读/删除保护的属性。这是因为它用于处理程序，例如 self.locks=[] 是一个常见的初学者错误。
- 将 `settings.COMMAND_DEFAULT_ARG_REGEX` 的默认值从 `None` 更改为一个正则表达式，表示 cmdname 和 args 之间必须有空格或 `/` 分隔。这更符合常见的期望。
- 添加 `settings.MXP_ENABLED=True` 和 `settings.MXP_OUTGOING_ONLY=True` 作为合理的默认值，以避免已知的安全问题，玩家输入 MXP 链接。
- 使 `MonitorHandler.add/remove` 支持 `category` 以监视具有类别的属性（之前仅使用键，完全忽略类别）。
