# EvEditor

Evennia 提供了一个强大的行编辑器 `evennia.utils.eveditor.EvEditor`，它模仿了著名的 VI 编辑器。这个编辑器支持逐行编辑、撤销/重做、行删除、查找/替换、填充和去缩进等功能。

## 启动编辑器

编辑器的创建方式如下：

```python
from evennia.utils.eveditor import EvEditor

EvEditor(caller,
         loadfunc=None, savefunc=None, quitfunc=None,
         key="")
```

- `caller` (Object 或 Account): 编辑器的使用者。
- `loadfunc` (可选 callable): 编辑器第一次启动时调用的函数。函数接受 `caller` 作为唯一参数，并返回用于编辑器缓冲区的初始文本。
- `savefunc` (可选 callable): 当用户保存缓冲区时调用，传入 `caller` 和 `buffer` 两个参数，其中 `buffer` 是当前的缓冲内容。
- `quitfunc` (可选 callable): 当用户退出编辑器时调用。如果给定，清理和退出的消息必须由此函数处理。
- `key` (可选 str): 在编辑时用于显示的标识文本，没有其他机械功能。
- `persistent` (默认为 `False`): 如果设置为 `True`，编辑器将在重启后依然保持打开状态。

## 使用 EvEditor

以下是一个示例命令，用于使用编辑器设置特定属性。

```python
from evennia import Command
from evennia.utils import eveditor

class CmdSetTestAttr(Command):
    """
    使用行编辑器设置 "test" 属性。

    用法：
       settestattr
    """
    key = "settestattr"
    
    def func(self):
        "设置回调并启动编辑器"
        
        def load(caller):
            "获取当前值"
            return caller.attributes.get("test")
        
        def save(caller, buffer):
            "保存缓冲区"
            caller.attributes.add("test", buffer)
        
        def quit(caller):
            "处理退出消息"
            caller.msg("编辑器已退出")
        
        key = f"{self.caller}/test"
        # 启动编辑器
        eveditor.EvEditor(self.caller,
                          loadfunc=load, savefunc=save, quitfunc=quit,
                          key=key)
```

### 持久编辑器

如果在创建编辑器时将 `persistent` 关键字设置为 `True`，则即使在重启游戏时，编辑器也将保持打开状态。为了实现持久性，编辑器的回调函数（`loadfunc`，`savefunc` 和 `quitfunc`）需要定义为模块中的顶级函数。因为这些函数将被存储，Python 需要找到它们。

```python
from evennia import Command
from evennia.utils import eveditor

def load(caller):
    "获取当前值"
    return caller.attributes.get("test")

def save(caller, buffer):
    "保存缓冲区"
    caller.attributes.add("test", buffer)

def quit(caller):
    "处理退出消息"
    caller.msg("编辑器已退出")

class CmdSetTestAttr(Command):
    """
    使用行编辑器设置 "test" 属性。

    用法：
       settestattr
    """
    key = "settestattr"
    
    def func(self):
        "设置回调并启动编辑器"
        key = f"{self.caller}/test"
        # 启动编辑器
        eveditor.EvEditor(self.caller,
                          loadfunc=load, savefunc=save, quitfunc=quit,
                          key=key, persistent=True)
```

### 行编辑器使用

该编辑器尽可能模拟 `VIM` 编辑器。以下是来自编辑器内帮助命令 (`:h`) 的摘录。

```
 <txt>  - 任何非命令的输入都将添加到缓冲区末尾。
 :  <l> - 查看缓冲区或仅行 <l>
 :: <l> - 查看缓冲区，不显示行号或其他解析
 :::    - 在行上单独打印 ':' 字符...
 :h     - 显示此帮助信息。

 :w     - 保存缓冲区（不退出）
 :wq    - 保存缓冲区并退出
 :q     - 退出（如果缓冲区已更改，则询问保存）
 :q!    - 不保存退出，无需询问

 :u     - （撤销）回退到历史中
 :uu    - （重做）前进到历史中
 :UU    - 将所有更改重置为初始状态

 :dd <l>     - 删除行 <n>
 :dw <l> <w> - 删除整缓冲区或行 <l> 中的单词或正则表达式 <w>
 :DD         - 清空缓冲区

 :y  <l>        - 复制（yank）行 <l> 到复制缓冲区
 :x  <l>        - 剪切（cut）行 <l> 并存入复制缓冲区
 :p  <l>        - 在 <l> 行之前粘贴（put）先前复制的行
 :i  <l> <txt>  - 在行 <l> 插入新文本 <txt>。旧行将下移
 :r  <l> <txt>  - 用文本 <txt> 替换行 <l>
 :I  <l> <txt>  - 在行 <l> 开头插入文本 <txt>
 :A  <l> <txt>  - 在行 <l> 末尾追加文本 <txt>

 :s <l> <w> <txt> - 在缓冲区或行 <l> 中查找/替换单词或正则表达式 <w>

 :f <l>    - 对整个缓冲区或行 <l> 进行填充
 :fi <l>   - 对整个缓冲区或行 <l> 进行缩进
 :fd <l>   - 对整个缓冲区或行 <l> 去缩进

 :echo - 开启/关闭输入的回显（对某些客户端有帮助）

    说明：
    <l> - 行号或范围 lstart:lend，例如 '3:7'。
    <w> - 单个单词或用引号引起来的多个单词。
    <txt> - 较长字符串，通常不需要用引号括起来。
```

### EvEditor 编辑代码

`EvEditor` 还用于编辑 Evennia 中的某些 Python 代码。`py` 命令支持 `/edit` 开关，这将以代码模式打开 EvEditor。此模式与标准模式并没有显著不同，只是处理了代码块的自动缩进以及一些控制此行为的选项。

- `:<` 用于将未来行的缩进级别减少一层。
- `:+` 用于将未来行的缩进级别增加一层。
- `:=` 用于完全禁用自动缩进。

自动缩进的目的是使代码编辑更简单。Python 需要正确的缩进，这不仅仅是为了美观，而是为了决定代码块的起始和结束。`EvEditor` 会尝试猜测下一行的缩进级别。例如，当输入块 "if" 时，`EvEditor` 会在下一行建议增加一个缩进级别。然而，这个功能并不总是完美，有时需要使用上述选项来处理缩进。

`:=` 可以完全关闭自动缩进。这在尝试粘贴已经正确缩进的多行代码时特别有用。

要在代码模式下查看 `EvEditor`，可以使用 `@py/edit` 命令。输入你的代码（可以在一行或多行中）。然后可以使用 `:w` 选项（保存不退出）来执行你输入的代码。`:!` 也会执行同样的操作。在不关闭编辑器的情况下执行代码在你希望测试输入的代码后继续添加新行时非常有用。
