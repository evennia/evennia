# 性别替换

由 Griatch 贡献于 2015 年

这是一个简单的性别感知角色类，允许用户在文本中插入自定义标记以指示性别感知消息。它依赖于一个修改过的 `msg()` 方法，旨在为如何实现此类功能提供灵感和起点。

一个对象可以具有以下性别：

- 男性 (他/他的)
- 女性 (她/她的)
- 中性 (它/它的)
- 模糊 (他们/他们的)

## 安装

在 `mygame/commands/default_cmdset.py` 中导入并添加 `SetGender` 命令到你的默认命令集：

```python
# mygame/commands/default_cmdsets.py

# ...

from evennia.contrib.game_systems.gendersub import SetGender   # <---

# ...

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # ...
    def at_cmdset_creation(self):
        # ...
        self.add(SetGender())   # <---
```

让你的 `Character` 继承自 `GenderCharacter`。

```python
# mygame/typeclasses/characters.py

# ...

from evennia.contrib.game_systems.gendersub import GenderCharacter  # <---

class Character(GenderCharacter):  # <---
    # ...
```

重载服务器（在游戏内使用 `evennia reload` 或 `reload`）。

## 用法

使用时，消息可以包含特殊标签以指示基于所指对象的性别代词。大小写将被保留。

- `|s`, `|S`: 主格形式：他，她，它，He，She，It，They
- `|o`, `|O`: 宾格形式：他，她，它，Him，Her，It，Them
- `|p`, `|P`: 所有格形式：他的，她的，它的，His，Her，Its，Their
- `|a`, `|A`: 绝对所有格形式：他的，她的，它的，His，Hers，Its，Theirs

例如，

```
char.msg("%s falls on |p face with a thud." % char.key)
"Tom falls on his face with a thud"
```

默认性别是“模糊”（他们/他们的）。

要使用此功能，可以让 DefaultCharacter 继承自此类，或更改 setting.DEFAULT_CHARACTER 指向此类。

`gender` 命令用于设置性别。需要将其添加到默认命令集中才能使用。


----

<small>此文档页面并非由 `evennia/contrib/game_systems/gendersub/README.md`自动生成。如想阅读最新文档，请参阅原始README.md文件。</small>
