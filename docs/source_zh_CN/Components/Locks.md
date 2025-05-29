# 锁

对于大多数游戏来说，限制玩家的行为是个好主意。在 Evennia 中，这种限制通过称为*锁*的机制来应用和检查。所有 Evennia 实体（[命令](./Commands.md)、[对象](./Objects.md)、[脚本](./Scripts.md)、[账户](./Accounts.md)、[帮助系统](./Help-System.md)、[消息](./Msg.md) 和 [频道](./Channels.md)）都是通过锁来访问的。

锁可以被视为限制 Evennia 实体特定使用的“访问规则”。每当另一个实体想要进行这种访问时，锁将以不同的方式分析该实体，以确定是否应授予访问权限。Evennia 实现了一种“锁定”理念——所有实体都是不可访问的，除非你明确定义一个允许部分或全部访问的锁。

让我们举个例子：一个对象上有一个锁，限制了人们如何“删除”该对象。除了知道它限制了删除之外，锁还知道只有 ID 为 `34` 的玩家才被允许删除它。所以每当一个玩家尝试在对象上运行 `delete` 时，`delete` 命令会确保检查这个玩家是否真的被允许这样做。它调用锁，然后检查玩家的 ID 是否为 `34`。只有这样，它才会允许 `delete` 继续其工作。

## 使用锁

游戏中的命令用于在对象上设置锁是 `lock`：

```
> lock obj = <lockstring>
```

`<lockstring>` 是一个特定格式的字符串，用于定义锁的行为。我们将在下一部分详细介绍 `<lockstring>` 的格式。

在代码中，Evennia 通过通常称为 `locks` 的机制来处理所有相关实体上的锁。这是一个处理器，允许你添加、删除和检查锁。

```python
myobj.locks.add(<lockstring>)
```

可以调用 `locks.check()` 来执行锁检查，但为了隐藏底层实现，所有对象也有一个方便的函数叫做 `access`。最好使用这个函数。在下面的示例中，`accessing_obj` 是请求“删除”访问的对象，而 `obj` 是可能被删除的对象。这是它在 `delete` 命令内部的样子：

```python
if not obj.access(accessing_obj, 'delete'):
    accessing_obj.msg("抱歉，你不能删除它。")
    return
```

### 定义锁

在 Evennia 中定义锁（即访问限制）是通过向对象的 `locks` 属性添加简单的锁定义字符串来完成的，使用 `obj.locks.add()`。

以下是一些锁字符串的示例（不包括引号）：

```python
delete:id(34)   # 仅允许对象 #34 删除
edit:all()      # 允许所有人编辑
# 只有那些不是“very_weak”或是管理员的人可以拾取这个
get: not attr(very_weak) or perm(Admin)
```

形式上，锁字符串具有以下语法：

```python
access_type: [NOT] lockfunc1([arg1,..]) [AND|OR] [NOT] lockfunc2([arg1,...]) [...]
```

其中 `[]` 表示可选部分。`AND`、`OR` 和 `NOT` 不区分大小写，多余的空格会被忽略。`lockfunc1, lockfunc2` 等是锁系统中可用的特殊_锁函数_。

因此，锁字符串由限制类型（`access_type`）、一个冒号（`:`）和一个涉及函数调用的表达式组成，确定通过锁所需的条件。每个函数返回 `True` 或 `False`。`AND`、`OR` 和 `NOT` 的工作方式与 Python 中相同。如果总结果为 `True`，则通过锁。

你可以通过在锁字符串中用分号（`;`）分隔来创建多个锁类型。下面的字符串与前面的示例结果相同：

```
delete:id(34);edit:all();get: not attr(very_weak) or perm(Admin)
```

### 有效的 access_types

`access_type` 是锁字符串的第一部分，定义了锁控制的能力类型，例如“delete”或“edit”。原则上，你可以为 `access_type` 命名任何名称，只要它在特定对象中是唯一的。访问类型的名称不区分大小写。

如果你想确保锁被使用，你应该选择你（或默认命令集）实际检查的 `access_type` 名称，例如上面使用的 `delete` 示例中的 'delete' `access_type`。

以下是默认命令集检查的 access_types。

- [命令](./Commands.md)
  - `cmd` - 这定义了谁可以调用此命令。
- [对象](./Objects.md):
  - `control` - 谁是对象的“所有者”。可以设置锁、删除它等。默认为对象的创建者。
  - `call` - 谁可以调用存储在此对象上的对象命令，除了对象本身。默认情况下，对象与同一位置的任何人共享其命令（例如，你可以在房间中“按下”一个 `Button` 对象）。对于角色和怪物（可能只为自己使用这些命令，不想共享），通常应完全关闭，使用类似 `call:false()` 的设置。
  - `examine` - 谁可以检查此对象的属性。
  - `delete` - 谁可以删除对象。
  - `edit` - 谁可以编辑对象的属性和属性。
  - `view` - 如果 `look` 命令将在描述中显示/列出此对象，并且你将能够看到其描述。请注意，如果你通过名称专门定位它，系统仍然会找到它，只是无法查看它。请参见 `search` 锁以完全隐藏项目。
  - `search` - 这控制对象是否可以通过 `DefaultObject.search` 方法找到（通常在命令中用 `caller.search` 引用）。这是创建完全“不可检测”游戏对象的方法。如果不明确设置此锁，则假定所有对象都是可搜索的。
  - `get`- 谁可以拾取对象并随身携带。
  - `puppet` - 谁可以“成为”此对象并将其作为他们的“角色”进行控制。
  - `attrcreate` - 谁可以在对象上创建新属性（默认 True）
- [角色](./Objects.md#characters):
  - 与对象相同
- [出口](./Objects.md#exits):
  - 与对象相同
  - `traverse` - 谁可以通过出口。
- [账户](./Accounts.md):
  - `examine` - 谁可以检查账户的属性。
  - `delete` - 谁可以删除账户。
  - `edit` - 谁可以编辑账户的属性和属性。
  - `msg` - 谁可以向账户发送消息。
  - `boot` - 谁可以踢出账户。
- [属性](./Attributes.md): （仅由 `obj.secure_attr` 检查）
  - `attrread` - 查看/访问属性
  - `attredit` - 更改/删除属性
- [频道](./Channels.md):
  - `control` - 谁在管理频道。这意味着能够删除频道、踢出监听者等。
  - `send` - 谁可以发送到频道。
  - `listen` - 谁可以订阅和收听频道。
- [帮助条目](./Help-System.md):
  - `view` - 如果帮助条目标题应显示在帮助索引中
  - `read` - 谁可以查看此帮助条目（通常是所有人）
  - `edit` - 谁可以编辑此帮助条目。

举个例子，每当要穿越一个出口时，会检查一个类型为 *traverse* 的锁。因此，为出口对象定义合适的锁类型将涉及一个锁字符串 `traverse: <lock functions>`。

### 自定义 access_types

如上所述，锁的 `access_type` 部分只是锁的“名称”或“类型”。文本是一个任意字符串，必须在对象中是唯一的。如果添加与对象上已存在的锁具有相同 `access_type` 的锁，新锁将覆盖旧锁。

例如，如果你想创建一个公告板系统，并想限制谁可以阅读公告板或发布到公告板。你可以定义如下的锁：

```python
obj.locks.add("read:perm(Player);post:perm(Admin)")
```

这将为具有 `Player` 权限或更高权限的角色创建一个“read”访问类型，并为具有 `Admin` 权限或更高权限的角色创建一个“post”访问类型（参见下文了解 `perm()` 锁函数的工作原理）。在测试这些权限时，只需像这样检查（在此示例中，`obj` 可能是公告板系统上的一个公告板，`accessing_obj` 是尝试阅读公告板的玩家）：

```python
if not obj.access(accessing_obj, 'read'):
    accessing_obj.msg("抱歉，你不能阅读这个。")
    return
```

### 锁函数

_锁函数_ 是一个普通的 Python 函数，放置在 Evennia 查找这些函数的位置。Evennia 查找的模块是列表 `settings.LOCK_FUNC_MODULES`。*所有函数* 在这些模块中的任何一个将自动被视为有效的锁函数。默认的锁函数在 `evennia/locks/lockfuncs.py` 中可以找到，你可以在 `mygame/server/conf/lockfuncs.py` 中开始添加自己的锁函数。你可以通过设置添加更多模块路径。要替换默认锁函数，只需添加一个具有相同名称的函数。

这是锁函数的基本定义：

```python
def lockfunc_name(accessing_obj, accessed_obj, *args, **kwargs):
    return True # 或 False
```

`accessing object` 是想要获得访问权限的对象。`accessed object` 是被访问的对象（具有锁的对象）。函数始终返回一个布尔值，确定锁是否通过。

`*args` 将成为传递给锁函数的参数元组。因此，对于锁字符串 `"edit:id(3)"`（一个名为 `id` 的锁函数），锁函数中的 `*args` 将是 `(3,)`。

`**kwargs` 字典始终由 Evennia 提供一个默认关键字，`access_type`，这是一个字符串，表示正在检查的访问类型。对于锁字符串 `"edit:id(3)"`，`access_type` 将是 `"edit"`。这在默认 Evennia 中未使用。

在锁定义中显式给出的任何参数将作为额外参数出现。

```python
# 一个简单的示例锁函数。用例如 `id(34)` 调用。这是在例如 mygame/server/conf/lockfuncs.py 中定义的

def id(accessing_obj, accessed_obj, *args, **kwargs):
    if args:
        wanted_id = args[0]
        return accessing_obj.id == wanted_id
    return False
```

以上可以在锁函数中这样使用：

```python
# 我们从前面有 `obj` 和 `owner_object`
obj.locks.add(f"edit: id({owner_object.id})")
```

我们可以用类似这样的方式检查“edit”锁是否通过：

```python
# 例如作为命令的 func() 方法的一部分
if not obj.access(caller, "edit"):
    caller.msg("你没有权限编辑这个！")
    return
```

在此示例中，除了具有正确 `id` 的 `caller` 之外，其他人都会收到错误。

> （使用 `*` 和 `**` 语法会使 Python 自动将所有额外参数放入列表 `args` 中，并将所有关键字参数放入字典 `kwargs` 中。如果你不熟悉 `*args` 和 `**kwargs` 的工作原理，请参阅 Python 手册）。

一些有用的默认锁函数（请参阅 `src/locks/lockfuncs.py`）：

- `true()/all()` - 允许所有人访问
- `false()/none()/superuser()` - 不允许任何人访问。超级用户完全绕过检查，因此是唯一会通过此检查的人。
- `perm(perm)` - 这会尝试匹配给定的 `permission` 属性，首先在账户上，其次在角色上。请参见[下文](./Permissions.md)。
- `perm_above(perm)` - 类似于 `perm`，但要求比给定的权限级别更高。
- `id(num)/dbref(num)` - 检查访问对象是否具有某个 dbref/id。
- `attr(attrname)` - 检查访问对象上是否存在某个 [属性](./Attributes.md)。
- `attr(attrname, value)` - 检查访问对象上是否存在某个属性*并且*具有给定的值。
- `attr_gt(attrname, value)` - 检查访问对象上是否具有大于（`>`）给定值的属性。
- `attr_ge, attr_lt, attr_le, attr_ne` - 分别对应于 `>=`、`<`、`<=` 和 `!=`。
- `tag(tagkey[, category])` - 检查访问对象是否具有指定的标签和可选类别。
- `objtag(tagkey[, category])` - 检查*被访问对象*是否具有指定的标签和可选类别。
- `objloctag(tagkey[, category])` - 检查*被访问对象*的位置是否具有指定的标签和可选类别。
- `holds(objid)` - 检查访问对象是否包含给定名称或 dbref 的对象。
- `inside()` - 检查访问对象是否在被访问对象内部（`holds()` 的反向）。
- `pperm(perm)`、`pid(num)/pdbref(num)` - 与 `perm`、`id/dbref` 相同，但始终查找*账户*的权限和 dbref，而不是角色。
- `serversetting(settingname, value)` - 仅在 Evennia 具有给定设置或设置为给定值时返回 True。

### 检查简单字符串

有时你不需要查找特定的锁，只是想检查一个锁字符串。一个常见的用法是在命令内部，以检查用户是否具有某个权限。锁处理器有一个方法 `check_lockstring(accessing_obj, lockstring, bypass_superuser=False)` 来实现这一点。

```python
# 在命令定义内部
if not self.caller.locks.check_lockstring(self.caller, "dummy:perm(Admin)"):
    self.caller.msg("你必须是管理员或更高权限才能执行此操作！")
    return
```

请注意，由于此方法实际上不执行锁查找，因此 `access_type` 可以留作一个虚拟值。

### 默认锁

Evennia 为所有新对象和账户设置了一些基本锁（如果我们不这样做，从一开始就没有人能访问任何东西）。这在各自实体的根[类型类](./Typeclasses.md)中定义，在钩子方法 `basetype_setup()` 中（通常你不想编辑它，除非你想更改房间和出口存储其内部变量的基本方式）。这在 `at_object_creation` 之前调用一次，因此只需将它们放在子对象的后一个方法中即可更改默认值。此外，创建命令如 `create` 会更改你创建的对象的锁——例如，它设置 `control` 锁类型，以允许你（其创建者）控制和删除对象。

## 更多锁定义示例

```
examine: attr(eyesight, excellent) or perm(Builders)
```

只有当你具有“优秀”的视力（即在自己身上定义了一个值为 `excellent` 的属性 `eyesight`）或具有“Builders”权限字符串时，才允许你对这个对象进行*检查*。

```
open: holds('the green key') or perm(Builder)
```

这可以由“门”对象上的 `open` 命令调用。如果你是 Builder 或在你的库存中有正确的钥匙，则通过检查。

```
cmd: perm(Builders)
```

Evennia 的命令处理器查找类型为 `cmd` 的锁，以确定用户是否被允许调用特定命令。当你定义一个命令时，这就是你必须设置的锁类型。请参阅默认命令集中的大量示例。如果角色/账户未通过 `cmd` 锁类型，则命令甚至不会出现在他们的 `help` 列表中。

```
cmd: not perm(no_tell)
```

“权限”也可以用于阻止用户或实施高度特定的禁令。上述示例将作为锁字符串添加到 `tell` 命令。这将允许所有*没有*“权限” `no_tell` 的人使用 `tell` 命令。你可以轻松地给一个账户赋予“权限” `no_tell`，以此来禁用他们对这个特定命令的使用。

```python
dbref = caller.id
lockstring = "control:id(%s);examine:perm(Builders);delete:id(%s) or perm(Admin);get:all()" % (dbref, dbref)
new_obj.locks.add(lockstring)
```

这就是 `create` 命令设置新对象的方式。按顺序，此权限字符串将该对象的所有者设置为创建者（运行 `create` 的人）。Builders 可以检查对象，而只有管理员和创建者可以删除它。每个人都可以拾取它。

### 一个完整的设置对象锁的示例

假设我们有两个对象——一个是我们自己（不是超级用户），另一个是一个称为 `box` 的[对象](./Objects.md)。

```
> create/drop box
> desc box = "这是一个非常大且沉重的箱子。"
```

我们想限制哪些对象可以拾起这个沉重的箱子。假设要做到这一点，我们要求潜在的举重者在自己身上有一个属性 *strength*，其值大于 50。我们首先将其分配给自己。

```
> set self/strength = 45
```

好的，所以为了测试我们让自己变得强壮，但还不够强壮。现在我们需要看看当有人试图拾起这个箱子时会发生什么——他们使用默认集合中的 `get` 命令。在其代码中，我们找到这个代码段：

```python
if not obj.access(caller, 'get'):
    if obj.db.get_err_msg:
        caller.msg(obj.db.get_err_msg)
    else:
        caller.msg("你不能拿这个。")
    return
```

所以 `get` 命令查找类型为 *get* 的锁（不太令人惊讶）。它还查找被检查对象上的一个称为 _get_err_msg_ 的[属性](./Attributes.md)，以返回自定义错误消息。听起来不错！我们先在箱子上设置这个：

```
> set box/get_err_msg = 你没有足够的力量来抬起这个箱子。
```

接下来，我们需要在我们的箱子上设置一个类型为 *get* 的锁。我们希望它只有在访问对象具有正确值的属性 *strength* 时才会通过。为此，我们需要创建一个锁函数来检查属性是否具有大于给定值的值。幸运的是，Evennia 中已经包含了这样一个锁函数（请参阅 `evennia/locks/lockfuncs.py`），称为 `attr_gt`。

所以锁字符串将如下所示：`get:attr_gt(strength, 50)`。我们现在将其放在箱子上：

```
lock box = get:attr_gt(strength, 50)
```

尝试 `get` 该对象，你应该收到我们不够强壮的消息。然而，将你的力量增加到 50 以上，你就可以毫无问题地拾起它。完成！一个非常沉重的箱子！

如果你想在 Python 代码中设置这个，它看起来像这样：

```python
from evennia import create_object

# 创建，然后设置锁
box = create_object(None, key="box")
box.locks.add("get:attr_gt(strength, 50)")

# 或者我们可以立即在创建时分配锁
box = create_object(None, key="box", locks="get:attr_gt(strength, 50)")

# 设置属性
box.db.desc = "这是一个非常大且沉重的箱子。"
box.db.get_err_msg = "你没有足够的力量来抬起这个箱子。"

# 一个沉重的箱子，准备好抵挡所有但最强壮的人……
```

## 关于 Django 的权限系统

Django 还实现了一个全面的权限/安全系统。我们不使用它的原因是因为它是以应用程序为中心的（在 Django 的意义上）。其权限字符串的形式为 `appname.permstring`，并且它会为应用程序中的每个数据库模型自动添加三个权限——对于应用程序 evennia/object，这将是例如 'object.create'、'object.admin' 和 'object.edit'。这对于 Web 应用程序来说很有意义，但对于 MUD 来说则不然，尤其是当我们尝试尽可能隐藏底层架构时。

然而，Django 的权限并没有完全消失。我们在登录期间使用它来验证密码。它还专门用于管理 Evennia 的基于 Web 的管理站点，这是 Evennia 数据库的图形前端。你可以直接从 Web 界面编辑和分配这些权限。它与上面描述的权限是独立的。
