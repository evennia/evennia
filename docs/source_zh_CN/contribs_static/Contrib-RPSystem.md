# Evennia角色扮演基础系统

由 Griatch 贡献于 2015 年

这是一个完整的角色扮演表情系统。包括简短描述和识别（在你为他们分配名字之前，只能通过外貌认识人）。房间姿势。面具/伪装（隐藏你的描述）。可以直接在表情中说话，带有可选的语言混淆（如果你不懂语言，单词会被混淆，你也可以有不同语言的不同“声音”混淆）。耳语可以从远处部分听到。一个非常强大的表情内引用系统，用于引用和区分目标（包括对象）。

该系统包含两个主要模块——角色扮演表情系统和语言混淆模块。

## 角色扮演表情

此模块包含 `ContribRPObject`、`ContribRPRoom` 和 `ContribRPCharacter` 类型类。如果你从这些类型类继承你的对象/房间/角色（或将它们设为默认），你将获得以下功能：

- 对象/房间将能够拥有姿势，并报告其中物品的姿势（后者对房间最有用）。
- 角色将获得姿势和简短描述（sdescs），这些将用于替代他们的键。他们将获得管理识别（自定义sdesc替换）、伪装自己以及高级自由形式表情命令的命令。

更详细地说，此RP基础系统为游戏引入了以下功能，这些功能在许多RP中心游戏中很常见：

- 使用导演姿态表情的表情系统（名字/sdescs）。这使用可自定义的替换名词（/me, @ 等）来代表你在表情中。你可以使用 /sdesc, /nick, /key 或 /alias 来引用房间中的对象。你可以使用任意数量的sdesc子部分来区分本地sdesc，或使用 /1-sdesc 等来区分它们。表情还识别嵌套的说话并区分大小写。
- 用于表情和任何引用（如 object.search()）中的真实角色名称的sdesc混淆。这依赖于在角色上设置的 `SdescHandler` `sdesc`，并利用自定义 `Character.get_display_name` 钩子。如果未设置sdesc，则使用角色的 `key`。这在表情系统中特别有用。
- recog系统为角色分配你自己的昵称，然后可以用于引用。用户可以识别一个用户并为他们分配任何个人昵称。这将在描述中显示并用于引用他们。这利用了Evennia的昵称功能。
- 面具用于隐藏你的身份（使用简单锁）。
- 姿势系统用于设置房间持久姿势，在房间描述中可见，并在查看人/对象时可见。这是一个简单的属性，修改角色在房间中作为sdesc + 姿势时的查看方式。
- 表情内说话，包括与语言混淆例程的无缝集成（如 contrib/rplanguage.py）。

### 安装

将此模块中的 `RPSystemCmdSet` 添加到你的 `CharacterCmdSet`：

```python
# mygame/commands/default_cmdsets.py

# ...

from evennia.contrib.rpg.rpsystem import RPSystemCmdSet  <---

class CharacterCmdSet(default_cmds.CharacterCmdset):
    # ...
    def at_cmdset_creation(self):
        # ...
        self.add(RPSystemCmdSet())  # <---

```

你还需要让你的角色/对象/房间继承此模块中的类型类：

```python
# in mygame/typeclasses/characters.py

from evennia.contrib.rpg.rpsystem import ContribRPCharacter

class Character(ContribRPCharacter):
    # ...

```

```python
# in mygame/typeclasses/objects.py

from evennia.contrib.rpg.rpsystem import ContribRPObject

class Object(ContribRPObject):
    # ...

```

```python
# in mygame/typeclasses/rooms.py

from evennia.contrib.rpg.rpsystem import ContribRPRoom

class Room(ContribRPRoom):
    # ...

```

你需要设置Evennia以使用RPsystem的形式来区分sdescs（如`3-tall`），以使其与Evennia的其他多重匹配搜索/命令的分隔方式兼容：

```python
SEARCH_MULTIMATCH_REGEX = r"(?P<number>[0-9]+)-(?P<name>[^-]*)(?P<args>.*)"
SEARCH_MULTIMATCH_TEMPLATE = " {number}-{name}{aliases}{info}\n"
```

最后，你需要重新加载服务器，并可能需要强制重新加载你的对象，如果你最初创建它们时没有使用此功能。

例如你的角色：

```
> type/reset/force me = typeclasses.characters.Character
```

### 使用

#### Sdescs

```
> look

Tavern
The tavern is full of nice people

*A tall man* is standing by the bar.
```

以上是一个玩家的sdesc为“a tall man”的示例。这也是一个静态*姿势*的示例：“standing by the bar”是由高个子男人的玩家设置的，以便人们在看他时可以一目了然地知道发生了什么。

```
> emote /me looks at /Tall and says "Hello!"
```

我看到：

```
Griatch looks at Tall man and says "Hello".
```

高个子男人（假设他的名字是Tom）看到：

```
The godlike figure looks at Tom and says "Hello".
```

请注意，默认情况下，标签的大小写很重要，因此 `/tall` 将导致“tall man”，而 `/Tall` 将变为“Tall man”，而 /TALL 将变为 /TALL MAN。如果你不想要这种行为，你可以将 `send_emote` 函数的 `case_sensitive` 参数设置为 `False`。

#### 语言集成

可以通过在语言键前加前缀来识别特定语言的语音。

```
emote says with a growl, orcish"Hello".
```

这将识别语音“Hello”为用兽人语说的，然后将该信息传递给角色的 `process_language`。默认情况下，它不会做太多事情，但你可以接入一个语言系统，例如下面的 `rplanguage` 模块，以做更有趣的事情。

## 语言和耳语混淆系统

此模块旨在与表情系统（如 `contrib/rpg/rpsystem.py`）一起使用。它提供了在游戏中以各种方式混淆口语的能力：

- 语言：语言功能定义了一个伪语言映射到任意数量的语言。字符串将根据缩放进行混淆，该缩放（最可能）将作为说话者和听者的语言技能的加权平均输入。
- 耳语：耳语功能将沿0-1的比例逐渐“淡出”耳语，其中淡出是基于逐渐移除耳语中（据称）更容易被偷听的部分（例如，“s”声音往往即使在无法确定其他含义时也可以听到）。

### 安装

此模块不添加新命令；将其嵌入到你的说话/表情/耳语命令中。

### 使用：

```python
from evennia.contrib.rpg.rpsystem import rplanguage

# 需要执行一次，这里我们创建“默认”语言
rplanguage.add_language()

say = "This is me talking."
whisper = "This is me whispering."

print(rplanguage.obfuscate_language(say, level=0.0))
# <<< "This is me talking."
print(rplanguage.obfuscate_language(say, level=0.5))
# <<< "This is me byngyry."
print(rplanguage.obfuscate_language(say, level=1.0))
# <<< "Daly ly sy byngyry."

result = rplanguage.obfuscate_whisper(whisper, level=0.0)
# <<< "This is me whispering"
result = rplanguage.obfuscate_whisper(whisper, level=0.2)
# <<< "This is m- whisp-ring"
result = rplanguage.obfuscate_whisper(whisper, level=0.5)
# <<< "---s -s -- ---s------"
result = rplanguage.obfuscate_whisper(whisper, level=0.7)
# <<< "---- -- -- ----------"
result = rplanguage.obfuscate_whisper(whisper, level=1.0)
# <<< "..."
```

要设置新语言，请在此模块中导入并使用 `add_language()` 辅助方法。这允许你自定义你正在创建的半随机语言的“感觉”。特别是 `word_length_variance` 有助于使翻译单词的长度相对于原始单词有所不同，并有助于改变你正在创建的语言的“感觉”。你还可以添加自己的字典，并为输入单词列表“固定”随机单词。

以下是使用“圆润”元音和声音的“精灵语”示例：

```python
# 元音/辅音语法可能性
grammar = ("v vv vvc vcc vvcc cvvc vccv vvccv vcvccv vcvcvcc vvccvvcc "
           "vcvvccvvc cvcvvcvvcc vcvcvvccvcvv")

# 所有不在此组中的都被视为辅音
vowels = "eaoiuy"

# 你需要在此处拥有所有最小语法的代表，因此如果存在语法 v，则必须至少有一个仅包含一个元音的音素可用
phonemes = ("oi oh ee ae aa eh ah ao aw ay er ey ow ia ih iy "
            "oy ua uh uw y p b t d f v t dh s z sh zh ch jh k "
            "ng g m n l r w")

# 翻译的长度与原始长度相比的变化程度。0是最小值，较高的值给出更大的随机性（包括完全删除短词）
word_length_variance = 1

# 如果专有名词（以大写字母开头的单词）应被翻译。如果不是（默认），这意味着例如名字在语言之间保持不变。
noun_translate = False

# 所有专有名词（句子开头不以大写字母开头的单词）可以始终添加后缀或前缀
noun_postfix = "'la"

# 字典中的单词将始终以这种方式翻译。'auto_translations' 是一个列表或文件名，用于帮助通过为列表中的每个单词创建一次随机翻译并保存结果以供后续使用来构建更大的字典。
manual_translations = {"the":"y'e", "we":"uyi", "she":"semi", "he":"emi",
                      "you": "do", 'me':'mi','i':'me', 'be':"hy'e", 'and':'y'}

rplanguage.add_language(key="elvish", phonemes=phonemes, grammar=grammar,
                         word_length_variance=word_length_variance,
                         noun_translate=noun_translate,
                         noun_postfix=noun_postfix, vowels=vowels,
                         manual_translations=manual_translations,
                         auto_translations="my_word_file.txt")
```

这将产生一种更“圆润”和“柔和”的语言。少量的 `manual_translations` 也确保至少看起来表面上“合理”。

`auto_translations` 关键字很有用，它接受一个列表或一个文本文件的路径（每行一个单词）。这些单词的列表用于根据语法规则“固定”翻译。这些翻译在语言存在期间会持久保存。

这允许快速构建大量从不改变的翻译单词。这会产生一种看似中等一致的语言，因为像“the”这样的单词将始终被翻译成相同的东西。其缺点（或优点，取决于你的游戏）是玩家最终可能会学会这些单词的含义，即使他们的角色不知道该语言。
