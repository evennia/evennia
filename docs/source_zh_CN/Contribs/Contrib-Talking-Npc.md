# 健谈的 NPC 示例

由 Griatch 于 2011 年贡献，grungies1138 于 2016 年更新

这是一个能够进行简单菜单驱动对话的静态 NPC 对象示例。适合作为任务发布者或商人。

## 安装

通过创建一个类型类为 `contrib.tutorials.talking_npc.TalkingNPC` 的对象来创建 NPC，例如：

```
create/drop John : contrib.tutorials.talking_npc.TalkingNPC
```

在与 NPC 同一房间中使用 `talk` 命令来开始对话。

如果同一个房间中有多个健谈的 NPC，你将选择与哪个 NPC 进行对话（Evennia 会自动处理这一点）。

这种 EvMenu 的使用非常简单；有关更复杂的可能性，请参见 EvMenu。


----

<small>此文档页面并非由 `evennia/contrib/tutorials/talking_npc/README.md`自动生成。如想阅读最新文档，请参阅原始README.md文件。</small>
