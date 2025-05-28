# Easy Fillable Form

贡献者 - Tim Ashley Jenkins, 2018

此模块包含一个生成 `EvMenu` 的函数，该菜单为玩家提供了一个可以按任意顺序填写的表单（例如用于角色生成或构建）。每个字段的值可以进行验证，函数允许对文本和整数输入进行轻松检查，设定最小值和最大值/字符长度，或者通过自定义函数进行验证。一旦表单提交，表单的数据将作为字典提交给您选择的任何可调用对象。

## 用法

初始化可填写表单菜单的函数相当简单，包括调用者、表单模板和回调 `callback(caller, result)`，该回调将在提交表单数据时传递给：

```python
init_fill_field(formtemplate, caller, formcallback)
```

表单模板被定义为字典列表 - 每个字典代表表单中的一个字段，并包含字段名称和行为的数据。例如，以下基本表单模板将允许玩家填写简单的角色简介：

```python
PROFILE_TEMPLATE = [
    {"fieldname": "Name", "fieldtype": "text"},
    {"fieldname": "Age", "fieldtype": "number"},
    {"fieldname": "History", "fieldtype": "text"},
]
```

这将向玩家展示一个 `EvMenu`，显示此基本表单：

```
      Name:
       Age:
   History:
```

在此菜单中，玩家可以使用 `<field> = <new value>` 的语法为任何字段分配新值，例如：

```
    > name = Ashley
    Field 'Name' set to: Ashley
```

单独输入 'look' 将显示表单及其当前值：

```
    > look

      Name: Ashley
       Age:
    History:
```

数字字段要求输入整数，并会拒绝任何无法转换为整数的文本：

```
    > age = youthful
    Field 'Age' requires a number.
    > age = 31
    Field 'Age' set to: 31
```

表单数据以 `EvTable` 的形式呈现，因此任意长度的文本将整齐地换行。

```
    > history = EVERY MORNING I WAKE UP AND OPEN PALM SLAM[...]
    Field 'History' set to: EVERY MORNING I WAKE UP AND[...]
    > look

      Name: Ashley
       Age: 31
   History: EVERY MORNING I WAKE UP AND OPEN PALM SLAM A VHS INTO THE SLOT.
            IT'S CHRONICLES OF RIDDICK AND RIGHT THEN AND THERE I START DOING
            THE MOVES ALONGSIDE WITH THE MAIN CHARACTER, RIDDICK. I DO EVERY
            MOVE AND I DO EVERY MOVE HARD.
```

当玩家输入 'submit'（或您指定的提交命令）时，菜单退出，表单的数据将作为字典传递给您指定的函数，如下所示：

```python
formdata = {"Name": "Ashley", "Age": 31, "History": "EVERY MORNING I[...]}
```

您可以在该函数中对这些数据进行任意处理 - 表单可以用于在角色上设置数据，帮助构建器创建对象，或用于玩家制作物品或执行涉及多个变量的其他复杂操作。

您可以在表单模板中也指定表单将接受的数据 - 假设例如您不接受低于 18 岁或高于 100 岁的值。您可以通过在字段字典中指定 "min" 和 "max" 值来实现：

```python
PROFILE_TEMPLATE = [
    {"fieldname": "Name", "fieldtype": "text"},
    {"fieldname": "Age", "fieldtype": "number", "min": 18, "max": 100},
    {"fieldname": "History", "fieldtype": "text"},
]
```

现在，如果玩家试图输入超出范围的值，表单将不接受该值：

```
    > age = 10
    Field 'Age' requires a minimum value of 18.
    > age = 900
    Field 'Age' has a maximum value of 100.
```

为文本字段设置 'min' 和 'max' 则将分别作为玩家输入的最小或最大字符长度。

提供表单给玩家有很多种方式 - 字段可以具有默认值或在空值时显示自定义消息，并且玩家输入可以通过自定义函数进行验证，从而提供了极大的灵活性。还有一个 'bool' 字段的选项，仅接受 True / False 输入，并可以自定义表示给玩家的选择（例如：是/否，开/关，启用/禁用等）。

此模块包含一个简单的示例表单，演示了所有包含的功能 - 一个允许玩家撰写消息给另一个在线角色并在自定义延迟后发送的命令。您可以通过在游戏的 `default_cmdsets.py` 模块中导入此模块并将 `CmdTestMenu` 添加到您的默认角色的命令集中进行测试。

## 字段模板键：

### 必需：

```
fieldname (str): 字段名称，呈现给玩家。
fieldtype (str): 所需值的类型：'text'、'number' 或 'bool'。
```

### 可选：

- max (int): 最大字符长度（如果是文本）或值（如果是数字）。
- min (int): 最小字符长度（如果是文本）或值（如果是数字）。
- truestr (str): 在布尔字段中表示 'True' 值的字符串。
  （例如，'开启'、'启用'、'是'）
- falsestr (str): 在布尔字段中表示 'False' 值的字符串。
  （例如，'关闭'、'禁用'、'否'）
- default (str): 初始值（如果未给出则为空）。
- blankmsg (str): 字段为空时显示的消息。
- cantclear (bool): 如果为 True，则字段不能被清除。
- required (bool): 如果为 True，则表单在字段为空时不能提交。
- verifyfunc (callable): 用于验证输入的可调用名称 - 以 `(caller, value)` 为参数。如果函数返回 True，则玩家的输入被视为有效 - 如果返回 False，则输入被拒绝。返回的任何其他值将充当字段的新值，替换玩家的输入。这允许使用非字符串或整数的值（例如对象 dbrefs）。对于布尔字段，返回 '0' 或 '1' 将将该字段设置为 False 或 True。


----

<small>此文档页面并非由 `evennia/contrib/utils/fieldfill/README.md`自动生成。如想阅读最新文档，请参阅原始README.md文件。</small>
