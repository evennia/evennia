# 添加命令提示符

在 MUD 游戏中，*提示符* 是相当常见的：

```
HP: 5, MP: 2, SP: 8
>
```

提示符显示有关角色的有用信息，通常是玩家希望随时掌握的内容。它可以是生命值、魔力、金币和当前位置等信息。它还可能显示游戏中的时间、天气等。

传统上，提示符（无论是否更改）会随着服务器的每次回复一起返回，并单独显示在一行上。许多现代 MUD 客户端（包括 Evennia 自己的网页客户端）允许识别提示符，并将其固定在一个位置进行更新（通常就在输入行上方）。

## 固定位置的提示符

提示符通过对象的 `msg()` 方法中的 `prompt` 关键字发送。提示符将不带换行符地发送。

```python
self.msg(prompt="HP: 5, MP: 2, SP: 8")
```

你可以将发送普通文本与发送（更新）提示符结合起来：

```python
self.msg("This is a text", prompt="This is a prompt")
```

你可以按需更新提示符，通常使用 [OOB](../Concepts/OOB.md) 跟踪相关属性（如角色的生命值）。例如，你可以确保在攻击命令导致生命值变化时更新提示符。

下面是一个从命令类发送/更新提示符的简单示例：

```python
from evennia import Command

class CmdDiagnose(Command):
    """
    查看你受了多重的伤

    用法: 
      diagnose [target]

    这将估计目标的健康状况。同时更新目标的提示符。
    """ 
    key = "diagnose"
    
    def func(self):
        if not self.args:
            target = self.caller
        else:
            target = self.caller.search(self.args)
            if not target:
                return
        # 尝试获取生命值、魔力和耐力
        hp = target.db.hp
        mp = target.db.mp
        sp = target.db.sp

        if None in (hp, mp, sp):
            # 属性未定义          
            self.caller.msg("不是有效的目标！")
            return 
         
        text = f"你诊断 {target} 的生命值为 {hp}，魔力为 {mp}，耐力为 {sp}。"
        prompt = f"{hp} HP, {mp} MP, {sp} SP"
        self.caller.msg(text, prompt=prompt)
```

## 每个命令的提示符

如上所述发送的提示符使用标准的 telnet 指令（Evennia 网页客户端会获得一个特殊标志）。大多数 MUD telnet 客户端会理解并允许用户捕获这一点，并在其更新之前保持提示符到位。因此，*原则上* 你不需要每个命令都更新提示符。

然而，由于用户基础的多样性，可能不清楚使用了哪些客户端以及用户的技能水平。因此，随每个命令发送提示符是一种安全的通用做法。你不需要手动编辑每个命令。相反，你可以编辑自定义命令的基类（如 `mygame/commands/command.py` 文件夹中的 `MuxCommand`），并重载 `at_post_cmd()` 钩子。这个钩子总是在命令的主 `func()` 方法之后调用。

```python
from evennia import default_cmds

class MuxCommand(default_cmds.MuxCommand):
    # ...
    def at_post_cmd(self):
        "在 self.func() 之后调用。"
        caller = self.caller        
        prompt = f"{caller.db.hp} HP, {caller.db.mp} MP, {caller.db.sp} SP"
        caller.msg(prompt=prompt)
```

### 修改默认命令

如果你想在 Evennia 的默认命令中添加像这样的简单内容，而不直接修改它们，最简单的方法是使用多重继承将它们包装到你自己的基类中：

```python
# 在（例如）mygame/commands/mycommands.py 中

from evennia import default_cmds
# 我们的自定义 MuxCommand，带有 at_post_cmd 钩子
from commands.command import MuxCommand

# 重载 look 命令
class CmdLook(default_cmds.CmdLook, MuxCommand):
    pass
```

这样做的结果是，你的自定义 `MuxCommand` 中的钩子将通过多重继承混合到默认的 `CmdLook` 中。接下来，只需将其添加到你的默认命令集中：

```python
# 在 mygame/commands/default_cmdsets.py 中

from evennia import default_cmds
from commands import mycommands

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # ...
    def at_cmdset_creation(self):
        # ...
        self.add(mycommands.CmdLook())
```

这将自动用你自己的版本替换游戏中的默认 `look` 命令。
