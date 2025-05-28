# 容器

由 InspectorCaracal 贡献（2023）

添加将对象放入其他容器对象的能力，提供容器类型类并扩展某些基本命令。

## 安装

要安装，请在您的 `default_cmdsets.py` 文件中导入并添加 `ContainerCmdSet` 到 `CharacterCmdSet`：

```python
from evennia.contrib.game_systems.containers import ContainerCmdSet

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # ...
    
    def at_cmdset_creation(self):
        # ...
        self.add(ContainerCmdSet)
```

这将用 contrib 提供的容器友好的版本替换默认的 `look` 和 `get` 命令，同时添加一个新的 `put` 命令。

## 用法

该贡献包括一个 `ContribContainer` 类型类，具备作为容器使用所需的所有设置。要使用它，您只需在游戏中创建一个具有该类型类的对象 - 它将自动继承您在基础对象类型类中实现的内容。

```bash
create bag:game_systems.containers.ContribContainer
```

贡献的 `ContribContainer` 设有最大容纳物品数量的容量限制。可以为每个对象单独更改此设置。

在代码中：
```python
obj.capacity = 5
```
在游戏中：
```bash
set box/capacity = 5
```

您还可以通过在对象上设置 `get_from` 锁类型来使其他对象可用作容器。

```bash
lock mysterious box = get_from:true()
```

## 扩展

`ContribContainer` 类设计为可以直接使用，但您也可以从中继承以扩展自己的容器类的功能。除了在对象创建时预设容器锁外，它还附带三个主要添加项：

### `capacity` 属性

`ContribContainer.capacity` 是一个 `AttributeProperty` - 这意味着您可以在代码中通过 `obj.capacity` 访问它，也可以在游戏中通过 `set obj/capacity = 5` 设置它 - 代表容器的容量（整数形式）。您可以在自己的容器类中覆盖此属性，使用更复杂的容量表示。

### `at_pre_get_from` 和 `at_pre_put_in` 方法

这两个方法在尝试从容器获取对象或将对象放入容器时作为额外检查调用。贡献的 `ContribContainer.at_pre_get_from` 默认不进行额外验证，而 `ContribContainer.at_pre_put_in` 则进行简单的容量检查。

您可以在自己的子类中重写这些方法，以进行额外的容量或访问检查。
