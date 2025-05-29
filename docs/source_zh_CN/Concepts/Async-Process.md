# 异步进程

```{important}
这是一个高级主题。
```

## 同步与异步

```{sidebar}
这在 [命令持续时间教程](../Howtos/Howto-Command-Duration.md) 中也有探讨。
```

大多数程序代码是*同步*运行的。这意味着代码中的每个语句在下一个语句开始之前都会被处理并完成。这使得代码易于理解。在许多情况下，这也是一种*要求*——后续代码通常依赖于先前语句中计算或定义的内容。

考虑在传统 Python 程序中的这段代码：

```python
    print("before call ...")
    long_running_function()
    print("after call ...")
```

运行时，这段代码会先打印 `"before call ..."`，然后 `long_running_function` 开始工作，无论需要多长时间。只有在它完成后，系统才会打印 `"after call ..."`。这很容易理解且逻辑清晰。Evennia 的大多数工作方式都是如此，通常命令按它们编码的严格顺序执行是很重要的。

Evennia 通过 Twisted 是一个单进程多用户服务器。简单来说，这意味着它快速地在处理玩家输入之间切换，以至于每个玩家都感觉他们在同时进行操作。然而，这只是一个巧妙的错觉：如果一个用户运行了一个包含 `long_running_function` 的命令，*所有*其他玩家实际上都被迫等待，直到它完成。

需要说明的是，在现代计算机系统上，这很少成为问题。很少有命令运行时间长到其他用户会注意到。而且如前所述，大多数时候你*希望*所有命令严格按顺序发生。

## `utils.delay`

```{sidebar} delay() vs time.sleep()
这相当于 `time.sleep()`，但 `delay` 是异步的，而 `sleep` 会在睡眠期间锁定整个服务器。
```

`delay` 函数是 `run_async` 的一个简单版本。它实际上只是将命令的执行延迟到将来的某个时间。

```python
     from evennia.utils import delay

     # [...]
     # 例如在命令中，`self.caller` 可用
     def callback(obj):
        obj.msg("Returning!")
     delay(10, callback, self.caller)
```

这将延迟回调的执行 10 秒。提供 `persistent=True` 以使延迟在服务器 `reload` 时保持。在等待期间，你可以正常输入命令。

你也可以尝试以下代码片段，看看它是如何工作的：

```python
py from evennia.utils import delay; delay(10, lambda who: who.msg("Test!"), self)
```

等待 10 秒，“Test!” 应该会回显给你。

## `@utils.interactive` 装饰器

`@interactive` [装饰器](https://realpython.com/primer-on-python-decorators/) 使任何函数或方法都可以以交互方式“暂停”和/或等待玩家输入。

```python
    from evennia.utils import interactive

    @interactive
    def myfunc(caller):
        
      while True:
          caller.msg("Getting ready to wait ...")
          yield(5)
          caller.msg("Now 5 seconds have passed.")

          response = yield("Do you want to wait another 5 secs?")  

          if response.lower() not in ("yes", "y"):
              break 
```

`@interactive` 装饰器赋予了函数暂停的能力。使用 `yield(seconds)` 将实现这一点——它将在给定的秒数后异步暂停，然后继续。这在技术上等同于使用 `call_async`，在 5 秒后继续执行回调。但使用 `@interactive` 的代码更容易理解。

在 `@interactive` 函数中，`response = yield("question")` 允许你向用户询问输入。然后你可以像使用 Python 的 `input` 函数一样处理输入。

所有这些使得 `@interactive` 装饰器非常有用。但它有一些注意事项：

- 被装饰的函数/方法/可调用对象必须有一个名为 `caller` 的参数。Evennia 将寻找这个名称的参数，并将其视为输入源。
- 以这种方式装饰函数会将其变成 Python [生成器](https://wiki.python.org/moin/Generators)。这意味着：
    - 你不能从生成器中使用 `return <value>`（只有空的 `return` 可以）。要从用 `@interactive` 装饰的函数/方法中返回值，你必须使用一个特殊的 Twisted 函数 `twisted.internet.defer.returnValue`。Evennia 也在 `evennia.utils` 中方便地提供了这个函数：

    ```python
    from evennia.utils import interactive, returnValue
    
    @interactive
    def myfunc():
    
        # ... 
        result = 10
    
        # 必须使用这个而不是 `return result`
        returnValue(result)
    ```

## `utils.run_async`

```{warning}
除非你有一个非常明确的目的，否则你不太可能从 `run_async` 中得到预期的结果。特别是，它仍将在与服务器其他部分相同的线程中运行你的长时间运行的函数。因此，虽然它是异步运行的，但非常繁重且 CPU 密集的操作仍会阻塞服务器。因此，不要将其视为在不影响服务器其他部分的情况下卸载繁重操作的方法。
```

当你不关心命令完成的顺序时，可以*异步*运行它。这使用 `src/utils/utils.py` 中的 `run_async()` 函数：

```python
    run_async(function, *args, **kwargs)
```

其中 `function` 将与 `*args` 和 `**kwargs` 一起异步调用。示例：

```python
    from evennia import utils
    print("before call ...")
    utils.run_async(long_running_function)
    print("after call ...")
```

现在，运行此代码时，你会发现程序不会等待 `long_running_function` 完成。实际上，你会立即看到 `"before call ..."` 和 `"after call ..."` 被打印出来。长时间运行的函数将在后台运行，你（和其他用户）可以正常继续操作。

使用异步调用的一个复杂之处在于如何处理该调用的结果。如果 `long_running_function` 返回一个你需要的值怎么办？在调用 `long_running_function` 后尝试处理结果的代码行没有意义——正如我们所看到的，`"after call ..."` 在 `long_running_function` 完成之前就已经打印出来了，这使得那行代码对于处理函数的数据没有意义。相反，必须使用*回调*。

`utils.run_async` 接受不会传递给长时间运行函数的保留关键字参数：

- `at_return(r)`（*回调*）是在异步函数（上面的 `long_running_function`）成功完成时调用的。参数 `r` 将是该函数的返回值（或 `None`）。

    ```python
        def at_return(r):
            print(r)
    ```

- `at_return_kwargs` - 一个可选字典，将作为关键字参数传递给 `at_return` 回调。
- `at_err(e)`（*错误回调*）是在异步函数失败并引发异常时调用的。此异常以*失败*对象 `e` 的形式传递给错误回调。如果你没有提供自己的错误回调，Evennia 将自动添加一个静默地将错误写入 evennia 日志的回调。下面是一个错误回调的示例：

```python
        def at_err(e):
            print("There was an error:", str(e))
```

- `at_err_kwargs` - 一个可选字典，将作为关键字参数传递给 `at_err` 错误回调。

在 [命令](../Components/Commands.md) 定义中进行异步调用的示例：

```python
    from evennia import utils, Command

    class CmdAsync(Command):

       key = "asynccommand"
    
       def func(self):     
           
           def long_running_function():  
               #[... 大量耗时代码 ...]
               return final_value
           
           def at_return_function(r):
               self.caller.msg(f"The final value is {r}")
    
           def at_err_function(e):
               self.caller.msg(f"There was an error: {e}")

           # 执行异步调用，设置所有回调
           utils.run_async(long_running_function, at_return=at_return_function,
at_err=at_err_function)
```

就是这样——从这里开始，我们可以忘记 `long_running_function`，继续做其他需要完成的事情。*无论何时*它完成，`at_return_function` 函数将被调用，我们将看到最终值。如果没有，我们将看到一条错误消息。

> 从技术上讲，`run_async` 只是一个非常薄且简化的 [Twisted Deferred](https://twistedmatrix.com/documents/9.0.0/core/howto/defer.html) 对象的包装器；如果没有提供错误回调，包装器还会设置一个默认的错误回调。如果你知道自己在做什么，没有什么能阻止你绕过这个实用函数，根据自己的喜好构建一个更复杂的回调链。
