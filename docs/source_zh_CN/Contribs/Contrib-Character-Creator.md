# 角色创建器

由 InspectorCaracal 贡献，2022年

用于管理和启动游戏内角色创建菜单的命令。

## 安装

在游戏文件夹的 `commands/default_cmdsets.py` 中，导入并将 `ContribChargenCmdSet` 添加到 `AccountCmdSet` 中。

示例：
```python
from evennia.contrib.rpg.character_creator.character_creator import ContribChargenCmdSet

class AccountCmdSet(default_cmds.AccountCmdSet):

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(ContribChargenCmdSet)
```

在游戏文件夹的 `typeclasses/accounts.py` 中，导入并从 `ContribChargenAccount` 继承你的账户类。

（你也可以将 `at_look` 方法直接复制到自己的类中。）

### 示例：

```python
from evennia.contrib.rpg.character_creator.character_creator import ContribChargenAccount

class Account(ContribChargenAccount):
    # 你的账户类代码
```

在设置文件 `server/conf/settings.py` 中，添加以下设置：

```python
AUTO_CREATE_CHARACTER_WITH_ACCOUNT = False
AUTO_PUPPET_ON_LOGIN = False
```

（如果你想允许玩家创建多个角色，可以使用设置 `MAX_NR_CHARACTERS` 自定义。）

默认情况下，新的 `charcreate` 命令将引用由此贡献提供的示例菜单，因此你可以在构建自己的菜单之前对其进行测试。
你可以在 [此处参考示例菜单](github:develop/evennia/contrib/rpg/character_creator/example_menu.py)，以获取构建自己菜单的思路。

一旦你有了自己的菜单，只需将其添加到设置中以使用。例如，如果你的菜单在 `mygame/word/chargen_menu.py` 中，则在设置文件中添加以下内容：

```python
CHARGEN_MENU = "world.chargen_menu"
```

## 使用

### EvMenu

为了使用此贡献，你需要创建自己的角色创建 EvMenu。附带的 `example_menu.py` 提供了多种有用的菜单节点技巧，以及基本属性示例供你参考。它可以直接以教学模式运行供你自己/开发者使用，或用作你自己菜单的基础。

示例菜单包含代码、提示和以下类型决策节点的说明：

#### 信息页

一小组节点，让你在承诺之前随意浏览不同选择的信息。

#### 选项类别

一对节点，允许你将任意数量的选项分为单独的类别。

基本节点有一个选项列表作为类别，子节点显示实际的角色选择。

#### 多项选择

允许玩家从列表中选择和取消选择选项，以便选择多个选项。

#### 起始对象

允许玩家从一组选定的起始对象中选择，完成角色创建时将创造这些对象。

#### 选择姓名

该贡献假定玩家将在角色创建过程中选择他们的姓名，因此包含必要代码来完成此操作！

### `charcreate` 命令

该贡献重载了角色创建命令 `charcreate`，以使用角色创建菜单，并支持退出/恢复流程。此外，与核心命令不同，它设计为在菜单中稍后选择角色姓名，因此不会解析传递给它的任何参数。

### 对 `Account` 的更改

贡献版本的工作方式与核心 Evennia 大致相同，但修改了 `ooc_appearance_template` 以匹配贡献的命令语法，并修改了 `at_look` 方法以识别进行中的角色。

如果你已经修改了自己的 `at_look` 钩子，这是一项简单的更改：只需在可玩角色列表循环的开头添加此部分。

```python
    # 循环开始的地方
    for char in characters:
        # ...
        # 贡献代码从这里开始
        if char.db.chargen_step:
            # 当前正在进行的角色；不显示占位符名称
            result.append(" - |Y进行中|n (|wcharcreate|n 继续)")
            continue
        # 其余代码继续在这里
```


----

<small>此文档页面并非由 `evennia/contrib/rpg/character_creator/README.md`自动生成。如想阅读最新文档，请参阅原始README.md文件。</small>
