# Evennia 用于角色扮演会话

本教程将解释如何使用一个新的 Evennia 服务器设置一个实时或逐帖桌面风格的游戏。

场景如下：你和一群朋友想在线玩一个桌面角色扮演游戏。你们中的一个将成为游戏大师，你们都同意使用书面文本进行游戏。你们希望能够实时角色扮演（当人们碰巧同时在线时），也希望在他们可以的时候发布帖子，并赶上自他们上次在线以来发生的事情。

我们将需要和使用以下功能：

* 能够让你们中的一个成为具有特殊能力的 *GM*（游戏大师）。
* 玩家可以创建、查看和填写的 *角色表*。它也可以被锁定，以便只有 GM 可以修改。
* 一个 *掷骰机制*，用于 RPG 规则要求的任何类型的骰子。
* *房间*，以提供位置感并分隔正在进行的游戏——这意味着角色从一个位置移动到另一个位置，以及 GM 显式地移动它们。
* *频道*，用于轻松地将文本发送给所有订阅的账户，无论位置如何。
* 账户间的 *消息* 功能，包括同时发送给多个收件人，无论位置如何。

我们会发现大多数这些功能已经是 Evennia 的标准配置的一部分，但我们可以根据我们的特定用例扩展默认设置。下面我们将从头到尾详细说明这些组件。

## 开始

我们假设你从头开始。你需要根据 [快速入门设置](../Setup/Installation.md) 指南安装 Evennia。使用 `evennia init <gamedirname>` 初始化一个新的游戏目录。在本教程中，我们假设你的游戏目录名为 `mygame`。你可以使用默认数据库，并暂时保持所有其他设置为默认。熟悉 `mygame` 文件夹，然后再继续。你可能想浏览 [初学者教程](Beginner-Tutorial/Part1/Beginner-Tutorial-Part1-Overview.md)，以大致了解哪些地方会被修改。

## 游戏大师角色

简要说明：

* 最简单的方法：作为管理员，只需使用标准 `perm` 命令为一个账户赋予 `Admins` 权限。
* 更好但更费力的方法：制作一个自定义命令来设置/取消上述设置，同时调整角色以向其他账户显示你更新的 GM 状态。

### 权限层次结构

Evennia 自带以下 [权限层次结构](../Components/Permissions.md)：*Players, Helpers, Builders, Admins* 和 *Developers*。我们可以更改这些，但这样我们就需要更新我们的默认命令以使用这些更改。我们希望保持简单，因此我们将不同的角色映射到此权限阶梯上。

1. `Players` 是普通玩家的权限。对于在服务器上创建新账户的任何人，这是默认设置。
2. `Helpers` 类似于 `Players`，但他们还可以创建/编辑新的帮助条目。这可以授予愿意帮助撰写背景故事或自定义日志的玩家。
3. `Builders` 在我们的情况下不使用，因为 GM 应该是唯一的世界构建者。
4. `Admins` 是 GM 应该拥有的权限级别。管理员可以执行构建者可以做的所有事情（创建/描述房间等），但也可以踢出账户、重命名它们等。
5. `Developers` 级别权限是服务器管理员，他们能够重启/关闭服务器以及更改权限级别。

> _超级用户_ 不属于层次结构，实际上完全绕过它。我们假设服务器管理员将“只是”开发者。

### 如何授予权限

默认情况下，只有 `Developers` 可以更改权限级别。只有他们可以访问 `@perm` 命令：

```
> perm Yvonne
Permissions on Yvonne: accounts

> perm Yvonne = Admins
> perm Yvonne
Permissions on Yvonne: accounts, admins

> perm/del Yvonne = Admins
> perm Yvonne
Permissions on Yvonne: accounts
```

在添加更高权限时无需删除基本的 `Players` 权限：将使用最高权限。权限级别名称对大小写不敏感。你也可以使用复数和单数形式，因此“Admins”与“Admin”具有相同的权限。

### 可选：制作一个 GM 授权命令

使用 `perm` 可以直接使用，但这只是最低要求。其他账户能否一眼看出谁是 GM 会更好吗？此外，我们不应该真的需要记住权限级别被称为“Admins”。如果我们可以只使用 `@gm <account>` 和 `@notgm <account>` 并同时更改某些内容以使新的 GM 状态显而易见，那会更容易。

所以让我们使这成为可能。我们将做以下事情：

1. 我们将自定义默认角色类。如果此类的对象具有特定标志，其名称将附加字符串 `(GM)`。
2. 我们将添加一个新命令，供服务器管理员正确分配 GM 标志。

#### 角色修改

首先让我们从自定义角色开始。我们建议你浏览 [账户](../Components/Accounts.md) 页面开头，以确保你知道 Evennia 如何区分 OOC“账户对象”（不要与 `Accounts` 权限混淆，这只是一个指定你访问权限的字符串）和 IC“角色对象”。

打开 `mygame/typeclasses/characters.py` 并修改默认 `Character` 类：

```python
# 在 mygame/typeclasses/characters.py 中

# [...]

class Character(DefaultCharacter):
    # [...]
    def get_display_name(self, looker, **kwargs):
        """
        此方法自定义角色名称的显示方式。我们假设
        只有“Developers”和“Admins”类型的权限需要
        特别注意。
        """
        name = self.key
        selfaccount = self.account     # 如果我们没有被控制，将为 None
        lookaccount = looker.account   #              - " -

        if selfaccount and selfaccount.db.is_gm:
           # GM。显示名称为 name(GM)
           name = f"{name}(GM)"

        if lookaccount and \
          (lookaccount.permissions.get("Developers") or lookaccount.db.is_gm):
            # Developers/GMs 看到 name(#dbref) 或 name(GM)(#dbref)
            name = f"{name}(#{self.id})"

        return name
```

上面，我们更改了角色名称的显示方式：如果控制此角色的账户是 GM，我们会在角色名称后附加字符串 `(GM)`，以便每个人都能知道谁是老板。如果我们自己是开发者或 GM，我们将看到附加到角色名称的数据库 ID，这在对具有相同名称的角色进行数据库搜索时会有所帮助。我们将基于具有名为 `is_gm` 的标志（一个 [属性](../Components/Attributes.md)）来确定“gm-ingness”。我们将在下面确保新的 GM 实际上获得此标志。

> **额外练习：** 这只会在 *角色* 被 GM 账户控制时显示 `(GM)` 文本，即，它只会显示给同一位置的人。如果我们希望它也在例如 `who` 列表和频道中弹出，我们需要对 `mygame/typeclasses/accounts.py` 中的 `Account` 类型类进行类似更改。我们将此作为读者的练习。

#### 新的 @gm/@ungm 命令

我们将在这里详细描述如何创建和添加 Evennia [命令](../Components/Commands.md)，希望在将来添加命令时不需要如此详细。我们将在这里构建 Evennia 的默认“mux-like”命令。

打开 `mygame/commands/command.py` 并在底部添加一个新的 Command 类：

```python
# 在 mygame/commands/command.py 中

from evennia import default_cmds

# [...]

import evennia

class CmdMakeGM(default_cmds.MuxCommand):
    """
    更改账户的 GM 状态

    用法：
      @gm <account>
      @ungm <account>

    """
    # 注意使用没有 @ 的键意味着 @gm !gm 等都可以工作
    key = "gm"
    aliases = "ungm"
    locks = "cmd:perm(Developers)"
    help_category = "RP"

    def func(self):
        "实现命令"
        caller = self.caller

        if not self.args:
            caller.msg("用法：@gm account 或 @ungm account")
            return

        accountlist = evennia.search_account(self.args) # 返回一个列表
        if not accountlist:
            caller.msg(f"找不到账户 '{self.args}'")
            return
        elif len(accountlist) > 1:
            caller.msg(f"'{self.args}' 的多个匹配项：{accountlist}")
            return
        else:
            account = accountlist[0]

        if self.cmdstring == "gm":
            # 将某人变成 GM
            if account.permissions.get("Admins"):
                caller.msg(f"账户 {account} 已经是 GM。")
            else:
                account.permissions.add("Admins")
                caller.msg(f"账户 {account} 现在是 GM。")
                account.msg(f"你现在是 GM（由 {caller} 更改）。")
                account.character.db.is_gm = True
        else:
            # 输入了 @ungm - 撤销某人的 GM 状态
            if not account.permissions.get("Admins"):
                caller.msg(f"账户 {account} 不是 GM。")
            else:
                account.permissions.remove("Admins")
                caller.msg(f"账户 {account} 不再是 GM。")
                account.msg(f"你不再是 GM（由 {caller} 更改）。")
                del account.character.db.is_gm
```

该命令所做的只是定位目标账户，并在我们使用 `gm` 时为其分配 `Admins` 权限，或者在使用 `ungm` 别名时撤销它。我们还设置/取消设置 `is_gm` 属性，这是我们之前的新 `Character.get_display_name` 方法所期望的。

> 我们本可以将其分成两个单独的命令，或者选择类似 `gm/revoke <accountname>` 的语法。相反，我们检查此命令是如何调用的（存储在 `self.cmdstring` 中）以便采取相应的行动。两种方式都可以，实用性和编码风格决定了选择哪种方式。

为了实际使此命令可用（仅对开发者，由于其上的锁），我们将其添加到默认的账户命令集中。打开文件 `mygame/commands/default_cmdsets.py` 并找到 `AccountCmdSet` 类：

```python
# mygame/commands/default_cmdsets.py

# [...]
from commands.command import CmdMakeGM

class AccountCmdSet(default_cmds.AccountCmdSet):
    # [...]
    def at_cmdset_creation(self):
        # [...]
        self.add(CmdMakeGM())
```

最后，发出 `reload` 命令以将更改更新到服务器。开发者级别的玩家（或超级用户）现在应该可以使用 `gm/ungm` 命令。

## 角色表

简要说明：

* 使用 Evennia 的 EvTable/EvForm 构建角色表
* 将单个表与给定角色绑定。
* 添加新命令以修改角色表，供账户和 GM 使用。
* 使角色表可由 GM 锁定，以便玩家无法再修改它。

### 构建角色表

有很多方法可以用文本构建角色表，从手动粘贴字符串到更自动化的方法。究竟哪种方法最好/最简单取决于你要创建的表。我们将在这里展示两个使用 *EvTable* 和 *EvForm* 实用程序的示例。稍后我们将创建命令来编辑和显示这些实用程序的输出。

> 请注意，这些文档不显示颜色。请参阅 [文本标签文档](../Concepts/Tags-Parsed-By-Evennia.md) 以了解如何为表格和表单添加颜色。

#### 使用 EvTable 制作表单

[EvTable](../Components/EvTable.md) 是一个文本表格生成器。它有助于以有序的行和列显示文本。这是一个在代码中使用它的示例：

```python
# 这可以在 Python shell 中尝试，例如 iPython

from evennia.utils import evtable

# 我们现在将这些硬编码，以后我们将获取它们作为输入
STR, CON, DEX, INT, WIS, CHA = 12, 13, 8, 10, 9, 13

table = evtable.EvTable("Attr", "Value",
                        table = [
                           ["STR", "CON", "DEX", "INT", "WIS", "CHA"],
                           [STR, CON, DEX, INT, WIS, CHA]
                        ], align='r', border="incols")
```

上面，我们通过直接提供两列创建了一个两列表格。我们还告诉表格右对齐，并使用“incols”边框类型（仅在列之间绘制边框）。`EvTable` 类接受许多参数来自定义其外观，你可以在 [这里查看一些可能的关键字参数](github:evennia.utils.evtable#evtable__init__)。一旦你有了 `table`，你还可以通过 `table.add_row()` 和 `table.add_column()` 追加新的列和行：如果需要，表格将通过空行/列扩展以始终保持矩形。

打印上述表格的结果将是：

```python
table_string = str(table)

print(table_string)

 Attr | Value
~~~~~~+~~~~~~~
  STR |    12
  CON |    13
  DEX |     8
  INT |    10
  WIS |     9
  CHA |    13
```

这是一个简约但有效的角色表。通过将 `table_string` 与其他字符串结合，可以构建一个相当完整的角色图形表示。对于更高级的布局，我们将在接下来查看 EvForm。

#### 使用 EvForm 制作表单

[EvForm](../Components/EvForm.md) 允许创建由文本字符组成的二维“图形”。在此表面上，可以标记和标记矩形区域（“单元格”）以填充内容。此内容可以是普通字符串或 `EvTable` 实例（参见上一节，其中一个实例将是该示例中的 `table` 变量）。

在角色表的情况下，这些单元格可以与输入角色名称或其力量分数的行或框相媲美。EvMenu 还可以轻松地在代码中更新这些字段的内容（它使用 EvTables，因此你需要先重建表格，然后再将其发送到 EvForm）。

EvForm 的缺点是其形状是静态的；如果你尝试在一个区域中放入比其大小更多的文本，文本将被裁剪。类似地，如果你尝试将一个 EvTable 实例放入一个太小的字段中，EvTable 将尽力调整大小以适应，但最终会裁剪其数据，甚至如果太小而无法容纳任何数据，则会给出错误。

EvForm 在 Python 模块中定义。创建一个新文件 `mygame/world/charsheetform.py` 并进行如下修改：

```python
#coding=utf-8

# 在 mygame/world/charsheetform.py 中

FORMCHAR = "x"
TABLECHAR = "c"

FORM = """
.--------------------------------------.
|                                      |
| Name: xxxxxxxxxxxxxx1xxxxxxxxxxxxxxx |
|       xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx |
|                                      |
 >------------------------------------<
|                                      |
| ccccccccccc  Advantages:             |
| ccccccccccc   xxxxxxxxxxxxxxxxxxxxxx |
| ccccccccccc   xxxxxxxxxx3xxxxxxxxxxx |
| ccccccccccc   xxxxxxxxxxxxxxxxxxxxxx |
| ccccc2ccccc  Disadvantages:          |
| ccccccccccc   xxxxxxxxxxxxxxxxxxxxxx |
| ccccccccccc   xxxxxxxxxx4xxxxxxxxxxx |
| ccccccccccc   xxxxxxxxxxxxxxxxxxxxxx |
|                                      |
+--------------------------------------+
"""
```

`#coding` 声明（必须放在第一行才能工作）告诉 Python 使用 utf-8 编码文件。使用 `FORMCHAR` 和 `TABLECHAR` 我们定义了我们想要用来“标记”角色表中包含单元格和表格的区域的单字符。每个块（必须由至少一个非标记字符分隔）中嵌入标识符 1-4 以标识每个块。标识符可以是除 `FORMCHAR` 和 `TABLECHAR` 之外的任何单个字符。

> 你仍然可以在表单的其他地方使用 `FORMCHAR` 和 `TABLECHAR`，但不能以使其标识单元格/表格的方式使用。可识别的最小单元格/表格区域宽度为 3 个字符，包括标识符（例如 `x2x`）。

现在我们将内容映射到此表单。

```python
# 同样，这可以在 Python shell 中测试

# 在这里硬编码此信息，以后我们将询问
# 账户获取此信息。我们将重用来自 EvTable 示例的 'table' 变量。

NAME = "John, the wise old admin with a chip on his shoulder"
ADVANTAGES = "Language-wiz, Intimidation, Firebreathing"
DISADVANTAGES = "Bad body odor, Poor eyesight, Troubled history"

from evennia.utils import evform

# 从模块加载表单
form = evform.EvForm("world/charsheetform.py")

# 将数据映射到表单
form.map(cells={"1":NAME, "3": ADVANTAGES, "4": DISADVANTAGES},
         tables={"2":table})
```

我们创建了一些角色扮演风格的输入，并重用了来自之前 `EvTable` 示例的 `table` 变量。

> 请注意，如果你不想在单独的模块中创建表单，你 *可以* 直接将其加载到 `EvForm` 调用中，如下所示：`EvForm(form={"FORMCHAR":"x", "TABLECHAR":"c", "FORM": formstring})`，其中 `FORM` 指定表单为字符串，与上面模块中列出的方式相同。但请注意，`FORM` 字符串的第一行将被忽略，因此请以 `\n` 开始。

然后我们将它们映射到表单的单元格中：

```python
print(form)
```

```plaintext
.--------------------------------------.
|                                      |
| Name: John, the wise old admin with |
|        a chip on his shoulder        |
|                                      |
 >------------------------------------<
|                                      |
|  Attr|Value  Advantages:             |
| ~~~~~+~~~~~   Language-wiz,          |
|   STR|   12   Intimidation,          |
|   CON|   13   Firebreathing          |
|   DEX|    8  Disadvantages:          |
|   INT|   10   Bad body odor, Poor    |
|   WIS|    9   eyesight, Troubled     |
|   CHA|   13   history                |
|                                      |
+--------------------------------------+
```

如所见，文本和表格已插入到文本区域中，并在需要时添加了换行符。我们选择将优点/缺点作为普通字符串输入，这意味着长名称最终在行之间拆分。如果我们想要更好地控制显示，我们可以在每行后插入 `\n` 换行符，或者使用无边框的 `EvTable` 来显示这些内容。

### 将角色表绑定到角色

我们将假设我们使用上面的 `EvForm` 示例。我们现在需要将其附加到角色，以便可以修改它。为此，我们将稍微修改我们的 `Character` 类：

```python
# mygame/typeclasses/character.py

from evennia.utils import evform, evtable

[...]

class Character(DefaultCharacter):
    [...]
    def at_object_creation(self):
        "仅在对象首次创建时调用"
        # 我们将使用此方法阻止账户更改表单
        self.db.sheet_locked = False
        # 我们存储这些以便可以按需构建这些
        self.db.chardata  = {"str": 0,
                             "con": 0,
                             "dex": 0,
                             "int": 0,
                             "wis": 0,
                             "cha": 0,
                             "advantages": "",
                             "disadvantages": ""}
        self.db.charsheet = evform.EvForm("world/charsheetform.py")
        self.update_charsheet()

    def update_charsheet(self):
        """
        在任何输入数据更改后调用此方法以更新表单。
        """
        data = self.db.chardata
        table = evtable.EvTable("Attr", "Value",
                        table = [
                           ["STR", "CON", "DEX", "INT", "WIS", "CHA"],
                           [data["str"], data["con"], data["dex"],
                            data["int"], data["wis"], data["cha"]]],
                           align='r', border="incols")
        self.db.charsheet.map(tables={"2": table},
                              cells={"1":self.key,
                                     "3":data["advantages"],
                                     "4":data["disadvantages"]})
```

使用 `reload` 使此更改对所有 *新创建的* 角色可用。*已经存在的* 角色将 *不会* 定义角色表，因为 `at_object_creation` 只会调用一次。强制现有角色重新触发其 `at_object_creation` 的最简单方法是在游戏中使用 `typeclass` 命令：

```
typeclass/force <Character Name>
```

### 账户更改角色表的命令

我们将添加一个命令来编辑角色表的部分。打开 `mygame/commands/command.py`。

```python
# 在 mygame/commands/command.py 的末尾

ALLOWED_ATTRS = ("str", "con", "dex", "int", "wis", "cha")
ALLOWED_FIELDNAMES = ALLOWED_ATTRS + \
                     ("name", "advantages", "disadvantages")

def _validate_fieldname(caller, fieldname):
    "验证字段名称的辅助函数。"
    if fieldname not in ALLOWED_FIELDNAMES:
        list_of_fieldnames = ", ".join(ALLOWED_FIELDNAMES)
        err = f"允许的字段名称：{list_of_fieldnames}"
        caller.msg(err)
        return False
    if fieldname in ALLOWED_ATTRS and not value.isdigit():
        caller.msg(f"{fieldname} 必须接收一个数字。")
        return False
    return True

class CmdSheet(MuxCommand):
    """
    编辑角色表上的字段

    用法：
      @sheet field value

    示例：
      @sheet name Ulrik the Warrior
      @sheet dex 12
      @sheet advantages Super strength, Night vision

    如果没有参数，将查看当前角色表。

    允许的字段名称为：
       name,
       str, con, dex, int, wis, cha,
       advantages, disadvantages

    """

    key = "sheet"
    aliases = "editsheet"
    locks = "cmd: perm(Players)"
    help_category = "RP"

    def func(self):
        caller = self.caller
        if not self.args or len(self.args) < 2:
            # 参数不足。显示表单
            if sheet:
                caller.msg(caller.db.charsheet)
            else:
                caller.msg("你没有角色表。")
            return

        # if caller.db.sheet_locked:
            caller.msg("你的角色表已锁定。")
            return

        # 按空格分割输入，一次
        fieldname, value = self.args.split(None, 1)
        fieldname = fieldname.lower() # 忽略大小写

        if not _validate_fieldnames(caller, fieldname):
            return
        if fieldname == "name":
            self.key = value
        else:
            caller.chardata[fieldname] = value
        caller.update_charsheet()
        caller.msg(f"{fieldname} 被设置为 {value}。")
```

此命令的大部分是错误检查，以确保输入了正确类型的数据。注意 `sheet_locked` 属性是如何被检查的，如果没有设置，将返回。

你可以将此命令导入 `mygame/commands/default_cmdsets.py` 并添加到 `CharacterCmdSet` 中，方法与之前将 `@gm` 命令添加到 `AccountCmdSet` 中相同。

### GM 更改角色表的命令

游戏大师使用与玩家基本相同的输入来编辑角色表，除了他们可以在其他玩家而不是自己身上进行编辑。他们也不会被任何 `sheet_locked` 标志阻止。

```python
# 继续在 mygame/commands/command.py 中

class CmdGMsheet(MuxCommand):
    """
    GM 修改角色表

    用法：
      @gmsheet character [= fieldname value]

    开关：
      lock - 锁定角色表，以便账户
             不能再编辑它（GM 仍然可以）
      unlock - 解锁角色表，允许账户
             编辑。

    示例：
      @gmsheet Tom
      @gmsheet Anna = str 12
      @gmsheet/lock Tom

    """
    key = "gmsheet"
    locks = "cmd: perm(Admins)"
    help_category = "RP"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("用法：@gmsheet character [= fieldname value]")

        if self.rhs:
            # rhs（右侧）仅在给定 '=' 时设置。
            if len(self.rhs) < 2:
                caller.msg("你必须指定字段名称和值。")
                return
            fieldname, value = self.rhs.split(None, 1)
            fieldname = fieldname.lower()
            if not _validate_fieldname(caller, fieldname):
                return
            charname = self.lhs
        else:
            # 没有 '='，所以我们一定是想查看角色表
            fieldname, value = None, None
            charname = self.args.strip()

        character = caller.search(charname, global_search=True)
        if not character:
            return

        if "lock" in self.switches:
            if character.db.sheet_locked:
                caller.msg("角色表已锁定。")
            else:
                character.db.sheet_locked = True
                caller.msg(f"{character.key} 不能再编辑他们的角色表。")
        elif "unlock" in self.switches:
            if not character.db.sheet_locked:
                caller.msg("角色表已解锁。")
            else:
                character.db.sheet_locked = False
                caller.msg(f"{character.key} 现在可以编辑他们的角色表。")

        if fieldname:
            if fieldname == "name":
                character.key = value
            else:
                character.db.chardata[fieldname] = value
            character.update_charsheet()
            caller.msg(f"你将 {character.key} 的 {fieldname} 设置为 {value}。")
        else:
            # 仅显示
            caller.msg(character.db.charsheet)
```

`gmsheet` 命令需要额外的参数来指定要编辑的角色的角色表。它还接受 `/lock` 和 `/unlock` 开关以阻止玩家修改他们的表单。

在使用之前，应将其添加到默认的 `CharacterCmdSet` 中，与普通的 `sheet` 相同。由于其上的锁定设置，此命令仅对 `Admins`（即 GM）或更高权限级别可用。

## 掷骰器

Evennia 的 *contrib* 文件夹已经带有一个完整的掷骰器。要将其添加到游戏中，只需将 `contrib.dice.CmdDice` 导入 `mygame/commands/default_cmdsets.py`，并将 `CmdDice` 添加到 `CharacterCmdset` 中，如本教程中其他命令所做的那样。经过 `@reload`，你将能够使用正常的 RPG 风格格式掷骰：

```
roll 2d6 + 3
7
```

使用 `help dice` 查看支持的语法，或查看 `evennia/contrib/dice.py` 了解其实现方式。

## 房间

Evennia 自带房间，因此无需额外工作。GM 将自动拥有所有需要的构建命令。完整的教程可在 [建筑教程](Beginner-Tutorial/Part1/Beginner-Tutorial-Building-Quickstart.md) 中找到。
以下是一些有用的亮点：

* `dig roomname;alias = exit_there;alias, exit_back;alias` - 这是挖掘新房间的基本命令。你可以指定任何出口名称，只需输入出口名称即可到达那里。
* `tunnel direction = roomname` - 这是一个专门的命令，只接受主方向（n,ne,e,se,s,sw,w,nw）以及进/出和上/下。它还会自动在相反方向构建“匹配”出口。
* `create/drop objectname` - 这会在当前位置创建并放置一个新的简单对象。
* `desc obj` - 更改对象的外观描述。
* `tel object = location` - 将对象传送到指定位置。
* `search objectname` - 在数据库中查找对象。

> TODO：描述如何添加一个记录房间，记录说话和姿势到日志文件，以便人们可以在事后访问。

## 频道

Evennia 自带 [频道](../Components/Channels.md)，并在文档中进行了全面描述。为简洁起见，这里是正常使用的相关命令：

* `channel/create = new_channel;alias;alias = short description` - 创建一个新频道。
* `channel/sub channel` - 订阅频道。
* `channel/unsub channel` - 取消订阅频道。
* `channels` 列出所有可用频道，包括你的订阅和你为它们设置的任何别名。

你可以阅读频道历史记录：例如，如果你在 `public` 频道聊天，你可以输入 `public/history` 查看该频道的最后 20 条帖子，或 `public/history 32` 查看从末尾开始的第 32 条帖子向后 20 条帖子。

## 私信

要相互发送私信，玩家可以使用 `page`（或 `tell`）命令：

```
page recipient = message
page recipient, recipient, ... = message
```

玩家可以单独使用 `page` 来查看最新消息。这也适用于他们不在线时发送的消息。
