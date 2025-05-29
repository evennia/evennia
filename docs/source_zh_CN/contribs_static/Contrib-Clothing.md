# 衣物

由 Tim Ashley Jenkins 贡献，2017年

提供了可穿戴衣物的类型类和命令。这些衣物的外观在角色穿戴时会附加到角色描述中。

当穿戴衣物时，这些物品会以列表的形式添加到角色的描述中。例如，如果穿戴以下衣物：

- 一条纤细而精致的项链
- 一双普通的鞋子
- 一顶漂亮的帽子
- 一条非常好看的裙子

将会得到如下附加描述：

```
Tim is wearing one nice hat, a thin and delicate necklace,
a very pretty dress and a pair of regular ol' shoes.
```

## 安装

要安装，请导入此模块，并在游戏的 `characters.py` 文件中让默认角色继承自 `ClothedCharacter`：

```python
from evennia.contrib.game_systems.clothing import ClothedCharacter

class Character(ClothedCharacter):
```

然后在 `mygame/commands/default_cmdsets.py` 中的角色设置中添加 `ClothedCharacterCmdSet`：

```python
from evennia.contrib.game_systems.clothing import ClothedCharacterCmdSet # <--

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # ...
    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        # ...
        self.add(ClothedCharacterCmdSet)    # <--
```

## 使用

安装完成后，你可以使用默认的构建命令创建衣物以测试系统：

```
create a pretty shirt : evennia.contrib.game_systems.clothing.ContribClothing
set shirt/clothing_type = 'top'
wear shirt
```

角色的描述可能看起来像这样：

Superuser(#1)
This is User #1.

Superuser is wearing one nice hat, a thin and delicate necklace,
a very pretty dress and a pair of regular ol' shoes.

角色也可以为他们的衣物指定穿着风格——例如，将围巾“系成紧紧的结在脖子周围”或“松松地披在肩上”——以增加自定义的便捷途径。例如，在输入：

wear scarf draped loosely across the shoulders

后，衣物在描述中将显示为：

Superuser(#1)
This is User #1.

Superuser is wearing a fanciful-looking scarf draped loosely
across the shoulders.

衣物可以用来覆盖其他物品，并提供了多种选项来定义你自己的衣物类型及其限制和行为。例如，可以使内衣自动被外衣覆盖，或限制可以穿着的每种类型物品的数量。系统本身相当自由灵活——你几乎可以用任何其他衣物覆盖任意衣物——但可以轻松地进行更严格的设置，还可以与护甲或其他装备系统结合。

## 配置

该贡献有几个可选配置，可以在 `settings.py` 中定义。以下是设置及其默认值。

```python
# 'wear style' 字符串的最大字符数，或 None 表示无限制。
CLOTHING_WEARSTYLE_MAXLENGTH = 50

# 衣物类型在描述中出现的顺序。
# 未指定类型的衣物或不在此列表中的衣物会排在最后。
CLOTHING_TYPE_ORDERED = [
        "hat",
        "jewelry",
        "top",
        "undershirt",
        "gloves",
        "fullbody",
        "bottom",
        "underpants",
        "socks",
        "shoes",
        "accessory",
    ]

# 可穿戴的衣物最大数量，或 None 表示无限制。
CLOTHING_OVERALL_LIMIT = 20

# 每种特定衣物类型可穿戴的最大数量。
# 如果衣物项目没有类型或未在此处指定，则唯一的最大限制是总体限制。
CLOTHING_TYPE_LIMIT = {"hat": 1, "gloves": 1, "socks": 1, "shoes": 1}

# 穿戴时将自动覆盖其他类型衣物的衣物类型。
# 注意，只有在衣物已经穿着的情况下，才能自动覆盖。你完全可以在穿上裤子后让内裤显露出来！
CLOTHING_TYPE_AUTOCOVER = {
        "top": ["undershirt"],
        "bottom": ["underpants"],
        "fullbody": ["undershirt", "underpants"],
        "shoes": ["socks"],
    }

# 任何类型的衣物不能用于覆盖其他衣物。
CLOTHING_TYPE_CANT_COVER_WITH = ["jewelry"]
```
