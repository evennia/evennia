# 添加命令冷却时间

在某些类型的游戏中，你可能希望限制命令的执行频率。如果一个角色施放了 *火焰风暴* 法术，你可能不希望他们反复使用这个命令。在一个高级战斗系统中，一个巨大的挥击可能会造成大量伤害，但代价是需要一段时间才能再次使用。

这种效果称为 *命令冷却时间*。

```{sidebar}
[Cooldown contrib](../Contribs/Contrib-Cooldowns.md) 是一个现成的解决方案，用于命令冷却时间。它基于此教程并实现了一个 [handler](Tutorial-Peristent-Handler) 在对象上以方便地管理和存储冷却时间。
```

这个教程展示了一种非常高效的方式来实现冷却时间。另一种更“主动”的方法是使用异步延迟，如 [Command-Duration howto](./Howto-Command-Duration.md#blocking-commands) 所建议的。如果你想在冷却结束后给用户发送一些信息，可以考虑结合这两个教程。

## 高效的冷却时间

我们的想法是，当一个 [Command](../Components/Commands.md) 运行时，我们存储它运行的时间。下次运行时，我们再次检查当前时间。只有当经过足够的时间后，命令才被允许运行。这是一种 _非常_ 高效的实现，仅在需要时进行检查。

```python
# 在 mygame/commands/spells.py 中

import time
from evennia import default_cmds

class CmdSpellFirestorm(default_cmds.MuxCommand):
    """
    法术 - 火焰风暴

    用法:
      cast firestorm <target>

    这将释放一场火焰风暴。你每五分钟只能释放一次火焰风暴（假设你有足够的法力）。
    """
    key = "cast firestorm"
    rate_of_fire = 60 * 2  # 2 分钟

    def func(self):
        "实现法术"

        now = time.time()
        last_cast = self.caller.db.firestorm_last_cast  # 可能为 None
        if last_cast and (now - last_cast < self.rate_of_fire):
            message = "你还不能再次施放这个法术。"
            self.caller.msg(message)
            return

        # [实现法术效果]

        # 如果法术成功施放，存储施放时间
        self.caller.db.firestorm_last_cast = now
```

我们指定 `rate_of_fire`，然后只需检查 `caller` 上的一个 [Attribute](../Components/Attributes.md) `firestorm_last_cast`。它要么是 `None`（因为法术从未施放过），要么是表示上次施放时间的时间戳。

### 非持久性冷却时间

上述实现将在重载后生效。如果你不希望这样，你可以让 `firestorm_last_cast` 成为一个 [NAttribute](../Components/Attributes.md#in-memory-attributes-nattributes)。例如：

```python
        last_cast = self.caller.ndb.firestorm_last_cast
        # ... 
        self.caller.ndb.firestorm_last_cast = now 
```

也就是说，使用 `.ndb` 而不是 `.db`。由于 `NAttribute` 纯粹在内存中，它们可以比 `Attribute` 更快地读写。因此，如果你的间隔很短且需要经常更改，这可能更优。缺点是如果服务器重载，它们会重置。

## 创建一个支持冷却时间的命令父类

如果你有许多不同的法术或其他带有冷却时间的命令，你不希望每次都添加这段代码。相反，你可以创建一个“冷却时间命令混入”类。_混入_ 是一个你可以“添加”到另一个类的类（通过多重继承）以赋予它某些特殊能力。以下是一个带有持久存储的示例：

```python
# 在 mygame/commands/mixins.py 中

import time

class CooldownCommandMixin:

    rate_of_fire = 60
    cooldown_storage_key = "last_used"
    cooldown_storage_category = "cmd_cooldowns"

    def check_cooldown(self):
        last_time = self.caller.attributes.get(
            key=self.cooldown_storage_key,
            category=self.cooldown_storage_category)
        return (time.time() - last_time) < self.rate_of_fire

    def update_cooldown(self):
        self.caller.attributes.add(
            key=self.cooldown_storage_key,
            value=time.time(),
            category=self.cooldown_storage_category
        )
```

这是为了混入一个命令中，所以我们假设 `self.caller` 存在。我们允许设置用于存储冷却时间的 Attribute 键/类别。

它还使用 Attribute 类别来确保它存储的内容不会与 caller 上的其他 Attribute 混淆。

以下是如何使用它：

```python
# 在 mygame/commands/spells.py 中

from evennia import default_cmds
from .mixins import CooldownCommandMixin

class CmdSpellFirestorm(
        CooldownCommandMixin, default_cmds.MuxCommand):
    key = "cast firestorm"

    cooldown_storage_key = "firestorm_last_cast"
    rate_of_fire = 60 * 2

    def func(self):

        if not self.check_cooldown():
            self.caller.msg("你还不能再次施放这个法术。")
            return

        # [法术效果发生]

        self.update_cooldown()
```

与之前相同，我们只是隐藏了冷却时间检查，你可以将这个混入类用于所有的冷却时间。

### 命令交叉

这个冷却时间检查的例子也适用于*不同*命令之间。例如，你可以让所有与火相关的法术使用相同的 `cooldown_storage_key`（如 `fire_spell_last_used`）来存储冷却时间。这意味着施放 *火焰风暴* 会在一段时间内阻止所有其他与火相关的法术。

同样，当你进行一次大剑挥击时，在你恢复平衡之前，其他类型的攻击可能会被阻止。
