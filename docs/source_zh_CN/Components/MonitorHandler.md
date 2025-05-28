# MonitorHandler

*MonitorHandler* 是一个用于监视对象属性或属性变化的系统。可以将监视器视为一种响应变化的触发器。

MonitorHandler 的主要用途是向客户端报告变化；例如，客户端会话可能会请求 Evennia 监视角色的 `health` 属性值，并在其变化时报告。这样，客户端可以根据需要更新其生命值条形图。

## 使用 MonitorHandler

可以通过单例 `evennia.MONITOR_HANDLER` 访问 MonitorHandler。处理程序的代码位于 `evennia.scripts.monitorhandler`。

以下是添加新监视器的方法：

```python
from evennia import MONITOR_HANDLER

MONITOR_HANDLER.add(obj, fieldname, callback,
                    idstring="", persistent=False, **kwargs)
```

- `obj` ([Typeclassed](./Typeclasses.md) 实体) - 要监视的对象。由于必须是类型化的，这意味着你不能使用 monitorhandler 监视 [Sessions](./Sessions.md) 上的变化。
- `fieldname` (str) - `obj` 上字段或[属性](./Attributes.md)的名称。如果你想监视数据库字段，必须指定其完整名称，包括起始的 `db_`（如 `db_key`、`db_location` 等）。任何不以 `db_` 开头的名称都被假定为属性的名称。这种区别很重要，因为 MonitorHandler 会自动知道要监视属性的 `db_value` 字段。
- `callback` (callable) - 当字段更新时，将以 `callback(fieldname=fieldname, obj=obj, **kwargs)` 的形式调用。
- `idstring` (str) - 用于区分同一对象和字段名上的多个监视器。这是为了以后正确识别和移除监视器所必需的。它也用于保存监视器。
- `persistent` (bool) - 如果为 True，监视器将在服务器重启后继续存在。

示例：

```python
from evennia import MONITOR_HANDLER as monitorhandler

def _monitor_callback(fieldname="", obj=None, **kwargs):    
    # 报告回调，适用于 db-fields 和 Attributes
    if fieldname.startswith("db_"):
        new_value = getattr(obj, fieldname)
    else: # 一个属性    
        new_value = obj.attributes.get(fieldname)
    obj.msg(f"{obj.key}.{fieldname} 改变为 '{new_value}'。")

# （我们也可以在这里添加 _some_other_monitor_callback）

# 监视属性（假设我们已经有 obj）
monitorhandler.add(obj, "desc", _monitor_callback)  

# 使用两个不同的回调监视同一个 db-field（必须通过 id_string 区分）
monitorhandler.add(obj, "db_key", _monitor_callback, id_string="foo")  
monitorhandler.add(obj, "db_key", _some_other_monitor_callback, id_string="bar")
```

监视器由其监视的*对象实例*、对象上要监视的字段/属性的*名称*及其 `idstring`（`obj` + `fieldname` + `idstring`）的组合唯一标识。除非显式给出，否则 `idstring` 将为空字符串。

因此，要“取消监视”上述内容，你需要提供足够的信息，以便系统能够唯一找到要移除的监视器：

```python
monitorhandler.remove(obj, "desc")
monitorhandler.remove(obj, "db_key", idstring="foo")
monitorhandler.remove(obj, "db_key", idstring="bar")
```
