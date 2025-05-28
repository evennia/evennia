# 回合制战斗系统

本教程提供了一个完整的、尽管简化的 Evennia 战斗系统示例。它受到[邮件列表](https://groups.google.com/forum/#!msg/evennia/wnJNM2sXSfs/-dbLRrgWnYMJ)上讨论的启发。

## 战斗系统概念概述

大多数 MUD 将使用某种形式的战斗系统。主要有几种变体：

- **自由形式** - 实现最简单的战斗，常见于 MUSH 风格的角色扮演游戏。这意味着系统仅提供掷骰器，或者可能有命令来比较技能并给出结果。掷骰是用来根据游戏规则解决战斗并指导场景的。可能需要一名游戏管理员来解决规则争议。
  
- **快速反应** - 这是传统的 MUD 砍杀风格战斗。在快速反应系统中，正常的“移动和探索模式”和“战斗模式”之间往往没有区别。你输入攻击命令，系统将计算攻击是否命中以及造成了多少伤害。通常攻击命令会有某种超时状态或恢复/平衡的概念，以减少反复发送攻击命令或客户端脚本的优势。而最简单的系统只需反复输入 `kill <target>`，更复杂的快速反应系统则包括防御姿态和战术位置等内容。

- **回合制** - 回合制系统意味着系统会暂停，以确保所有战斗者在继续之前可以选择他们的行动。在某些系统中，输入的行动会立即执行（像快速反应系统），而在其他系统中，解决在回合结束时同时发生。回合制系统的缺点是，游戏必须切换到“战斗模式”，并且还需要特别注意如何处理新战斗者和时间的推移。优点是成功不依赖于输入速度或设置快速客户端宏。这可能允许在战斗中进行动作表演，这对重角色扮演的游戏是一个优势。

要实现自由形式的战斗系统，你只需要一个掷骰器和一本角色扮演规则书。请参阅 [contrib/dice.py](../Contribs/Contrib-Dice.md) 获取示例掷骰器。要实现快速反应系统，你基本上需要一些战斗[命令](../Components/Commands.md)，可能是带有[冷却时间](./Howto-Command-Cooldown.md)的命令。你还需要一个[游戏规则模块](./Implementing-a-game-rule-system.md)来利用它。我们将专注于回合制战斗系统。

## 教程概述

本教程将实现稍微复杂一点的回合制战斗系统。我们的示例具有以下特性：

- 战斗通过 `attack <target>` 启动，这将进入战斗模式。
- 角色可以使用 `attack <target>` 加入正在进行的战斗。
- 每回合每个战斗角色将输入两个命令，他们的内部顺序很重要，并且将按给定顺序逐一比较。使用 `say` 和 `pose` 是自由的。
- 命令（在我们的示例中）很简单；他们可以 `hit <target>`（击打目标）、`feint <target>`（佯攻目标）或 `parry <target>`（格挡目标）。他们还可以选择 `defend`（防御），作为一种通用被动防御。最后，他们还可以选择 `disengage/flee`（脱战/逃跑）。
- 攻击使用经典的[石头剪刀布](https://en.wikipedia.org/wiki/Rock-paper-scissors)机制来决定成功：`hit` 击败 `feint`，`feint` 击败 `parry`，`parry` 击败 `hit`。`defend` 是一种通用的被动行动，有一定几率能够抵挡 `hit`（仅限此情况）。
- `disengage/flee` 必须连续输入两次，并且仅在此期间没有 `hit` 攻击到他们时才会成功。如果成功，他们将离开战斗模式。
- 一旦每个玩家输入了两个命令，所有命令将按顺序解决，结果将被报告。然后开始新的一回合。
- 如果玩家反应太慢，回合将超时，未设置的命令将设置为 `defend`。

为了创建战斗系统，我们将需要以下组件：

- 一个战斗处理器。这个系统的主要机制。它是为每场战斗创建的一个[脚本](../Components/Scripts.md)对象。它不被分配给特定对象，而是由战斗角色共享，并处理所有战斗信息。由于脚本是数据库实体，这也意味着战斗不会受到服务器重载的影响。

- 一个战斗[命令集](../Components/Command-Sets.md)，包含战斗所需的相关命令，例如各种攻击/防御选项及 `flee/disengage`（脱战/逃跑）以离开战斗模式的命令。

- 一个规则解析系统。有关如何制作此类模块的基础知识在[规则系统教程](./Implementing-a-game-rule-system.md)中进行了描述。我们将在这里简述这样一个模块，以实现回合结束时的战斗解析。

- 一个 `attack` [命令](../Components/Commands.md)，用来启动战斗模式。它将添加到默认命令集中。它将创建战斗处理器并将角色添加到其中，同时将战斗命令集分配给角色。

## 战斗处理器

_战斗处理器_ 是作为独立的 [脚本](../Components/Scripts.md) 实现的。当第一个角色决定攻击另一角色时，会创建该脚本，并在没有人再战斗时被删除。每个处理器代表一个战斗实例，仅此一场战斗。每个战斗实例可以容纳任意数量的角色，但每个角色一次只能参与一场战斗（玩家需要从第一场战斗中脱战才能加入另一场）。

我们不将此脚本存储在任何特定角色上，因为任何角色都可能随时离开战斗。相反，脚本保存对所有参与战斗的角色的引用。另一方面，所有角色都持有对当前战斗处理器的反向引用。虽然我们在这里没有太多使用这个特性，但这可能允许角色上的战斗命令直接访问和更新战斗处理器状态。

_注意：实现战斗处理器的另一种方法是使用常规 Python 对象，并使用[TickerHandler](../Components/TickerHandler.md)来处理时间。这将需要为角色添加自定义钩子方法或实现自定义 TickerHandler 类的子类以跟踪回合。尽管 TickerHandler 使用起来简单，但在这种情况下，脚本提供更多的功能。_

以下是基础战斗处理器。假设我们的游戏文件夹名为 `mygame`，我们将它存储在 `mygame/typeclasses/combat_handler.py` 中：

```python
# mygame/typeclasses/combat_handler.py

import random
from evennia import DefaultScript
from world.rules import resolve_combat

class CombatHandler(DefaultScript):
    """
    这是战斗处理器的实现。
    """

    # 标准脚本钩子 

    def at_script_creation(self):
        "脚本首次创建时调用"

        self.key = f"combat_handler_{random.randint(1, 1000)}"
        self.desc = "handles combat"
        self.interval = 60 * 2  # 两分钟超时
        self.start_delay = True
        self.persistent = True   

        # 存储所有战斗者
        self.db.characters = {}
        # 存储每回合的所有行动
        self.db.turn_actions = {}
        # 每个战斗者输入的行动数量
        self.db.action_count = {}

    def _init_character(self, character):
        """
        初始化处理器的反向引用
        和战斗命令集到角色上
        """
        character.ndb.combat_handler = self
        character.cmdset.add("commands.combat.CombatCmdSet")

    def _cleanup_character(self, character):
        """
        从处理器中移除角色，并清除
        反向引用和命令集
        """
        dbref = character.id 
        del self.db.characters[dbref]
        del self.db.turn_actions[dbref]
        del self.db.action_count[dbref]        
        del character.ndb.combat_handler
        character.cmdset.delete("commands.combat.CombatCmdSet")

    def at_start(self):
        """
        无论是在首次启动时还是在服务器重启后
        脚本被重启时都会调用。我们需要将此战斗处理器重新分配给
        所有角色，以及重新分配命令集。
        """
        for character in self.db.characters.values():
            self._init_character(character)

    def at_stop(self):
        "在脚本被停止/销毁之前调用。"
        for character in list(self.db.characters.values()):
            # 注意：上面的 list() 调用使列表与数据库断开连接
            self._cleanup_character(character)

    def at_repeat(self):
        """
        每 self.interval 秒（回合超时）被调用
        或在 force_repeat 被调用时（因为每个人都输入了他们的
        命令）。我们通过检查
        `normal_turn_end` NAttribute 的存在来知道这一点，在调用
        force_repeat 之前会设置。
        
        """
        if self.ndb.normal_turn_end:
            # 我们到这里是因为回合正常结束
            # （调用了 force_repeat） - 不输出消息
            del self.ndb.normal_turn_end
        else:        
            # 回合超时
            self.msg_all("回合计时器超时。继续。")
        self.end_turn()

    # 战斗处理器方法

    def add_character(self, character):
        "将战斗者添加到处理器"
        dbref = character.id
        self.db.characters[dbref] = character        
        self.db.action_count[dbref] = 0
        self.db.turn_actions[dbref] = [("defend", character, None),
                                       ("defend", character, None)]
        # 设置反向引用
        self._init_character(character)
       
    def remove_character(self, character):
        "从处理器中移除战斗者"
        if character.id in self.db.characters:
            self._cleanup_character(character)
        if not self.db.characters:
            # 如果没有更多角色在战斗，删除此处理器
            self.stop()

    def msg_all(self, message):
        "将消息发送给所有战斗者"
        for character in self.db.characters.values():
            character.msg(message)

    def add_action(self, action, character, target):
        """
        由战斗命令调用以向处理器注册行动。

         action - 标识行动的字符串，如 "hit" 或 "parry"
         character - 执行行动的角色
         target - 目标角色或 None

        行动存储在一个字典中，以每个角色为键，每个角色保持最多 2 个行动的列表。行动被存储为
        一个元组 (character, action, target)。 
        """
        dbref = character.id
        count = self.db.action_count[dbref]
        if 0 <= count <= 1: # 仅允许 2 个行动            
            self.db.turn_actions[dbref][count] = (action, character, target)
        else:        
            # 如果我们已经使用了太多行动，报告错误
            return False
        self.db.action_count[dbref] += 1
        return True

    def check_end_turn(self):
        """
        由命令调用以最终触发
        回合解析。我们检查每个人是否都添加了所有行动；如果是，
        则强制脚本立即重复（这将调用
        `self.at_repeat()` 同时重置所有计时器）。 
        """
        if all(count > 1 for count in self.db.action_count.values()):
            self.ndb.normal_turn_end = True
            self.force_repeat() 

    def end_turn(self):
        """
        解析所有行动，通过调用规则模块。 
        然后重置一切并开始下一个回合。它
        通常在 at_repeat() 中调用。
        """        
        resolve_combat(self, self.db.turn_actions)

        if len(self.db.characters) < 2:
            # 在战斗中角色少于 2 个，删除此处理器
            self.msg_all("战斗已结束")
            self.stop()
        else:
            # 在下一个回合之前重置计数器
            for character in self.db.characters.values():
                self.db.characters[character.id] = character
                self.db.action_count[character.id] = 0
                self.db.turn_actions[character.id] = [("defend", character, None),
                                                  ("defend", character, None)]
            self.msg_all("下一个回合开始 ...")
```

这实现了我们战斗处理器的所有有用属性。这个脚本将在重启时存活下来，并将在重新上线时自动重新赋值。甚至当前的战斗状态也应该保持不变，因为每个回合都会在属性中保存。重要的是要注意使用脚本的标准 `at_repeat` 钩子和 `force_repeat` 方法来结束每个回合。这允许所有内容通过相同的机制进行，代码重复最少。

在此处理器中缺少的方法是让玩家查看他们设置的行动或在最后一个角色添加行动之前更改他们的行动（但在此之前）。我们将此留作练习。

## 战斗命令

我们的战斗命令——在战斗中可用的命令——（在我们示例中）非常简单。在完整的实现中，可用的命令可能由玩家持有的武器或他们掌握的技能决定。

我们在 `mygame/commands/combat.py` 中创建它们。

```python
# mygame/commands/combat.py

from evennia import Command

class CmdHit(Command):
    """
    打击敌人

    用法：
      hit <target>

    用你当前的武器袭击目标敌人。
    """
    key = "hit"
    aliases = ["strike", "slash"]
    help_category = "combat"

    def func(self):
        "实现命令"
        if not self.args:
            self.caller.msg("用法: hit <target>")
            return 
        target = self.caller.search(self.args)
        if not target:
            return
        ok = self.caller.ndb.combat_handler.add_action("hit", 
                                                       self.caller, 
                                                       target) 
        if ok:
            self.caller.msg("你将 'hit' 添加到战斗队列")
        else:
            self.caller.msg("每回合只能排队两个行动！")
 
        # 告诉处理器检查回合是否结束
        self.caller.ndb.combat_handler.check_end_turn()
```

其他命令 `CmdParry`、`CmdFeint`、`CmdDefend` 和 `CmdDisengage` 看起来基本相同。我们还应该添加一个自定义 `help` 命令来列出所有可用的战斗命令及其作用。

我们只需将它们全部放入命令集。我们在同一模块的末尾这样做：

```python
# mygame/commands/combat.py

from evennia import CmdSet
from evennia import default_cmds

class CombatCmdSet(CmdSet):
    key = "combat_cmdset"
    mergetype = "Replace"
    priority = 10 
    no_exits = True

    def at_cmdset_creation(self):
        self.add(CmdHit())
        self.add(CmdParry())
        self.add(CmdFeint())
        self.add(CmdDefend())
        self.add(CmdDisengage())    
        self.add(CmdHelp())
        self.add(default_cmds.CmdPose())
        self.add(default_cmds.CmdSay())
```

## 规则模块

实现规则模块的通用方法可以在[规则系统教程](./Implementing-a-game-rule-system.md)中找到。适当的解析可能要求我们更改角色以存储诸如力量、武器技能等。当角色对象持有统计信息以影响其技能时，它们选择的武器将影响其选择，同时也能够失去生命等。

在每个回合内，有“子回合”，每个子回合由每个角色的一项行动组成。每个子回合内的行动是同时发生的，只有在所有行动被解析后，我们才能进行下一个子回合（或结束整个回合）。

_注意：在我们简单示例中，子回合彼此之间没有相互影响（除了 `disengage/flee`），而且的确没有任何效果携带到下一个回合中。回合制系统真正的力量在于可以在这里添加真正的战术可能性；例如，如果你的攻击被格挡，那么你的下一个行动会处于不利状态。成功的佯攻将为随后的攻击打开机会等等。_

我们的石头剪刀布设置如下工作：

- `hit` 击败 `feint` 和 `flee/disengage`。它有一定的随机几率对抗 `defend` 失败。
- `parry` 击败 `hit`。
- `feint` 击败 `parry`，然后算作 `hit`。
- `defend` 无效，但有抵挡 `hit` 的几率。
- `flee/disengage` 必须连续成功两次（即在回合中没有被 `hit` 击中）。如果成功，角色将离开战斗。

```python
# mygame/world/rules.py

import random


# 消息 

def resolve_combat(combat_handler, actiondict):
    """
    由战斗处理器调用
    actiondict 是一个字典，包含每个角色的两项行动
    的列表：
    {char.id:[(action1, char, target), (action2, char, target)], ...}
    """
    flee = {}  # 跟踪每个角色的逃跑命令数量
    for isub in range(2):
        # 循环子回合
        messages = []
        for subturn in (sub[isub] for sub in actiondict.values()):
            # 为每个角色解析子回合
            action, char, target = subturn
            if target:
                taction, tchar, ttarget = actiondict[target.id][isub]
            if action == "hit":
                if taction == "parry" and ttarget == char:
                    messages.append(
                        f"{char} 尝试击打 {tchar}，但 {tchar} 挡住了攻击！"
                    )
                elif taction == "defend" and random.random() < 0.5:
                    messages.append(
                        f"{tchar} 防御住了 {char} 的攻击。"
                    )
                elif taction == "flee":
                    flee[tchar] = -2
                    messages.append(
                        f"{char} 阻止了 {tchar} 脱离战斗，给予了重击！"
                    )
                else:
                    messages.append(
                        f"{char} 击中 {tchar}，突破了他们的 {taction}！"
                    )
            elif action == "parry":
                if taction == "hit":
                    messages.append(f"{char} 挡住了 {tchar} 的攻击。")
                elif taction == "feint":
                    messages.append(
                        f"{char} 尝试防御，但是 {tchar} 佯攻并击中了！"
                    )
                else:
                    messages.append(f"{char} 防御无效。")
            elif action == "feint":
                if taction == "parry":
                    messages.append(
                        f"{char} 越过 {tchar} 的防御，成功击中！"
                    )
                elif taction == "hit":
                    messages.append(f"{char} 佯攻，但被 {tchar} 击败！")
                else:
                    messages.append(f"{char} 佯攻无效。")
            elif action == "defend":
                messages.append(f"{char} 选择防御。")
            elif action == "flee":
                if char in flee:
                    flee[char] += 1
                else:
                    flee[char] = 1
                    messages.append(
                        f"{char} 尝试脱离战斗（需要连续两回合成功）"
                    )

        # 回显每个子回合的结果
        combat_handler.msg_all("\n".join(messages))

    # 在两个子回合结束时，测试是否有角色成功逃走
    for (char, fleevalue) in flee.items():
        if fleevalue == 2:
            combat_handler.msg_all(f"{char} 从战斗中撤回。")
            combat_handler.remove_character(char)
```

为了简单起见（并节省空间），该示例规则模块实际上解析每次交互两次——首先在每个角色时，然后再处理目标。同时，由于我们在这里使用了战斗处理器的 `msg_all` 方法，系统输出将变得非常冗余。为了清理，大家可以想象追踪所有可能的交互，以确保每个配对只处理和报告一次。

## 战斗发起命令

这是我们需要的最后一个组件，一个命令以启动战斗。这将把所有内容结合在一起。我们将其与其它战斗命令一起存储。

```python
# mygame/commands/combat.py

from evennia import create_script


class CmdAttack(Command):
    """
    启动战斗

    用法：
      attack <target>

    这将与 <target> 启动战斗。如果 <target>
    已经在战斗中，你将加入战斗。 
    """
    key = "attack"
    help_category = "General"

    def func(self):
        "处理命令"
        if not self.args:
            self.caller.msg("用法：attack <target>")
            return
        target = self.caller.search(self.args)
        if not target:
            return
        # 设置战斗
        if target.ndb.combat_handler:
            # 目标已经在战斗中 - 加入它            
            target.ndb.combat_handler.add_character(self.caller)
            target.ndb.combat_handler.msg_all(f"{self.caller} 加入了战斗！")
        else:
            # 创建新的战斗处理器
            chandler = create_script("combat_handler.CombatHandler")
            chandler.add_character(self.caller)
            chandler.add_character(target)
            self.caller.msg(f"你攻击 {target}！你已进入战斗。")
            target.msg(f"{self.caller} 攻击了你！你已进入战斗。")       
```

`attack` 命令不会进入战斗命令集，而是进入默认命令集。如果你不确定如何操作，请参阅[添加命令教程](Beginner-Tutorial/Part1/Beginner-Tutorial-Adding-Commands.md)。

## 扩展示例

此时，你应当有一个简单但灵活的回合制战斗系统。我们在这个示例中采取了一些快捷方式和简化。玩家的输出可能在战斗中过于冗长，并且在周围信息的显示上过于有限。改变命令的方法或列出命令，查看谁在战斗中等信息可能是必要的——这将需要针对每个游戏和风格进行测试。此外，目前没有信息显示给同一房间中的其他人，可能应该将一些较少的详细信息回显给房间，以展示正在发生的事情。
