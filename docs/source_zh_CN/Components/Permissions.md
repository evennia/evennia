# 权限

*权限* 只是存储在 `Objects` 和 `Accounts` 上的处理程序 `permissions` 中的一个文本字符串。可以将其视为一种专门用于访问检查的 [Tag](./Tags.md)。因此，它们通常与 [Locks](./Locks.md) 紧密结合。权限字符串不区分大小写，因此 "Builder" 和 "builder" 是相同的。

权限用于方便地构建访问级别和层次结构。它由 `perm` 命令设置，并通过 `PermissionHandler.check` 方法以及专门的 `perm()` 和 `pperm()` [锁函数](./Locks.md)进行检查。

所有新账户都被赋予由 `settings.PERMISSION_ACCOUNT_DEFAULT` 定义的默认权限集。

## 超级用户

严格来说，Evennia 中有两种类型的用户：*超级用户* 和其他所有人。
超级用户是你创建的第一个用户，对象 `#1`。这是一个全能的服务器所有者账户。
从技术上讲，超级用户不仅可以访问所有内容，还可以*绕过*权限检查。

这使得超级用户不可能被锁定，但也使其不适合实际测试游戏的锁和限制（见下面的 `quell`）。通常只需要一个超级用户。

## 使用权限

在游戏中，你可以使用 `perm` 命令来添加和删除权限：

```
> perm/account Tommy = Builders
> perm/account/del Tommy = Builders
```

注意使用 `/account` 开关。这意味着你将权限分配给 [Accounts](./Accounts.md) Tommy，而不是任何也恰好名为 "Tommy" 的 [Character](./Objects.md)。如果你不想使用 `/account`，你也可以在名称前加上 `*` 以指示要查找的是账户：

```
> perm *Tommy = Builders
```

在对象（尤其是 NPC）上设置权限可能有其理由，但为了赋予玩家权力，你通常应该将权限放在 `Account` 上——这可以确保它们被保留，*无论* 他们当前正在操控哪个角色。

这在从*层次结构树*（见下文）分配权限时尤其重要，因为账户的权限将覆盖其角色的权限。因此，为了避免混淆，你通常应该将层次权限放在账户上，而不是他们的角色/操控对象上。

如果你 _确实_ 想开始在你的 _操控对象_ 上使用权限，你可以使用 `quell`：

```
> quell 
> unquell   
```

这会降级到操控对象上的权限，然后再回到你的账户权限。平息在你想“以”他人身份尝试某些事情时很有用。对于超级用户来说，这也很有用，因为这使他们可以受到锁的影响（从而可以测试事物）。

在代码中，你可以通过 `PermissionHandler` 添加/删除权限，它位于所有类型化实体上，作为属性 `.permissions`：

```python
account.permissions.add("Builders")
account.permissions.add("cool_guy")
obj.permissions.add("Blacksmith")
obj.permissions.remove("Blacksmith")
```

### 权限层次结构

通过编辑元组 `settings.PERMISSION_HIERARCHY` 可以将选定的权限字符串组织成一个*权限层次结构*。Evennia 的默认权限层次结构如下（按权力递增顺序）：

```
Guest            # 临时账户，仅在 GUEST_ENABLED=True 时使用（最低）
Player           # 可以聊天和发送消息（默认级别）
Helper           # 可以编辑帮助文件
Builder          # 可以编辑世界
Admin            # 可以管理账户
Developer        # 类似超级用户，但受锁影响（最高）
```

（除了不区分大小写，层次权限还理解复数形式，因此你可以交替使用 `Developers` 和 `Developer`）。

当检查层次权限时（使用以下方法之一），你将通过检查你的级别*及以下*。也就是说，如果你拥有“Admin”层次权限，你也将通过要求“Builder”、“Helper”等的检查。

相比之下，如果你检查非层次权限，如“Blacksmith”，你必须*完全*拥有该权限才能通过。

### 检查权限

需要注意的是，当你检查一个*操控* [Object](./Objects.md)（如角色）的权限时，检查将始终首先使用连接到该对象的任何 `Account` 的权限，然后再检查对象上的权限。在层次权限（Admins, Builders 等）的情况下，将始终使用账户权限（这可以阻止账户通过操控高级角色来提升其权限）。如果查找的权限不在层次结构中，则需要精确匹配，首先在账户上检查，如果未找到（或没有连接的账户），则在对象本身上检查。

### 使用 obj.permissions.check() 检查

检查实体是否具有权限的最简单方法是检查其 _PermissionHandler_，它存储为所有类型化实体上的 `.permissions`。

```python
if obj.permissions.check("Builder"):
    # 允许建造者执行操作

if obj.permissions.check("Blacksmith", "Warrior"):
    # 为铁匠或战士执行操作

if obj.permissions.check("Blacksmith", "Warrior", require_all=True):
    # 仅为同时是铁匠和战士的人执行操作
```

使用 `.check` 方法是推荐的方式，它将考虑层次权限、检查账户/会话等。

```{warning}
不要将 `.permissions.check()` 与 `.permissions.has()` 混淆。`.has()` 方法检查字符串是否在该 PermissionHandler 上专门定义。它不会考虑权限层次结构、操控等。如果你正在操作权限，`.has` 可能有用，但在进行访问检查时请使用 `.check`。
```

### 锁函数

虽然 `PermissionHandler` 提供了一种简单的方式来检查权限，[锁字符串](./Locks.md) 提供了一种描述如何访问某物的小型语言。`perm()` _锁函数_ 是在锁中使用权限的主要工具。

假设我们有一个 `red_key` 对象。我们还有红色的箱子，我们希望用这个钥匙解锁这些箱子。

```
perm red_key = unlocks_red_chests
```

这为 `red_key` 对象赋予了“unlocks_red_chests”权限。接下来我们锁定我们的红色箱子：

```
lock red chest = unlock:perm(unlocks_red_chests)
```

当尝试用这把钥匙解锁红色箱子时，箱子类型类可以获取钥匙并进行访问检查：

```python
# 在定义箱子的某个类型类文件中

class TreasureChest(Object):

  # ...

  def open_chest(self, who, tried_key):

      if not chest.access(who, tried_key, "unlock"):
          who.msg("钥匙不合适！")
          return
      else:
          who.msg("钥匙合适！箱子打开了。")
          # ...
```

默认的 `perm` 锁函数有几种变体：

- `perm_above` - 需要比提供的层次权限*更高*的权限。例如：`"edit: perm_above(Player)"`
- `pperm` - 仅查看 `Accounts` 上的权限，从不查看任何操控对象（无论是否为层次权限）。
- `pperm_above` - 类似 `perm_above`，但仅适用于账户。

### 一些示例

添加权限并使用锁进行检查

```python
account.permissions.add("Builder")
account.permissions.add("cool_guy")
account.locks.add("enter:perm_above(Player) and perm(cool_guy)")
account.access(obj1, "enter") # 这将返回 True！
```

一个具有连接账户的操控对象的示例：

```python
account.permissions.add("Player")
puppet.permissions.add("Builders")
puppet.permissions.add("cool_guy")
obj2.locks.add("enter:perm_above(Accounts) and perm(cool_guy)")

obj2.access(puppet, "enter") # 这将返回 False，因为操控对象权限低于账户权限，并且权限优先。
```

## 平息

`quell` 命令可用于强制 `perm()` 锁函数忽略账户上的权限，而仅使用角色上的权限。这可以用于例如员工以较低权限级别测试事物。使用 `unquell` 返回正常操作。请注意，平息将使用账户或角色上的任何层次权限中的最小值，因此无法通过平息到高权限角色来提升账户权限。超级用户也可以通过这种方式平息他们的权力，使他们可以受到锁的影响。
</details>
