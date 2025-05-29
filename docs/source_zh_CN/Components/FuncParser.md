# FuncParser 内联文本解析

[FuncParser](evennia.utils.funcparser.FuncParser) 用于提取和执行嵌入在字符串中的“内联函数”，格式为 `$funcname(args, kwargs)`。它会执行匹配的“内联函数”，并用调用返回的结果替换调用。

要测试它，我们可以让 Evennia 对每个传出的消息应用 FuncParser。默认情况下这是禁用的（并非所有人都需要此功能）。要激活，请在设置文件中添加：

```python
FUNCPARSER_PARSE_OUTGOING_MESSAGES_ENABLED = True
```

重载后，你可以在游戏中尝试：

```shell
> say I got $randint(1,5) gold!
You say "I got 3 gold!"
```

要转义内联函数（例如向某人解释其工作原理），使用 `$$`：

```shell
> say To get a random value from 1 to 5, use $$randint(1,5).
You say "To get a random value from 1 to 5, use $randint(1,5)."
```

虽然 `randint` 看起来和工作方式与标准 Python 库中的 `random.randint` 类似，但它并不是。它是一个名为 `randint` 的 `inlinefunc`，在 Evennia 中可用（它内部使用标准库函数）。出于安全原因，只有明确分配为内联函数的函数才可用。

你可以手动应用 `FuncParser`。解析器初始化时需要识别字符串中的内联函数。下面是一个仅理解 `$pow` 内联函数的解析器示例：

```python
from evennia.utils.funcparser import FuncParser

def _power_callable(*args, **kwargs):
    """This will be callable as $pow(number, power=<num>) in string"""
    pow = int(kwargs.get('power', 2))
    return float(args[0]) ** pow

# 创建解析器并告诉它 '$pow' 表示使用 _power_callable
parser = FuncParser({"pow": _power_callable})
```

接下来，只需将包含 `$func(...)` 标记的字符串传递给解析器：

```python
parser.parse("We have that 4 x 4 x 4 is $pow(4, power=3).")
"We have that 4 x 4 x 4 is 64."
```

通常返回值总是转换为字符串，但你也可以从调用中获取实际的数据类型：

```python
parser.parse_to_any("$pow(4)")
16
```

你不必从头定义所有的内联函数。在 `evennia.utils.funcparser` 中，你会发现可以导入并插入到解析器中的现成内联函数字典。有关详细信息，请参见下文的[默认 funcparser 可调用项](#default-funcparser-callables)。

## 使用 FuncParser

FuncParser 可以应用于任何字符串。开箱即用时，它会在以下几种情况下应用：

- **传出消息**。从服务器发送的所有消息都通过 FuncParser 处理，并且每个可调用项都提供接收消息对象的 [Session](./Sessions.md)。这可能允许消息在发送时根据不同的接收者进行修改。
- **原型值**。一个 [Prototype](./Prototypes.md) 字典的值通过解析器运行，使每个可调用项都能引用原型的其余部分。在 Prototype ORM 中，这允许构建者安全地调用函数以将非字符串值设置为原型值、获取随机值、引用原型的其他字段等。
- **消息中的角色姿态**。在 [Object.msg_contents](evennia.objects.objects.DefaultObject.msg_contents) 方法中，传出的字符串会解析特殊的 `$You()` 和 `$conj()` 可调用项，以决定给定的接收者是否应该看到“你”或角色的名字。

```{important}
内联函数解析器并不是一个“软编码”编程语言。例如，它没有循环和条件语句。虽然原则上你可以扩展它以完成非常高级的事情，并允许构建者拥有很大的权限，但 Evennia 期望你在游戏外的合适文本编辑器中进行全面编码，而不是在游戏中进行。
```

你可以将内联函数解析应用于任何字符串。[FuncParser](evennia.utils.funcparser.FuncParser) 被导入为 `evennia.utils.funcparser`。

```python
from evennia.utils import funcparser

parser = FuncParser(callables, **default_kwargs)
parsed_string = parser.parse(input_string, raise_errors=False,
                              escape=False, strip=False,
                              return_str=True, **reserved_kwargs)

# 可调用项也可以作为模块路径传递
parser = FuncParser(["game.myfuncparser_callables", "game.more_funcparser_callables"])
```

在这里，`callables` 指向一组普通的 Python 函数（参见下一节），以便你在解析字符串时将它们提供给解析器。它可以是：

- 一个 `dict`，格式为 `{"functionname": callable, ...}`。这允许你精确选择要包含的可调用项及其命名方式。你想让一个可调用项以多个名称可用吗？只需将其多次添加到字典中，并使用不同的键。
- 一个 `module` 或（更常见的）一个模块的 `python-path`。该模块可以定义一个字典 `FUNCPARSER_CALLABLES = {"funcname": callable, ...}` - 这将被导入并像上面的 `dict` 一样使用。如果没有定义此变量，则模块中的每个顶级函数（其名称不以下划线 `_` 开头）都将被视为合适的可调用项。函数的名称将是可以调用它的 `$funcname`。
- 一个模块/路径的 `list`。这允许你从多个来源提取模块以进行解析。
- `**default` kwargs 是可选的 kwargs，每次使用此解析器时都会传递给所有可调用项 - 除非用户在调用中明确覆盖它。这对于提供用户可以根据需要调整的合理标准非常有用。

`FuncParser.parse` 接受更多参数，并且可以根据每个解析的字符串而有所不同。

- `raise_errors` - 默认情况下，任何来自可调用项的错误都会被悄悄忽略，结果是失败的函数调用将原样显示。如果设置了 `raise_errors`，那么解析将停止，并且将引发发生的任何异常。处理此问题将取决于你。
- `escape` - 返回一个字符串，其中每个 `$func(...)` 都已转义为 `\$func()`。
- `strip` - 从字符串中删除所有 `$func(...)` 调用（就像每个调用返回 `''` 一样）。
- `return_str` - 当 `True`（默认）时，`parser` 总是返回一个字符串。如果为 `False`，它可能返回字符串中单个函数调用的返回值。这与使用 `.parse_to_any` 方法相同。
- `**reserved_keywords` 始终传递给字符串中的每个可调用项。它们会覆盖在实例化解析器时给出的任何 `**defaults`，并且用户无法覆盖它们 - 如果他们输入相同的 kwarg，它将被忽略。这对于提供当前会话、设置等非常有用。
- `funcparser` 和 `raise_errors` 始终作为保留关键字添加 - 第一个是 `FuncParser` 实例的反向引用，第二个是给 `FuncParser.parse` 的 `raise_errors` 布尔值。

以下是使用默认/保留关键字的示例：

```python
def _test(*args, **kwargs):
    # 执行操作
    return something

parser = funcparser.FuncParser({"test": _test}, mydefault=2)
result = parser.parse("$test(foo, bar=4)", myreserved=[1, 2, 3])
```

在这里，可调用项将被调用为：

```python
_test('foo', bar='4', mydefault=2, myreserved=[1, 2, 3],
      funcparser=<FuncParser>, raise_errors=False)
```

`mydefault=2` kwarg 可以被覆盖，如果我们以 `$test(mydefault=...)` 的方式调用，但 `myreserved=[1, 2, 3]` 将始终按原样发送，并将覆盖调用 `$test(myreserved=...)`。`funcparser`/`raise_errors` kwargs 也始终作为保留 kwargs 包含。

## 定义自定义可调用项

所有可用给解析器的可调用项必须具有以下签名：

```python
def funcname(*args, **kwargs):
    # ...
    return something
```

> `*args` 和 `**kwargs` 必须始终包含。如果你不确定如何在 Python 中使用 `*args` 和 `**kwargs`，[请阅读此处](https://www.digitalocean.com/community/tutorials/how-to-use-args-and-kwargs-in-python-3)。

从你的可调用项中最内层的 `$funcname(...)` 调用输入将始终是 `str`。以下是一个 `$toint` 函数的示例；它将数字转换为整数。

```shell
"There's a $toint(22.0)% chance of survival."
```

进入 `$toint` 可调用项（作为 `args[0]`）的是字符串 `"22.0"`。该函数负责将其转换为数字，以便我们可以将其转换为整数。我们还必须正确处理无效输入（如非数字）。

如果要标记错误，请引发 `evennia.utils.funcparser.ParsingError`。这将停止整个字符串的解析，并且可能会或可能不会引发异常，这取决于你在创建解析器时设置的 `raise_errors`。

然而，如果你嵌套函数，最内层函数的返回值可能不是字符串。让我们引入 `$eval` 函数，它使用 Python 的 `literal_eval` 和/或 `simple_eval` 评估简单表达式。它返回其评估的任何数据类型。

```shell
"There's a $toint($eval(10 * 2.2))% chance of survival."
```

由于 `$eval` 是最内层的调用，它将获得一个字符串作为输入 - 字符串 `"10 * 2.2"`。它评估此表达式并返回 `float` `22.0`。这次最外层的 `$toint` 将以此 `float` 而不是字符串进行调用。

> 由于用户可能会以任何顺序嵌套你的可调用项，因此安全验证输入非常重要。请参阅下一节以获取有用的工具来帮助实现这一点。

在这些示例中，结果将嵌入到较大的字符串中，因此整个解析的结果将是一个字符串：

```python
parser.parse(above_string)
"There's a 22% chance of survival."
```

然而，如果你使用 `parse_to_any`（或 `parse(..., return_str=False)`），并且不在最外层函数调用周围添加任何额外的字符串，你将获得最外层可调用项的返回类型：

```python
parser.parse_to_any("$toint($eval(10 * 2.2)")
22
parser.parse_to_any("the number $toint($eval(10 * 2.2).")
"the number 22"
parser.parse_to_any("$toint($eval(10 * 2.2)%")
"22%"
```

### 转义特殊字符

在字符串中输入 funcparser 可调用项时，它看起来像字符串中的常规函数调用：

```python
"This is a $myfunc(arg1, arg2, kwarg=foo)."
```

逗号（`,`）和等号（`=`）被视为分隔参数和 kwargs。同样，右括号（`)`）关闭参数列表。有时你想在参数中包含逗号而不破坏参数列表。

```python
"The $format(forest's smallest meadow, with dandelions) is to the west."
```

你可以通过多种方式进行转义。

- 在特殊字符如 `,` 和 `=` 前添加转义字符 `\`

```python
"The $format(forest's smallest meadow\, with dandelions) is to the west."
```

- 用双引号包裹你的字符串。与原始 Python 不同，你不能用单引号 `'` 进行转义，因为这些也可能是撇号（如上面的 `forest's`）。结果将是一个逐字字符串，包含除最外层双引号之外的所有内容。

```python
'The $format("forest's smallest meadow, with dandelions") is to the west.'
```

- 如果你希望在字符串中出现逐字的双引号，可以用 `\"` 进行转义。

```python
'The $format("forest's smallest meadow, with \"dandelions\"') is to the west.'
```

### 安全转换输入

由于你不知道用户可能以何种顺序使用你的可调用项，因此它们应始终检查其输入的类型并转换为可调用项所需的类型。还要注意，从字符串转换时，支持的输入类型有限。这是因为 FunctionParser 字符串可以由非开发人员玩家/构建者使用，并且某些内容（如复杂的类/可调用项等）无法从字符串表示转换。

在 `evennia.utils.utils` 中有一个帮助器，称为 [safe_convert_to_types](evennia.utils.utils.safe_convert_to_types)。此函数以安全的方式自动转换简单数据类型：

```python
from evennia.utils.utils import safe_convert_to_types

def _process_callable(*args, **kwargs):
    """
    $process(expression, local, extra1=34, extra2=foo)
    """
    args, kwargs = safe_convert_to_type(
      (('py', str), {'extra1': int, 'extra2': str}),
      *args, **kwargs)

    # args/kwargs 现在应该是正确的类型
```

换句话说，在可调用项 `$process(expression, local, extra1=.., extra2=...)` 中，第一个参数将由“py”转换器处理（如下所述），第二个将通过常规 Python `str` 传递，kwargs 将分别由 `int` 和 `str` 处理。你可以提供自己的转换器函数，只要它接受一个参数并返回转换后的结果。

```python
args, kwargs = safe_convert_to_type(
        (tuple_of_arg_converters, dict_of_kwarg_converters), *args, **kwargs)
```

特殊转换器 `"py"` 将尝试使用以下工具将字符串参数转换为 Python 结构（你可能也会发现它们在自己的实验中很有用）：

- [ast.literal_eval](https://docs.python.org/3.8/library/ast.html#ast.literal_eval) 是一个内置的 Python 函数。它仅支持字符串、字节、数字、元组、列表、字典、集合、布尔值和 `None`。仅此而已 - 不允许对数据进行算术或修改。这对于将输入行中的单个值和列表/字典转换为真实的 Python 对象非常有用。
- [simpleeval](https://pypi.org/project/simpleeval/) 是一个第三方工具，随 Evennia 一起提供。它允许评估简单（因此安全）的表达式。可以使用 `+-/*` 对数字和字符串进行操作，还可以进行简单的比较，如 `4 > 3` 等。它不接受更复杂的容器，如列表/字典等，因此它与 `literal_eval` 互为补充。

```{warning}
使用 Python 的内置函数 `eval()` 或 `exec()` 作为转换器可能很诱人，因为它们能够将任何有效的 Python 源代码转换为 Python。除非你真的非常了解只有开发人员才能修改传入可调用项的字符串，否则绝不要这样做。解析器是为不受信任的用户设计的（如果你被信任，你已经可以访问 Python）。让不受信任的用户将字符串传递给 `eval`/`exec` 是一个重大安全风险。它允许调用者在你的服务器上运行任意 Python 代码。这是恶意删除硬盘的路径。不要这样做，晚上会睡得更好。
```

## 默认 funcparser 可调用项

以下是一些示例可调用项，你可以导入并添加到解析器中。它们在 `evennia.utils.funcparser` 中按全局级别字典划分。只需在创建 `FuncParser` 实例时导入字典并合并/添加一个或多个字典，即可使这些可调用项可用。

### `evennia.utils.funcparser.FUNCPARSER_CALLABLES`

这些是“基础”可调用项。

- `$eval(expression)` ([代码](evennia.utils.funcparser.funcparser_callable_eval)) - 使用 `literal_eval` 和 `simple_eval`（参见上一节）尝试将字符串表达式转换为 Python 对象。它处理例如字面量列表 `[1, 2, 3]` 和简单表达式，如 `"1 + 2"`。
- `$toint(number)` ([代码](evennia.utils.funcparser.funcparser_callable_toint)) - 始终将输出转换为整数（如果可能）。
- `$add/sub/mult/div(obj1, obj2)` ([代码](evennia.utils.funcparser.funcparser_callable_add)) - 这将两个元素相加/减/乘/除。虽然简单的加法可以用 `$eval` 完成，但这也可以用于将两个列表相加，这是 `eval` 无法做到的；例如 `$add($eval([1,2,3]), $eval([4,5,6])) -> [1, 2, 3, 4, 5, 6]`。
- `$round(float, significant)` ([代码](evennia.utils.funcparser.funcparser_callable_round)) - 将输入浮点数四舍五入为提供的有效数字。例如 `$round(3.54343, 3) -> 3.543`。
- `$random([start, [end]])` ([代码](evennia.utils.funcparser.funcparser_callable_random)) - 这类似于 Python `random()` 函数，但如果 start/end 都是整数，则会随机化为整数值。在没有参数的情况下，将返回介于 0 和 1 之间的浮点数。
- `$randint([start, [end]])` ([代码](evennia.utils.funcparser.funcparser_callable_randint)) - 类似于 `randint()` Python 函数，并始终返回整数。
- `$choice(list)` ([代码](evennia.utils.funcparser.funcparser_callable_choice)) - 输入将自动解析为与 `$eval` 相同，并且预计为可迭代对象。将返回该列表的随机元素。
- `$pad(text[, width, align, fillchar])` ([代码](evennia.utils.funcparser.funcparser_callable_pad)) - 这将填充内容。`$pad("Hello", 30, c, -)` 将导致文本居中于一个宽度为 30 的块中，并被 `-` 字符包围。
- `$crop(text, width=78, suffix='[...]')` ([代码](evennia.utils.funcparser.funcparser_callable_crop)) - 这将裁剪超过宽度的文本，默认情况下以 `[...]` 后缀结尾，该后缀也适合宽度。如果未给出宽度，将使用客户端宽度或 `settings.DEFAULT_CLIENT_WIDTH`。
- `$space(num)` ([代码](evennia.utils.funcparser.funcparser_callable_space)) - 这将插入 `num` 个空格。
- `$just(string, width=40, align=c, indent=2)` ([代码](evennia.utils.funcparser.funcparser_callable_justify)) - 将文本调整为给定宽度，左/右/居中对齐或使用 'f' 进行完全对齐（在宽度上展开文本）。
- `$ljust` - 左对齐的快捷方式。接受 `$just` 的所有其他 kwarg。
- `$rjust` - 右对齐的快捷方式。
- `$cjust` - 居中对齐的快捷方式。
- `$clr(startcolor, text[, endcolor])` ([代码](evennia.utils.funcparser.funcparser_callable_clr)) - 为文本着色。颜色用一个或两个字符给出，不带前导 `|`。如果未给出结束颜色，字符串将返回到中性，因此 `$clr(r, Hello)` 相当于 `|rHello|n`。

### `evennia.utils.funcparser.SEARCHING_CALLABLES`

这些是需要访问检查以搜索对象的可调用项。因此，在运行解析器时需要传递一些额外的保留 kwargs：

```python
parser.parse_to_any(string, caller=<object or account>, access="control", ...)
```

`caller` 是必需的，它是要进行访问检查的对象。`access` kwarg 是要检查的 [锁类型](./Locks.md)，默认值为 `"control"`。

- `$search(query,type=account|script,return_list=False)` ([代码](evennia.utils.funcparser.funcparser_callable_search)) - 这将查找并尝试通过键或别名匹配对象。使用 `type` kwarg 搜索 `account` 或 `script`。默认情况下，如果有多个匹配项，将不返回任何内容；如果 `return_list` 为 `True`，则将返回 0、1 或多个匹配项的列表。
- `$obj(query)`，`$dbref(query)` - `$search` 的遗留别名。
- `$objlist(query)` - `$search` 的遗留别名，总是返回一个列表。

### `evennia.utils.funcparser.ACTOR_STANCE_CALLABLES`

这些用于实现角色姿态表情。它们默认由 [DefaultObject.msg_contents](evennia.objects.objects.DefaultObject.msg_contents) 方法使用。你可以在页面 [根据接收者更改消息](../Concepts/Change-Message-Per-Receiver.md) 上阅读更多相关信息。

在解析器方面，所有这些内联函数都需要在解析器中传递额外的 kwargs（默认由 `msg_contents` 完成）：

```python
parser.parse(string, caller=<obj>, receiver=<obj>, mapping={'key': <obj>, ...})
```

在这里，`caller` 是发送消息的人，`receiver` 是看到消息的人。`mapping` 包含通过这些可调用项访问的其他对象的引用。

- `$you([key])` ([代码](evennia.utils.funcparser.funcparser_callable_you)) - 如果未给出 `key`，则表示 `caller`，否则将使用 `mapping` 中的对象。随着消息发送给不同的接收者，`receiver` 会发生变化，这将被替换为字符串 `you`（如果你和接收者是同一实体）或 `you_obj.get_display_name(looker=receiver)` 的结果。这允许单个字符串根据谁看到它而有所不同，并且也可以以相同的方式引用其他人。
- `$You([key])` - 与 `$you` 相同，但始终大写。
- `$conj(verb [,key])` ([代码](evennia.utils.funcparser.funcparser_callable_conjugate)) - 根据谁看到字符串，将动词从第二人称现在时变为第三人称现在时。例如 `"$You() $conj(smiles)."` 将显示为 "You smile." 和 "Tom smiles."，具体取决于谁看到它。这利用 [evennia.utils.verb_conjugation](evennia.utils.verb_conjugation) 中的工具进行操作，仅适用于英语动词。
- `$pron(pronoun [,options] [,key])` ([代码](evennia.utils.funcparser.funcparser_callable_pronoun)) - 动态映射代词（如 his、herself、you、its 等）从第一/第二人称到第三人称。
- `$pconj(verb, [,key])` ([代码](evennia.utils.funcparser.funcparser_callable_conjugate_for_pronouns)) - 在第二和第三人称之间结合动词，如 `$conj`，但用于代词而不是名词，以考虑复数性别。例如 `"$Pron(you) $pconj(smiles)"` 将对其他人显示为 "He smiles"（性别为“男性”）或 "They smile"（性别为“复数”）。

### `evennia.prototypes.protfuncs`

这由 [Prototype 系统](./Prototypes.md) 使用，并允许在原型中添加引用。解析将在生成之前进行。

可用于原型的内联函数：

- 所有 `FUNCPARSER_CALLABLES` 和 `SEARCHING_CALLABLES`
- `$protkey(key)` - 返回同一原型中另一个键的值。请注意，系统将尝试将其转换为“真实”值（如将字符串 "3" 转换为整数 3），出于安全原因，并非所有嵌入的值都可以这样转换。然而，你可以使用内联函数进行嵌套调用，包括添加自己的转换器。

### 示例

以下是包括默认可调用项和两个自定义可调用项的示例。

```python
from evennia.utils import funcparser
from evennia.utils import gametime

def _dashline(*args, **kwargs):
    if args:
        return f"\n-------- {args[0]} --------"
    return ''

def _uptime(*args, **kwargs):
    return gametime.uptime()

callables = {
    "dashline": _dashline,
    "uptime": _uptime,
    **funcparser.FUNCPARSER_CALLABLES,
    **funcparser.ACTOR_STANCE_CALLABLES,
    **funcparser.SEARCHING_CALLABLES
}

parser = funcparser.FuncParser(callables)

string = "This is the current uptime:$dashline($toint($uptime()) seconds)"
result = parser.parse(string)
```

在上面，我们定义了两个可调用项 `_dashline` 和 `_uptime`，并将它们映射到名称 `"dashline"` 和 `"uptime"`，这就是我们可以在字符串中调用它们为 `$header` 和 `$uptime` 的方式。我们还可以访问所有默认值（如 `$toint()`）。

上述解析结果将类似于：

```
This is the current uptime:
-------- 343 seconds --------
```
