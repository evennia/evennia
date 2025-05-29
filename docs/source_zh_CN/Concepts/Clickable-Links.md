# 可点击链接

Evennia 允许在支持的客户端中使用可点击的链接。这会标记某些文本，使其可以通过鼠标点击，进而触发给定的 Evennia 命令或在外部浏览器中打开一个 URL。要查看可点击的链接，玩家必须使用 Evennia 网页客户端或支持 [MXP](http://www.zuggsoft.com/zmud/mxp.htm) 的第三方 telnet 客户端（*注意：Evennia 仅支持可点击链接，不支持其他 MXP 功能*）。

对于缺乏 MXP 支持的客户端，用户只会看到链接作为普通文本。

```{important}
默认情况下，无法从游戏内添加可点击链接。尝试这样做时，链接将会以普通文本返回。这是一种安全措施。有关更多信息，请参见[设置](#settings)。
```

## 点击运行命令

```
|lc command |lt text |le
```

示例：

```
"If you go |lcnorth|ltto the north|le you will find a cottage."
```

这将显示为 "If you go __to the north__ you will find a cottage."，点击链接将执行命令 `north`。

## 点击在浏览器中打开 URL

```
|lu url |lt text |le 
```

示例：

```
"Omnious |luhttps://mycoolsounds.com/chanting|ltchanting sounds|le are coming from beyond the door."
```

这将显示为 "Omnious **chanting sounds** are coming from beyond the door"，如果客户端支持，点击链接将在浏览器中打开 URL。

## 设置

启用/禁用 MXP（默认启用）。

```
MXP_ENABLED = True 
```

默认情况下，帮助条目有可点击的主题。

```
HELP_CLICKABLE_TOPICS = True
```

默认情况下，可点击链接仅在 _代码中提供的字符串_（或通过 [批处理脚本](../Components/Batch-Processors.md)）中可用。你 _不能_ 从游戏内部创建可点击链接——结果将不会显示为可点击。

这是一种安全措施。想象一下，如果用户能够在他们的描述中输入可点击链接，例如：

```
|lc give 1000 gold to Bandit |ltClick here to read my backstory!|le
```

点击链接的玩家可能会不小心支付 1000 金币给强盗。

这由以下默认设置控制：

```
MXP_OUTGOING_ONLY = True
```

只有在你确定你的游戏不会因此被利用时，才禁用此保护。
