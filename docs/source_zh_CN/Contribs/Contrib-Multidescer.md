# Evennia 多重描述器

由 Griatch 贡献于 2016 年

“多重描述器”是来自 MUSH 世界的一个概念。它允许将你的描述拆分为任意命名的“部分”，然后可以随意替换。这是一种快速管理外观的方法（例如更换衣服），适用于更自由形式的角色扮演系统。这也可以很好地与 `rpsystem` 贡献模块配合使用。

这个多重描述器不需要对 Character 类进行任何更改，而是使用 `multidescs` 属性（一个列表），如果不存在则创建它。它添加了一个新的 `+desc` 命令（在 Evennia 中，+ 是可选的）。

## 安装

像任何自定义命令一样，只需将新的 `+desc` 命令添加到默认的 cmdset 中：将 `evennia.contrib.game_systems.multidescer.CmdMultiDesc` 导入到 `mygame/commands/default_cmdsets.py` 中，并将其添加到 `CharacterCmdSet` 类中。

重新加载服务器，你应该可以使用 `+desc` 命令（它将替换默认的 `desc` 命令）。

## 用法

在游戏中使用 `+desc` 命令：

```
+desc [key]                - 显示当前描述，带有 <key>
+desc <key> = <text>       - 添加/替换带有 <key> 的描述
+desc/list                 - 列出描述（简略）
+desc/list/full            - 列出描述（完整文本）
+desc/edit <key>           - 在行编辑器中添加/编辑描述 <key>
+desc/del <key>            - 删除描述 <key>
+desc/swap <key1>-<key2>   - 交换列表中 <key1> 和 <key2> 的位置
+desc/set <key> [+key+...] - 设置描述为默认或组合多个描述
```

例如，你可以为衣服设置一个描述，为靴子、发型或其他任何东西设置另一个描述。使用 `|/` 添加多行描述和段落的换行符，使用 `|_` 强制缩进和空白（我们在示例中不包含颜色，因为它们在此文档中不显示）。

```
+desc base = A handsome man.|_
+desc mood = He is cheerful, like all is going his way.|/|/
+desc head = On his head he has a red hat with a feather in it.|_
+desc shirt = His chest is wrapped in a white shirt. It has golden buttons.|_
+desc pants = He wears blue pants with a dragon pattern on them.|_
+desc boots = His boots are dusty from the road.
+desc/set base + mood + head + shirt + pants + boots
```

当查看这个角色时，你现在会看到（假设自动换行）

```
A handsome man. He is cheerful, like all is going his way.

On his head he has a red hat with a feather in it. His chest is wrapped in a
white shirt. It has golden buttons. He wears blue pants with a dragon
pattern on them. His boots are dusty from the road.
```

如果你现在这样做

```
+desc mood = He looks sullen and forlorn.|/|/
+desc shirt = His formerly white shirt is dirty and has a gash in it.|_
```

你的描述将变为

```
A handsome man. He looks sullen and forlorn.

On his head he has a red hat with a feather in it. His formerly white shirt
is dirty and has a gash in it. He wears blue pants with a pattern on them.
His boots are dusty from the road.
```

你可以使用任意数量的“部分”来构建你的描述，并可以根据需要和角色扮演的要求进行交换和替换。


----

<small>此文档页面并非由 `evennia/contrib/game_systems/multidescer/README.md`自动生成。如想阅读最新文档，请参阅原始README.md文件。</small>
