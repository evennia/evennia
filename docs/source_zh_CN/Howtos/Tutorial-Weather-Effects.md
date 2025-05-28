# 向房间添加天气消息

本教程将指导我们为我们的 MUD 创建一个简单的天气系统。我们希望使用的方式是让所有户外房间定期和半随机地回显天气相关的消息。例如，“云层在上方聚集”，“开始下雨”等等。

可以想象，每个游戏中的户外房间都运行了一个脚本，定期触发。然而，对于这个特定的例子，更有效的方法是使用“计时器订阅”模型。

原理很简单：不是让每个对象单独跟踪时间，而是让它们订阅一个全局计时器，由它来处理时间管理。这不仅集中和组织了大量代码，还减少了计算开销。

Evennia 的 [TickerHandler](../Components/TickerHandler.md) 特别提供了这样的订阅模型。我们将为我们的天气系统使用它。

我们将创建一个新的 WeatherRoom 类型类，该类能够感知昼夜循环。

```python
import random
from evennia import DefaultRoom, TICKER_HANDLER

ECHOES = ["The sky is clear.", 
          "Clouds gather overhead.",
          "It's starting to drizzle.",
          "A breeze of wind is felt.",
          "The wind is picking up"]  # 等等  

class WeatherRoom(DefaultRoom):
    "这个房间会在规定的时间间隔内被更新"
    
    def at_object_creation(self):
        "只在对象创建时调用"
        TICKER_HANDLER.add(60 * 60, self.at_weather_update)

    def at_weather_update(self, *args, **kwargs):
        "在规定的时间间隔内被调用"
        echo = random.choice(ECHOES)
        self.msg_contents(echo)
```

在 `at_object_creation` 方法中，我们简单地将自己添加到 TickerHandler，并告诉它每小时调用一次 `at_weather_update` （`60*60` 秒）。在测试期间，您可能希望尝试更短的时间间隔。

为了使这一切发挥作用，我们还创建了一个自定义钩子 `at_weather_update(*args, **kwargs)`，这是 TickerHandler 钩子所需的调用信号。

从此以后，该房间将在天气变化时通知房间内的所有人。当然，这个特定例子非常简单——天气的回响只是随机选择，并不关心之前的天气状态。将其扩展为更现实的情况将是一个有用的练习。
