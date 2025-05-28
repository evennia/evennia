# 听取发言的 NPC

```
> say hi 
你说：“hi”
桥下的巨魔回答：“你好啊。”
```

本文将解释如何让 NPC 对角色在其当前位置说话做出反应。这一原理适用于其他场景，例如敌人加入战斗或对角色拔出武器作出反应。

```python
# mygame/typeclasses/npc.py

from characters import Character

class Npc(Character):
    """
    扩展角色类的 NPC 类型类。
    """
    def at_heard_say(self, message, from_obj):
        """
        一个简单的监听和响应。这使得子类 NPC 可以轻松地对发言作出不同反应。
        """ 
        # message 的形式为 `<Person> says, "say_text"`
        # 我们想要提取 say_text，而不包含引号和任何空格
        message = message.split('says, ')[1].strip(' "')

        # 我们将在下面的 .msg() 中使用这个
        return f"{from_obj} 说：'{message}'"
```

我们添加了一个简单的方法 `at_heard_say`，用于格式化它听到的内容。我们假设传入的方法消息的形式为 `某人说，“你好”`，并确保在这个例子中仅提取出 `你好`。

我们实际上还没有调用 `at_heard_say`。我们将在下一步中处理它。

当房间中的某人对这个 NPC 说话时，它的 `msg` 方法将被调用。我们将修改 NPC 的 `.msg` 方法来捕捉发言，以便 NPC 可以回应。

```python
# mygame/typeclasses/npc.py

from characters import Character

class Npc(Character):

    # [at_heard_say() goes here]

    def msg(self, text=None, from_obj=None, **kwargs):
        "自定义 msg() 方法以响应发言。"

        if from_obj != self:
            # 确保不重复自己说过的话，否则会导致循环
            try:
                # 如果 text 来自发言，`text` 是 `('say_text', {'type': 'say'})`
                say_text, is_say = text[0], text[1]['type'] == 'say'
            except Exception:
                is_say = False
            if is_say:
                # 首先获取响应（如果有）
                response = self.at_heard_say(say_text, from_obj)
                # 如果有响应
                if response is not None:
                    # 说出我们自己的话，使用返回值
                    self.execute_cmd(f"say {response}")   
    
        # 如果任何人有人对这个 NPC 进行操纵，这是必要的——否则你将不会收到来自服务器的任何反馈（连查看结果都会看不到）
        super().msg(text=text, from_obj=from_obj, **kwargs) 
```

所以，假如 NPC 收到了发言，并且该发言并不是来自 NPC 本身，它将使用 `at_heard_say` 钩子回显它。以上示例中的一些注意事项：

- **第 15 行**：`text` 输入可以因调用此 `msg` 的位置而异。如果你查看 [say 命令的代码](evennia.commands.default.general.CmdSay)，你会发现它会通过 `("Hello", {"type": "say"})` 调用 `.msg`。我们利用这个知识来判断这是否来自发言。
- **第 24 行**：我们使用 `execute_cmd` 来调用 NPC 的自己的 `say` 命令。这是可行的，因为 NPC 实际上是 `DefaultCharacter` 的子类 - 因此它上会有 `CharacterCmdSet`！通常你应尽量少用 `execute_cmd`；直接调用命令使用的实际代码通常更高效。对于本教程，调用命令的做法更简短，同时确保所有钩子都能触发。
- **第 26 行**：注意关于 `super` 的注释在最后。这将触发父类中的“默认” `msg`。只要没有人操纵该 NPC（通过 `@ic <npcname>`），这其实并不必要，但明智的是将其保留在这里，因为操控它的玩家如果 `msg()` 从不向他们返回任何内容，将会完全失去视线！

现在完成这部分内容，让我们创建一个 NPC 并看看它会说些什么。

```
reload
create/drop Guild Master:npc.Npc
```

（你也可以将路径给定为 `typeclasses.npc.Npc`，但 Evennia 会自动查找 `typeclasses` 文件夹，因此稍微简短一点）。

```
> say hi
你说：“hi”
Guild Master 说：“你说：'hi'”
```

## 各种说明

实现此类功能的方法有很多。一种替代的示例是在 *Character* 上修改 `at_say` 钩子。它可以检测到是否发送给 NPC，并直接调用 `at_heard_say` 钩子。

虽然教程的解决方案有优点，仅在 NPC 类中包含了代码，但将其与使用角色类结合提供了更直接的控制权，以决定 NPC 将如何响应。选择哪种方式取决于你游戏的具体设计需求。
