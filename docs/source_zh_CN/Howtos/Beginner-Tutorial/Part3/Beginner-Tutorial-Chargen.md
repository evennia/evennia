# 角色生成

在之前的课程中，我们已经确定了角色的样子。现在，我们需要给玩家一个创建角色的机会。

## 工作原理

一个全新的Evennia安装在你登录时会自动创建一个与账户同名的新角色。这既快速又简单，模仿了旧的MUD风格。你可以想象这样做，然后在原地自定义角色。

不过，我们会更复杂一些。我们希望用户在登录时能够使用菜单创建角色。

我们通过编辑`mygame/server/conf/settings.py`并添加以下行来实现这一点：

```python
AUTO_CREATE_CHARACTER_WITH_ACCOUNT = False
```

这样做后，使用新账户连接游戏时会进入“OOC”模式。`look`的OOC版本（位于Account cmdset中）会显示可用角色的列表（如果有的话）。你还可以输入`charcreate`来创建一个新角色。`charcreate`是Evennia自带的一个简单命令，只需让你用给定的名称和描述创建一个新角色。我们稍后会修改它以启动我们的角色生成。现在我们只需记住，这就是我们将如何开始菜单。

在_Knave_中，大多数角色生成是随机的。这意味着本教程可以非常紧凑，同时仍能展示基本思想。我们将创建一个如下所示的菜单：

```
Silas

STR +1
DEX +2
CON +1
INT +3
WIS +1
CHA +2

你身材瘦长，面孔凹陷，头发肮脏，讲话气喘吁吁，穿着异国服装。
你曾是一个草药师，但你被追捕，最终成为了一个流浪者。你诚实但也多疑。你是中立阵营。

你的物品：
锁子甲，口粮，口粮，剑，火把，火把，火把，火把，火把，火种盒，凿子，哨子

----------------------------------------------------------------------------------------
1. 更改你的名字
2. 交换两个能力值（一次）
3. 接受并创建角色
```

如果你选择1，你会进入一个新的菜单节点：

```
你当前的名字是Silas。输入一个新名字或留空以中止。
-----------------------------------------------------------------------------------------
```

你现在可以输入一个新名字。按下回车后，你将返回到第一个菜单节点，显示你的角色，现在有了新名字。

如果你选择2，你会进入另一个菜单节点：

```
你当前的能力：

STR +1
DEX +2
CON +1
INT +3
WIS +1
CHA +2

你可以交换两个能力的值。
你只能这样做一次，所以请谨慎选择！

要交换例如STR和INT的值，请输入“STR INT”。留空以中止。
------------------------------------------------------------------------------------------
```

如果你在这里输入`WIS CHA`，WIS将变为`+2`，CHA将变为`+1`。然后你将再次返回到主节点以查看你的新角色，但这次交换选项将不再可用（你只能这样做一次）。

如果你最终选择“接受并创建角色”选项，角色将被创建，你将离开菜单：

```
角色已创建！
```

## 随机表

```{sidebar}
完整的Knave随机表可以在
[evennia/contrib/tutorials/evadventure/random_tables.py](../../../api/evennia.contrib.tutorials.evadventure.random_tables.md)中找到。
```

> 创建一个新模块`mygame/evadventure/random_tables.py`。

由于_Knave_的大多数角色生成是随机的，我们将需要从_Knave_规则书中掷骰随机表。虽然我们在[规则教程](./Beginner-Tutorial-Rules.md)中添加了在随机表上掷骰的功能，但我们还没有添加相关的表。

```python
# 在 mygame/evadventure/random_tables.py 中

chargen_tables = {
    "physique": [
        "athletic", "brawny", "corpulent", "delicate", "gaunt", "hulking", "lanky",
        "ripped", "rugged", "scrawny", "short", "sinewy", "slender", "flabby",
        "statuesque", "stout", "tiny", "towering", "willowy", "wiry",
    ],
    "face": [
        "bloated", "blunt", "bony", # ...
    ], # ...
}
```

这些表只是从_Knave_规则中复制的。我们将这些方面分组到一个字典`character_generation`中，以将角色生成专用表与我们将在此处保留的其他随机表分开。

## 存储菜单状态

```{sidebar}
角色生成的完整实现可以在
[evennia/contrib/tutorials/evadventure/chargen.py](../../../api/evennia.contrib.tutorials.evadventure.chargen.md)中找到。
```

> 创建一个新模块`mygame/evadventure/chargen.py`。

在角色生成过程中，我们将需要一个实体来存储/保留更改，就像一个“临时角色纸”一样。

```python
# 在 mygame/evadventure/chargen.py 中

from .random_tables import chargen_tables
from .rules import dice

class TemporaryCharacterSheet:

    def _random_ability(self):
        return min(dice.roll("1d6"), dice.roll("1d6"), dice.roll("1d6"))

    def __init__(self):
        self.ability_changes = 0  # 我们尝试交换能力的次数

        # 名字可能会在以后修改
        self.name = dice.roll_random_table("1d282", chargen_tables["name"])

        # 基础属性值
        self.strength = self._random_ability()
        self.dexterity = self._random_ability()
        self.constitution = self._random_ability()
        self.intelligence = self._random_ability()
        self.wisdom = self._random_ability()
        self.charisma = self._random_ability()

        # 物理属性（仅用于角色扮演目的）
        physique = dice.roll_random_table("1d20", chargen_tables["physique"])
        face = dice.roll_random_table("1d20", chargen_tables["face"])
        skin = dice.roll_random_table("1d20", chargen_tables["skin"])
        hair = dice.roll_random_table("1d20", chargen_tables["hair"])
        clothing = dice.roll_random_table("1d20", chargen_tables["clothing"])
        speech = dice.roll_random_table("1d20", chargen_tables["speech"])
        virtue = dice.roll_random_table("1d20", chargen_tables["virtue"])
        vice = dice.roll_random_table("1d20", chargen_tables["vice"])
        background = dice.roll_random_table("1d20", chargen_tables["background"])
        misfortune = dice.roll_random_table("1d20", chargen_tables["misfortune"])
        alignment = dice.roll_random_table("1d20", chargen_tables["alignment"])

        self.desc = (
            f"You are {physique} with a {face} face, {skin} skin, {hair} hair, {speech} speech,"
            f" and {clothing} clothing. You were a {background.title()}, but you were"
            f" {misfortune} and ended up a knave. You are {virtue} but also {vice}. You are of the"
            f" {alignment} alignment."
        )

        #
        self.hp_max = max(5, dice.roll("1d8"))
        self.hp = self.hp_max
        self.xp = 0
        self.level = 1

        # 随机装备
        self.armor = dice.roll_random_table("1d20", chargen_tables["armor"])

        _helmet_and_shield = dice.roll_random_table("1d20", chargen_tables["helmets and shields"])
        self.helmet = "helmet" if "helmet" in _helmet_and_shield else "none"
        self.shield = "shield" if "shield" in _helmet_and_shield else "none"

        self.weapon = dice.roll_random_table("1d20", chargen_tables["starting weapon"])

        self.backpack = [
            "ration",
            "ration",
            dice.roll_random_table("1d20", chargen_tables["dungeoning gear"]),
            dice.roll_random_table("1d20", chargen_tables["dungeoning gear"]),
            dice.roll_random_table("1d20", chargen_tables["general gear 1"]),
            dice.roll_random_table("1d20", chargen_tables["general gear 2"]),
        ]
```

这里我们遵循_Knave_规则书来随机化能力、描述和装备。`dice.roll()`和`dice.roll_random_table`方法现在变得非常有用！这里的一切都应该很容易理解。

与基础_Knave_的主要区别在于，我们制作了一个“起始武器”的表（在Knave中你可以选择你喜欢的任何东西）。

我们还初始化了`.ability_changes = 0`。Knave只允许我们交换两个能力的值_一次_。我们将用它来知道是否已经完成。

### 显示角色纸

现在我们有了临时角色纸，我们应该让它易于可视化。

```python
# 在 mygame/evadventure/chargen.py 中

_TEMP_SHEET = """
{name}

STR +{strength}
DEX +{dexterity}
CON +{constitution}
INT +{intelligence}
WIS +{wisdom}
CHA +{charisma}

{description}

你的物品：
{equipment}
"""

class TemporaryCharacterSheet:

    # ...

    def show_sheet(self):
        equipment = (
            str(item)
            for item in [self.armor, self.helmet, self.shield, self.weapon] + self.backpack
            if item
        )

        return _TEMP_SHEET.format(
            name=self.name,
            strength=self.strength,
            dexterity=self.dexterity,
            constitution=self.constitution,
            intelligence=self.intelligence,
            wisdom=self.wisdom,
            charisma=self.charisma,
            description=self.desc,
            equipment=", ".join(equipment),
        )

```

新的`show_sheet`方法从临时角色纸中收集数据，并以漂亮的形式返回它。制作一个像`_TEMP_SHEET`这样的“模板”字符串可以让你在以后想要更改外观时更容易更改内容。

### 应用角色

一旦我们对角色满意，我们需要用我们选择的统计数据实际创建它。这有点复杂。

```python
# 在 mygame/evadventure/chargen.py 中

# ...

from .characters import EvAdventureCharacter
from evennia import create_object
from evennia.prototypes.spawner import spawn


class TemporaryCharacterSheet:

    # ...

    def apply(self):
        # 用给定的能力创建角色对象
        new_character = create_object(
            EvAdventureCharacter,
            key=self.name,
            attrs=(
                ("strength", self.strength),
                ("dexterity", self.dexterity),
                ("constitution", self.constitution),
                ("intelligence", self.intelligence),
                ("wisdom", self.wisdom),
                ("charisma", self.wisdom),
                ("hp", self.hp),
                ("hp_max", self.hp_max),
                ("desc", self.desc),
            ),
        )
        # 生成装备（在它工作之前需要创建原型）
        if self.weapon:
            weapon = spawn(self.weapon)
            new_character.equipment.move(weapon)
        if self.shield:
            shield = spawn(self.shield)
            new_character.equipment.move(shield)
        if self.armor:
            armor = spawn(self.armor)
            new_character.equipment.move(armor)
        if self.helmet:
            helmet = spawn(self.helmet)
            new_character.equipment.move(helmet)

        for item in self.backpack:
            item = spawn(item)
            new_character.equipment.store(item)

        return new_character
```

我们使用`create_object`创建一个新的`EvAdventureCharacter`。我们将所有相关数据从临时角色纸中传入。这是这些成为实际角色的时候。

```{sidebar}
原型基本上是一个描述对象应该如何创建的`dict`。由于它只是代码的一部分，可以存储在Python模块中，并用于快速_生成_（创建）这些原型中的内容。
```

每件装备都是一个独立的对象。我们将在这里假设所有游戏物品都被定义为[原型](../../../Components/Prototypes.md)，其键为其名称，如“剑”、“锁子甲”等。

我们实际上还没有创建这些原型，所以现在我们需要假设它们在那里。一旦一件装备被生成，我们确保将其移动到我们在[装备课程](./Beginner-Tutorial-Equipment.md)中创建的`EquipmentHandler`中。

## 初始化EvMenu

Evennia带有一个基于[命令集](../../../Components/Command-Sets.md)的完整菜单生成系统，称为[EvMenu](../../../Components/EvMenu.md)。

```python
# 在 mygame/evadventure/chargen.py 中

from evennia import EvMenu

# ...

# 角色生成菜单


# 这部分放在模块底部

def start_chargen(caller, session=None):
    """
    这是从命令启动角色生成的起点。

    """

    menutree = {}  # TODO!

    # 这将生成角色的所有随机组件
    tmp_character = TemporaryCharacterSheet()

    EvMenu(
        caller,
        menutree,
        session=session,
        startnode="node_chargen",
        startnode_input=("", {"tmp_character": tmp_character}),
    )

```

这个第一个函数是我们将从其他地方调用的（例如从自定义的`charcreate`命令）以启动菜单。

它接受`caller`（想要启动菜单的人）和一个`session`参数。后者将帮助跟踪我们正在使用的客户端连接（根据Evennia设置，你可以使用多个客户端连接）。

我们创建一个`TemporaryCharacterSheet`并将所有这些传入`EvMenu`。`startnode`和`startnode_input`关键字确保进入菜单时进入“node_chargen”节点（我们将在下面创建）并用提供的参数调用它。

一旦发生这种情况，用户将进入菜单，不需要进一步的步骤。

`menutree`是我们接下来要创建的。它描述了可以跳转到的菜单“节点”。

## 主节点：选择要做的事情

这是第一个菜单节点。它将作为一个中心枢纽，可以从中选择不同的操作。

```python
# 在 mygame/evadventure/chargen.py 中

# ...

# 在模块末尾，但在`start_chargen`函数之前

def node_chargen(caller, raw_string, **kwargs):

    tmp_character = kwargs["tmp_character"]

    text = tmp_character.show_sheet()

    options = [
        {
           "desc": "更改你的名字",
           "goto": ("node_change_name", kwargs)
        }
    ]
    if tmp_character.ability_changes <= 0:
        options.append(
            {
                "desc": "交换两个能力值（一次）",
                "goto": ("node_swap_abilities", kwargs),
            }
        )
    options.append(
        {
            "desc": "接受并创建角色",
            "goto": ("node_apply_character", kwargs)
        },
    )

    return text, options

# ...
```

这里有很多要解析的内容！在Evennia中，命名节点函数为`node_*`是惯例。虽然不是必需的，但它有助于你跟踪什么是节点，什么不是。

每个菜单节点都应该接受`caller, raw_string, **kwargs`作为参数。这里的`caller`是你传入`EvMenu`调用的`caller`。`raw_string`是用户为了_进入此节点_而给出的输入，因此当前为空。`**kwargs`是传入`EvMenu`的所有额外关键字参数。它们也可以在节点之间传递。在这种情况下，我们将关键字`tmp_character`传递给`EvMenu`。我们现在在节点中拥有临时角色纸！

> 请注意，上面我们使用`startnode="node_chargen"`和元组`startnode_input=("", {"tmp_character": tmp_character})`创建了菜单。假设我们将上述函数注册为节点`"node_chargen"`，它将首先被调用为`node_chargen(caller, "", tmp_character=tmp_character)`（EvMenu会自行添加`caller`）。这是我们在菜单启动时将外部数据传入菜单的一种方式。

一个`EvMenu`节点必须始终返回两样东西——`text`和`options`。`text`是用户在查看此节点时将看到的内容。`options`是，从这里开始到其他地方应该呈现的选项。

对于文本，我们只是获取临时角色纸的漂亮打印。单个选项被定义为一个像这样的`dict`：

```python
{
    "key": ("name". "alias1", "alias2", ...),  # 如果跳过，则自动显示一个数字
    "desc": "描述选择选项时会发生什么的文本",
    "goto": ("节点名称或可调用对象", kwargs_to_pass_into_next_node_or_callable)
}
```

多个选项字典以列表或元组返回。理解`goto`选项键很重要。它的工作是直接指向另一个节点（通过给出其名称），或指向一个Python可调用对象（如函数）_然后返回该名称_。你还可以传递kwargs（作为字典）。这将在可调用对象或下一个节点中作为`**kwargs`提供。

虽然一个选项可以有一个`key`，但你也可以跳过它，只得到一个运行的数字。

在我们的`node_chargen`节点中，我们通过名称指向三个节点：`node_change_name`、`node_swap_abilities`和`node_apply_character`。我们还确保将`kwargs`传递给每个节点，因为其中包含我们的临时角色纸。

这些选项中的中间选项仅在我们尚未交换两个能力时出现——为了知道这一点，我们检查`.ability_changes`属性以确保它仍然是0。

## 节点：更改你的名字

如果你在`node_chargen`中选择更改名字，这就是你到达的地方。

```python
# 在 mygame/evadventure/chargen.py 中

# ...

# 在上一个节点之后

def _update_name(caller, raw_string, **kwargs):
    """
    由下面的node_change_name使用，以检查用户输入的内容
    并在适当时更新名称。

    """
    if raw_string:
        tmp_character = kwargs["tmp_character"]
        tmp_character.name = raw_string.lower().capitalize()

    return "node_chargen", kwargs


def node_change_name(caller, raw_string, **kwargs):
    """
    更改角色的随机名称。

    """
    tmp_character = kwargs["tmp_character"]

    text = (
        f"你当前的名字是 |w{tmp_character.name}|n。"
        "输入一个新名字或留空以中止。"
    )

    options = {
                   "key": "_default",
                   "goto": (_update_name, kwargs)
              }

    return text, options
```

这里有两个函数——菜单节点本身（`node_change_name`）和一个帮助_goto_function_（`_update_name`）来处理用户的输入。

对于（单个）选项，我们使用一个名为`_default`的特殊`key`。这使得这个选项成为一个catch-all：如果用户输入的内容与任何其他选项不匹配，这就是将使用的选项。由于我们在这里没有其他选项，所以无论用户输入什么，我们都会始终使用此选项。

还要注意，选项的`goto`部分指向`_update_name`可调用对象，而不是节点的名称。我们需要继续将`kwargs`传递给它！

当用户在此节点上输入任何内容时，将调用`_update_name`可调用对象。它具有与节点相同的参数，但它不是一个节点——我们将仅用于_找出_下一个要去的节点。

在`_update_name`中，我们现在有一个`raw_string`参数的用途——这就是用户在上一个节点上写的内容，记得吗？这现在要么是一个空字符串（意味着忽略它），要么是角色的新名称。

像`_update_name`这样的goto函数必须返回要使用的下一个节点的名称。它还可以选择性地返回要传递给该节点的`kwargs`——我们希望始终这样做，以便不会丢失我们的临时角色纸。在这里，我们将始终返回到`node_chargen`。

> 提示：如果从goto可调用对象返回`None`，你将始终返回到你所在的最后一个节点。

## 节点：交换能力

你通过从`node_chargen`节点选择第二个选项来到这里。

```python
# 在 mygame/evadventure/chargen.py 中

# ...

# 在上一个节点之后

_ABILITIES = {
    "STR": "strength",
    "DEX": "dexterity",
    "CON": "constitution",
    "INT": "intelligence",
    "WIS": "wisdom",
    "CHA": "charisma",
}


def _swap_abilities(caller, raw_string, **kwargs):
    """
    由node_swap_abilities使用以解析用户的输入并交换能力值。

    """
    if raw_string:
        abi1, *abi2 = raw_string.split(" ", 1)
        if not abi2:
            caller.msg("这看起来不对。")
            return None, kwargs
        abi2 = abi2[0]
        abi1, abi2 = abi1.upper().strip(), abi2.upper().strip()
        if abi1 not in _ABILITIES or abi2 not in _ABILITIES:
            caller.msg("不是熟悉的能力集。")
            return None, kwargs

        # 看起来不错 = 交换值。我们需要将STR转换为strength等
        tmp_character = kwargs["tmp_character"]
        abi1 = _ABILITIES[abi1]
        abi2 = _ABILITIES[abi2]
        abival1 = getattr(tmp_character, abi1)
        abival2 = getattr(tmp_character, abi2)

        setattr(tmp_character, abi1, abival2)
        setattr(tmp_character, abi2, abival1)

        tmp_character.ability_changes += 1

    return "node_chargen", kwargs


def node_swap_abilities(caller, raw_string, **kwargs):
    """
    允许交换两个能力的值，一次。

    """
    tmp_character = kwargs["tmp_character"]

    text = f"""
你当前的能力：

STR +{tmp_character.strength}
DEX +{tmp_character.dexterity}
CON +{tmp_character.constitution}
INT +{tmp_character.intelligence}
WIS +{tmp_character.wisdom}
CHA +{tmp_character.charisma}

你可以交换两个能力的值。
你只能这样做一次，所以请谨慎选择！

要交换例如STR和INT的值，请输入|wSTR INT|n。留空以中止。
"""

    options = {"key": "_default", "goto": (_swap_abilities, kwargs)}

        return text, options
```

这是更多的代码，但逻辑是相同的——我们有一个节点（`node_swap_abilities`）和一个goto可调用帮助程序（`_swap_abilities`）。我们捕获用户在节点上输入的所有内容（例如`WIS CON`）并将其传递给帮助程序。

在`_swap_abilities`中，我们需要分析用户的`raw_string`以查看他们想要做什么。

帮助程序中的大多数代码都是验证用户没有输入无意义的内容。如果他们这样做了，我们使用`caller.msg()`告诉他们，然后返回`None, kwargs`，这将重新运行相同的节点（名称选择）。

由于我们希望用户能够输入“CON”而不是更长的“constitution”，我们需要一个映射`_ABILITIES`来轻松地在两者之间转换（它存储为临时角色纸上的`consitution`）。一旦我们知道他们想要交换哪些能力，我们就这样做并增加`.ability_changes`计数器。这意味着此选项将不再从主节点中可用。

最后，我们再次返回到`node_chargen`。

## 节点：创建角色

我们通过选择完成角色生成的选项从主节点进入这里。

```python
node_apply_character(caller, raw_string, **kwargs):
    """
    结束角色生成并创建角色。我们还将控制它。

    """
    tmp_character = kwargs["tmp_character"]
    new_character = tmp_character.apply(caller)

    caller.account.add_character(new_character)

    text = "角色已创建！"

    return text, None
```

进入节点时，我们将使用临时角色纸的`.apply`方法创建一个包含所有装备的新角色。

这是一个_结束节点_，因为它返回`None`而不是选项。之后，菜单将退出。我们将回到默认的角色选择屏幕。该屏幕上显示的角色是`_playable_characters`属性中列出的角色，因此我们还需要将新角色添加到其中。

## 将节点连接在一起

```python
def start_chargen(caller, session=None):
    """
    这是从命令启动角色生成的起点。

    """
    menutree = {  # <----- 现在可以添加这个！
        "node_chargen": node_chargen,
        "node_change_name": node_change_name,
        "node_swap_abilities": node_swap_abilities,
        "node_apply_character": node_apply_character,
    }

    # 这将生成角色的所有随机组件
    tmp_character = TemporaryCharacterSheet()

    EvMenu(
        caller,
        menutree,
        session=session,
        startnode="node_chargen",  # <-- 确保已设置！
        startnode_input=("", {"tmp_character": tmp_character}),
    )
```

现在我们有了所有的节点，我们将它们添加到之前留空的`menutree`中。我们只添加节点，而不是goto帮助程序！我们在`menutree`字典中设置的键是我们应该用来从菜单内部指向节点的名称（我们已经这样做了）。

我们还添加了一个关键字参数`startnode`，指向`node_chargen`节点。这告诉EvMenu在菜单启动时首先跳转到该节点。

## 结论

本课教我们如何使用`EvMenu`制作交互式角色生成器。在一个比_Knave_更复杂的RPG中，菜单会更大更复杂，但相同的原则适用。

结合之前的课程，我们现在已经完成了玩家角色的基本内容——他们如何存储他们的统计数据，如何处理他们的装备以及如何创建他们。

在下一课中，我们将讨论EvAdventure _Rooms_的工作原理。
