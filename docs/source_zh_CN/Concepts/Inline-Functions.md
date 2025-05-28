# 内联函数

```{sidebar}
有关内联函数的更多信息，请参阅 [FuncParser](../Components/FuncParser.md) 文档。
```

_内联函数_，也称为 _funcparser 函数_，是嵌入形式的字符串：

```
$funcname(args, kwargs)
```

例如：

```
> say the answer is $eval(24 * 12)!
You say, "the answer is 288!"
```

默认情况下，传出字符串的一般处理是禁用的。要激活传出字符串的内联函数解析，请在你的设置文件中添加：

```python
FUNCPARSER_PARSE_OUTGOING_MESSAGES_ENABLED = True
```

内联函数由 [FuncParser](../Components/FuncParser.md) 提供。在其他一些情况下也会启用：

- 处理[原型](../Components/Prototypes.md)；这些“原型函数”允许原型在生成时动态更改其值。例如，你可以设置 `{key: '$choice(["Bo", "Anne", "Tom"])'`，每次生成一个随机命名的角色。
- 处理传递给 `msg_contents` 方法的字符串。这允许[根据接收者发送不同的消息](./Change-Message-Per-Receiver.md)。
