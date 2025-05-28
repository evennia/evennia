# 游戏任务

```{warning}
本教程课程尚未完成，且实现中存在一些严重的错误。因此，请将其作为参考，但代码尚未准备好直接使用。
```

一个 _任务_ 是游戏中的常见特征。从经典的取物任务（例如，收集 10 朵花）到复杂的任务链，涉及戏剧和阴谋，任务在我们的游戏中需要得以妥善跟踪。

任务遵循特定的发展过程：

1. 任务被 _开始_。这通常涉及玩家接受任务，来自任务给予者、工作板或其他来源。但任务也可以突然降临到玩家身上（“在房子倒塌之前拯救家庭！”）。
2. 一旦任务被接受并分配给角色，它的状态可能为 `Started`（进行中）、`Abandoned`（放弃）、`Failed`（失败）或 `Complete`（完成）。
3. 一个任务可以由一个或多个“步骤”组成。每个步骤都有其自己的完成条件。
4. 在适当的时机，任务的 _进度_ 将被检查。这可以在定时器触发时或尝试“提交”任务时进行检查。在检查时，当前的“步骤”会与其完成条件进行对比。如果条件满足，该步骤关闭并检查下一个步骤，直到遇到尚未完成的步骤，或者没有更多步骤为止，此时整个任务完成。

```{sidebar}
一个任务的示例实现可以在 `evennia/contrib/tutorials` 下的 [evadventure/quests.py](evennia.contrib.tutorials.evadventure.quests) 找到。
```

为了在代码中表示任务，我们需要：
- 一种便捷灵活的方式来编写检查任务状态和当前步骤的代码。我们希望这段脚本尽可能灵活。理想的情况下，我们希望能够用完整的 Python 代码编写任务的逻辑。
- 持久性。我们接受任务的事实，以及它的状态和其他标志必须保存在数据库中，并能在服务器重启后生存。

我们将通过两段 Python 代码实现这一目标：
- `EvAdventureQuest`：一个 Python 类，带有帮助方法，供我们调用以检查当前任务状态，判断给定任务步骤是否完成。我们将通过简单地继承此基类并以标准化的方式实现新方法来创建和编写新任务。
- `EvAdventureQuestHandler` 将作为每个角色的 `character.quests` 存在。它将持有角色当前或曾参与的所有 `EvAdventureQuest`，并负责使用 [Attributes](../../../Components/Attributes.md) 在角色中存储任务状态。

## 任务处理器

> 创建一个新的模块 `evadventure/quests.py`。

我们在 [NPC 和怪物 AI 的课程](./Beginner-Tutorial-AI.md#the-aihandler) 中见过一个基于对象的处理器（`AIHandler`）的实现。

```{code-block} python
:linenos: 
:emphasize-lines: 9,10,11,14-18,21,24-28
# 在 evadventure/quests.py 中

class EvAdventureQuestHandler:
    quest_storage_attribute_key = "_quests"
    quest_storage_attribute_category = "evadventure"

    def __init__(self, obj):
        self.obj = obj
        self.quest_classes = {}
        self.quests = {}
        self._load()

    def _load(self):
        self.quest_classes = self.obj.attributes.get(
            self.quest_storage_attribute_key,
            category=self.quest_storage_attribute_category,
            default={},
        )
        # 实例化所有任务
        for quest_key, quest_class in self.quest_classes.items():
            self.quests[quest_key] = quest_class(self.obj)

    def _save(self):
        self.obj.attributes.add(
            self.quest_storage_attribute_key,
            self.quest_classes,
            category=self.quest_storage_attribute_category,
        )
    
    def get(self, quest_key):
        return self.quests.get(quest_key)

    def all(self):
        return list(self.quests.values())

    def add(self, quest_class):
        self.quest_classes[quest_class.key] = quest_class
        self.quests[quest_class.key] = quest_class(self.obj)
        self._save()

    def remove(self, quest_key):
        quest = self.quests.pop(quest_key, None)
        self.quest_classes.pop(quest_key, None)
        self.quests.pop(quest_key, None)
        self._save()
```

```{sidebar} 持久化处理器模式
持久化处理器在 Evennia 中普遍使用。您可以在 [制作持久化对象处理器](../../Tutorial-Persistent-Handler.md) 教程中了解有关它们的更多信息。
```

- **第 9 行**：我们知道任务本身将是继承自 `EvAdventureQuest` 的 Python 类（我们尚未创建）。我们将在处理器的 `self.quest_classes` 中存储这些类。注意类与类的 _实例_ 之间的区别！类本身无法持有任何 _状态_，例如该任务对于这个特定角色的状态。类只持有 Python 代码。
- **第 10 行**：我们在处理器中为 `self.quests` 预留了另一个属性。该字典将持有 `EvAdventureQuest` 的 _实例_。
- **第 11 行**：请注意，我们在此调用 `self._load()` 方法，每当访问该处理器时，它会从数据库加载数据。
- **第 14-18 行**：我们使用 `self.obj.attributes.get` 从角色中获取名为 `_quests` 的 [Attribute](../../../Components/Attributes.md)，类别为 `evadventure`。如果不存在（因为我们还没有开始任何任务），我们只是返回一个空字典。
- **第 21 行**：在这里我们循环遍历所有类并实例化它们。我们还尚未定义这些任务类的样子，但通过使用 `self.obj`（即角色）实例化它们，我们应该能够覆盖 - 由于角色类，任务能够访问所有其他内容（毕竟，这个处理器本身也可以通过 `obj.quests` 从那个任务实例访问）。
- **第 24 行**：在这里我们执行对应的保存操作。

处理器的其他部分只是获取、添加和从处理器中删除任务的访问方法。在这些代码中，我们做了一个假设，即任务类具有唯一任务名称的 `.key` 属性。

以下是在实践中使用它的示例：

```python
# 在某个任务代码中 

from evennia import search_object
from evadventure import quests 

class EvAdventureSuperQuest(quests.EvAdventureQuest):
    key = "superquest"
    # 任务实现这里

def start_super_quest(character):
    character.quests.add(EvAdventureSuperQuest)
```
```{sidebar} 属性中可以保存什么？
有关此事的更多详细信息，请参见 [属性文档](../../../Components/Attributes.md#what-types-of-data-can-i-save-in-an-attribute)。
```
我们选择存储类而不是类的实例。原因涉及到可以存储在数据库 `Attribute` 中的内容 - `Attribute` 的一个限制是，我们无法保存一个包含其他嵌入实体的类实例。如果我们直接保存任务实例，可能它们会包含“隐藏”的数据库实体 - 比如，对角色的引用，也许是完成任务所需的对象引用等。Evennia 会在尝试保存该数据时失败。
相反，我们仅存储类，将这些类与角色实例化，并让任务单独存储其状态标志，如下所示：

```python 
# 在 evadventure/quests.py 中 

class EvAdventureQuestHandler: 

    # ... 
    quest_data_attribute_template = "_quest_data_{quest_key}"
    quest_data_attribute_category = "evadventure"

    # ... 

    def save_quest_data(self, quest_key):
        quest = self.get(quest_key)
        if quest:
            self.obj.attributes.add(
                self.quest_data_attribute_template.format(quest_key=quest_key),
                quest.data,
                category=self.quest_data_attribute_category,
            )

    def load_quest_data(self, quest_key):
        return self.obj.attributes.get(
            self.quest_data_attribute_template.format(quest_key=quest_key),
            category=self.quest_data_attribute_category,
            default={},
        )

```

这与 `_load` 和 `_save` 方法的功能相同，除了它获取一个属性 `.data`（这将是一个 `dict`）并将其保存。只要确保在任务的 `.data` 属性发生变化时从任务内调用这些方法，所有内容都将顺利进行 - 原因在于 `Attributes` 知道如何正确分析 `dict` 并安全序列化其中找到的任何数据库实体。

我们的处理器已准备就绪。我们在 [角色课程](./Beginner-Tutorial-Characters.md) 中创建了 `EvAdventureCharacter` 类 - 现在让我们向其添加任务支持。

```python
# 在 evadventure/characters.py 中

# ...

from evennia.utils import lazy_property
from evadventure.quests import EvAdventureQuestHandler

class EvAdventureCharacter(LivingMixin, DefaultCharacter): 
    # ...

    @lazy_property
    def quests(self): 
        return EvAdventureQuestHandler(self)

    # ...
```

我们还需要一种表示任务本身的方式！
## 任务类

```{code-block} python
:linenos:
:emphasize-lines: 7,12,13,34-36
# 在 evadventure/quests.py 中

# ...

class EvAdventureQuest:

    key = "base-quest"
    desc = "基础任务"
    start_step = "start"
    
    def __init__(self, quester):
        self.quester = quester
        self.data = self.questhandler.load_quest_data(self.key)
        self._current_step = self.get_data("current_step")

        if not self.current_step:
            self.current_step = self.start_step

    def add_data(self, key, value):
        self.data[key] = value
        self.questhandler.save_quest_data(self.key)

    def get_data(self, key, default=None):
        return self.data.get(key, default)

    def remove_data(self, key):
        self.data.pop(key, None)
        self.questhandler.save_quest_data(self.key)
    
    @property
    def questhandler(self):
        return self.quester.quests

    @property
    def current_step(self):
        return self._current_step

    @current_step.setter
    def current_step(self, step_name):
        self._current_step = step_name
        self.add_data("current_step", step_name)
```

- **第 7 行**：每个类都必须有一个 `.key` 属性，以唯一标识该任务。我们在任务处理器中依赖这一点。
- **第 12 行**：在此类中，当它在 `EvAdventureQuestHandler._load()` 中被实例化时，将 `quester`（即角色）传入该类。
- **第 13 行**：我们直接使用 `questhandler.load_quest_data` 方法将任务数据加载到 `self.data` 中（这又是从角色的 Attribute 中加载）。请注意，`.questhandler` 属性在 **第 34-36 行** 中被定义，作为访问处理器的快捷方式。

`add_data`、`get_data` 和 `remove_data` 方法是便捷的封装，用于通过处理器上的匹配方法获取和存储数据。实现任务时，我们应优先考虑使用 `.get_data`、`add_data` 和 `remove_data`，而不是直接操作 `.data`，因为前者会确保将其自动保存到数据库。

`current_step` 跟踪我们所在的当前任务“步骤”；这意味着什么取决于每个任务。我们设置了便捷属性来设置 `current_step`，并确保将其作为“current_step”保存在数据字典中。

任务可以有几种可能的状态：“已开始”、“已完成”、“已放弃”和“已失败”。我们创建了一些属性和方法，以便轻松控制这些状态，同时在后台保存一切：

```python
# 在 evadventure/quests.py 中

# ... 

class EvAdventureQuest:

    # ... 

    @property
    def status(self):
        return self.get_data("status", "started")

    @status.setter
    def status(self, value):
        self.add_data("status", value)

    @property
    def is_completed(self):
        return self.status == "completed"

    @property
    def is_abandoned(self):
        return self.status == "abandoned"

    @property
    def is_failed(self):
        return self.status == "failed"

    def complete(self):
        self.status = "completed"

    def abandon(self):
        self.status = "abandoned"

    def fail(self):
        self.status = "failed"
```

到目前为止，我们只是为检查状态添加了便捷函数。那么实际的“任务”方面将如何工作呢？

当系统想要检查任务的进度时，它将调用该类的 `.progress()` 方法。同样，若要获取当前步骤的帮助，它将调用 `.help()` 方法。

```python
    start_step = "start"

    # 任务的帮助条目（也可以是方法）
    help_start = "您需要先开始"
    help_end = "您需要结束任务"

    def progress(self, *args, **kwargs):
        getattr(self, f"step_{self.current_step}")(*args, **kwargs)

    def help(self, *args, **kwargs):
        if self.status in ("abandoned", "completed", "failed"):
            help_resource = getattr(self, f"help_{self.status}",
                                    f"您已 {self.status} 此任务。")
        else:
            help_resource = getattr(self, f"help_{self.current_step}", "没有帮助可用。")

        if callable(help_resource):
            # help_* 方法可以用于动态生成帮助
            return help_resource(*args, **kwargs)
        else:
            # 通常它只是一个字符串
            return str(help_resource)
```

```{sidebar} *args 和 **kwargs 是什么？
这些是可选的，但允许您向任务检查传递额外信息。这在您希望添加额外上下文以确定任务步骤是否当前完成时可能非常强大。
```
调用 `.progress(*args, **kwargs)` 方法将调用名为 `step_<current_step>(*args, **kwargs)` 的方法。也就是说，如果我们处于 _start_ 步骤，调用的方法将是 `self.step_start(*args, **kwargs)`。这个方法在哪里？它尚未实现！实际上，实施类似的方法取决于我们，为每个任务实现这样的步骤，并添加正确的方法，我们将能够轻松地为任务添加更多步骤。

同样，调用 `.help(*args, **kwargs)` 将尝试查找属性 `help_<current_step>`。如果这是一个可调用的，它将被称为例如 `self.help_start(*args, **kwargs)`。如果它作为字符串给出，则将字符串按原样返回，`*args`、`**kwargs` 将被忽略。

### 示例任务 

```python
# 在某个任务模块中，例如 world/myquests.py

from evadventure.quests import EvAdventureQuest 

class ShortQuest(EvAdventureQuest): 

    key = "simple-quest"
    desc = "一个非常简单的任务。"

    def step_start(self, *args, **kwargs): 
        """示例步骤！"""
        self.quester.msg("任务开始了！")
        self.current_step = "end"

    def step_end(self, *args, **kwargs): 
        if not self.is_completed:
            self.quester.msg("任务结束了！")
            self.complete()
```

这是一个非常简单的任务，在两次 `.progress()` 检查后将自动解决。以下是此任务的完整生命周期：

```python 
# 在某个模块中的某个地方，使用 evennia shell 或在游戏中 使用 py

from evennia import search_object 
from world.myquests import ShortQuest 

character = search_object("MyCharacterName")[0]
character.quests.add(ShortQuest)

# 这将向角色回显“任务已开始！”
character.quests.get("short-quest").progress()                     
# 这将向角色回显“任务结束！”
character.quests.get("short-quest").progress()
```

### 一个有用的命令

玩家必须知道他们有哪些任务，并能够检查它们。下面是处理此任务的简单 `quests` 命令：

```python
# 在 evadventure/quests.py 中

class CmdQuests(Command):
    """
    列出所有任务及其状态，并获取有关特定任务状态的信息。

    用法：
        quests
        quest <questname>

    """
    key = "quests"
    aliases = ["quest"]

    def parse(self):
        self.quest_name = self.args.strip()

    def func(self):
        if self.quest_name:
            quest = self.caller.quests.get(self.quest_name)
            if not quest:
                self.msg(f"找不到任务 {self.quest_name}。")
                return
            self.msg(f"任务 {quest.key}: {quest.status}\n{quest.help()}")
            return

        quests = self.caller.quests.all()
        if not quests:
            self.msg("没有任务。")
            return

        for quest in quests:
            self.msg(f"任务 {quest.key}: {quest.status}")
```

将其添加到 `mygame/commands/default_cmdsets.py` 的 `CharacterCmdSet` 中。如果您不确定如何操作，请遵循 [添加命令的课程](../Part1/Beginner-Tutorial-Adding-Commands.md#add-the-echo-command-to-the-default-cmdset)。重新加载，如果您作为 `EvAdventureCharacter` 玩，您应该能够使用 `quests` 来查看您的任务。

## 测试 

> 创建一个新的文件夹 `evadventure/tests/test_quests.py`。

```{sidebar} 
一个任务的示例测试套件可以在 `evennia/contrib/tutorials/evadventure` 中找到，例如 [tests/test_quests.py](evennia.contrib.tutorials.evadventure.tests.test_quests)。
```
任务的测试意味着创建一个测试角色、制作一个虚拟任务，将其添加到角色的任务处理器中，确保所有方法正常工作。创建测试任务，以便在调用 `.progress()` 时它将自动向前推进，以便您确保其按预期工作。

## 结论 

我们在这里创建的只是任务框架。实际的复杂性将在创建任务本身时到来（也就是说，实现 `step_<current_step>(*args, **kwargs)` 方法），这将在稍后进行，在本教程的 [第 4 部分](../Part4/Beginner-Tutorial-Part4-Overview.md) 中。
