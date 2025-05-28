# 需要时间完成的命令

在某些类型的游戏中，命令不应该立即开始和结束。例如，装填弩箭可能需要一点时间，而敌人冲过来时你可能没有这个时间。同样，制作盔甲也不会是即时的。在某些游戏中，移动或改变姿势本身也需要一定的时间。

引入命令执行“延迟”的两种主要方法：

- 在命令的 `func` 方法中使用 `yield`。
- 使用 `evennia.utils.delay` 实用函数。

我们将在下面简化这两种方法。

## 使用 `yield` 暂停命令

`yield` 是 Python 中的一个保留字，用于创建 [生成器](https://realpython.com/introduction-to-python-generators/)。在这个教程中，我们只需要知道 Evennia 会使用它来“暂停”命令的执行一段时间。

```{sidebar} 仅在 Command.func 中有效！

`yield` 功能仅在命令的 `func` 方法中有效。Evennia 特别为其提供了这种方便的快捷方式。在其他地方使用将不起作用。如果你想在其他地方使用相同的功能，你应该查看 [interactive 装饰器](../Concepts/Async-Process.md#the-interactive-decorator)。
```

```python
class CmdTest(Command):
    """
    一个测试命令，用于测试等待。

    用法:
        test
    """

    key = "test"

    def func(self):
        self.msg("十秒钟前...")
        yield 10
        self.msg("之后。")
```

- **第15行**：这是关键行。`yield 10` 告诉 Evennia 暂停命令并等待10秒钟再执行其余部分。如果你添加这个命令并运行它，你会看到第一条消息，然后在十秒钟的暂停后看到下一条消息。你可以在命令中多次使用 `yield`。

这种语法不会“冻结”所有命令。在命令“暂停”时，你可以执行其他命令（甚至再次调用相同的命令）。其他玩家也不会被冻结。

> 使用 `yield` 是非持久性的。如果在命令“暂停”时 `reload` 游戏，该暂停状态将丢失，并且在服务器重载后不会恢复。

## 使用 `utils.delay` 暂停命令

`yield` 语法易于阅读、理解和使用，但它是非持久性的，如果你需要更高级的选项，它的灵活性不够。

`evennia.utils.delay` 是一种更强大的引入延迟的方法。与 `yield` 不同，它可以实现持久性，并且在 `Command.func` 之外也能工作。然而，它的编写稍显繁琐，因为与 `yield` 不同，它不会在调用的行上实际停止。

```python
from evennia import default_cmds, utils
    
class CmdEcho(default_cmds.MuxCommand):
    """
    等待回声

    用法: 
      echo <string>
    
    调用并等待回声。
    """
    key = "echo"
    
    def echo(self):
        "在10秒后调用。"
        shout = self.args
        self.caller.msg(
            "你听到回声: "
            f"{shout.upper()} ... "
            f"{shout.capitalize()} ... "
            f"{shout.lower()}"
        )
    
    def func(self):
        """
         这是在初始呼喊时调用的。            
        """
        self.caller.msg(f"你大喊 '{self.args}' 并等待回声 ...")
        # 这是非阻塞等待10秒，然后调用 self.echo
        utils.delay(10, self.echo) # 10秒后调用 echo
```

将此新回声命令导入默认命令集并重载服务器。你会发现需要10秒钟才能看到你的呼喊返回。

- **第14行**：我们添加了一个新方法 `echo`。这是一个 _回调_——一个将在一定时间后调用的方法/函数。
- **第30行**：在这里我们使用 `utils.delay` 告诉 Evennia “请等待10秒钟，然后调用 `self.echo`”。注意我们传递的是 `self.echo` 而不是 `self.echo()`！如果我们使用后者，`echo` 将立即触发。相反，我们让 Evennia 在十秒后为我们进行这个调用。

你还会发现这是一个*非阻塞*效果；你可以在此期间发出其他命令，游戏将照常进行。回声将在其自己的时间内返回给你。

`utils.delay` 的调用签名是：

```python
utils.delay(timedelay, callback, persistent=False, *args, **kwargs) 
```

```{sidebar} *args 和 **kwargs 

这些用于指示应在此处获取任意数量的参数或关键字参数。在代码中，它们分别被视为 `tuple` 和 `dict`。

`*args` 和 `**kwargs` 在 Evennia 的许多地方使用。[在此查看在线教程](https://realpython.com/python-kwargs-and-args)。
```
如果你设置 `persistent=True`，此延迟将在 `reload` 后继续。如果你传递 `*args` 和/或 `**kwargs`，它们将被传递到 `callback` 中。因此，你可以将更复杂的参数传递给延迟函数。

重要的是要记住，`delay()` 调用不会在调用时“暂停”（像上一节中的 `yield` 那样）。`delay()` 调用后的行实际上会立即执行。你必须告诉它在时间过去后调用哪个函数（即“回调”）。这听起来可能有些奇怪，但在异步系统中是正常的做法。你还可以将这样的调用链接在一起：

```python
from evennia import default_cmds, utils
    
class CmdEcho(default_cmds.MuxCommand):
    """
    等待回声

    用法: 
      echo <string>
    
    调用并等待回声
    """
    key = "echo"
    
    def func(self):
        "这会启动一系列延迟调用"
        self.caller.msg(f"你大喊 '{self.args}'，等待回声 ...")

        # 等待2秒钟，然后调用 self.echo1
        utils.delay(2, self.echo1)
    
    # 回调链，从上面开始
    def echo1(self):
        "第一次回声"
        self.caller.msg(f"... {self.args.upper()}")
        # 等待2秒钟，进行下一个
        utils.delay(2, self.echo2)

    def echo2(self):
        "第二次回声"
        self.caller.msg(f"... {self.args.capitalize()}")
        # 再等待2秒钟
        utils.delay(2, callback=self.echo3)

    def echo3(self):
        "最后一次回声"
        self.caller.msg(f"... {self.args.lower()} ...")
```

上述版本将使回声一个接一个地到达，每个回声之间间隔两秒。

- **第19行**：这启动了链，告诉 Evennia 等待2秒钟，然后调用 `self.echo1`。
- **第22行**：这是在2秒后调用的。它告诉 Evennia 再等2秒钟，然后调用 `self.echo2`。
- **第28行**：这是在又2秒后（共4秒）调用的。它告诉 Evennia 再等2秒钟，然后调用 `self.echo3`。
- **第34行**：在再2秒（共6秒）后调用。这结束了延迟链。

```
> echo Hello!
... HELLO!
... Hello!
... hello! ...
```

```{warning} 关于 time.sleep

你可能知道 Python 自带的 `time.sleep` 函数。执行 `time.sleep(10)` 会暂停 Python 10秒。**不要使用这个**，它在 Evennia 中不起作用。如果你使用它，你将阻塞 _整个服务器_（每个人！）10秒！

如果你想要详细信息，`utils.delay` 是一个 [Twisted Deferred](https://docs.twisted.org/en/twisted-22.1.0/core/howto/defer.html) 的薄包装。这是一个 [异步概念](../Concepts/Async-Process.md)。
```

## 制作一个阻塞命令

`yield` 和 `utils.delay()` 都会暂停命令，但允许用户在第一个命令等待完成时使用其他命令。

在某些情况下，你可能希望该命令“阻止”其他命令运行。例如，制作头盔：你很可能不应该同时开始制作盾牌，甚至不能走出铁匠铺。

实现阻塞的最简单方法是使用[如何实现命令冷却](./Howto-Command-Cooldown.md)教程中介绍的技术。在那个教程中，我们通过将当前时间与上次使用命令的时间进行比较来实现冷却时间。如果你可以这样做，这是最好的方法。对于我们的制作示例，如果你不想自动更新玩家的进度，这可能效果很好。

简而言之：
- 如果你不介意玩家主动输入以检查他们的状态，请按照命令冷却教程中的方法比较时间戳。按需是效率最高的。
- 如果你希望 Evennia 在不采取进一步行动的情况下告诉用户他们的状态，你需要使用 `yield`、`delay`（或其他一些主动的时间管理方法）。

这是一个使用 `utils.delay` 告诉玩家冷却时间已过的示例：

```python
from evennia import utils, default_cmds
    
class CmdBigSwing(default_cmds.MuxCommand):
    """
    大力挥舞你的武器

    用法:
      swing <target>
    
    进行一次强力挥击。这样做会使你在恢复之前容易受到反击。
    """
    key = "bigswing"
    locks = "cmd:all()"
    
    def func(self):
        "进行挥击" 

        if self.caller.ndb.off_balance:
            # 我们仍然失去平衡。
            self.caller.msg("你失去平衡，需要时间恢复！")
            return      
      
        # [攻击/命中代码在此处...]
        self.caller.msg("你大力挥舞！你现在失去平衡。")   

        # 设置失去平衡标志
        self.caller.ndb.off_balance = True
            
        # 等待8秒钟才能恢复。在此期间，由于顶部的检查，我们将无法再次挥击。        
        utils.delay(8, self.recover)
    
    def recover(self):
        "这将在8秒后调用"
        del self.caller.ndb.off_balance            
        self.caller.msg("你恢复了平衡。")
```    

注意，在冷却时间之后，用户会收到一条消息，告诉他们现在可以再次挥击。

通过将 `off_balance` 标志存储在角色上（而不是在命令实例本身上），它也可以被其他命令访问。当你失去平衡时，其他攻击可能也不起作用。你还可以让敌人的命令检查你的 `off_balance` 状态以获得奖励。

## 让命令可以中止

可以想象，你可能希望在长时间运行的命令完成之前中止它。如果你正在制作盔甲，当怪物进入你的铁匠铺时，你可能希望停止制作。

你可以像上面实现“阻塞”命令一样实现这一点，只是相反。下面是一个可以通过开始战斗来中止的制作命令示例：

```python
from evennia import utils, default_cmds
    
class CmdCraftArmour(default_cmds.MuxCommand):
    """
    制作盔甲
    
    用法:
       craft <name of armour>
    
    这将制作一套盔甲，假设你有所有的组件和工具。执行其他操作（例如攻击某人）将中止制作过程。
    """
    key = "craft"
    locks = "cmd:all()"
    
    def func(self):
        "开始制作"

        if self.caller.ndb.is_crafting:
            self.caller.msg("你已经在制作了！")
            return 
        if self._is_fighting():
            self.caller.msg("你不能在战斗中开始制作！")
            return
            
        # [制作代码，检查组件、技能等]          

        # 开始制作
        self.caller.ndb.is_crafting = True
        self.caller.msg("你开始制作 ...")
        utils.delay(60, self.step1)
    
    def _is_fighting(self):
        "检查是否在战斗中。"
        if self.caller.ndb.is_fighting:                
            del self.caller.ndb.is_crafting 
            return True
      
    def step1(self):
        "盔甲构建的第一步"
        if self._is_fighting(): 
            return
        self.msg("你制作了盔甲的第一部分。")
        utils.delay(60, callback=self.step2)

    def step2(self):
        "盔甲构建的第二步"
        if self._is_fighting(): 
            return
        self.msg("你制作了盔甲的第二部分。")            
        utils.delay(60, self.step3)

    def step3(self):
        "盔甲构建的最后一步"
        if self._is_fighting():
            return          
    
        # [创建盔甲对象等代码]

        del self.caller.ndb.is_crafting
        self.msg("你完成了你的盔甲。")
    
    
# 中止制作的命令示例
    
class CmdAttack(default_cmds.MuxCommand):
    """
    攻击某人
    
    用法:
        attack <target>
    
    尝试对某人造成伤害。这将中止你可能正在进行的制作。
    """
    key = "attack"
    aliases = ["hit", "stab"]
    locks = "cmd:all()"
    
    def func(self):
        "实现命令"

        self.caller.ndb.is_fighting = True
    
        # [...]
```

上述代码创建了一个延迟的制作命令，该命令将逐步创建盔甲。如果在此过程中发出 `attack` 命令，它将设置一个标志，导致制作在下次尝试更新时被悄然取消。
