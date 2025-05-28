# 批处理器示例

由 Griatch 贡献，2012年

这是用于批处理器的简单示例。批处理器用于从一个或多个静态文件生成游戏内内容。文件可以使用版本控制存储，然后“应用”到游戏中以创建内容。

有两种批处理器类型：

- **Batch-cmd 处理器**：一个由 `#` 分隔的 Evennia 命令列表，会按顺序执行，例如 `create`、`dig`、`north` 等。当运行这种类型的脚本（文件名以 `.ev` 结尾）时，脚本的调用者将是执行脚本操作的对象。

- **Batch-code 处理器**：一个完整的 Python 脚本（文件名以 `.py` 结尾），通过执行 Evennia API 调用来构建，例如 `evennia.create_object` 或 `evennia.search_object` 等。它可以分成以注释分隔的块，这样可以逐步执行脚本的部分（在这方面，它与普通 Python 文件有些不同）。

## 用法

要测试这两个示例批处理文件，你需要 `Developer` 或 `superuser` 权限，登录游戏并运行以下命令：

    > batchcommand/interactive tutorials.batchprocessor.example_batch_cmds
    > batchcode/interactive tutorials.batchprocessor.example_batch_code

`/interactive` 会把你带入交互模式，这样可以跟随脚本的执行。如果跳过它，将一次构建所有内容。

这两个命令产生相同的结果 - 创建一个红色按钮对象、一张桌子和一把椅子。如果你在运行任一命令时加上 `/debug` 选项，这些对象将在之后被删除（例如用于快速测试语法，而不想不断生成新对象）。


----

<small>此文档页面并非由 `evennia/contrib/tutorials/batchprocessor/README.md`自动生成。如想阅读最新文档，请参阅原始README.md文件。</small>
