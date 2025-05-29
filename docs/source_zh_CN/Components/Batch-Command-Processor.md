# 批量命令处理器

有关使用批处理器的介绍和动机，请参见 [此处](./Batch-Processors.md)。本页面描述了批量-*命令* 处理器。批量-*代码* 处理器覆盖 [此处](./Batch-Code-Processor.md)。

批量命令处理器是一个超级用户专用功能，通过以下命令调用：

```
> batchcommand path.to.batchcmdfile
```

其中 `path.to.batchcmdfile` 是指向 *批量命令文件* 的路径，并以 "`.ev`" 结尾。该路径是相对于您在设置中定义的用于保存批量文件的文件夹，以 Python 路径的形式给出的。默认文件夹是（假设您的游戏位于 `mygame` 文件夹中） `mygame/world`。因此，如果您想要运行位于 `mygame/world/batch_cmds.ev` 中的示例批量文件，您可以使用：

```
> batchcommand batch_cmds
```

批量命令文件包含以注释分隔的 Evennia 游戏内命令列表。处理器将从头到尾运行批量文件。请注意，*如果其中的命令失败，它将不会停止*（处理器无法识别所有不同命令的失败情况）。因此，请密切关注输出，或使用 *交互模式*（见下文）以更受控制的方式逐步运行文件。

## 批量文件

批量文件是一个简单的纯文本文件，其中包含 Evennia 命令。就像您在游戏中所写的命令一样，只是行间分隔的方式更灵活。

以下是 `*.ev` 文件的语法规则。您会发现这非常简单：

- 所有在行首具有 `#`（哈希符号）的行被视为 *注释*。所有非注释行被视为命令和/或它们的参数。
- 注释行具有实际功能——它们标记 *上一个命令定义的结束*。因此，切勿在文件中直接写两个命令——用注释将它们分开，否则第二个命令将被视为第一个命令的参数。此外，使用大量注释也是良好的实践。
- 以 `#INSERT` 开头的行是注释行，但也表示一个特殊指令。语法为 `#INSERT <path.batchfile>`，尝试将给定的批量命令文件导入当前文件。插入的批量文件（以 `.ev` 结尾）将在 `#INSERT` 指令的那一点正常运行。
- 命令定义中的额外空格是 *被忽略的*。
- 完全空白的一行在文本中会转化为换行。因此，两行空白将意味着一个新的段落（这显然只与接受此类格式的命令相关，例如 `@desc` 命令）。
- 文件中的最后一个命令不需要以注释结束。
- 您 *不能* 在批量文件中嵌套另一个 `batchcommand` 语句。如果您想将多个批量文件链接在一起，请使用 `#INSERT` 批量指令。此外，您还不能在批量文件中启动 `batchcode` 命令，这两个批处理器不兼容。

以下是位于 `evennia/contrib/tutorial_examples/batch_cmds.ev` 中找到的示例文件的一个版本。

```bash
#
# 这是 Evennia 的一个示例批处理构建文件。
#

# 这将创建一个红色按钮
@create button:tutorial_examples.red_button.RedButton
# (此注释结束 @create 的输入)
# 下一条命令。让我们创建一些东西。
@set button/desc = 
  This is a large red button. Now and then 
  it flashes in an evil, yet strangely tantalizing way. 

  A big sign sits next to it. It says:

-----------
 
 Press me! 

-----------

  ... It really begs to be pressed! You 
know you want to! 

# 这将插入来自另一个批量命令文件的命令，该文件名为 batch_insert_file.ev。
#INSERT examples.batch_insert_file

# (这结束了 @set 命令）。请注意，单行换行和参数中的多余空格会被忽略。空行会在输出中转化为换行。
# 现在让我们把按钮放到它应该在的地方（让我们假设 ##2 是我们示例中的邪恶巢穴）
@teleport #2
# (此注释结束 @teleport 命令。) 
# 现在我们扔掉它，以便其他人可以看到它。
drop button
```

要测试此命令，请运行 `@batchcommand` 在文件上：

```
> batchcommand contrib.tutorial_examples.batch_cmds
```

一个按钮将被创建、描述并在 Limbo 中放下。所有命令将由调用命令的用户执行。

> 请注意，如果您与按钮交互，您可能会发现其描述发生变化，丢失您之前设置的自定义描述。这仅仅是这个特定对象的工作方式。

## 交互模式

交互模式允许您更逐步地控制批量文件的执行。这对于调试很有用，如果您有一个大型批量文件且只更新其中的一小部分——再次运行整个文件将是浪费时间（而且在创建对象的情况下，您将最终拥有多个同名对象，例如）。使用 `batchcommand` 和 `/interactive` 标志进入交互模式。

```
> @batchcommand/interactive tutorial_examples.batch_cmds
```

您将看到：

```
01/04: @create button:tutorial_examples.red_button.RedButton  (hh for help)
```

这表明您处于 `@create` 命令上，这是该批量文件中的四个命令中的第一个。请注意，此时命令 `@create` *尚未* 被实际处理！

要查看您即将运行的完整命令，请使用 `ll`（批处理处理器版的 `look`）。使用 `pp` 实际处理当前命令（这将实际上 `@create` 该按钮）——并确保它按预期工作。使用 `nn`（下一个）转到下一个命令。使用 `hh` 获取命令列表。

如果有错误，请在批量文件中修复它们，然后使用 `rr` 重新加载文件。您仍将在相同的命令下，可以根据需要轻松再次运行它。这样形成简单的调试周期。它还允许您重新运行单个麻烦的命令——如前所述，在大型批量文件中这非常有用。请注意，在许多情况下，命令依赖于先前的命令（例如，如果上述示例中的 `create` 失败，则后续命令将没有任何操作对象）。

使用 `nn` 和 `bb`（下一个和向后）逐步浏览文件；例如，`nn 12` 将跳跃 12 步向前（而不处理其中的任何命令）。在交互模式下，所有正常的 Evennia 命令也应照常工作。

## 限制和注意事项

批量命令构建的主要问题是，当您运行批量命令脚本时，您（*您*，作为您的角色）实际上是在游戏中移动，按顺序创建和构建房间，就像您逐个输入这些命令一样。

您必须在创建文件时考虑到这一点，以便您能够“走到”（或瞬移到）正确的地方。这也意味着您可能会受到您创建的事物的影响，例如，怪物攻击您或陷阱立即伤害您。

如果您知道您的房间和对象将通过批量命令脚本部署，您可以提前进行规划。为此，您可以利用非持久性属性 `batch_batchmode`——该属性只在批处理器运行时被设置。以下是使用它的示例：

```python
class HorribleTrapRoom(Room):
    # ... 
    def at_object_receive(self, received_obj, source_location, **kwargs):
        """进入房间时应用可怕的陷阱！"""
        if received_obj.ndb.batch_batchmode: 
            # 如果我们当前正在构建房间，则跳过
            return 
        # 开始可怕的陷阱代码
```

因此，如果我们正在构建房间时，将跳过此钩子。这可以用于任何东西，包括确保怪物在创建时不会开始攻击您。

还有其他策略，例如为活动对象添加一个开/关开关，并确保在创建时始终设置为 *关闭*。

## .ev 文件的编辑器高亮显示

- [GNU Emacs](https://www.gnu.org/software/emacs/) 用户可能会发现使用 Emacs 的 *evennia mode* 是很有趣的。这是一个 Emacs 主模式，位于 `evennia/utils/evennia-mode.el` 中。它在编辑 `.ev` 文件时提供正确的语法高亮和用 `<tab>` 进行缩进。请参阅该文件的头部获取安装说明。
- [VIM](https://www.vim.org/) 用户可以使用 amfl 的 [vim-evennia](https://github.com/amfl/vim-evennia) 模式，查看其说明以获取安装说明。
