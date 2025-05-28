# 创建持久化对象处理器

一个 _处理器_ 是将对象功能进行分组的便捷方式。这使您能够在一个地方逻辑性地归组与该对象相关的所有操作。本教程将示范如何创建自己的处理器，并确保您存储在其中的数据在重载后仍然存在。

例如，当您执行 `obj.attributes.get("key")` 或 `obj.tags.add('tagname')` 时，您就是在调用存储在 `obj` 上的 `.attributes` 和 `tags` 中的处理器。这些处理器上有方法（在本示例中是 `get()` 和 `add()`）。

## 基础处理器示例

以下是设置对象处理器的基本方法：

```python
from evennia import DefaultObject, create_object
from evennia.utils.utils import lazy_property

class NameChanger:
    def __init__(self, obj):
        self.obj = obj

    def add_to_key(self, suffix):
        self.obj.key = f"{self.obj.key}_{suffix}"

# 创建一个测试对象
class MyObject(DefaultObject):
    @lazy_property
    def namechange(self):
        return NameChanger(self)

obj = create_object(MyObject, key="test")
print(obj.key)
>>> "test"
obj.namechange.add_to_key("extra")
print(obj.key)
>>> "test_extra"
```

这里发生的事情是我们创建了一个新的类 `NameChanger`。我们使用 `@lazy_property` 装饰器来设置它——这意味着处理器在实际被调用之前不会被创建，只有当有人真正想要使用它，即访问 `obj.namechange` 时，才会创建。被装饰的 `namechange` 方法返回处理器，并确保用 `self` 初始化——这在处理器内部被称为 `obj`！

然后，我们创建了一个简单的方法 `add_to_key`，该方法使用处理器来修改对象的键。在这个示例中，处理器的作用并不明显，但以这种方式分组功能可以使 API 易于记忆，并且还可以让您缓存数据以便于访问——这就是 `AttributeHandler`（`attributes`）和 `TagHandler`（`tags`）工作的方式。

## 在处理器中持久化存储数据

假设我们想在处理器中跟踪“任务”。“任务”是代表任务的常规类。我们为示例简化如下：

```python
# 例如在 mygame/world/quests.py 中

class Quest:
    key = "寻找红钥匙的任务"

    def __init__(self):
        self.current_step = "开始"

    def check_progress(self):
        # 使用 self.current_step 来检查
        # 此任务的进度
        getattr(self, f"step_{self.current_step}")()

    def step_start(self):
        # 在这里检查任务步骤是否完成
        self.current_step = "找到红钥匙"
        
    def step_find_the_red_key(self):
        # 检查步骤是否完成
        self.current_step = "交任务"
        
    def step_hand_in_quest(self):
        # 检查是否已将任务交给任务发布者
        self.current_step = None  # 完成
```

我们希望开发者能够创建这个类的子类以实现不同的任务。具体的工作方式并不重要，关键是我们希望跟踪 `self.current_step`——这是一个 _应该在服务器重载后保留_ 的属性。但迄今为止，`Quest` 没有办法做到这一点，它只是一个与数据库没有联系的普通 Python 类。

### 具有保存/加载功能的处理器

让我们创建一个 `QuestHandler` 来管理角色的任务。

```python
# 例如在相同的 mygame/world/quests.py 中

class QuestHandler:
    def __init__(self, obj):
        self.obj = obj
        self.do_save = False
        self._load()

    def _load(self):
        self.storage = self.obj.attributes.get(
            "quest_storage", default={}, category="quests")

    def _save(self):
        self.obj.attributes.add(
            "quest_storage", self.storage, category="quests")
        self._load()  # 重要
        self.do_save = False

    def add(self, questclass):
        self.storage[questclass.key] = questclass(self.obj)
        self._save()

    def check_progress(self):
        quest.check_progress()
        if self.do_save:
            # 如果 Quest 希望保存进度，.do_save 会在处理器中被设置
            self._save()
```

该处理器是一个普通的 Python 类，没有自己的数据库存储。但是它与 `.obj` 相关联，我们假设它是一个完整的类型化实体，在其上我们可以创建持久化的 [属性](../Components/Attributes.md) 来以我们喜欢的方式存储数据！

我们创建了两个辅助方法 `_load` 和 `_save`，它们处理本地提取并将 `storage` 保存到该对象的属性中。为了避免保存更多必要的数据，我们有一个属性 `do_save`。我们将在下面的 `Quest` 中设置这个属性。

> 请注意，一旦我们 `_save` 数据，我们需要再次调用 `_load`。这样可以确保我们在处理器中存储的版本被正确反序列化。如果您收到有关数据为 `bytes` 的错误，您可能错过了这一步。

### 使任务可持久化存储

处理器将把所有 `Quest` 对象作为 `dict` 保存在 `obj` 上的属性中。但我们还没有完成，`Quest` 对象也需要访问 `obj`——这不仅对判断任务是否完成（例如，`Quest` 必须能够检查任务者的背包以查看他们是否拥有红钥匙）很重要，还允许 `Quest` 在其状态发生变化时通知处理器并应保存该状态。

我们将 `Quest` 更改为如下：

```python
from evennia.utils import dbserialize

class Quest:
    def __init__(self, obj):
        self.obj = obj
        self._current_step = "开始"

    def __serialize_dbobjs__(self):
        self.obj = dbserialize.dbserialize(self.obj)

    def __deserialize_dbobjs__(self):
        if isinstance(self.obj, bytes):
            self.obj = dbserialize.dbunserialize(self.obj)

    @property
    def questhandler(self):
        return self.obj.quests

    @property
    def current_step(self):
        return self._current_step

    @current_step.setter
    def current_step(self, value):
        self._current_step = value
        self.questhandler.do_save = True  # 这会触发处理器的保存！

    # [与之前相同]
```

`Quest.__init__` 现在接收 `obj` 作为参数，以匹配我们在 `QuestHandler.add` 中传递给它的内容。我们希望监控 `current_step` 的变化，因此将其设置为一个属性。当我们编辑该值时，我们在处理器上设置 `do_save` 标志，这意味着在检查完所有任务的进度后，它将状态保存到数据库。`Quest.questhandler` 属性允许我们轻松回到处理器（及其所在的对象）。

`__serialize__dbobjs__` 和 `__deserialize_dbobjs__` 方法是必要的，因为 `Attributes` 不能存储“隐藏”的数据库对象（`Quest.obj` 属性）。这些方法帮助 Evennia 在保存 `Quest` 时正确地序列化/反序列化它。有关更多信息，请参见 [存储单个对象](../Components/Attributes.md#storing-single-objects) 中的属性。

### 将所有内容整合在一起

最后我们需要做的是将任务处理器添加到角色中：

```python
# 在 mygame/typeclasses/characters.py 中

from evennia import DefaultCharacter
from evennia.utils.utils import lazy_property
from .world.quests import QuestHandler  # 作为示例

class Character(DefaultCharacter):
    # ...
    @lazy_property
    def quests(self):
        return QuestHandler(self)
```

您现在可以创建您的任务类来描述任务，并通过以下方式将它们添加到角色中：

```python
character.quests.add(FindTheRedKey)
```

并可以稍后执行：

```python
character.quests.check_progress()
```

确保任务数据在重载之间不会丢失。

您可以在 Evennia 仓库中找到一个完备的任务处理器示例 [EvAdventure 任务](evennia.contrib.tutorials.evadventure.quests) 的贡献。
