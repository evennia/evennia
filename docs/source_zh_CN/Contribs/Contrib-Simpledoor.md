# SimpleDoor

由 Griatch 贡献于 2016 年

这是一个简单的双向出口，代表可以从两侧打开和关闭的门。可以轻松扩展以使其可锁定、可破坏等。

请注意，SimpleDoor 基于 Evennia 的锁，因此它对超级用户无效（超级用户会绕过所有锁）。超级用户总是可以反复关闭/打开门，而锁不会阻止你。要使用门，请使用 `quell` 或非超级用户账户。

## 安装：

将此模块中的 `SimpleDoorCmdSet` 导入 `mygame/commands/default_cmdsets`，并将其添加到你的 `CharacterCmdSet`：

```python
# 在 mygame/commands/default_cmdsets.py 中

from evennia.contrib.grid import simpledoor  <---

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # ...
    def at_cmdset_creation(self):
        # ...
        self.add(simpledoor.SimpleDoorCmdSet)

```

## 使用：

要试用，请 `dig` 一个新房间，然后使用（重载的）`@open` 命令打开一个通往它的新门，如下所示：

```
@open doorway:contrib.grid.simpledoor.SimpleDoor = otherroom

open doorway
close doorway
```

注意：这使用了锁，因此如果你是超级用户，你将不会被锁住的门阻挡——如果是这样，请 `quell` 自己。普通用户会发现，一旦门从另一侧关闭，他们将无法通过门的任一侧。


----

<small>此文档页面并非由 `evennia/contrib/grid/simpledoor/README.md`自动生成。如想阅读最新文档，请参阅原始README.md文件。</small>
