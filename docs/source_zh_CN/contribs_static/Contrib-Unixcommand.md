# 类 Unix 命令风格

由 Vincent Le Geoff (vlgeoff) 于 2017 年贡献

此模块包含一个命令类，使用替代语法解析器在游戏中实现 Unix 风格的命令语法。这意味着可以使用 `--options`、位置参数以及类似 `-n 10` 的语法。对于普通玩家来说，这可能不是最佳语法，但对于构建者来说，当他们需要一个命令执行多种功能并带有多种选项时，这可能非常有用。它在底层使用 Python 标准库中的 `ArgumentParser`。

## 安装

要使用此模块，请从您的命令中继承此模块中的 `UnixCommand`。您需要重写两个方法：

- `init_parser` 方法，用于向解析器添加选项。注意，当从 `UnixCommand` 继承时，通常不应重写常规的 `parse` 方法。
- `func` 方法，在解析命令后调用以执行命令（与任何命令类似）。

以下是一个简单的示例：

```python
from evennia.contrib.base_systems.unixcommand import UnixCommand

class CmdPlant(UnixCommand):
    '''
    种植一棵树或植物。

    此命令用于在您所在的房间种植一些东西。

    示例：
      plant orange -a 8
      plant strawberry --hidden
      plant potato --hidden --age 5
    '''

    key = "plant"

    def init_parser(self):
        "向解析器添加参数。"
        # 'self.parser' 继承自 `argparse.ArgumentParser`
        self.parser.add_argument("key",
                help="要在此处种植的植物的关键字")
        self.parser.add_argument("-a", "--age", type=int,
                default=1, help="要种植植物的年龄")
        self.parser.add_argument("--hidden", action="store_true",
                help="新种植的植物是否对玩家隐藏？")

    def func(self):
        "仅在解析器成功时调用 func。"
        # 'self.opts' 包含解析后的选项
        key = self.opts.key
        age = self.opts.age
        hidden = self.opts.hidden
        self.msg("准备种植 '{}', 年龄={}, 隐藏={}。".format(
                key, age, hidden))
```

要了解 argparse 的全部功能和支持的选项类型，请访问 [argparse 的文档](https://docs.python.org/2/library/argparse.html)。
