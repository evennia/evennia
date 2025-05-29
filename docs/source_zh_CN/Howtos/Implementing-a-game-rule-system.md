# 实现游戏规则系统

从代码的角度来看，创建一个在线角色扮演游戏最简单的方法就是直接拿一本纸质的 RPG 规则书，召集一群游戏管理员，并开始与登录的玩家运行场景。游戏管理员可以在电脑前掷骰子，并告诉玩家结果。这与传统的桌面游戏只相差一步，对员工的要求很高——即使他们非常投入，也不太可能全天候跟上整个游戏的进程。

因此，即使是最专注于角色扮演的游戏，也往往允许玩家在一定程度上自我调解。一种常见的方法是引入*编码系统*——也就是说，让计算机承担一些繁重的工作。一项基本的措施是增加一个在线掷骰子工具，以便每个人都可以进行掷骰，确保没有人作弊。这个层面上，你可以找到最基础的角色扮演 MUSH。

编码系统的优势在于，只要规则是公平的，计算机也是公平的——它不做任何判断，也没有个人恩怨（而且不可能被指控有此类问题）。此外，计算机不需要休息，无论玩家什么时候登录，它都可以保持在线。缺点是，编码系统不灵活，无法适应人类玩家在角色扮演中可能想到的非编程行动。出于这个原因，许多重角色扮演的 MUDs 采用了一种混合变体——他们在战斗和技能进阶等方面使用编码系统，但将角色扮演大部分留给自由形式，由游戏管理员监督。

最后，在另一端是较少或没有角色扮演的游戏，其中游戏机制（因此玩家的公平性）是最重要的方面。在此类游戏中，游戏内所有有价值的事件都是由代码产生的。这类游戏非常普遍，从砍杀类 MUD 到各种战术模拟游戏都有。

因此，你的第一个决定需要是你想要什么类型的系统。这个页面将尝试提供一些关于如何组织系统“编码”部分的想法，尽管其大小可能各不相同。

## 总体系统架构

我们强烈建议你将规则系统尽可能独立地编码。也就是说，不要将技能检查代码、种族加成计算、骰子修正等分散到你的游戏各处。

- 将你在规则书中需要查找的所有内容放入 `mygame/world` 中的一个模块。尽可能隐藏这些内容。把它想象成一个黑箱（或者是全知游戏管理员的代码表示）。你游戏的其余部分将向这个黑箱提问并获取答案。它如何得出这些结果不需在黑箱外部被了解。这样做使得你可以更轻松地在一个地方更改和更新内容。
- 仅存储每个游戏对象所需的最小信息。也就是说，如果你的角色需要健康值、技能列表等，存储这些在角色上——而不是存储如何掷骰或修改它们。
- 接下来是确定你希望如何在对象和角色上存储信息。你可以选择将信息存储为单独的 [属性](../Components/Attributes.md)，比如 `character.db.STR=34` 和 `character.db.Hunting_skill=20`。但你也可以使用某种自定义存储方式，如字典 `character.db.skills = {"Hunting":34, "Fishing":20, ...}`。一种更复杂的解决方案是查看 [Trait handler contrib](../Contribs/Contrib-Traits.md)。最后，你甚至可以使用 [自定义 Django 模型](../Concepts/Models.md)。哪个更好取决于你的游戏及其系统的复杂性。
- 创建一个清晰的 [API](https://en.wikipedia.org/wiki/Application_programming_interface) 供你的规则使用。也就是说，创建方法/函数，提供如角色和你想检查的技能。也就是说，你想要类似这样的东西：

    ```python
        from world import rules
        result = rules.roll_skill(character, "hunting")
        result = rules.roll_challenge(character1, character2, "swords")
    ```

你可能需要根据游戏的需要，让这些函数变得更复杂或更简单。例如，房间的属性可能会影响掷骰的结果（如果房间是黑暗的、着火的等）。确定你需要传入游戏机制模块的内容是了解你需要在引擎中添加的内容的好方法。

## 编码系统

受桌面角色扮演游戏的启发，大多数游戏系统模仿某种掷骰机制。为此，Evennia 提供了一个完整的 [掷骰子贡献](../Contribs/Contrib-Dice.md)。对于自定义实现，Python 提供了多种方法来使用其内置的 `random` 模块随机化结果。无论如何实现，我们将在本文中将确定结果的行动称为“掷骰”。

在自由形式的系统中，掷骰的结果仅与值进行比较，玩家（或游戏管理员）只需就其含义达成一致。在编码系统中，结果需要以某种方式被处理。许多事情可能是规则执行结果：

- 生命值可能会增加或减少，这可能会以各种方式影响角色。
- 可能需要增加经验值，如果使用基于等级的系统，玩家可能需要被告知他们已提升等级。
- 需要将房间范围的影响报告给房间，可能会影响房间中的每个人。

还有许多其他事情属于“编码系统”的范畴，包括天气、NPC 人工智能和游戏经济等。基本上，游戏管理员在桌面角色扮演游戏中控制的关于世界的一切都可以在某种程度上通过编码系统进行模拟。

## 规则模块示例

以下是一个简单的规则模块示例。我们假设我们的简单示例游戏如下：

- 角色只有四个数值：
    - 他们的 `level`，初始为 1。
    - 技能 `combat`，决定他们击中目标的能力，初始为 5 到 10 之间的值。
    - 他们的力量 `STR`，决定他们造成的伤害，初始为 1 到 10 之间的值。
    - 他们的生命值 `HP`，初始为 100。
- 当一个角色的 `HP` 达到 0 时，认为他们“被击败”。他们的生命值被重置，并获得一个失败消息（作为死亡代码的代替）。
- 能力作为简单的属性存储在角色上。
- “掷骰”是通过掷一个 100 面的骰子完成的。如果结果低于 `combat` 值，则表示成功，并进行伤害掷骰。伤害是通过掷一个 6 面骰子加上 `STR` 的值进行的（在这个例子中，我们忽略武器，假设 `STR` 是唯一的关键）。
- 每次成功的 `attack` 掷骰会获得 1-3 点经验值（`XP`）。每当 XP 的数量达到 `(level + 1) ** 2` 时，角色会升级。当升级时，角色的 `combat` 值增加 2 点，`STR` 增加 1（这作为一个真正进阶系统的代替）。

### 角色

角色类型类很简单。它放在 `mygame/typeclasses/characters.py` 中。那里已经有一个空的 `Character` 类，Evennia 将查找并使用它。

```python
from random import randint
from evennia import DefaultCharacter

class Character(DefaultCharacter):
    """
    自定义规则限制角色。我们在 1-10 之间随机化
    初始的技能和能力值。
    """
    def at_object_creation(self):
        "仅在首次创建时调用"
        self.db.level = 1
        self.db.HP = 100
        self.db.XP = 0
        self.db.STR = randint(1, 10)
        self.db.combat = randint(5, 10)
```

`@reload` 服务器以加载新的代码。然而，使用 `examine self` 并不会显示新的属性。这是因为 `at_object_creation` 钩子仅在*新*角色创建时调用。你的角色已经被创建，因此将不会拥有它们。要强制重载，请使用以下命令：

```
@typeclass/force/reset self
```

现在，`examine self` 命令将显示新的属性。

### 规则模块

这是一个位于 `mygame/world/rules.py` 的模块。

```python
from random import randint

def roll_hit():
    "掷 1d100"
    return randint(1, 100)

def roll_dmg():
    "掷 1d6"
    return randint(1, 6)

def check_defeat(character):
    "检查角色是否被 '击败'。"
    if character.db.HP <= 0:
       character.msg("你倒下了，被击败了！")
       character.db.HP = 100   # 重置

def add_XP(character, amount):
    "将 XP 添加到角色，跟踪等级增加。"
    character.db.XP += amount
    if character.db.XP >= (character.db.level + 1) ** 2:
        character.db.level += 1
        character.db.STR += 1
        character.db.combat += 2
        character.msg(f"你现在是 {character.db.level} 级了！")

def skill_combat(*args):
    """
    确定战斗的结果。掷骰低于其战斗技能的
    并且高于对手的掷骰，则击中。
    """
    char1, char2 = args
    roll1, roll2 = roll_hit(), roll_hit()
    failtext_template = "你被 {attacker} 击中，受到了 {dmg} 点伤害！"
    wintext_template = "你击中 {target}，造成了 {dmg} 点伤害！"
    xp_gain = randint(1, 3)
    if char1.db.combat >= roll1 > roll2:
        # char 1 击中
        dmg = roll_dmg() + char1.db.STR
        char1.msg(wintext_template.format(target=char2, dmg=dmg))
        add_XP(char1, xp_gain)
        char2.msg(failtext_template.format(attacker=char1, dmg=dmg))
        char2.db.HP -= dmg
        check_defeat(char2)
    elif char2.db.combat >= roll2 > roll1:
        # char 2 击中
        dmg = roll_dmg() + char2.db.STR
        char1.msg(failtext_template.format(attacker=char2, dmg=dmg))
        char1.db.HP -= dmg
        check_defeat(char1)
        char2.msg(wintext_template.format(target=char1, dmg=dmg))
        add_XP(char2, xp_gain)
    else:
        # 平局
        drawtext = "你们都无法找到破绽。"
        char1.msg(drawtext)
        char2.msg(drawtext)

SKILLS = {"combat": skill_combat}

def roll_challenge(character1, character2, skillname):
    """
    根据给定的技能名称确定两名角色之间的技能挑战的结果。
    """
    if skillname in SKILLS:
        SKILLS[skillname](character1, character2)
    else:
        raise RunTimeError(f"找不到技能名称 {skillname}。")
```

这几项功能实现了我们简单规则系统的全部内容。我们有一个函数来检查“被击败”条件并将 `HP` 重置为 100。我们定义了一个通用的“技能”函数。可以用相同的签名添加多个技能；我们的 `SKILLS` 字典使得无论它们的实际函数名称是什么都能轻松查找技能。最后，访问函数 `roll_challenge` 只是选择技能并获取结果。

在这个例子中，技能函数实际上做了很多——它不仅掷骰结果，还通过 `character.msg()` 调用通知每个人他们的结果。

以下是游戏命令中使用的示例：

```python
from evennia import Command
from world import rules

class CmdAttack(Command):
    """
    攻击对手

    用法：
      attack <target>

    这将攻击同一房间中的目标，用你赤手空拳造成伤害。
    """
    def func(self):
        "实现战斗"

        caller = self.caller
        if not self.args:
            caller.msg("你需要选择一个目标进行攻击。")
            return

        target = caller.search(self.args)
        if target:
            rules.roll_challenge(caller, target, "combat")
```

注意这个命令是多么简单，以及你可以让它多么通用。通过扩展这个功能，可以轻松提供任何数量的战斗命令——你可以轻松地掷骰挑战并选择不同的技能进行检查。如果你有一天决定要改变命中率的计算方式，你不需要更改每个命令，只需更改 `rules` 模块中的单个 `roll_hit` 函数即可。
