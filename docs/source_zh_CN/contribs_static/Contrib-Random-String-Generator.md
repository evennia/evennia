# 伪随机生成器和注册表

由 Vincent Le Goff (vlgeoff) 贡献于 2017 年

这个实用程序可以用于根据特定标准生成伪随机的信息字符串。例如，你可以用它来生成电话号码、车牌号、验证码、游戏内的安全密码等。生成的字符串将被存储且不会重复。

## 使用示例

这是一个非常简单的示例：

```python
from evennia.contrib.utils.random_string_generator import RandomStringGenerator

# 创建一个电话号码生成器
phone_generator = RandomStringGenerator("phone number", r"555-[0-9]{3}-[0-9]{4}")

# 生成一个电话号码（格式为 555-XXX-XXXX，其中 X 为数字）
number = phone_generator.get()

# `number` 将包含类似于 "555-981-2207" 的内容
# 如果再次调用 `phone_generator.get`，将不会得到相同的号码
phone_generator.all()  # 将返回所有当前使用的电话号码列表
phone_generator.remove("555-981-2207")

# 该号码可以再次生成
```

## 导入

1. 从 contrib 中导入 `RandomStringGenerator` 类。
2. 创建该类的实例，传入两个参数：
   - 生成器的名称（如 "phone number"、"license plate"...）。
   - 表示预期结果的正则表达式。
3. 如上所示使用生成器的 `all`、`get` 和 `remove` 方法。

要了解如何阅读和创建正则表达式，可以参考 [re 模块的文档](https://docs.python.org/2/library/re.html)。以下是一些你可以使用的正则表达式示例：

- `r"555-\d{3}-\d{4}"`：555，一个破折号，3 位数字，另一个破折号，4 位数字。
- `r"[0-9]{3}[A-Z][0-9]{3}"`：3 位数字，一个大写字母，3 位数字。
- `r"[A-Za-z0-9]{8,15}"`：8 到 15 个字母和数字。

在后台，会创建一个脚本来存储单个生成器的生成信息。`RandomStringGenerator` 对象还将读取你提供的正则表达式，以查看所需的信息（字母、数字、更受限的类、简单字符等）。更复杂的正则表达式（例如带分支的）可能无法使用。
