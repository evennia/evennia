# Evennia 中的文本内标签解析

Evennia 会解析嵌入在文本中的各种特殊标签和标记，并根据数据是进出服务器动态转换。

- **颜色** - 使用 `|r`、`|n` 等标记文本的部分为颜色。这些颜色将为 Telnet 连接转换为 ANSI/XTerm256 颜色标签，并为 web 客户端转换为 CSS 信息。
  ```
  > say 你好，我今天戴着我的 |r红色帽子|n。
  ```

- **可点击链接** - 这允许你提供一个用户可以点击以执行游戏内命令的文本。其格式为 `|lc command |lt text |le`。可点击链接通常仅在 _输出_ 方向解析，因为如果用户可以提供它们，可能会成为安全问题。要激活，必须在设置中添加 `MXP_ENABLED=True`（默认禁用）。
  ```
  py self.msg("这是一个 |c look |lt可点击的 'look' 链接|le")
  ```

- **FuncParser 可调用函数** - 这些是形式为 `$funcname(args, kwargs)` 的完整函数调用，导致对 Python 函数的调用。解析器可以在不同情况下运行具有不同可调用函数的解析。解析器在所有输出消息上运行，如果 `settings.FUNCPARSER_PARSE_OUTGOING_MESSAGES_ENABLED=True`（默认禁用）。
  ```
  > say 答案是 $eval(40 + 2)!
  ```
