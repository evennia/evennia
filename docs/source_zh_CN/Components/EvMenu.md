# EvMenu

```shell
你的回答是“是”还是“否”？
_________________________________________
[Y]es! - 回答“是”。
[N]o! - 回答“否”。
[A]bort - 不回答任何内容，并中止。

> Y
你选择了“是”！

感谢你的回答。再见！
```

_EvMenu_ 用于生成分支多选菜单。每个菜单“节点”可以接受特定选项作为输入或自由格式输入。根据玩家的选择，他们会被转发到菜单中的不同节点。

`EvMenu` 实用类位于 [evennia/utils/evmenu.py](evennia.utils.evmenu)。它允许轻松地为游戏添加互动菜单；例如，用于实施角色创建、构建命令或类似功能。下面是提供 NPC 对话选择的示例：

以下是此页面顶部示例菜单的代码展示：

```python
from evennia.utils import evmenu

def _handle_answer(caller, raw_input, **kwargs):
    answer = kwargs.get("answer")
    caller.msg(f"You chose {answer}!")
    return "end"  # 下一个节点的名称

def node_question(caller, raw_input, **kwargs):
    text = "你的回答是“是”还是“否”？"
    options = (
        {"key": ("[Y]es!", "yes", "y"),
         "desc": "回答“是”。",
         "goto": _handle_answer, {"answer": "yes"}},
        {"key": ("[N]o!", "no", "n"),
         "desc": "回答“否”。",
         "goto": _handle_answer, {"answer": "no"}},
        {"key": ("[A]bort", "abort", "a"),
         "desc": "不回答任何内容，并中止。",
         "goto": "end"}
    )
    return text, options

def node_end(caller, raw_input, **kwargs):
    text = "感谢你的回答。再见！"
    return text, None  # 空选项结束菜单

evmenu.EvMenu(caller, {"start": node_question, "end": node_end})

```

注意在末尾对 `EvMenu` 的调用；这会立即为 `caller` 创建菜单。它还将两个节点函数分配给菜单节点名称 `start` 和 `end，`这就是菜单随后用来引用节点的名称。

菜单的每个节点都是一个返回文本和描述可选项列表的函数。

每个选项详细说明它应该显示的内容（键/描述）以及下一个要转到的节点（goto）。 “goto” 应该是下一个要转到的节点名称（如果是 `None`，则会重新运行相同的节点）。

在上面的示例中，`Abort` 选项像字符串一样给出了“end”节点名称，而是使用可调用的 `_handle_answer`，但传递不同的参数给它。 `_handle_answer` 然后返回下一个节点的名称（这使你可以在选择后执行某些操作，然后再跳到菜单的下一个节点）。请注意，`_handle_answer` 不是菜单中的节点，它只是一个辅助函数。

选择“是”（或“否”）时，发生的事情是调用 `_handle_answer` 并回显你的选择，然后导向“end”节点，这将退出菜单（因为它没有返回任何选项）。

你还可以使用 [EvMenu 模板语言](#evmenu-templating-language) 编写菜单。这使你可以使用文本字符串生成更简单的菜单，减少样板。让我们使用模板语言创建完全相同的菜单：

```python
from evennia.utils import evmenu

def _handle_answer(caller, raw_input, **kwargs):
    answer = kwargs.get("answer")
    caller.msg(f"You chose {answer}!")
    return "end"  # 下一个节点的名称

menu_template = """

## node start

你的回答是“是”还是“否”？

## options

[Y]es!;yes;y: 回答“是”。 -> handle_answer(answer=yes)
[N]o!;no;n: 回答“否”。 -> handle_answer(answer=no)
[A]bort;abort;a: 不回答任何内容，并中止。 -> end

## node end

感谢你的回答。再见！

"""

evmenu.template2menu(caller, menu_template, {"handle_answer": _handle_answer})

```

如上所示，`_handle_answer` 相同，但菜单结构在 `menu_template` 字符串中描述。`template2menu` 辅助函数使用模板字符串和可调用的映射（我们必须在这里添加 `handle_answer`）来为我们构建完整的 EvMenu。

这里是另一个菜单示例，我们可以选择如何与 NPC 互动：

```
守卫怀疑地看着你。
“这里没人应该在……” 
他说着，一只手放在他的武器上。
_______________________________________________
 1. 尝试贿赂他 [魅力 + 10金币]
 2. 说服他你在这里工作 [智力]
 3. 向他的虚荣心诉求 [魅力]
 4. 尝试击晕他 [运气 + 敏捷]
 5. 尝试逃跑 [敏捷]
```

```python

def _skill_check(caller, raw_string, **kwargs):
    skills = kwargs.get("skills", [])
    gold = kwargs.get("gold", 0)

    # 在这里执行技能检查，决定检查是否通过
    # 然后基于结果决定返回哪个节点名称...

    return next_node_name

def node_guard(caller, raw_string, **kwarg):
    text = (
        '守卫怀疑地看着你。\n'
        '"这里没人应该在......"\n'
        '他说着，一只手放在他的武器上。'
    options = (
        {"desc": "尝试贿赂 [魅力 + 10金币]",
         "goto": (_skill_check, {"skills": ["Cha"], "gold": 10})},
        {"desc": "说服他你在这里工作 [智力] 。",
         "goto": (_skill_check, {"skills": ["Int"]})},
        {"desc": "向他的虚荣心诉求 [魅力]",
         "goto": (_skill_check, {"skills": ["Cha"]})},
        {"desc": "尝试击晕他 [运气 + 敏捷]",
         "goto": (_skill_check, {"skills": ["Luck", "Dex"]})},
        {"desc": "尝试逃跑 [敏捷]",
         "goto": (_skill_check, {"skills": ["Dex"]})}
    return text, options
    )

# 下面调用 EvMenu，包括所有节点...

```

注意，通过跳过选项的 `key`，我们得到了一个（自动生成的）编号选项列表供选择。

在这里，`_skill_check` 辅助函数将检查（掷骰子，你的属性到底是什么意思取决于你的游戏）以决定你的方法是否成功。然后它可能会选择将你指向继续对话的节点，或者也许把你扔进战斗中！


## 启动菜单

初始化菜单是使用对 `evennia.utils.evmenu.EvMenu` 类的调用来完成的。这是最常见的方式 - 从 [Command](./Commands.md) 内部：

```python
# 在，例如 gamedir/commands/command.py

from evennia.utils.evmenu import EvMenu

class CmdTestMenu(Command):

    key = "testcommand"

    def func(self):

	EvMenu(self.caller, "world.mymenu")

```

运行此命令时，菜单将开始使用从 `mygame/world/mymenu.py` 加载的菜单节点。有关如何定义菜单节点的下一节。

`EvMenu` 有以下可选调用：

```python
EvMenu(caller, menu_data,
       startnode="start",
       cmdset_mergetype="Replace", cmdset_priority=1,
       auto_quit=True, auto_look=True, auto_help=True,
       cmd_on_exit="look",
       persistent=False,
       startnode_input="",
       session=None,
       debug=False,
       **kwargs)

```

 - `caller`（对象或账户）：是使用菜单的对象的引用。这个对象将被分配一个新的 [CmdSet](./Command-Sets.md)，用于处理菜单。
 - `menu_data`（str，模块或 dict）：是一个模块或 Python 路径，模块中的全局级别函数将被视为菜单节点。它们在模块中的名称将是它们在模块中引用的名称。重要的是，以下划线 `_` 开头的函数名称将被加载器忽略。或者，这可以是一个直接映射 `{"nodename":function, ...}`。
 - `startnode`（str）：是菜单节点的名称，用于启动菜单。更改此设置意味着您可以根据情况跳入菜单树的不同位置，从而可能重用菜单条目。
 - `cmdset_mergetype`（str）：通常是 “Replace” 或 “Union” 之一（见 [CmdSets](Command- Sets)）。第一个意味着菜单是独占的 - 用户在菜单中没有访问任何其他命令。联合合并类型意味着菜单与先前命令共存（并可能重载它们，因此在这种情况下要小心命名菜单条目）。
 - `cmdset_priority`（int）：合并菜单命令集的优先级。这允许高级用法。
 - `auto_quit`，`auto_look`，`auto_help`（bool）：如果其中任何一个为 `True`，菜单会自动向用户提供 `quit`、`look` 或 `help` 命令。你会希望关闭这个功能的主要原因是如果你想在菜单中使用别名“q”、“l”或“h”。 `auto_help` 还会在你的菜单节点中启用任意“工具提示”的能力（见下文），至少建议为 `quit` 为 True - 如果为 `False`，则菜单 *必须* 自身提供 “exit node” （没有任何选项的节点），否则用户将被困在菜单中，直到服务器重新加载（或者如果菜单是 `persistent` 则永远被困）！
 - `cmd_on_exit`（str）：此命令字符串将在菜单关闭后立即执行。从经验来看，触发“look”命令以确保用户意识到状态变化是有用的；但可以使用任何命令。如果设置为 `None`，退出菜单后将不会触发命令。
 - `persistent`（bool） - 如果为 `True`，菜单将在重新加载后仍然存在（以便用户不会因重新加载而被踢出 - 确保他们可以自行退出！）
 - `startnode_input`（str 或 (str, dict) 元组）：将输入文本或输入文本+kwargs 传递给起始节点，就像是输入在虚构的前一个节点上。这在根据初始化菜单的命令参数以不同方式启动菜单时非常有用。
 - `session`（Session）：在 `MULTISESSION_MODE` 高于2的情况下从 [Account](./Accounts.md) 调用菜单时很有用，以确保只有正确的会话看到菜单输出。
 - `debug`（bool）：如果设置，菜单中将提供 `menudebug` 命令。使用它列出菜单的当前状态，并使用 `menudebug <variable>` 检查列表中某个特定状态变量。
 - 所有其他关键字参数将在节点的初始数据中可用。它们将作为 `caller.ndb._evmenu` 的属性在所有节点中可用（见下文）。这些在菜单是 `persistent` 时也会在 `reload` 后存活。

您不需要将 `EvMenu` 实例存储在任何地方 - 初始化它的行为将把它存储在 `caller.ndb._evmenu` 中。此对象将在菜单退出时自动删除，您还可以使用它在整个菜单的可访问过程中存储自己的临时变量。您在运行过程中存储在持久的 `_evmenu` 上的临时变量将 *不会* 在 `@reload` 后存活，仅在您在原始 `EvMenu` 调用中设置的存活。

## 菜单节点

EvMenu 节点由以下格式的函数组成。

```python
def menunodename1(caller):
    # 代码
    return text, options

def menunodename2(caller, raw_string):
    # 代码
    return text, options

def menunodename3(caller, raw_string, **kwargs):
    # 代码
    return text, options

```

> 虽然上述所有格式都是可以的，但建议坚持使用第三种和最后一种形式，因为它提供了最大的灵活性。之前的形式主要是为了与当前菜单的向后兼容，与旧版 EvMenu 兼容，可能会在未来被弃用。


### 节点的输入参数

 - `caller`（对象或账户）：使用菜单的对象 - 通常是角色，但也可以是会话或账户，具体取决于菜单的使用位置。
 - `raw_string`（str）：如果提供，则将设置为用户在 *先前* 节点上输入的确切文本（即输入到此节点的命令）。在菜单的起始节点，这将是一个空字符串，除非 `startnode_input` 被设置。
 - `kwargs`（dict）：这些额外的关键字参数是在用户在 *先前* 节点上做出选择时传递给节点的额外可选参数。这可能包括状态标志和有关确切选择了哪个选项的详细信息（单凭 `raw_string` 可能无法确定）。传递到 `kwargs` 中的内容取决于您在创建先前节点时的设计。

### 节点的返回值

每个节点函数都必须返回两个变量，`text` 和 `options`。


#### text

`text` 变量是一个字符串或元组。这是最简单的形式： 

```python
text = "节点文本"
```

这将显示为进入该节点时的菜单节点中的文本。您可以在节点中动态地修改此内容。如果返回 `None` 则允许节点文本为空 - 这将导致一个没有文本的节点，仅包含选项。  

```python
text = ("节点文本", "帮助文本")
```

在这种形式中，我们还添加了可选的帮助文本。如果在初始化 EvMenu 时 `auto_help=True`，用户将能够使用 `h` 或 `help` 查看此文本。如果用户提供了一个自定义选项，覆盖 `h` 或 `help`，则将显示该选项。

如果 `auto_help=True` 且未提供帮助文本，则使用 `h|elp` 将给出通用错误消息。

```python
text = ("节点文本", {"帮助主题 1": "帮助 1",
                      ("帮助主题 2", "别名1", ...): "帮助 2", ...})
```

这是“工具提示”或“多帮助类别”模式。这也要求在初始化 EvMenu 时 `auto_help=True`。通过提供 `dict` 作为 `text` 元组的第二个元素，用户将能够帮助关于这些主题中的任何一个。使用元组作为键可以将多个别名添加到同一帮助条目。这允许用户在不离开给定节点的情况下获取更详细的帮助文本。

注意在“工具提示”模式下，正常的 `h|elp` 命令将不起作用。`h|elp` 条目必须在 dict 中手动添加。作为示例，这将重现正常的帮助功能： 

```python
text = ("节点文本", {("帮助", "h"): "帮助条目...", ...})
```

#### options

`options` 列表描述用户在查看此节点时可用的所有选择。如果 `options` 返回为 `None`，则表示该节点是一个 *退出节点* - 将显示任何文本，然后立即退出菜单，执行 `exit_cmd`（如给定）。

否则，`options` 应该是一个字典列表（或元组），每个选项一个。如果只有一个选项可用，则也可以返回单个字典。这可能看起来像这样：

```python
def node_test(caller, raw_string, **kwargs):

    text = "一个哥布林攻击你！"

    options = (
	{"key": ("攻击", "a", "att"),
         "desc": "全力袭击敌人",
         "goto": "node_attack"},
	{"key": ("防御", "d", "def"),
         "desc": "保持警惕并自我防守",
         "goto": (_defend, {"str": 10, "enemyname": "哥布林"})})

    return text, options

```

这将生成一个菜单节点，显示如下：


```
一个哥布林攻击你！
________________________________

攻击：全力袭击敌人
防御：保持警惕并自我防守

```

##### 选项键 “key”

选项的 `key` 是用户选择该选项所需输入的内容。如果作为元组提供，第一个字符串将是显示在屏幕上的内容，而其余部分是选择该选项的别名。在上面的示例中，用户可以输入“攻击”（或“attack”，不区分大小写）、“a”或“att”来攻击哥布林。别名对于在选择中添加自定义着色非常有用。别名元组的第一个元素应该是彩色版本，后面是没有颜色的版本 - 否则用户需要输入颜色代码来选择该选项。

请注意，`key` 是 *可选的*。如果未提供键，它将自动替换为从 `1` 开始的运行编号。如果移除每个选项的 `key` 部分，结果菜单节点将看起来像这样：

```
一个哥布林攻击你！
________________________________

1：全力袭击敌人
2：保持警惕并自我防守

```

您想使用 `key` 还是依靠数字主要是风格和菜单类型的问题。

EvMenu 接受一个重要的特殊 `key`，仅作为 `"_default"`。 此键在用户输入不匹配任何其他固定键时使用。它在获取用户输入时特别有用：

```python
def node_readuser(caller, raw_string, **kwargs):
    text = "请输入你的名字"

    options = {"key": "_default",
               "goto": "node_parse_input"}

    return text, options

```

`"_default"` 选项不会出现在菜单中，因此上面的节点只会显示 `“请输入你的名字”`。用户输入的名称将在下一个节点中作为 `raw_string` 显示。


#### 选项键 'desc'

这仅包含选择菜单选项时会发生的描述。对于 `"_default"` 选项或如果键本身已经很长或描述性，则不严格需要。但是通常最好保持 `key` 简短，并将更多详细内容放在 `desc` 中。


#### 选项键 'goto'

这是选项的操作部分，只有在用户选择该选项时才会触发。以下是三种编写方式：

```python

def _action_two(caller, raw_string, **kwargs):
    # 执行一些操作...
    return "计算出要去的节点"

def _action_three(caller, raw_string, **kwargs):
    # 执行一些操作...
    return "node_four", {"mode": 4}

def node_select(caller, raw_string, **kwargs):

    text = ("选择一个",
            "帮助 - 它们都有不同的事情...")

    options = ({"desc": "选项一",
		            "goto": "node_one"},
	             {"desc": "选项二",
		            "goto": _action_two},
	             {"desc": "选项三",
		            "goto": (_action_three, {"key": 1, "key2": 2})}
              )

    return text, options

```

如上所示，`goto` 可以指向一个单独的 `nodename` 字符串 - 要转到的节点名称。当给出时，EvMenu 将寻找具有该名称的节点，并调用其关联的函数，如下所示：

```python
    nodename(caller, raw_string, **kwargs)
```

这里，`raw_string` 始终是用户在此节点上输入的内容，`kwargs` 和当前节点的输入相同（它们会被传递）。

另外，`goto` 可以指向“goto-callable”。这些可调用项通常在与菜单节点相同的模块中定义，并以 `_` 开头命名（以避免被解析为节点）。这些可调用项将像节点函数一样调用 - `callable(caller, raw_string, **kwargs)`，其中 `raw_string` 是用户在该节点上输入的内容，`**kwargs` 从节点自己的输入转发。

`goto` 选项键也可以指向一个元组 `(callable, kwargs)` - 这允许在传递给 goto-callable 的 kwargs 中进行自定义，例如，您可以使用同一可调用项，但根据实际选择的选项更改传递给它的 kwargs。

“goto callable” 必须返回一个字符串 “nodename” 或一个元组 `("nodename", mykwargs)`。这将导致下一个节点像这样被调用 `nodename(caller, raw_string, **kwargs)` 或 `nodename(caller, raw_string, **mykwargs)` - 所以这允许根据选择的选项更改（或替换）下一个节点的输入选项。

有一个重要的情况 - 如果 goto-callable 返回 `None` 作为一个 `nodename`， *当前节点将再次运行*，可能有不同的 kwargs。这使得很容易重复使用一个节点，例如允许不同的选项更新一些传递并在每次迭代时进行操作的文本。


### 临时存储

当菜单开始时，EvMenu 实例存储在 `caller` 的 `caller.ndb._evmenu` 中。原则上，只要你知道自己在做什么，就可以通过这个对象访问菜单的内部状态。这也是存储临时的、更全局变量的好地方，这样你就不必通过 `**kwargs` 从节点到节点传递。 `_evmnenu` 将在菜单关闭时自动删除，这意味着您不需要担心清理任何内容。

如果您想要 *永久* 状态存储，那么最好是在 `caller` 上使用属性。请记住，这将在菜单关闭后保持，因此您需要自己处理所需的清理工作。


### 自定义菜单格式

`EvMenu` 节点、选项等的显示由 `EvMenu` 类上的一系列格式化方法控制。要自定义这些，只需创建一个新的子类 `EvMenu` 并根据需要重写。下面是一个示例：

```python
from evennia.utils.evmenu import EvMenu

class MyEvMenu(EvMenu):

    def nodetext_formatter(self, nodetext):
        """
        格式化节点文本。

        参数：
            nodetext (str)：完整的节点文本（描述节点的文本）。

        返回：
            nodetext (str)：格式化的节点文本。

        """

    def helptext_formatter(self, helptext):
        """
        格式化节点的帮助文本

        参数：
            helptext (str)：节点的未格式化帮助文本。

        返回：
            helptext (str)：格式化的帮助文本。

        """

    def options_formatter(self, optionlist):
        """
        格式化选项块。

        参数：
            optionlist (list)：与此节点相关的每个选项的 (key, description) 元组的列表。
            caller (Object, Account 或 None， 可选)：节点的调用者。

        返回：
            options (str)：格式化的选项显示。

        """

    def node_formatter(self, nodetext, optionstext):
        """
        格式化整个节点。

        参数：
            nodetext (str)：由 `self.nodetext_formatter` 返回的节点文本。
            optionstext (str)：由 `self.options_formatter` 返回的选项显示。
            caller (Object, Account 或 None，可选)：节点的调用者。

        返回：
            node (str)：要显示的格式化节点。

        """

```
有关其默认实现的详细信息，请参见 `evennia/utils/evmenu.py`。

## EvMenu 模板语言

在 `evmenu.py` 中，有两个辅助函数 `parse_menu_template` 和 `template2menu`，用于解析 _菜单模板_ 字符串为 EvMenu：

    evmenu.template2menu(caller, menu_template, goto_callables)

你也可以通过生成一个菜单树来按两步执行此操作，并使用它正常调用 EvMenu：

    menutree = evmenu.parse_menu_template(caller, menu_template, goto_callables)
    EvMenu(caller, menutree)

使用后者的解决方案，可以将正常创建的菜单节点与模板引擎生成的节点混合使用。

`goto_callables` 是一个映射 `{"funcname": callable, ...}`，其中每个可调用项必须是模块全局函数，形式为 `funcname(caller, raw_string, **kwargs)`（像任何 goto-callable 一样）。`menu_template` 是以下形式的多行字符串：

```python
menu_template = """

## node node1

节点的文本

## options

key1: desc1 -> node2
key2: desc2 -> node3
key3: desc3 -> node4
"""
```

每个菜单节点由 `## node <name>` 定义，包含节点的文本，然后是 `## options`。`## NODE` 和 `## OPTIONS` 也有效。模板中不允许 Python 代码逻辑，这段代码不会被评估而是被解析。更高级的动态用法需要完整的节点函数。

除了定义节点/选项之外，`#` 充当注释 - 后面的一切将被模板解析器忽略。

### 模板选项

选项语法是

    <key>: [desc ->] nodename or function-call

“desc” 部分是可选的，如果不给出，则可以跳过 `->`：

    key: nodename

键可以是字符串和数字。用 `;` 分隔别名。

    key: node1
    1: node2
    key;k: node3
    foobar;foo;bar;f;b: node4

键以特殊字母 `>` 开头表示之后是什么是全局/正则表达式匹配。

    >: node1          - 匹配空输入
    > foo*: node1     - 以 foo 开头的所有内容
    > *foo: node3     - 以 foo 结尾的所有内容
    > [0-9]+?: node4  - 正则表达式（所有数字）
    > *: node5        - 捕获所有其他内容（放在最后一个选项中）

这是从选项调用 goto-function 的方式：

    key: desc -> myfunc(foo=bar)

为此，`template2menu` 或 `parse_menu_template` 必须提供一个包含 `{"myfunc": _actual_myfunc_callable}` 的字典。可用于模板的所有可调用项必须以这种方式映射。goto 可调用项表现得像正常的 EvMenu goto-callable，并应具有 ` _actual_myfunc_callable(caller, raw_string, **kwargs)` 的调用格式，并返回下一个节点（在模板中传递动态 kwargs 到下一个节点则不起作用 - 如果你想要高级动态数据传递则使用完整的 EvMenu）。

这些可调用项中只允许无参数或命名参数。因此

    myfunc()         # OK
    myfunc(foo=bar)  # OK
    myfunc(foo)      # error!

这是因为这些属性作为 `**kwargs` 传递给 goto 可调用项。

### 模板示例

```python
from random import random
from evennia.utils import evmenu

def _gamble(caller, raw_string, **kwargs):

    caller.msg("你掷骰子...")
    if random() < 0.5:
        return "loose"
    else:
        return "win"

template_string = """

## node start

死亡耐心地将一组骨骰递给你。

“投掷”

他说。

## options

1: 投掷骰子 -> gamble()
2: 尝试说服自己不投掷 -> start

## node win

骰子在石头上叮当作响。

“看来你这次赢了”

死亡说道。

# (由于没有选项，结束菜单)

## node loose

骰子在石头上叮当作响。

“你的运气到了”

死亡说道。

“你要跟我走。”

# (这结束了菜单，但接下来发生什么 - 谁知道！)

"""

# 将模板内可调用名称映射到真实 Python 代码
goto_callables = {"gamble": _gamble}
# 启动 evmenu 为 caller
evmenu.template2menu(caller, template_string, goto_callables)

```

## 请求单行输入

这描述了询问用户简单问题的两种方法。使用 Python 的 `input` 在 Evennia 中 *不* 有效。 `input` 会 *阻塞* 整个服务器，直到那个玩家输入其文本，这不是你想要的。

### `yield` 方法

在你的命令（仅） `func` 方法中，你可以使用 Python 内置的 `yield` 命令请求输入，类似于 `input`。看起来是这样的：

```python
result = yield("请输入你的答案：")
```

这会将“请输入你的答案”发送给命令的 `self.caller`，然后在此点暂停。服务器上的所有其他玩家都不会受到影响。一旦调用者输入回复，代码执行将继续，您可以对 `result` 执行操作。以下是一个示例：

```python
from evennia import Command
class CmdTestInput(Command):
    key = "test"
    def func(self):
        result = yield("请输入一些内容：")
        self.caller.msg(f"你输入了 {result}。")
        result2 = yield("现在再输入一些其他内容：")
        self.caller.msg(f"现在你输入了 {result2}。")
```

使用 `yield` 简单直观，但它仅访问 `self.caller` 的输入，并且无法中止或超时暂停，直到玩家做出回应。在底层，它实际上只是一个包装器，调用以下部分中的 `get_input` 函数。

> 重要提示：在 Python 中 *不能* 在同一方法中混合 `yield` 和 `return <value>`。它与 `yield` 将方法变成一个 [生成器](https://www.learnpython.org/en/Generators) 有关。没有参数的 `return` 是有效的，只需不要执行 `return <value>`。通常在 `func()` 中不需要这样做，但值得记住。

### `get_input` 方法

evmenu 模块提供了一个名为 `get_input` 的辅助函数。它是 `yield` 语句的包装，通常更易于使用和直观。但 `get_input` 提供更多灵活性和强大功能。虽然在与 EvMenu 相同的模块中，`get_input` 从本质上是与它无关。`get_input` 允许你询问并接收用户的简单单行输入，而无需发起完整的菜单来做到这一点。使用时，像这样调用 `get_input`：

```python
get_input(caller, prompt, callback)
```

这里 `caller` 是应该接收作为 `prompt` 提供的输入提示的实体。`callback` 是你定义的处理用户答案的可调用函数 `function(caller, prompt, user_input)`。一旦运行，调用者会在其屏幕上看到 `prompt` 出现，*任何* 输入的文本都将发送到回调中，供你处理。

以下是完全解释的回调和示例调用：

```python
from evennia import Command
from evennia.utils.evmenu import get_input

def callback(caller, prompt, user_input):
    """
    这是你自己定义的回调。

    参数：
        caller (Account 或 Object)：被询问输入的对象
        prompt (str)：当前提示的副本
        user_input (str)：来自账户的输入。

    返回：
        repeat (bool)：如果未设置或为 False，则退出输入提示并清理。如果返回任何内容
        True，保持在提示中，这意味着此回调将再次被调用，处理下一个用户输入。
    """
    caller.msg(f"当被问到 '{prompt}' 时，你回答了 '{user_input}'。")

get_input(caller, "写点什么！", callback)
```

这将显示为

```
写点什么！
> 你好
当被问到 '写点什么！' 时，你回答了 '你好'。

```

通常，`get_input` 函数在任何输入后退出，但如示例文档所示，您可以返回 True 自回调以重复提示，直到您通过所需的检查。

> 注意：您 *不能* 通过在回调中放置新的 `get_input` 调用来链接连续的问题。如果你想要那样，可以使用 EvMenu；否则，你可以查看 `get_input` 的实现并实现自己的机制（它只是使用命令集嵌套），或者可以查看 [邮件列表上建议的扩展](https://groups.google.com/forum/#!category-topic/evennia/evennia-questions/16pi0SfMO5U)。

#### 示例：是/否提示

以下是使用 `get_input` 函数的 Yes/No 提示示例：

```python
def yesno(caller, prompt, result):
    if result.lower() in ("y", "yes", "n", "no"):
        # 处理是/否回答的内容
        # ...
        # 如果返回 None/False，提示状态将在此后退出
    else:
        # 回答不是正确的是/否形式
        caller.msg("请回答“是”或“否”。\n{prompt}")
        # 返回 True 确保提示状态不会退出
        return True

# 提问
get_input(caller, "Evennia 很棒吗（是/否）？", yesno)
```

## `@list_node` 装饰器

`evennia.utils.evmenu.list_node` 是与 `EvMenu` 节点函数一起使用的高级装饰器。它用于快速创建菜单，以操作大量项目。


```
这里的文本
______________________________________________

1. 选项1     7. 选项7      13. 选项13
2. 选项2     8. 选项8      14. 选项14
3. 选项3     9. 选项9      [p]revius page
4. 选项4    10. 选项10      page 2
5. 选项5    11. 选项11     [n]ext page
6. 选项6    12. 选项12

```

该菜单将自动创建一个多页选项列表，可以翻阅。人们可以检查每个条目，然后使用 prev/next 选择。用法如下：

```python
from evennia.utils.evmenu import list_node


...

_options(caller):
    return ['选项1', '选项2', ... '选项100']

_select(caller, menuchoice, available_choices):
    # 分析选择
    return "next_node"

@list_node(options, select=_select, pagesize=10)
def node_mylist(caller, raw_string, **kwargs):
    ...

    return text, options

```

传递给 `list_node` 的 `options` 作为应该在节点中显示每个选项的字符串列表、生成器或可调用对象。

`select` 在上面的示例中是一个可调用项，但也可以是菜单节点的名称。如果是可调用项，`menuchoice` 参数保存已选择的内容，而 `available_choices` 保存所有可用选项。可调用项应该根据选择返回要转到的菜单（或返回 `None` 以重新运行相同的节点）。如果是菜单节点的名称，则该选择将作为 `selection` kwarg 传递给节点。

被装饰的节点本身应返回要在节点中显示的 `text`。它必须返回至少一个空字典以获取选项。返回选项时，它们将补充由 `list_node` 装饰器自动创建的选项。

## 示例菜单

以下是一个图示，帮助可视化数据从节点到节点流动，包括中间的 goto-callables： 

```
        ┌─
        │  def nodeA(caller, raw_string, **kwargs):
        │      text = "选择如何操作 2 和 3。"
        │      options = (
        │          {
        │              "key": "A",
        │              "desc": "将 2 乘以 3",
        │              "goto": (_callback, {"type": "mult", "a": 2, "b": 3})
        │          },                      ───────────────────┬────────────
        │          {                                          │
        │              "key": "B",                            └───────────────┐
        │              "desc": "将 2 和 3 相加",                                 │
  Node A│              "goto": (_callback, {"type": "add", "a": 2, "b": 3})   │
        │          },                      ─────────────────┬─────────────    │
        │          {                                        │                 │
        │              "key": "C",                          │                 │
        │              "desc": "显示值 5",                    │                 │
        │              "goto": ("node_B", {"c": 5})         │                 │
        │          }                      ───────┐          │                 │
        │      )                                 └──────────┼─────────────────┼───┐
        │      return text, options                         │                 │   │
        └─                                       ┌──────────┘                 │   │
                                                 │                            │   │
                                                 │ ┌──────────────────────────┘   │
        ┌─                                       ▼ ▼                              │
        │  def _callback(caller, raw_string, **kwargs):                           │
Goto-   │      if kwargs["type"] == "mult":                                       │
        │          return "node_B", {"c": kwargs["a"] * kwargs["b"]}              │
        │                           ───────────────┬────────────────              │
        │                                          │                              │
        │                                          └───────────────────┐          │
        │                                                              │          │
        │      elif kwargs["type"] == "add":                           │          │
        │          return "node_B", {"c": kwargs["a"] + kwargs["b"]}   │          │
        └─                          ────────┬───────────────────────   │          │
                                            │                          │          │
                                            │ ┌────────────────────────┼──────────┘
                                            │ │                        │
                                            │ │ ┌──────────────────────┘
        ┌─                                  ▼ ▼ ▼
        │  def nodeB(caller, raw_string, **kwargs):
  Node B│      text = "操作的结果：" + kwargs["c"]
        │      return text, {}
        └─

        ┌─
   菜单 │  EvMenu(caller, {"node_A": nodeA, "node_B": nodeB}, startnode="node_A")
   开始│
        └─
```

在上面，我们创建一个非常简单/愚蠢的菜单（在最后的 `EvMenu` 调用中），将节点标识符 `"node_A"` 映射到 Python 函数 `nodeA`，将 `"node_B"` 映射到函数 `nodeB`。 

我们在 `"node_A"` 中启动菜单，在那里我们获得三种选项 A、B 和 C。选项 A 和 B 将通过一个可调用的 `_callback` 路由，该可调用项要么将 2 和 3 相乘，要么相加，然后继续跳到 `"node_B"`。选项 C 直接跳转至 `"node_B"`，传递数字 5。 

在每一步中，我们传递一个 dict，作为下一步进入的 `**kwargs`。如果没有传递任何内容（这是可选的），则下一步的 `**kwargs` 将是空的。

更多示例：

- **[简单分支菜单](./EvMenu.md#example-simple-branching-menu)** - 从选项中选择
- **[动态跳转](./EvMenu.md#example-dynamic-goto)** - 根据响应跳转到不同节点
- **[设置调用者属性](./EvMenu.md#example-set-caller-properties)** - 更改事物的菜单
- **[获取任意输入](./EvMenu.md#example-get-arbitrary-input)** - 输入文本
- **[在节点之间存储数据](./EvMenu.md#example-storing-data-between-nodes)** - 在菜单中保持状态和信息
- **[重复相同节点](./EvMenu.md#example-repeating-the-same-node)** - 验证节点内的输入，然后再移到下一个
- **[是/否提示](#example-yesno-prompt)** - 以有限可能的响应输入文本（这不是使用 EvMenu，而是概念上相似但技术上无关的 `get_input` 辅助函数，通过 `evennia.utils.evmenu.get_input` 访问）


### 示例：简单分支菜单

以下是一个简单分支菜单节点的例子，根据选择引导到不同的其他节点：

```python
# 在 mygame/world/mychargen.py 中

def define_character(caller):
    text = \
    """
    你想更改角色的哪个方面？
    """
    options = ({"desc": "更改名称",
                "goto": "set_name"},
               {"desc": "更改描述",
                "goto": "set_description"})
    return text, options

EvMenu(caller, "world.mychargen", startnode="define_character")

```

这将产生以下节点显示：

```
你想更改角色的哪个方面？
_________________________
1: 更改名称
2: 更改描述
```

注意，由于我们没有指定“名称”键，EvMenu 将让用户输入数字。在以下示例中，我们将不包括 `EvMenu` 调用，但只显示在菜单内运行的节点。 此外，因为 `EvMenu` 还接受一个字典来描述菜单，所以我们在示例中也可以这样调用它：

```python
EvMenu(caller, {"define_character": define_character}, startnode="define_character")

```

### 示例：动态跳转

```python
def _is_in_mage_guild(caller, raw_string, **kwargs):
    if caller.tags.get('mage', category="guild_member"):
        return "mage_guild_welcome"
    else:
        return "mage_guild_blocked"

def enter_guild(caller):
    text = '你对魔法警卫说：'
    options = (
        {'desc': '我需要进入那里。',
         'goto': _is_in_mage_guild},
        {'desc': '没关系',
         'goto': 'end_conversation'}
    )
    return text, options
```

这个简单的可调用跳转会根据 `caller` 的身份分析发生的事情。`enter_guild` 节点将给你一个选择对警卫说什么的机会。如果你尝试进入，你将根据（在此示例中）是否在自己身上设置了正确的 [Tag](./Tags.md) 而被引导到不同的节点。请注意，由于我们没有在选项字典中包含任何 “key”，因此你只会在数字间选择。

### 示例：设置调用者属性

下面是一个将参数传递给 `goto` 可调用项的示例，并使用它来影响下一个节点：

```python
def _set_attribute(caller, raw_string, **kwargs):
    "获取要修改并设置的属性"

    attrname, value = kwargs.get("attr", (None, None))
    next_node = kwargs.get("next_node")

    caller.attributes.add(attrname, value)

    return next_node


def node_background(caller):
    text = f"""
    {caller.key} 在童年时经历了一次创伤事件。
    这是什么呢？
    """

    options = (
        {"key": "death",
         "desc": "家中发生暴力死亡",
         "goto": (_set_attribute, {"attr": ("experienced_violence", True),
                                   "next_node": "node_violent_background"})},
        {"key": "betrayal",
         "desc": "一个值得信赖的成人的背叛",
         "goto": (_set_attribute, {"attr": ("experienced_betrayal", True),
                                   "next_node": "node_betrayal_background"})}
    )
    return text, options
```

这将给出以下输出：

```
Kovash the magnificent 童年时经历了一次创伤事件。
这是什么呢？
____________________________________________________
death: 家中发生暴力死亡
betrayal: 一个值得信赖的成人的背叛
```

上述示例使用 `_set_attribute` 辅助函数根据用户的选择设置属性。在这种情况下，该辅助函数不知道调用它的节点是什么 - 我们甚至告诉它应该返回哪个节点名称，因此选择会导致菜单中的不同路径。我们还可以想象辅助函数可以分析其他选择。

### 示例：获取任意输入

一个示例菜单，询问用户输入任意信息。

```python
def _set_name(caller, raw_string, **kwargs):
    inp = raw_string.strip()

    prev_entry = kwargs.get("prev_entry")

    if not inp:
        # 空输入意味着接受或中止
        if prev_entry:
            caller.key = prev_entry
            caller.msg(f"将名称设置为 {prev_entry}。")
            return "node_background"
        else:
            caller.msg("已中止。")
            return "node_exit"
    else:
        # 重新运行旧节点，但传入所输入的名称
        return None, {"prev_entry": inp}

def enter_name(caller, raw_string, **kwargs):
    # 检查是否已经输入名称
    prev_entry = kwargs.get("prev_entry")

    if prev_entry:
        text = f"当前名称: {prev_entry}。\n输入另一个名称或 <return> 接受。"
    else:
        text = "输入角色的名称或 <return> 中止。"

    options = {"key": "_default",
               "goto": (_set_name, {"prev_entry": prev_entry})}

    return text, options
```

这将显示如下内容：

```
输入角色的名称或 <return> 中止。

> Gandalf

当前名称: Gandalf.
输入另一个名称或 <return> 接受。

>

将名称设置为 Gandalf。
```

在这里，我们重复使用相同的节点两次读取用户输入。输入的任何内容都会被 `_default` 选项捕获，并传递给辅助函数。我们还传递了之前输入的名称，这样可以对“空”输入做出正确反应 - 如果接受输入，继续到名为 `"node_background"` 的节点，或者如果按下 Enter 而未输入任何内容，则返回退出节点。通过从辅助函数返回 `None`，我们能够自动重新运行上一个节点，并更新其输入 kwargs，以显示不同的文本。

### 示例：在节点之间存储数据

可以通过将数据存储在 `caller.ndb._evmenu` 中来方便地存储数据，这可以从每个节点访问。这样做的好处是 `_evmenu` NAttribute 会在退出菜单时自动删除。

```python
def _set_name(caller, raw_string, **kwargs):
    caller.ndb._evmenu.charactersheet = {}
    caller.ndb._evmenu.charactersheet['name'] = raw_string
    caller.msg(f"你将名称设置为 {raw_string}")
    return "node_background"

def node_set_name(caller):
    text = '输入你的名字:'
    options = {'key': '_default',
               'goto': _set_name}

    return text, options

...
def node_view_sheet(caller):
    text = f"角色信息表:\n {caller.ndb._evmenu.charactersheet}"

    options = ({"key": "接受",
                "goto": "finish_chargen"},
               {"key": "拒绝",
                "goto": "start_over"})

    return text, options
```

而不是通过 `kwargs` 在节点之间传递角色信息，我们将其临时设置在 `caller.ndb._evmenu.charactersheet` 上，使其易于从所有节点访问。在结束时查看它，如果接受角色，则菜单可能将结果保存到永久存储并退出。

> 一点要记住的是，存储在 `caller.ndb._evmenu` 上的内容在 `@reloads` 之间并不持久。如果你正在使用持久菜单（`EvMenu(..., persistent=True)`），你应该使用 `caller.db` 来存储菜单数据。你必须自己确保在用户退出菜单时清除这些数据。

### 示例：重复相同节点

有时，你想要将一系列菜单节点连接在一起，但不希望用户在验证输入的内容之前继续到下一个节点。例如，登录菜单的常见示例：

```python
def _check_username(caller, raw_string, **kwargs):
    # 假设 lookup_username() 存在
    if not lookup_username(raw_string):
        # 通过返回 `None` 重新运行当前节点
        caller.msg("|r用户名未找到。请再试一次。")
        return None
    else:
        # 用户名正确 - 继续到下一个节点
        return "node_password"

def node_username(caller):
    text = "请输入你的用户名。"
    options = {"key": "_default",
               "goto": _check_username}
    return text, options

def _check_password(caller, raw_string, **kwargs):
    nattempts = kwargs.get("nattempts", 0)
    if nattempts > 3:
        caller.msg("尝试次数过多。正在注销")
        return "node_abort"
    elif not validate_password(raw_string):
        caller.msg("密码错误。请再试一次。")
        return None, {"nattempts": nattempts + 1}
    else:
        # 密码被接受
        return "node_login"

def node_password(caller, raw_string, **kwargs):
    text = "输入你的密码。"
    options = {"key": "_default",
               "goto": _check_password}
    return text, options
```

这将显示如下内容：

```
---------------------------
请输入你的用户名。
---------------------------

> Fo

------------------------------
用户名未找到。请再试一次。
______________________________
abort: (返回开始)
------------------------------

> Foo

---------------------------
请输入你的密码。
---------------------------

> Bar

--------------------------
密码错误。请再试一次。
--------------------------
```

在这里，`goto` 可调用项将在出现错误时返回到上一个节点。在密码尝试的情况下，将增加 `nattempts` 参数，该参数将从一个迭代传递到下一个迭代，直到尝试次数过多。

### 示例：在字典中定义节点

你还可以直接在字典中定义节点，以便输入到 `EvMenu` 创建器中。

```python
def mynode(caller):
   # 一个正常的菜单节点函数
   return text, options

menu_data = {"node1": mynode,
             "node2": lambda caller: (
                      "这是节点文本",
                     ({"key": "去节点 1",
                       "desc": "去节点 1 (mynode)",
                       "goto": "node1"},
                      {"key": "去节点 2",
                       "desc": "去第三节点",
                       "goto": "node3"})),
             "node3": lambda caller, raw_string: (
                       # ... 等等) }

# 启动菜单，假设 'caller' 在之前可用
EvMenu(caller, menu_data, startnode="node1")
```

字典的键成为节点标识符。你可以使用任何可调用结构在右侧描述每个节点。如果使用 Python 的 `lambda` 表达式，可以非常快速地生成节点。但如果你使用，`lambda` 表达式的功能要比完整的函数有限，无法在其主体中使用诸如 `if` 的关键字。

除非处理相对简单的动态菜单，否则使用 `lambda` 定义菜单可能会更麻烦。通过使每个节点函数更灵活，你可以更容易地创建动态菜单。例如，查看 [NPC 商店教程](../Howtos/Tutorial-NPC-Merchants.md) 获取示例。
