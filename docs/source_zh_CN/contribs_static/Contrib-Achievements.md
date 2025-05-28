# Achievements

一个简单但相当全面的成就追踪系统。成就使用普通的 Python 字典定义，类似于核心原型系统，虽然期望你只在角色或账户上使用，但它们可以在任何类型类对象上跟踪。

该贡献提供了几个用于追踪和访问成就的函数，以及一个基本的游戏内命令用于查看成就状态。

## 安装

这个贡献需要创建一个或多个包含你的成就数据的模块文件，然后将它们添加到你的设置文件中以使其可用。

> 请参阅下方的“创建成就”部分，了解在该模块中需要放置的内容。

```python
# 在 server/conf/settings.py 中

ACHIEVEMENT_CONTRIB_MODULES = ["world.achievements"]
```

为了让玩家查看他们的成就，你还需要将 `achievements` 命令添加到默认角色和/或账户命令集中。

```python
# 在 commands/default_cmdsets.py 中

from evennia.contrib.game_systems.achievements.achievements import CmdAchieve

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        # ...
        self.add(CmdAchieve)
```

**可选** - 成就贡献默认在 `achievements` 属性上存储个别进度数据，通过 `obj.db.achievements` 访问。你可以通过为设置 `ACHIEVEMENT_CONTRIB_ATTRIBUTE` 分配一个属性（键，类别）元组来更改此设置。

例如：
```python
# 在 settings.py 中

ACHIEVEMENT_CONTRIB_ATTRIBUTE = ("progress_data", "achievements")
```

## 创建成就

一个成就由在你的成就模块中定义的简单 Python 字典表示。

每个成就需要定义某些特定的键才能正常工作，同时还有几个可选键可用于覆盖默认值。

> 注意：任何未在此处描述的附加键都将包含在访问这些成就时的数据中，因此你可以轻松添加自己的扩展功能。

#### 必需键

- **name** (str): 成就的可搜索名称。无需唯一。
- **category** (str): 可以促使此成就进展的条件的类别或一般类型。通常这将是一个玩家行为或结果。例如，对于杀死 10 只老鼠的成就，你会使用“defeat”的类别。
- **tracking** (str 或列表): 可以促使此成就进展的特定条件子集。例如，对于杀死 10 只老鼠的成就，你会使用“rat”的跟踪值。一个成就也可以跟踪多个事物，例如杀死 10 只老鼠或蛇。对于这种情况，将所有值的列表分配给 `tracking`，例如 `["rat", "snake"]`。

#### 可选键

- **key** (str): *默认值为未设置时：变量名称.* 唯一的，不区分大小写的键标识此成就。
> 注意：如果有任何成就具有相同的唯一键，则仅会加载 *一个*。这是不区分大小写的，但标点符号得到尊重——“ten_rats”、“Ten_Rats”和“TEN_RATS”将冲突，但“ten_rats”和“ten rats”不会。
- **desc** (str): 成就的更长描述。此类用途通常是口味文本或完成该成就的提示。
- **count** (int): *默认值为未设置时：1* 此成就要求的条件必须累积以完成该成就的计数。例如，杀死 10 只老鼠的成就将有一个“count”值为 `10`。对于使用“separate”跟踪类型的成就，*每个*受跟踪项目必须累积到此数字才能完成。
- **tracking_type** (str): *默认值为未设置时：`"sum"`* 有两种有效的跟踪类型：“sum”（默认为此）和“separate”。`"sum"` 会在每次任何受跟踪的项目匹配时递增单个计数器。`"separate"` 将为每个跟踪项有一个计数器。（有关差异的演示，请参见示例成就部分。）
- **prereqs** (str 或列表): 任何必须在此成就开始跟踪进展之前完成的成就的 *键*。

### 示例成就

一个简单的成就，仅需首次登录即可获得。此成就没有前提条件，并且只需完成一次即可。
```python
# 此成就的唯一键为 "first_login_achieve"
FIRST_LOGIN_ACHIEVE = {
    "name": "Welcome!", # 可搜索的，玩家友好的显示名称
    "desc": "We're glad to have you here.", # 更长的描述
    "category": "login", # 这一类行动的类型
    "tracking": "first", # 具体登录行为
}
```

一个杀死 10 只老鼠的成就，以及另一个杀死 10 只 * dire * 老鼠的成就，该成就要求先完成“杀死 10 只老鼠”的成就。只有在完成第一个成就之前，凶残的老鼠的成就才会开始跟踪 *任何* 进展。
```python
# 此成就具有唯一键 "ten_rats"，而不是 "achieve_ten_rats"
ACHIEVE_TEN_RATS = {
    "key": "ten_rats",
    "name": "The Usual",
    "desc": "Why do all these inns have rat problems?",
    "category": "defeat",
    "tracking": "rat",
    "count": 10,
}

ACHIEVE_DIRE_RATS = {
    "name": "Once More, But Bigger",
    "desc": "Somehow, normal rats just aren't enough any more.",
    "category": "defeat",
    "tracking": "dire rat",
    "count": 10,
    "prereqs": "ACHIEVE_TEN_RATS",
}
```

一个购买 5 只苹果、橙子或梨的成就。“sum”跟踪类型意味着所有物品都被加在一起——所以可以通过购买 5 只苹果、5 只梨、3 只苹果、1 只橙子和 1 只梨或任何这三种水果的组合完成，总数为 5。
```python
FRUIT_FAN_ACHIEVEMENT = {
    "name": "A Fan of Fruit", # 注意，这里没有描述——这也是允许的！
    "category": "buy",
    "tracking": ("apple", "orange", "pear"),
    "count": 5,
    "tracking_type": "sum", # 这是默认值，但这里为了清晰起见，包含
}
```

一个购买 5 *每种*苹果、橙子和梨的成就。“separate”跟踪类型意味着每个受跟踪物品独立的计数，所以你需要 5 只苹果、5 只橙子和 5 只梨。
```python
FRUIT_BASKET_ACHIEVEMENT = {
    "name": "Fruit Basket",
    "desc": "One kind of fruit just isn't enough.",
    "category": "buy",
    "tracking": ("apple", "orange", "pear"),
    "count": 5,
    "tracking_type": "separate",
}
```

## 用法

你需要做的两个主要事情，以便在游戏中使用成就贡献是 **追踪成就** 和 **获取成就信息**。第一个通过函数 `track_achievements` 完成；第二个可以通过 `search_achievement` 或 `get_achievement` 完成。

### 追踪成就

#### `track_achievements`

在游戏机制中你可能想要追踪成就的任何行为或功能中，添加一个调用 `track_achievements` 来更新该玩家的成就进度。

使用“杀死 10 只老鼠”的示例成就，你可能会有一些代码在角色被击败时触发：为了示例起见，我们假设我们在基本对象类上有一个 `at_defeated` 方法，当对象被击败时被调用。

将成就追踪添加到其中看起来可以像这样：

```python
# 在 typeclasses/objects.py 中

from contrib.game_systems.achievements import track_achievements

class Object(ObjectParent, DefaultObject):
    # ....

    def at_defeated(self, victor):
        """当这个对象在战斗中被击败时调用"""
        # 我们将使用 "mob_type" 标签类别作为跟踪信息
        # 这样我们就可以有名为 "black rat" 和 "brown rat" 的老鼠，它们都是老鼠
        mob_type = self.tags.get(category="mob_type")
        # 只有一个mob被击败，所以我们包括计数1
        track_achievements(victor, category="defeated", tracking=mob_type, count=1)
```

如果一个玩家击败了一个标记为 `rat` 的对象，而该对象的标签类别为 `mob_type`，那么它将计入杀死老鼠的成就。

你也可以将跟踪信息硬编码到游戏中，以便于特殊或唯一的情况。例如，前面描述的成就 `FIRST_LOGIN_ACHIEVE` 可以这样跟踪：

```python
# 在 typeclasses/accounts.py 中
from contrib.game_systems.achievements import track_achievements

class Account(DefaultAccount):
    # ...

    def at_first_login(self, **kwargs):
        # 这个函数只在账户第一次登录时调用
        # 因此我们已经知道，可以告诉追踪器这是第一次
        track_achievements(self, category="login", tracking="first")
```

`track_achievements` 函数还可以返回一个值：一个可迭代对象，包含通过该更新新完成的任何成就的键。你可以忽略这个值，或者你可以用它例如向玩家发送消息，告诉他们他们最新的成就。

### 获取成就

获取特定成就信息的主要方法是 `get_achievement`，它接受已知的成就键并返回该成就的数据。

不过，为了处理更多可变和玩家友好的输入，还有 `search_achievement`，它不仅对键进行部分匹配，还对成就的显示名称和描述进行匹配。

#### `get_achievement`

一个实用功能，用于从成就的唯一键中检索特定成就的数据。它不能用于搜索，但如果你已经知道一个成就的键——例如，从 `track_achievements` 的结果中——可以通过这种方式检索其数据。

#### 示例：

```python
from evennia.contrib.game_systems.achievements import get_achievement

def toast(achiever, completed_list):
    if completed_list:
        # `completed_data` 将是一个字典列表 - 未识别的键返回空字典
        completed_data = [get_achievement(key) for key in completed_list]
        names = [data.get('name') for data in completed_data]
        achiever.msg(f"|wAchievement Get!|n {iter_to_str(name for name in names if name)}")
```

#### `search_achievement`

一个实用功能，用于通过名称或描述搜索成就。它处理部分匹配并返回一个匹配成就的字典。为游戏提供的 `achievements` 命令使用此功能从用户输入中查找匹配的成就。

#### 示例：

第一个示例搜索“fruit”，返回水果拼盘成就，因为它的键和姓名中都包含“fruit”。

第二个示例搜索“usual”，返回十只老鼠成就，由于其显示名称。

```python
>>> from evennia.contrib.game_systems.achievements import search_achievement
>>> search_achievement("fruit")
{'fruit_basket_achievement': {'name': 'Fruit Basket', 'desc': "One kind of fruit just isn't enough.", 'category': 'buy', 'tracking': ('apple', 'orange', 'pear'), 'count': 5, 'tracking_type': 'separate'}}
>>> search_achievement("usual")
{'ten_rats': {'key': 'ten_rats', 'name': 'The Usual', 'desc': 'Why do all these inns have rat problems?', 'category': 'defeat', 'tracking': 'rat', 'count': 10}}
```

### `achievements` 命令

该贡献提供的命令 `CmdAchieve` 旨在可按原样使用，具有多个开关以根据各种进度状态过滤成就，并能够按成就名称搜索。

为了使其更容易为自己的游戏定制（例如，显示你可能添加的一些额外成就数据），格式和样式代码从命令逻辑中分离出来，进入 `CmdAchieve` 之上的 `format_achievement` 方法和 `template` 属性。

#### 示例输出

```
> achievements
The Usual
Why do all these inns have rat problems?
70% complete
A Fan of Fruit

Not Started
```

```
> achievements/progress
The Usual
Why do all these inns have rat problems?
70% complete
```

```
> achievements/done
There are no matching achievements.
```
