# 冷却时间

由 owllex 贡献（2021）

冷却时间用于建模速率限制的操作，如角色可执行特定操作的频率；在某些时间过去之前，其命令不能再次使用。此贡献提供了一个简单的冷却时间处理器，可以附加到任何类型类上。冷却时间是一个轻量级的持久异步计时器，您可以查询以查看某段时间是否已经过去。

冷却时间完全是异步的，必须查询以了解其状态。它们不会触发回调，因此不适合在特定时间表上需要发生某些事情的用例（对此，请使用延迟或 TickerHandler）。

有关这一概念的更多信息，请参见 Evennia [教程](Howto-Command-Cooldown)。

## 安装

要使用冷却时间，只需在您想要支持冷却时间的任何对象类型的类型类定义中添加以下属性。这将暴露一个新的 `cooldowns` 属性，将数据持久化到对象的属性存储中。您可以将其设置在基础 `Object` 类型类上，以在每种类型的对象上启用冷却时间跟踪，或者仅将其放在您的 `Character` 类型类上。

默认情况下，CoolDownHandler 将使用 `cooldowns` 属性，但如果需要，您可以通过传递 `db_attribute` 参数的不同值来自定义此设置。

```python
from evennia.contrib.game_systems.cooldowns import CooldownHandler
from evennia.utils.utils import lazy_property

@lazy_property
def cooldowns(self):
    return CooldownHandler(self, db_attribute="cooldowns")
```

## 示例

假设您已在您的角色类型类上安装了冷却时间，您可以使用冷却时间来限制您执行命令的频率。以下代码片段将限制角色每 10 秒只能使用一次强力攻击命令。

```python
class PowerAttack(Command):
    def func(self):
        if self.caller.cooldowns.ready("power attack"):
            self.do_power_attack()
            self.caller.cooldowns.add("power attack", 10)
        else:
            self.caller.msg("那还没有准备好！")
```
