# 根据接收者变化的消息

在一个位置发送消息给所有人是通过对所有 [对象](../Components/Objects.md)使用 [msg_contents](evennia.objects.objects.DefaultObject.msg_contents) 方法来处理的。它最常用于房间。

```python
room.msg_contents("Anna walks into the room.")
```

你还可以在字符串中嵌入引用：

```python
room.msg_contents("{anna} walks into the room.",
                  from_obj=caller,
                  mapping={'anna': anna_object})
```

使用 `exclude=object_or_list_of_object` 来跳过向一个或多个目标发送消息。

这样做的好处是 `anna_object.get_display_name(looker)` 将为每个旁观者调用；这允许 `{anna}` 部分根据谁看到字符串而有所不同。其工作方式取决于游戏的 _立场_。

立场表示你的游戏如何向玩家回显消息。了解你想如何处理立场对文字游戏很重要。通常考虑的有两种主要立场，_演员立场_ 和 _导演立场_。

| 立场     | 你看到的    |    同一位置的其他人看到的 |
| --- | --- | --- |
| 演员立场 | 你捡起了石头 | Anna 捡起了石头 |
|导演立场 | Anna 捡起了石头 | Anna 捡起了石头 |

混合使用两种立场并不罕见——游戏中的命令以演员立场讲述，而导演立场用于复杂的表情和角色扮演。然而，通常应该尽量保持一致。

## 导演立场

虽然不如演员立场常见，但导演立场具有简单的优势，特别是在角色扮演 MUD 中，使用较长的角色扮演表情。技术上实现也相对简单，因为无论视角如何，大家看到的文本都是一样的。

以下是一个展示房间的生动文本示例：

```plaintext
Tom picks up the gun, whistling to himself.
```

每个人都会看到这个字符串，包括 Tom 和其他人。以下是将其发送给房间中所有人的方法。

```python
text = "Tom picks up the gun, whistling to himself."
room.msg_contents(text)
```

可能需要通过让名字 `Tom` 被不同的人以不同的方式看到来进行扩展，但句子的英语语法不会改变。技术上这很容易做到，玩家也很容易编写。

## 演员立场

这意味着游戏在执行操作时会对“你”进行描述。在演员立场中，每当你执行一个动作时，你应该收到与那些 _观察_ 你执行该动作的人不同的消息。

```plaintext
Tom picks up the gun, whistling to himself.
```

这是 _其他人_ 应该看到的。玩家自己应该看到的是：

```plaintext
You pick up the gun, whistling to yourself.
```

不仅需要将 "Tom" 映射为 "You"，还需要进行语法上的差异——"Tom walks" 与 "You walk" 以及 "himself" 与 "yourself"。这要复杂得多。对于开发人员来说，制作简单的 "You/Tom pick/picks up the stone" 消息，可以原则上从每个视角手工制作字符串，但有更好的方法。

`msg_contents` 方法通过使用带有一些非常特定的 `$inline-functions` 的 [FuncParser 函数](../Components/FuncParser.md) 来帮助解析输入字符串。内联函数基本上为你提供了一种迷你语言，用于构建 _一个_ 字符串，该字符串将根据谁看到它而适当更改。

```python
text = "$You() $conj(pick) up the gun, whistling to $pron(yourself)."
room.msg_contents(text, from_obj=caller, mapping={"gun": gun_object})
```

这些是可用的内联函数：

- `$You()/$you()` - 这是文本中对“你”的引用。对于发送文本的人，它将被替换为 "You/you"，对于其他人，则返回 `caller.get_display_name(looker)`。
- `$conj(verb)` - 这将根据谁看到字符串来变化动词（如 `pick` 变为 `picks`）。输入动词的原形。
- `$pron(pronoun[,options])` - 代词是你想用来代替专有名词的词，如 _him_、_herself_、_its_、_me_、_I_、_their_ 等。`options` 是一个以空格或逗号分隔的选项集，用于帮助系统将你的代词从第一/第二人称映射到第三人称，反之亦然。见下节。

### 关于 $pron() 的更多信息

`$pron()` 内联函数在第一/第二人称（I/you）与第三人称（he/she 等）之间进行映射。简而言之，它在这两个表格之间进行翻译...

| | 主格代词 | 宾格代词 | 物主形容词 | 物主代词 | 反身代词 |
| --- | --- | --- | --- | --- | --- |
|    **第一人称**          |   I    |    me   |    my    |   mine    |  myself      |
|    **第一人称复数**   |   we   |    us   |    our   |    ours   |   ourselves  |
|    **第二人称**          |   you  |    you  |    your  |    yours  |   yourself   |
|    **第二人称复数**   |   you  |    you  |    your  |    yours  |   yourselves  |

... 到这个表格（双向）：

| | 主格代词 | 宾格代词 | 物主形容词 | 物主代词 | 反身代词 |
| --- | --- | --- | --- | --- | --- |
|    **第三人称男性**     |   he   |    him  |    his   |    his    |   himself  |
|    **第三人称女性**   |   she  |    her  |    her   |    hers   |   herself  |
|    **第三人称中性**  |   it   |    it   |    its   |   theirs*  |   itself   |
|    **第三人称复数**   |   they |   them  |    their |    theirs |   themselves |

一些映射很简单。例如，如果你写 `$pron(yourselves)`，那么第三人称形式总是 `themselves`。但由于英语语法的特殊性，并非所有映射都是一对一的。例如，如果你写 `$pron(you)`，Evennia 将不知道应该映射到哪个第三人称等效项——你需要提供更多信息来帮助解决这个问题。这可以作为 `$pron` 的第二个以空格分隔的选项提供，或者系统将尝试自行解决。

- `pronoun_type` - 这是表格中的一列，可以作为 `$pron` 选项设置。

   - `subject pronoun`（别名 `subject` 或 `sp`）
   - `object pronoun`（别名 `object` 或 `op`）
   - `possessive adjective`（别名 `adjective` 或 `pa`）
   - `possessive pronoun`（别名 `pronoun` 或 `pp`）。

  （不需要指定反身代词，因为它们都是唯一的一对一映射）。指定代词类型主要是在使用 `you` 时需要，因为同一个 'you' 在英语语法中用于表示各种不同的东西。如果没有指定，并且映射不明确，则假定为 'subject pronoun'（he/she/it/they）。
- `gender` - 在 `$pron` 选项中设置为

   - `male`，或 `m`
   - `female'` 或 `f`
   - `neutral`，或 `n`
   - `plural`，或 `p`（是的，复数在此目的中被视为一种“性别”）。

  如果没有在选项中设置，系统将
  查找当前 `from_obj` 上的可调用或属性 `.gender`。可调用对象将被调用
  不带参数，并期望返回一个字符串 'male/female/neutral/plural'。如果没有找到，
  则假定为中性性别。
- `viewpoint`- 在 `$pron` 选项中设置为

   - `1st person`（别名 `1st` 或 `1`）
   - `2nd person`（别名 `2nd` 或 `2`）

   这仅在你想要第一人称视角时需要 - 如果
   不需要，则假定为第二人称。

`$pron()` 示例：

| 输入            |   你看到的  |  其他人看到的 |  备注 |
| --- | --- | ---| --- |
| `$pron(I, male)`    |         I           |     he       |   |
| `$pron(I, f)`    |         I           |     she       |   |
| `$pron(my)` | my | its | 识别出是物主形容词，假定为中性 |
| `$pron(you)`   |         you         |  it     | 假定为中性主格代词 |
| `$pron(you, f)`   |        you         |     she  | 指定为女性，假定为主格代词 |
| `$pron(you,op f)`   |      you         |     her | |
| `$pron(you,op p)`   |      you         |     them | |
| `$pron(you, f op)` | you | her | 指定为女性和宾格代词|
| `$pron(yourself)`  |       yourself    |     itself | |
| `$pron(its)`        |      your        |     its  | |
| `$Pron(its)`        |      Your        |     Its | 使用 $Pron 总是大写 |
| `$pron(her)`        |      you        |     her  | 第三人称 -> 第二人称 |
| `$pron(her, 1)`        |   I        |       her  | 第三人称 -> 第一人称 |
| `$pron(its, 1st)`      |  my        |       its  | 第三人称 -> 第一人称  |

注意最后三个例子 - 你可以指定第二人称形式，也可以指定第三人称并进行“反向”查找 - 你仍然会看到正确的第一/第二人称文本。所以写 `$pron(her)` 而不是 `$pron(you, op f)` 会得到相同的结果。

[$pron inlinefunc api 在这里找到](evennia.utils.funcparser.funcparser_callable_pronoun)

## 引用其他对象

`msg_contents` 还理解一个内联函数。这可以在本地用于美化你的字符串（适用于导演立场和演员立场）：

- `$Obj(name)/$obj(name)` 引用另一个实体，必须在 `msg_contents` 的 `mapping` 关键字参数中提供。对象的 `.get_display_name(looker)` 将被调用并插入。这实际上与我们在页面顶部第一个示例中使用的 `{anna}` 标记相同，但使用 `$Obj/$obj` 允许你轻松控制大小写。

使用方式如下：

```python
# 导演立场
text = "Tom picks up the $obj(gun), whistling to himself"

# 演员立场
text = "$You() $conj(pick) up the $obj(gun), whistling to $pron(yourself)"

room.msg_contents(text, from_obj=caller, mapping={"gun": gun_object})
```

根据你的游戏，Tom 现在可能会看到自己捡起了 `A rusty old gun`，而一个具有高枪械技能的旁观者可能会看到他捡起了 `A rare-make Smith & Wesson model 686 in poor condition` ...

## 识别系统和角色扮演

`$funcparser` 内联函数对游戏开发者非常强大，但对于普通玩家来说可能有点复杂。

[rpsystem contrib](evennia.contrib.rpg.rpsystem) 实现了一个完整的动态表情/姿态和识别系统，具有简短描述和伪装。它使用导演立场和自定义标记语言，如 `/me` `/gun` 和 `/tall man` 来引用位置中的玩家和对象。值得一看以获得灵感。
