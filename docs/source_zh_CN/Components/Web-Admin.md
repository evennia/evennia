# Web 管理后台

Evennia 的 _Web 管理后台_ 是一个定制的 [Django 管理站点](https://docs.djangoproject.com/en/4.1/ref/contrib/admin/)，用于通过图形界面操作游戏数据库。你需要登录网站才能使用它。登录后，它会作为一个 `Admin` 链接出现在你网站的顶部。当在本地运行时，你也可以访问 [http://localhost:4001/admin](http://localhost:4001/admin)。

几乎所有在管理后台完成的操作也可以通过使用管理员或构建者命令在游戏中完成。

## 使用方法

管理后台非常直观——你可以看到每种对象类型的列表，创建每种类型的新实例，还可以为它们添加新属性/标签。管理首页将总结所有相关实体及其使用情况。

不过，有一些用例需要额外的解释。

### 向属性添加对象

属性的 `value` 字段被封装成一种特殊形式。这通常不是你需要担心的事情（管理后台会为你封装/解封装值），_除非_ 你想在属性中存储一个数据库对象。这类对象实际上是作为一个 `tuple` 存储的，包含对象唯一的数据。

1. 找到你想添加到属性中的对象。在第一个部分的底部，你会找到字段 _Serialized string_。这个字符串显示一个 Python 元组，例如：

   ```
   ('__packed_dbobj__', ('objects', 'objectdb'), '2021:05:15-08:59:30:624660', 358)
   ```

   精确复制这个元组字符串（包括括号）到你的剪贴板。

2. 转到应该拥有新属性的实体并创建该属性。在其 `value` 字段中，粘贴之前复制的元组字符串。保存！

3. 如果你想在一个列表中存储多个对象，你可以通过字面输入一个 Python 列表 `[tuple, tuple, tuple, ...]` 来实现，其中你用逗号粘贴序列化的元组字符串。不过，在某些时候，通过代码来完成可能更容易。

### 关联账户和角色

在 `MULTISESSION_MODE` 0 或 1 中，每个连接可以有一个账户和一个角色，通常具有相同的名称。通常这是通过用户创建新账户并登录来完成的——然后会为他们创建一个匹配的角色。不过，你也可以在管理后台手动完成：

1. 首先在管理后台中创建完整的账户。
2. 接下来，创建一个对象（通常是 `Character` typeclass），并将其命名为与账户相同的名称。它还需要一个命令集。默认的 CharacterCmdset 是一个不错的选择。
3. 在 `Puppeting Account` 字段中，选择账户。
4. 确保保存所有内容。
5. 点击 `Link to Account` 按钮（这只有在你先保存的情况下才有效）。这将为账户添加所需的锁和属性，以便他们在下次登录时立即连接到角色。这将（在可能的情况下）：
   - 将 `account.db._last_puppet` 设置为角色。
   - 将角色添加到 `account.db._playable_characters` 列表中。
   - 添加/扩展角色上的 `puppet:` 锁以包括 `puppet:pid(<Character.id>)`

### 使用管理后台构建

可以（尽管在大规模情况下可能不太实用）在管理后台中构建和描述房间。

1. 使用合适的房间名称创建一个 `Room-typeclass` 的 `Object`。
2. 在房间上设置一个名为 'desc' 的属性——此属性的值是房间的描述。
3. 添加 `Tags`，`type` 为 'alias' 以添加房间别名（常规标签没有类型）

出口：

1. 出口是 `Exit` typeclass 的 `Objects`，因此创建一个。
2. 出口的 `Location` 是你刚刚创建的房间。
3. 设置 `Destination` 为出口的目的地。
4. 设置一个 'desc' 属性，当有人查看出口时会显示。
5. `Tags` 类型为 'alias' 是用户可以用来通过此出口的替代名称。

## 授予他人访问管理后台的权限

访问管理后台由账户上的 `Staff status` 标志控制。没有设置此标志，即使是超级用户也不会在网页上看到管理后台链接。员工状态在游戏中没有对应的权限。

只有超级用户可以更改 `Superuser status` 标志，并授予账户新权限。超级用户是唯一在游戏中也相关的权限级别。`Account` 管理页面上的 `User Permissions` 和 `Groups` _仅_ 影响管理后台——它们与游戏中的 [Permissions](./Permissions.md)（Player、Builder、Admin 等）没有联系。

为了让具有 `Staff status` 的员工能够实际执行任何操作，超级用户必须在其账户上至少授予一些权限。这也有助于限制错误。例如，不允许 `Can delete Account` 权限可能是个好主意。

```{important}

  如果你授予员工状态和权限给一个账户，但他们仍然无法访问管理后台的内容，请尝试重新加载服务器。

```

```{warning}

    如果员工可以访问游戏中的 ``py`` 命令，那么他们也可以将其管理后台的 ``Superuser status`` 设置为启用。原因是 ``py`` 赋予他们手动在其账户上设置 ``is_superuser`` 标志所需的所有权限。必须谨慎考虑对 ``py`` 命令的访问 ...

```

## 定制 Web 管理后台

定制管理后台是一个大话题，超出了本文档的范围。详情请参见 [官方 Django 文档](https://docs.djangoproject.com/en/4.1/ref/contrib/admin/)。这里只是一个简要概述。

有关生成网页的组件概述，请参见 [Website](./Website.md) 页面。Django 管理后台使用相同的原则，只是 Django 为我们提供了许多工具来自动生成管理后台。

管理后台模板位于 `evennia/web/templates/admin/` 中，但你会发现这里相对空。这是因为大多数模板直接从其在 Django 包中的原始位置继承（`django/contrib/admin/templates/`）。因此，如果你想覆盖其中一个，你需要从_那里_复制到你的 `mygame/templates/admin/` 文件夹中。CSS 文件也是如此。

管理站点的后端代码（视图）位于 `evennia/web/admin/` 中。它被组织为 `admin` 类，如 `ObjectAdmin`、`AccountAdmin` 等。这些类自动使用底层数据库模型为我们生成有用的视图，而无需我们自己编写表单等代码。

顶级 `AdminSite`（Django 文档中引用的管理配置）位于 `evennia/web/utils/adminsite.py` 中。

### 更改管理后台的标题

默认情况下，管理后台的标题是 `Evennia web admin`。要更改此标题，请将以下内容添加到你的 `mygame/web/urls.py` 中：

```python
# 在 mygame/web/urls.py 中

# ...

from django.conf.admin import site

#...

site.site_header = "My great game admin"
```

重新加载服务器，管理后台的标题将会更改。
