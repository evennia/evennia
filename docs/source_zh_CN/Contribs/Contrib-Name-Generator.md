# 随机名字生成器

由 InspectorCaracal 贡献（2022 年）

这是一个用于生成真实世界和幻想世界名字的模块。真实世界的名字可以生成为名字（个人名）、姓氏（家族名）或全名（名字、可选的中间名和姓氏）。名字数据来自 [Behind the Name](https://www.behindthename.com/)，并在 [CC BY-SA 4.0 许可](https://creativecommons.org/licenses/by-sa/4.0/)下使用。

幻想名字是根据基本的语音规则生成的，使用 CVC 音节语法。

无论是现实世界还是幻想世界的名字生成，都可以通过游戏的 `settings.py` 文件扩展，以包含更多信息。

## 安装

这是一个独立的实用工具。只需导入此模块（`from evennia.contrib.utils import name_generator`），并在需要的地方使用其功能即可。

## 用法

在需要的地方导入模块：
```python
from evennia.contrib.utils.name_generator import namegen
```

默认情况下，所有函数将返回一个包含生成名字的字符串。如果指定多个名字，或传递 `return_list=True` 作为关键字参数，返回值将是一个字符串列表。

该模块特别适用于命名新创建的 NPC，例如：
```python
npc_name = namegen.full_name()
npc_obj = create_object(key=npc_name, typeclass="typeclasses.characters.NPC")
```

## 可用设置

这些设置可以在游戏的 `server/conf/settings.py` 文件中定义。

- `NAMEGEN_FIRST_NAMES` 添加新的名字（个人名）列表。
- `NAMEGEN_LAST_NAMES` 添加新的姓氏（家族名）列表。
- `NAMEGEN_REPLACE_LISTS` - 如果只想使用在设置中定义的名字，请设置为 `True`。
- `NAMEGEN_FANTASY_RULES` 允许您添加新的语音规则以生成完全虚构的名字。有关详细信息，请参阅“自定义幻想名字样式规则”部分。

示例：
```python
NAMEGEN_FIRST_NAMES = [
    ("Evennia", 'mf'),
    ("Green Tea", 'f'),
]

NAMEGEN_LAST_NAMES = ["Beeblebrox", "Son of Odin"]

NAMEGEN_FANTASY_RULES = {
    "example_style": {
        "syllable": "(C)VC",
        "consonants": ['z', 'z', 'ph', 'sh', 'r', 'n'],
        "start": ['m'],
        "end": ['x', 'n'],
        "vowels": ["e", "e", "e", "a", "i", "i", "u", "o"],
        "length": (2, 4),
    }
}
```

## 生成真实名字

该模块提供了三个函数用于生成随机的真实世界名字：`first_name()`、`last_name()` 和 `full_name()`。如果希望一次生成多个名字，可以使用 `num` 关键字参数指定数量。

示例：
```python
>>> namegen.first_name(num=5)
['Genesis', 'Tali', 'Budur', 'Dominykas', 'Kamau']
>>> namegen.first_name(gender='m')
'Blanchard'
```

`first_name` 函数还接受一个 `gender` 关键字参数，以按性别关联过滤名字。'f' 表示女性，'m' 表示男性，'mf' 表示女性和男性，默认 `None` 匹配任何性别。

`full_name` 函数还接受 `gender` 关键字，以及定义全名由多少个名字组成的 `parts`。最少是两个：一个名字和一个姓氏。您还可以通过将关键字参数 `surname_first` 设置为 `True` 来生成姓氏在前的名字。

示例：
```python
>>> namegen.full_name()
'Keeva Bernat'
>>> namegen.full_name(parts=4)
'Suzu Shabnam Kafka Baier'
>>> namegen.full_name(parts=3, surname_first=True)
'Ó Muircheartach Torunn Dyson'
>>> namegen.full_name(gender='f')
'Wikolia Ó Deasmhumhnaigh'
```

### 添加您自己的名字

您可以通过设置 `NAMEGEN_FIRST_NAMES` 和 `NAMEGEN_LAST_NAMES` 添加其他名字。

`NAMEGEN_FIRST_NAMES` 应该是一个元组列表，其中第一个值是名字，第二个值是性别标志 - 'm' 表示仅男性，'f' 表示仅女性，'mf' 表示两者皆可。

`NAMEGEN_LAST_NAMES` 应该是一个字符串列表，其中每个项目是一个可用的姓氏。

示例：
```python
NAMEGEN_FIRST_NAMES = [
    ("Evennia", 'mf'),
    ("Green Tea", 'f'),
]

NAMEGEN_LAST_NAMES = ["Beeblebrox", "Son of Odin"]
```

如果希望您的自定义列表完全替换内置列表而不是扩展它们，请设置 `NAMEGEN_REPLACE_LISTS = True`。

## 生成幻想名字

使用 `fantasy_name` 函数生成完全虚构的名字。该模块提供了三种内置的名字风格，您可以使用这些风格，也可以在 `settings.py` 中放置自定义名字规则字典。

生成幻想名字需要使用规则集键作为 "style" 关键字，并可以返回单个名字或多个名字。默认情况下，它将以内置的 "harsh" 风格返回一个名字。该模块还提供了 "fluid" 和 "alien" 风格。

```python
>>> namegen.fantasy_name()
'Vhon'
>>> namegen.fantasy_name(num=3, style="harsh")
['Kha', 'Kizdhu', 'Godögäk']
>>> namegen.fantasy_name(num=3, style="fluid")
['Aewalisash', 'Ayi', 'Iaa']
>>> namegen.fantasy_name(num=5, style="alien")
["Qz'vko'", "Xv'w'hk'hxyxyz", "Wxqv'hv'k", "Wh'k", "Xbx'qk'vz"]
```

### 多词幻想名字

`fantasy_name` 函数一次只生成一个名字词，因此对于多词名字，您需要将部分组合在一起。根据您想要的最终结果，有几种方法可以实现。

#### 简单方法

如果只需要它有多个部分，可以一次生成多个名字并使用 `join` 连接它们。

```python
>>> name = " ".join(namegen.fantasy_name(num=2))
>>> name
'Dezhvözh Khäk'
```

如果希望名字之间有更多变化，也可以为不同的风格生成名字，然后将它们组合。

```python
>>> first = namegen.fantasy_name(style="fluid")
>>> last = namegen.fantasy_name(style="harsh")
>>> name = f"{first} {last}"
>>> name
'Ofasa Käkudhu'
```

#### "Nakku Silversmith"

一种常见的幻想名字做法是基于职业或头衔的姓氏。为了达到这种效果，可以使用 `last_name` 函数和自定义的姓氏列表，并将其与生成的幻想名字组合。

示例：
```python
NAMEGEN_LAST_NAMES = ["Silversmith", "the Traveller", "Destroyer of Worlds"]
NAMEGEN_REPLACE_LISTS = True

>>> first = namegen.fantasy_name()
>>> last = namegen.last_name()
>>> name = f"{first} {last}"
>>> name
'Tözhkheko the Traveller'
```

#### Elarion d'Yrinea, Thror Obinson

另一种常见的幻想名字风格是使用姓氏后缀或前缀。为此，您需要自己添加额外的部分。

示例：
```python
>>> names = namegen.fantasy_name(num=2)
>>> name = f"{names[0]} za'{names[1]}"
>>> name
"Tithe za'Dhudozkok"

>>> names = namegen.fantasy_name(num=2)
>>> name = f"{names[0]} {names[1]}son"
>>> name
'Kön Ködhöddoson'
```

### 自定义幻想名字样式规则

样式规则包含在一个字典的字典中，其中样式名称是键，样式规则是字典值。

以下是如何在 `settings.py` 中添加自定义样式：
```python
NAMEGEN_FANTASY_RULES = {
    "example_style": {
        "syllable": "(C)VC",
        "consonants": ['z', 'z', 'ph', 'sh', 'r', 'n'],
        "start": ['m'],
        "end": ['x', 'n'],
        "vowels": ["e", "e", "e", "a", "i", "i", "u", "o"],
        "length": (2, 4),
    }
}
```

然后，您可以使用 `namegen.fantasy_name(style="example_style")` 生成遵循该规则集的名字。

键 `syllable`、`consonants`、`vowels` 和 `length` 必须存在，并且 `length` 必须是最小和最大音节数。`start` 和 `end` 是可选的。

#### syllable
"syllable" 字段定义每个音节的结构。C 是辅音，V 是元音，括号表示可选。因此，示例 `(C)VC` 意味着每个音节总是有一个元音后跟一个辅音，并且有时在开头还有另一个辅音。例如 `en`，`bak`。

*注意：* 虽然这不是标准做法，但该模块允许您嵌套括号，每层出现的可能性更低。此外，任何其他字符放入音节结构中 - 例如撇号 - 将按原样读取和插入。模块中的 "alien" 风格规则给出了一个例子：音节结构是 `C(C(V))(')(C)`，这导致音节如 `khq`、`xho'q` 和 `q'` 的元音出现频率远低于 `C(C)(V)(')(C)`。

#### consonants
一个简单的辅音音素列表，可以从中选择。多字符字符串是完全可以接受的，例如 "th"，但每个将被视为单个辅音。

该函数使用了一种简单的加权形式，您可以通过在列表中放置更多副本来增加某个音素出现的可能性。

#### start 和 end
这些是 **可选** 的列表，用于音节的第一个和最后一个字母（如果是辅音）。您可以添加只能出现在音节开头或结尾的额外辅音，或者可以添加已经定义的辅音的额外副本，以增加它们在音节开头/结尾的频率。

例如，在上面的 `example_style` 中，我们有一个 `start` 为 m，`end` 为 x 和 n。结合其余的辅音/元音，这意味着您可以有音节 `mez`，但不能有 `zem`，并且可以有 `phex` 或 `phen`，但不能有 `xeph` 或 `neph`。

它们可以完全省略自定义规则集。

#### vowels
元音是一个简单的元音音素列表 - 与辅音完全相同，但用于元音选择。单字符或多字符字符串都可以。它使用与辅音相同的简单加权系统 - 您可以通过多次将其放入列表中来增加任何给定元音的频率。

#### length
一个包含名字最小和最大音节数的元组。

设置时，请记住音节可能有多长！4 个音节可能看起来不算多，但如果您有一个 (C)(V)VC 结构，并且有一到两个字母的音素，您可以获得每个音节最多八个字符。


----

<small>此文档页面并非由 `evennia/contrib/utils/name_generator/README.md`自动生成。如想阅读最新文档，请参阅原始README.md文件。</small>
