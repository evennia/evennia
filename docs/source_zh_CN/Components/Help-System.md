# 帮助系统

Evennia 的帮助系统非常全面，涵盖了命令帮助和常规的自由格式帮助文档。它支持子主题，并且如果未能找到匹配项，它将首先从替代主题中提供建议，然后通过在帮助条目中查找搜索词的提及来提供建议。

在游戏中，使用 `help` 命令访问帮助系统：

```
help <topic>
```

子主题可以通过 `help <topic>/<subtopic>/...` 访问。

## 处理三种类型的帮助条目

有三种方式生成帮助条目：

- 存储在数据库中
- 作为 Python 模块
- 从命令文档字符串中提取

### 数据库存储的帮助条目

可以通过以下方式在游戏中创建新的帮助条目：

```
sethelp <topic>[;aliases] [,category] [,lockstring] = <text>
```

例如：

```
sethelp The Gods;pantheon, Lore = In the beginning all was dark ...
```

这将在数据库中创建一个新的帮助条目。使用 `/edit` 开关可以打开 EvEditor，以便更方便地在游戏中编写（但请注意，开发人员也可以在游戏外使用常规代码编辑器创建帮助条目，见下文）。

[HelpEntry](evennia.help.models.HelpEntry) 存储数据库帮助。它不是一个类型化实体，不能使用类型类机制进行扩展。

以下是如何在代码中创建数据库帮助条目：

```python
from evennia import create_help_entry
entry = create_help_entry("emote",
                "Emoting is important because ...",
                category="Roleplaying", locks="view:all()")
```

### 文件存储的帮助条目

```{versionadded} 1.0
```

文件帮助条目由游戏开发团队在游戏外创建。帮助条目定义在普通的 Python 模块（以 `.py` 结尾的文件）中，包含一个 `dict` 来表示每个条目。需要服务器 `reload` 才能应用任何更改。

- Evennia 将查看 `settings.FILE_HELP_ENTRY_MODULES` 中给出的所有模块。这应该是 Evennia 要导入的 python-path 列表。
- 如果此模块包含一个顶级变量 `HELP_ENTRY_DICTS`，这将被导入，并且必须是一个帮助条目字典的 `list`。
- 如果未找到 `HELP_ENTRY_DICTS` 列表，模块中每个顶级变量为 `dict` 的条目将被视为帮助条目。在这种情况下，变量名称将被忽略。

如果你添加多个模块以供读取，列表中后面的相同键的帮助条目将覆盖前面的。

每个条目字典必须定义与所有帮助条目匹配的键。以下是一个帮助模块的示例：

```python
# 在 settings.FILE_HELP_ENTRY_MODULES 指向的模块中

HELP_ENTRY_DICTS = [
  {
    "key": "The Gods",   # 不区分大小写，也可以通过 'gods' 搜索
    "aliases": ['pantheon', 'religion'],
    "category": "Lore",
    "locks": "read:all()",  # 可选
    "text": '''
        The gods formed the world ...

        # Subtopics

        ## Pantheon

        The pantheon consists of 40 gods that ...

        ### God of love

        The most prominent god is ...

        ### God of war

        Also known as 'the angry god', this god is known to ...

    '''
  },
  {
    "key": "The mortals",
    # 其他条目...
  }
]
```

帮助条目文本将被去缩进并保留段落。你应该尝试保持字符串的合理宽度（这样看起来会更好）。只需重新加载服务器，基于文件的帮助条目即可查看。

### 命令帮助条目

[Command 类](./Commands.md) 的 `__docstring__` 会自动提取为帮助条目。你可以直接在类上设置 `help_category`。

```python
from evennia import Command

class MyCommand(Command): 
    """ 
    This command is great! 

    Usage: 
      mycommand [argument]

    When this command is called, great things happen. If you 
    pass an argument, even GREATER things HAPPEN!

    """

    key = "mycommand"

    locks: "cmd:all();read:all()"   # 默认 
    help_category = "General"       # 默认
    auto_help = True                # 默认 

    # ...
```

当你更新代码时，命令的帮助也会随之更新。这样做的目的是让开发人员在更改代码的同时更容易维护和更新命令文档。

### 锁定帮助条目

默认的 `help` 命令将所有可用的命令和帮助条目聚集在一起，以便可以搜索或列出。通过在命令/帮助条目上设置锁，可以限制谁可以阅读有关它的帮助。

- 未通过正常 `cmd` 锁的命令将在到达帮助命令之前被删除。在这种情况下，忽略下面的其他两种锁类型。
- `view` 访问类型决定命令/帮助条目是否应在主帮助索引中可见。如果未给出，则假定每个人都可以查看。
- `read` 访问类型决定命令/帮助条目是否可以实际阅读。如果给定 `read` 锁而未给出 `view`，则假定 `read` 锁也适用于 `view` 访问（因此如果你无法阅读帮助条目，它也不会显示在索引中）。如果未给出 `read` 锁，则假定每个人都可以阅读帮助条目。

对于命令，你可以像设置任何锁一样设置与帮助相关的锁：

```python
class MyCommand(Command):
    """
    <命令的文档字符串>
    """
    key = "mycommand"
    # 每个人都可以使用命令，构建者可以在帮助索引中查看，但只有开发人员可以实际阅读帮助（当然，这是一种奇怪的设置！）
    locks = "cmd:all();view:perm(Builders);read:perm(Developers)"
```

数据库帮助条目和文件帮助条目以相同的方式工作（除了不使用 `cmd` 类型锁）。文件帮助示例：

```python
help_entry = {
    # ...
    locks = "read:perm(Developer)",
    # ...
}
```

```{versionchanged} 1.0
   将旧的 'view' 锁更改为控制帮助索引包含，并添加了新的 'read' 锁类型以控制对条目本身的访问。
```

### 自定义帮助系统的外观

这几乎完全通过覆盖 `help` 命令 [evennia.commands.default.help.CmdHelp](evennia.commands.default.help.CmdHelp) 来完成。

由于可用命令可能随时变化，`help` 负责将三种来源的帮助条目（命令/数据库/文件）汇总在一起，并即时搜索它们。它还负责所有输出格式化。

为了更容易调整外观，改变视觉呈现和实体搜索的代码部分已被分解为命令类上的单独方法。在你的 `help` 版本中覆盖这些方法以更改显示或根据需要进行调整。有关详细信息，请参见上面的 API 链接。

## 子主题

```{versionadded} 1.0
```

与其制作一个非常长的帮助条目，不如将 `text` 分解为 _子主题_。在主帮助文本下方显示下一层子主题的列表，允许用户阅读有关某些不适合主文本的特定细节。

子主题使用类似于 markdown 标题的标记。顶级标题必须命名为 `# subtopics`（不区分大小写），后续标题必须是其子标题（例如 `## subtopic name` 等）。所有标题都不区分大小写（帮助命令将对其进行格式化）。主题最多可以嵌套到 5 级（这可能已经太多了）。解析器使用模糊匹配来查找子主题，因此不必完全输入。

以下是带有子主题的 `text` 示例。

```
The theatre is the heart of the city, here you can find ...
（这是主帮助文本，你可以通过 `help theatre` 获得）

# subtopics

## lore

The theatre holds many mysterious things...
（`help theatre/lore`）

### the grand opening

The grand opening is the name for a mysterious event where ghosts appeared ...
（这是 lore 的子子主题，可以通过 `help theatre/lore/grand` 或其他部分匹配访问）

### the Phantom

Deep under the theatre, rumors has it a monster hides ...
（另一个子子主题，可以通过 `help theatre/lore/phantom` 访问）

## layout

The theatre is a two-story building situated at ...
（`help theatre/layout`）

## dramatis personae

There are many interesting people prowling the halls of the theatre ...
（`help theatre/dramatis` 或 `help theathre/drama` 或 `help theatre/personae` 都可以工作）

### Primadonna Ada

Everyone knows the primadonna! She is ...
（在 dramatis personae 下的子主题，可以通过 `help theatre/drama/ada` 等访问）

### The gatekeeper

He always keeps an eye on the door and ...
（`help theatre/drama/gate`）
```

## 技术说明

#### 帮助条目冲突

如果你在三种可用条目类型之间有冲突的帮助条目（同名），优先级为：

```
Command-auto-help > Db-help > File-help
```

`sethelp` 命令（仅处理创建基于数据库的帮助条目）将在新帮助条目可能被同名/类似名命令或基于文件的帮助条目遮盖时发出警告。

#### 帮助条目容器

所有帮助条目（无论来源）都被解析为具有以下属性的对象：

- `key` - 这是主要主题名称。对于命令，这就是命令的 `key`。
- `aliases` - 帮助条目的备用名称。如果主要名称难以记住，这可能很有用。
- `help_category` - 条目的一般分组。这是可选的。如果未给出，它将使用 `settings.COMMAND_DEFAULT_HELP_CATEGORY` 为命令和 `settings.DEFAULT_HELP_CATEGORY` 为文件+数据库帮助条目提供的默认类别。
- `locks` - 锁字符串（对于命令）或 LockHandler（所有帮助条目）。这定义了谁可以阅读此条目。请参阅下一节。
- `tags` - 默认情况下不使用，但可以用于进一步组织帮助条目。
- `text` - 实际的帮助条目文本。这将被去缩进并去除开头和结尾的额外空格。

#### 帮助分页

滚动屏幕的 `text` 将自动由 [EvMore](./EvMore.md) 分页器分页（你可以通过 `settings.HELP_MORE_ENABLED=False` 控制）。如果你使用 EvMore 并希望精确控制分页器应该在哪个地方分页，请用控制字符 `\f` 标记分页。

#### 搜索引擎

由于需要搜索不同类型的数据，帮助系统必须在搜索整个集合之前将所有可能性收集到内存中。它使用 [Lunr](https://github.com/yeraydiazdiaz/lunr.py) 搜索引擎搜索主要的帮助条目集合。Lunr 是一个成熟的引擎，用于网页，比以前的解决方案产生更合理的结果。

一旦找到主要条目，子主题将通过简单的 `==`、`startswith` 和 `in` 匹配进行搜索（此时它们相对较少）。

```{versionchanged} 1.0
  用 lunr 包替换了旧的bag-of-words。
```
