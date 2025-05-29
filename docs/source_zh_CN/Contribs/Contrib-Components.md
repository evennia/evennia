# 组件

由 ChrisLR 贡献，2021年

使用组件/组合方法扩展类型类。

## 组件贡献

此贡献为 Evennia 引入了组件和组合。每个“组件”类代表将“启用”在类型类实例上的一个特性。您可以在整个类型类或运行时的单个对象上注册这些组件。它支持持久属性和内存属性，使用 Evennia 的 AttributeHandler。

## 优点
- 可以在多个类型类中重用特性而无需继承。
- 可以将每个特性整洁地组织成一个自包含的类。
- 可以在不检查其实例的情况下检查对象是否支持某个特性。

## 缺点
- 引入了额外的复杂性。
- 需要一个主机类型类实例。

## 如何安装

要为类型类启用组件支持，请导入并继承 `ComponentHolderMixin`，示例如下：

```python
from evennia.contrib.base_systems.components import ComponentHolderMixin

class Character(ComponentHolderMixin, DefaultCharacter):
    # ...
```

组件需要继承自 `Component` 类，并要求一个唯一名称。组件可以继承其他组件，但必须指定另一个名称。您可以将相同的“槽”分配给两个组件，以实现替代实现。

```python
from evennia.contrib.base_systems.components import Component

class Health(Component):
    name = "health"

class ItemHealth(Health):
    name = "item_health"
    slot = "health"
```

组件可以在类级别定义 `DBFields` 或 `NDBFields`。`DBField` 将以前缀键的形式将其值存储在主机的数据库中，`NDBField` 将以不持久的形式将其值存储在主机的 NDB 中。使用的键将是 'component_name::field_name'。它们在内部使用 `AttributeProperty`。

示例：
```python
from evennia.contrib.base_systems.components import Component, DBField

class Health(Component):
    health = DBField(default=1)
```

请注意，默认值是可选的，默认为 None。

将组件添加到主机时，还会添加一个同名的标签，类别为 'components'。名为 health 的组件将作为 `key="health", category="components"` 出现。这使得您可以通过使用标签检索具有特定组件的对象。

同样，可以使用 `TagField` 添加组件标签。`TagField` 接受默认值，并可以用于存储单个或多个标签。当组件添加时，默认值会自动添加。当组件被移除时，组件标签会从主机中清除。

示例：
```python
from evennia.contrib.base_systems.components import Component, TagField

class Health(Component):
    resistances = TagField()
    vulnerability = TagField(default="fire", enforce_single=True)
```

在本示例中，`resistances` 字段可以多次设置，并将保留添加的标签。`vulnerability` 字段将在本示例中用新标签覆盖之前的标签。

每个使用 `ComponentHolderMixin` 的类型类可以在类中通过 `ComponentProperty` 声明其组件。这些组件将始终存在于类型类中。还可以传递关键字参数以覆盖默认值。

示例：
```python
from evennia.contrib.base_systems.components import ComponentHolderMixin

class Character(ComponentHolderMixin, DefaultCharacter):
    health = ComponentProperty("health", hp=10, max_hp=50)
```

然后，您可以使用 `character.components.health` 进行访问。也存在更简短的形式 `character.cmp.health`。在定义了此组件的类型类中，`character.health` 也可以访问。

或者，您可以在运行时添加这些组件。您将必须通过组件处理程序访问它们。

示例：
```python
character = self
vampirism = components.Vampirism.create(character)
character.components.add(vampirism)

...

vampirism = character.components.get("vampirism")

# 或者
vampirism = character.cmp.vampirism
```

请记住，所有组件必须导入才能在列表中可见。因此，我建议将它们重新分组到一个包中。您可以在该包的 `__init__` 文件中导入所有组件。

由于 Evennia 导入类型类和 Python 导入的行为，我建议将组件包放在类型类包中。换句话说，在您的类型类文件夹中创建一个名为 `components` 的文件夹。然后，在 'typeclasses/__init__.py' 文件中添加对该文件夹的导入，如下所示：

```python
from typeclasses import components
```

这确保在导入类型类时，也会导入组件包。您还需要在包的 'typeclasses/components/__init__.py' 文件中导入每个组件。您只需从那里导入每个模块/文件，但识别正确的类是一个好习惯。

```python
from typeclasses.components.health import Health
```
```python
from typeclasses.components import health
```
上述两个示例都有效。

## 已知问题

将可变默认值（如列表）分配给 `DBField` 会在实例间共享它。要避免这种情况，您必须在字段上设置 `autocreate=True`，如下所示：

```python
health = DBField(default=[], autocreate=True)
```

## 完整示例
```python
from evennia.contrib.base_systems import components

# 这是组件类
class Health(components.Component):
    name = "health"

    # 将当前值和最大值作为属性存储在主机上，默认值为 100
    current = components.DBField(default=100)
    max = components.DBField(default=100)

    def damage(self, value):
        if self.current <= 0:
            return

        self.current -= value
        if self.current > 0:
            return

        self.current = 0
        self.on_death()

    def heal(self, value):
        hp = self.current
        hp += value
        if hp >= self.max:
            hp = self.max

        self.current = hp

    @property
    def is_dead(self):
        return self.current <= 0

    def on_death(self):
        # 行为在类型类中定义
        self.host.on_death()

# 这是角色如何继承混入并注册组件 'health'
class Character(ComponentHolderMixin, DefaultCharacter):
    health = ComponentProperty("health")

# 这是一个检查组件的命令示例
class Attack(Command):
    key = "attack"
    aliases = ('melee', 'hit')

    def at_pre_cmd(self):
        caller = self.caller
        targets = self.caller.search(args, quiet=True)
        valid_target = None
        for target in targets:
            # 尝试检索组件，如果不存在则获得 None。
            if target.components.health:
                valid_target = target

        if not valid_target:
            caller.msg("You can't attack that!")
            return True
```


----

<small>此文档页面并非由 `evennia/contrib/base_systems/components/README.md`自动生成。如想阅读最新文档，请参阅原始README.md文件。</small>
