# 默认命令语法

Evennia 允许使用任何命令语法。

如果你喜欢 DikuMUDs、LPMuds 或 MOOs 的处理方式，你可以在 Evennia 中模拟它们。如果你有雄心壮志，甚至可以设计一种全新的风格，完美契合你对理想游戏的梦想。有关如何实现这一点的信息，请参阅 [Command](../Components/Commands.md) 文档。

不过，我们提供了一个默认设置。默认的 Evennia 设置倾向于 *类似* [MUX2](https://www.tinymux.org/) 及其近亲 [PennMUSH](https://www.pennmush.org)、[TinyMUSH](https://github.com/TinyMUSH/TinyMUSH/wiki) 和 [RhostMUSH](http://www.rhostmush.com/)：

```
command[/switches] object [= options]
```

这种相似性部分上是历史原因，这些代码库为管理和构建提供了非常成熟的功能集。

然而，Evennia *不是* 一个 MUX 系统。它在许多方面的工作方式非常不同。例如，Evennia 故意缺少在线软代码语言（这一政策在我们的 [软代码政策页面](./Soft-Code.md) 中有解释）。Evennia 也不回避在适当时使用自己的语法：MUX 语法是经过长时间有机发展而来的，坦率地说，在某些地方相当晦涩。总而言之，默认命令语法最多应被称为“类似 MUX”或“受 MUX 启发”。

```{toctree}
:hidden:
Soft-Code
```
