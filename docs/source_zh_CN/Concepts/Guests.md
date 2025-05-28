# 客户端登录

Evennia 原生支持*客户端登录*。客户端登录是一种匿名的、低访问权限的账户类型，如果你希望用户在不创建真实账户的情况下尝试你的游戏，这将非常有用。

客户端账户默认是关闭的。要激活它们，请在你的 `game/settings.py` 文件中添加以下内容：

```python
GUEST_ENABLED = True
```

从此，用户可以使用 `connect guest`（在默认命令集中）以客户端账户登录。你可能需要更改你的[连接界面](../Components/Connection-Screen.md)以告知他们这一可能性。客户端账户与普通账户不同——用户注销或服务器重置时（但不是在重新加载期间），它们会被自动*删除*。它们实际上是可重复使用的一次性账户。

你可以在 `settings.py` 文件中添加一些变量来自定义客户端：

- `BASE_GUEST_TYPECLASS` - 客户端的默认 [typeclass](../Components/Typeclasses.md) 的 Python 路径。默认为 `"typeclasses.accounts.Guest"`。
- `PERMISSION_GUEST_DEFAULT` - 客户端账户的[权限级别](../Components/Locks.md)。默认为 `"Guest"`，这是层次结构中最低的权限级别（低于 `Player`）。
- `GUEST_START_LOCATION` - 新登录的客户端应出现的起始位置的 `#dbref`。默认为 `"#2"`（Limbo）。
- `GUEST_HOME` - 客户端的家位置。默认为 Limbo。
- `GUEST_LIST` - 这是一个列表，包含进入游戏时可能使用的客户端名称。此列表的长度也设置了可以同时登录的客户端数量。默认情况下，这是一个从 `"Guest1"` 到 `"Guest9"` 的九个名称的列表。
