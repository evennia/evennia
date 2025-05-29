# Nicks

*Nicks*，即*昵称*，是一个允许对象（通常是 [Account](./Accounts.md)）为其他游戏实体分配自定义替代名称的系统。

Nicks 不应与*别名*混淆。在游戏实体上设置别名实际上会更改该实体上的固有属性，游戏中的每个人都可以使用该别名来称呼实体。而*Nick*则是用于映射你自己可以用来指代该实体的不同方式。Nicks 也常用于替换你的输入文本，这意味着你可以为默认命令创建自己的别名。

默认情况下，Evennia 使用三种方式来确定何时尝试进行替换：

- inputline - 每当你在命令行中输入任何内容时都会尝试替换。这是默认设置。
- objects - 仅在引用对象时尝试替换。
- accounts - 仅在引用账户时尝试替换。

以下是在默认命令集中使用它的方法（使用 `nick` 命令）：

```
nick ls = look
```

对于习惯于在日常生活中使用 `ls` 命令的 Unix/Linux 用户来说，这是一个不错的选择。相当于 `nick/inputline ls = look`。

```
nick/object mycar2 = The red sports car
```

在此示例中，替换仅针对期望对象引用的命令进行，例如：

```
look mycar2
```

等同于 "`look The red sports car`"。

```
nick/accounts tom = Thomas Johnsson
```

这对于明确搜索账户的命令很有用：

```
@find *tom
```

可以使用 nicks 来加快输入速度。下面我们为自己添加了一种更快的方式来构建红色按钮。将来只需输入 *rb* 即可执行整个长字符串。

```
nick rb = @create button:examples.red_button.RedButton
```

Nicks 还可以用作构建适合 RP mud 的“recog”系统的起点。

```
nick/account Arnold = The mysterious hooded man
```

nick 替换器还支持 Unix 风格的*模板*：

```
nick build $1 $2 = @create/drop $1;$2
```

这将捕获以空格分隔的参数，并将它们存储在标签 `$1` 和 `$2` 中，以插入到替换字符串中。这个例子允许你输入 `build box crate`，Evennia 会看到 `@create/drop box;crate`。你可以使用任何介于 1 到 99 之间的 `$` 数字，但标记必须在 nick 模式和替换之间匹配。

> 如果你想捕获命令参数的“其余部分”，请确保在其右侧放置一个*没有空格的* `$` 标签——它将接收到直到行尾的所有内容。

你还可以使用 [shell-type 通配符](http://www.linfo.org/wildcard.html)：

- \* - 匹配所有内容。
- ? - 匹配单个字符。
- [seq] - 匹配序列中的所有内容，例如 [xyz] 将匹配 x、y 和 z。
- [!seq] - 匹配*不在*序列中的所有内容，例如 [!xyz] 将匹配除 x、y、z 之外的所有内容。

## 使用 nicks 编码

Nicks 作为 `Nick` 数据库模型存储，并通过 `nicks` 属性从常规 Evennia [对象](./Objects.md)引用——这被称为*NickHandler*。NickHandler 提供有效的错误检查、搜索和转换。

```python
# 一个命令/频道 nick：
obj.nicks.add("greetjack", "tell Jack = Hello pal!")

# 一个对象 nick：
obj.nicks.add("rose", "The red flower", nick_type="object")

# 一个账户 nick：
obj.nicks.add("tom", "Tommy Hill", nick_type="account")

# 我自己的自定义 nick 类型（由我自己的游戏代码以某种方式处理）：
obj.nicks.add("hood", "The hooded man", nick_type="my_identsystem")

# 获取翻译后的 nick：
full_name = obj.nicks.get("rose", nick_type="object")

# 删除先前设置的 nick
obj.nicks.remove("rose", nick_type="object")
```

在命令定义中，你可以通过 `self.caller.nicks` 访问 nick 处理器。有关更多示例，请参阅 `evennia/commands/default/general.py` 中的 `nick` 命令。

最后要注意的是，Evennia [频道](./Channels.md) 别名系统使用 `nick_type="channel"` 的 nicks，以允许用户为频道创建自己的自定义别名。

## 高级说明

在内部，nicks 是 [Attributes](./Attributes.md)，其 `db_attrype` 设置为 "nick"（普通 Attributes 的此设置为 `None`）。

nick 将替换数据存储在 Attribute.db_value 字段中，作为一个包含四个字段的元组 `(regex_nick, template_string, raw_nick, raw_template)`。其中 `regex_nick` 是 `raw_nick` 的转换正则表达式表示，`template-string` 是 `raw_template` 的一个版本，经过准备以有效替换任何 `$` 类型标记。`raw_nick` 和 `raw_template` 基本上是你输入到 `nick` 命令中的未更改字符串（带有未解析的 `$` 等）。

如果你需要出于某种原因访问该元组，可以这样做：

```python
tuple = obj.nicks.get("nickname", return_tuple=True)
# 或者，替代方法
tuple = obj.nicks.get("nickname", return_obj=True).value
```
