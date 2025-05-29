# 信号

_此功能从 Evennia 0.9 版本开始提供_。

在 Evennia 中，你可以通过多种方式插入自己的功能。最常见的方法是通过 *钩子*——在特定事件中调用的类型类上的方法。当你希望游戏实体在某些事情发生时表现出特定方式时，钩子是很好的选择。对于希望轻松附加新功能而不覆盖类型类内容的情况，_信号_ 是钩子的补充。

当 Evennia 中发生某些事件时，会触发一个 _信号_。其思想是你可以将任意数量的事件处理程序“附加”到这些信号上。你可以附加任意数量的处理程序，并且每当任何实体触发信号时，它们都会被触发。

Evennia 使用 [Django 信号系统](https://docs.djangoproject.com/en/4.1/topics/signals/)。

## 使用信号

首先，你需要创建一个处理程序：

```python
def myhandler(sender, **kwargs):
  # 执行操作
```

`**kwargs` 是必需的。然后将其附加到你选择的信号上：

```python
from evennia.server import signals

signals.SIGNAL_OBJECT_POST_CREATE.connect(myhandler)
```

这个特定的信号在账户连接到游戏后（post）触发。发生这种情况时，`myhandler` 将被触发，`sender` 是刚刚连接的账户。

如果你只想响应特定实体的效果，可以这样做：

```python
from evennia import search_account
from evennia import signals

account = search_account("foo")[0]
signals.SIGNAL_ACCOUNT_POST_CONNECT.connect(myhandler, account)
```

### 可用信号

所有信号（包括一些特定于 Django 的默认信号）都在模块 `evennia.server.signals` 中可用（有一个快捷方式 `evennia.signals`）。信号按发送者类型命名。因此，`SIGNAL_ACCOUNT_*` 返回 `Account` 实例作为发送者，`SIGNAL_OBJECT_*` 返回 `Object` 等。额外的关键字参数（kwargs）应该从信号处理程序中的 `**kwargs` 字典中提取。

- `SIGNAL_ACCOUNT_POST_CREATE` - 在 `Account.create()` 的最后触发。请注意，调用 `evennia.create.create_account`（由 `Account.create` 内部调用）*不会*触发此信号。这是因为使用 `Account.create()` 被认为是用户在登录期间自己创建账户的最常用方式。它传递一个额外的 kwarg `ip`，表示连接账户的客户端 IP。
- `SIGNAL_ACCOUNT_POST_LOGIN` - 账户通过身份验证后总是触发。发送额外的 kwarg `session`，表示涉及的新 [Session](./Sessions.md) 对象。
- `SIGNAL_ACCCOUNT_POST_FIRST_LOGIN` - 在 `SIGNAL_ACCOUNT_POST_LOGIN` 之前触发，但仅在这是首次连接时（即如果没有先前的会话连接）。也将 `session` 作为 kwarg 传递。
- `SIGNAL_ACCOUNT_POST_LOGIN_FAIL` - 当有人尝试登录账户但失败时发送。传递 `session` 作为额外的 kwarg。
- `SIGNAL_ACCOUNT_POST_LOGOUT` - 当账户注销时总是触发，无论其他会话是否仍然存在。传递断开连接的 `session` 作为 kwarg。
- `SIGNAL_ACCOUNT_POST_LAST_LOGOUT` - 在 `SIGNAL_ACCOUNT_POST_LOGOUT` 之前触发，但仅在这是该账户的最后一个会话断开时。传递 `session` 作为 kwarg。
- `SIGNAL_OBJECT_POST_PUPPET` - 当账户控制此对象时触发。额外的 kwargs `session` 和 `account` 代表控制实体。
- `SIGNAL_OBJECT_POST_UNPUPPET` - 当发送对象被解除控制时触发。额外的 kwargs 是 `session` 和 `account`。
- `SIGNAL_ACCOUNT_POST_RENAME` - 由设置 `Account.username` 触发。传递额外的 kwargs `old_name`，`new_name`。
- `SIGNAL_TYPED_OBJECT_POST_RENAME` - 当任何类型类实体的 `key` 被更改时触发。传递的额外 kwargs 是 `old_key` 和 `new_key`。
- `SIGNAL_SCRIPT_POST_CREATE` - 在脚本首次创建时触发，在任何钩子之后。
- `SIGNAL_CHANNEL_POST_CREATE` - 在频道首次创建时触发，在任何钩子之后。
- `SIGNAL_HELPENTRY_POST_CREATE` - 在帮助条目首次创建时触发。
- `SIGNAL_EXIT_TRAVERSED` - 在出口被穿越时触发，紧接在 `at_traverse` 钩子之后。`sender` 是出口本身，`traverser=` 关键字持有穿越出口的实体。

`evennia.signals` 模块还为你提供了对默认 Django 信号的便捷访问（这些使用不同的命名约定）。

- `pre_save` - 在任何数据库实体的 `.save` 方法触发时触发，保存之前。
- `post_save` - 在保存数据库实体之后触发。
- `pre_delete` - 在数据库实体被删除之前触发。
- `post_delete` - 在数据库实体被删除之后触发。
- `pre_init` - 在类型类的 `__init__` 方法之前触发（这反过来在 `at_init` 钩子触发之前发生）。
- `post_init` - 在 `__init__` 结束时触发（仍然在 `at_init` 钩子之前）。

这些是高度专业化的 Django 信号，对于大多数用户来说可能不太有用。但为了完整性，它们被包括在这里。

- `m2m_changed` - 在多对多字段（如 `db_attributes`）更改后触发。
- `pre_migrate` - 在数据库迁移开始之前使用 `evennia migrate` 触发。
- `post_migrate` - 在数据库迁移完成后触发。
- `request_started` - 在 HTTP 请求开始时发送。
- `request_finished` - 在 HTTP 请求结束时发送。
- `settings_changed` - 在由于 `@override_settings` 装饰器更改设置时发送（仅与单元测试相关）。
- `template_rendered` - 在测试系统渲染 http 模板时发送（仅对单元测试有用）。
- `connection_creation` - 在初始连接到数据库时发送。
