# Buffs

由 Tegiminis 贡献，2022年

Buff 是一个定时对象，附加到游戏实体上。它能够修改值、触发代码，或两者兼而有之。这在 RPG，特别是动作游戏中是一种常见的设计模式。

## 特性

- **`BuffHandler`**: 一个 Buff 处理器，可以应用到你的对象上。
- **`BaseBuff`**: 一个 Buff 类，用于扩展以创建你自己的 Buff。
- **`BuffableProperty`**: 一个样本属性类，展示如何自动检查修饰符。
- **`CmdBuff`**: 应用 Buff 的命令。
- **`samplebuffs.py`**: 一些示例 Buff 供学习使用。

## 快速开始
将处理器分配给对象的一个属性，如下所示：

```python
@lazy_property
def buffs(self) -> BuffHandler:
    return BuffHandler(self)
```

然后可以调用处理器来添加或操作 Buff，如：`object.buffs`。请参阅 **使用处理器**。

### 自定义

如果你想自定义处理器，可以给构造函数传递两个参数：
- **`dbkey`**: 你希望用作 Buff 数据库属性键的字符串。默认为 "buffs"。这允许你保持单独的 Buff 池，例如 "buffs" 和 "perks"。
- **`autopause`**: 如果你希望这个处理器在其拥有对象未被控制时自动暂停游戏时间 Buff。

> **注意**：如果启用了自动暂停，你必须在拥有对象的 `at_init` 钩子中初始化该属性。否则，热重载可能导致游戏时间 Buff 在控制或未控制时未能正确更新。

假设你希望为对象 `perks` 创建另一个处理器，它有一个单独的数据库并尊重游戏时间 Buff。你可以这样分配这个新属性：

```python
class BuffableObject(Object):
    @lazy_property
    def perks(self) -> BuffHandler:
        return BuffHandler(self, dbkey='perks', autopause=True)

    def at_init(self):
        self.perks
```

## 使用处理器

以下是如何使用你的新处理器。

### 应用 Buff

调用处理器的 `add` 方法。这需要一个类引用，也包含一些可选参数来定制 Buff 的持续时间、叠加等。你还可以传递一个字典，通过 `to_cache` 可选参数在 Buff 的缓存中存储任意的值。这不会覆盖缓存中的正常值。

```python
self.buffs.add(StrengthBuff)                            # 单个堆叠的 StrengthBuff，使用正常的持续时间
self.buffs.add(DexBuff, stacks=3, duration=60)          # 三个堆叠的 DexBuff，持续时间为 60 秒
self.buffs.add(ReflectBuff, to_cache={'reflect': 0.5})  # 单个堆叠的 ReflectBuff，带有额外的缓存值
```

应用 Buff 时检查两个重要属性：`refresh` 和 `unique`。
- **`refresh`**（默认：True）确定 Buff 在重新应用时是否刷新计时器。
- **`unique`**（默认：True）确定此 Buff 是否唯一；也就是说，对象上只存在一个。

这两个布尔值的组合创造了三种不同的键：
- `Unique为True，Refresh为True/False`：Buff 的默认键。
- `Unique为False，Refresh为True`：默认键与应用者的 dbref 结合。这使 Buff 变成“每个玩家唯一”，以便可以通过重新应用进行刷新。
- `Unique为False，Refresh为False`：默认键与随机数结合。

### 获取 Buff

处理器具有几个返回实例 Buff 的 getter 方法。虽然你在基本功能中不需要使用这些，但如果你想在应用后操纵 Buff，它们非常有用。处理器的 `check`/`trigger` 方法利用了一些这些 getter，而其他则只是为了方便开发者。

**`get(key)`** 是最基本的 getter。它返回一个单一的 Buff 实例，如果 Buff 不存在则返回 `None`。它也是唯一返回单个 Buff 实例而不是字典的 getter。

> **注意**：处理器方法 `has(buff)` 允许你在处理器缓存中检查匹配的键（如果是字符串）或 Buff 类（如果是类）是否存在，而不实际实例化 Buff。你应该使用这个方法进行基本的“这个 Buff 是否存在？”检查。

分组 getter 列在下方，返回格式为 `{buffkey: instance}` 的值字典。如果你想遍历所有这些 Buff，应该通过 `dict.values()` 方法进行。

- **`get_all()`** 返回处理器上的所有 Buff。你也可以使用 `handler.all` 属性。
- **`get_by_type(BuffClass)`** 返回指定类型的 Buff。
- **`get_by_stat(stat)`** 返回 `mods` 列表中具有指定 `stat` 字符串的 Buff。
- **`get_by_trigger(string)`** 返回 `triggers` 列表中具有指定字符串的 Buff。
- **`get_by_source(Object)`** 返回由指定 `source` 对象应用的 Buff。
- **`get_by_cachevalue(key, value)`** 返回缓存中具有匹配 `key: value` 对的 Buff。`value` 可选。

除了 `get_all()` 之外，所有分组 getter 都可以通过可选的 `to_filter` 参数“切片”现有字典。

```python
dict1 = handler.get_by_type(Burned)                     # 查找处理器上的所有“Burned” Buff
dict2 = handler.get_by_source(self, to_filter=dict1)    # 将 dict1 过滤以找到具有匹配来源的 Buff
```

> **注意**：大多数这些 getter 还有一个相关的处理器属性。例如，`handler.effects` 返回所有可以被触发的 Buff，这样可以通过 `get_by_trigger` 方法进行迭代。

### 移除 Buff

也有一些移除方法。一般来说，这些方法遵循与 getter 相同的格式。

- **`remove(key)`** 移除具有指定键的 Buff。
- **`clear()`** 移除所有 Buff。
- **`remove_by_type(BuffClass)`** 移除指定类型的 Buff。
- **`remove_by_stat(stat)`** 移除 `mods` 列表中具有指定 `stat` 字符串的 Buff。
- **`remove_by_trigger(string)`** 移除 `triggers` 列表中具有指定字符串的 Buff。
- **`remove_by_source(Object)`** 移除由指定来源应用的 Buff。
- **`remove_by_cachevalue(key, value)`** 移除具有匹配 `key: value` 对的 Buff。`value` 是可选的。

你还可以通过调用实例的 `remove` 辅助方法来移除 Buff。可以在上面列出的 getter 返回的字典上执行此操作。

```python
to_remove = handler.get_by_trigger(trigger)     # 查找所有具有指定触发器的 Buff
for buff in to_remove.values():                 # 通过辅助方法移除 to_remove 字典中的所有 Buff
    buff.remove()   
```

### 检查修饰符

当你想查看修改后的值时，调用处理器的 `check(value, stat)` 方法。这将返回 `value`，将任何相关 Buff 中的修改应用于处理器的拥有者（通过 `stat` 字符串识别）。

例如，假设你想修改你承受的伤害量。这可能看起来像这样：

```python
# 我们调用的方法来对自己造成伤害
def take_damage(self, source, damage):
    _damage = self.buffs.check(damage, 'taken_damage')
    self.db.health -= _damage
```

此方法在过程中相关的点调用 `at_pre_check` 和 `at_post_check` 方法。你可以通过此方法创建对检查的反应 Buff；例如，移除自身、改变其值或与游戏状态交互。

> **注意**：你还可以在检查时同时触发相关的 Buff，只需确保在 `check` 方法中将可选参数 `trigger` 设为 True。

修饰符是通过加法计算的——也就是说，所有相同类型的修饰符在应用之前共同添加。然后通过以下公式应用：

```python
(base + total_add) / max(1, 1.0 + total_div) * max(0, 1.0 + total_mult)
```

#### 乘法 Buff（高级）

在这个 Buff 系统中，乘法/除法修饰符默认是加法的。这意味着两个 +50% 的修饰符将等于 +100% 的修饰符。但是如果你想要应用乘法修饰符呢？

首先，你应该仔细考虑你是否真的想要乘法修饰符。这里有一些需要考虑的事情：

- 对于普通用户来说，它们是直观的，因为两个 +50% 的伤害 Buff 等于 +125% 而非 +100%。
- 它们会导致“能力爆炸”，即以正确的方式堆叠 Buff 可以使角色变得势不可挡。

进行完全加法的乘法器使你能够更好地控制游戏的平衡。相反，使用乘法器可以非常有趣地建造角色，明智地使用 Buff 和技能可以让你变成一击杀手。每种都有其存在的意义。

乘法 Buff 的最佳设计实践是将乘法器分成“层级”，每层单独应用。这可以通过多次调用 `check` 来轻松实现。

```python
damage = damage
damage = handler.check(damage, 'damage')
damage = handler.check(damage, 'empower')
damage = handler.check(damage, 'radiant')
damage = handler.check(damage, 'overpower')
```

#### Buff 强度优先级（高级）

有时候你只想应用对某个属性最强的修饰符。这通过处理器的 `check` 方法中的可选 `strongest` 布尔参数支持。

```python
def take_damage(self, source, damage):
    _damage = self.buffs.check(damage, 'taken_damage', strongest=True)
    self.db.health -= _damage
```

### 触发 Buff

当你想进行事件调用时，调用处理器的 `trigger(string)` 方法。这将调用所有具有相关触发器 `string` 的 Buff 的 `at_trigger` 钩子方法。

例如，假设你想触发一个 Buff 在你打击目标时“引爆”。你可以编写如下的 Buff：

```python
class Detonate(BaseBuff):
    ...
    triggers = ['take_damage']
    def at_trigger(self, trigger, *args, **kwargs):
        self.owner.take_damage(100)
        self.remove()
```

然后在你用于造成伤害的方法中调用 `handler.trigger('take_damage')`。

> **注意**：你也可以通过修饰符和 `at_post_check` 执行这一操作，具体取决于你如何希望增加伤害。

### Tick Buffs

Tick Buff 稍微特殊。它们类似于触发 Buff，因为它们可以运行代码，但不是在事件触发时，而是在定期的 Tick 上。此类 Buff 的常见用例是毒药或持续治疗。

```python
class Poison(BaseBuff):
    ...
    tickrate = 5
    def at_tick(self, initial=True, *args, **kwargs):
        _dmg = self.dmg * self.stacks
        if not initial:
            self.owner.location.msg_contents(
                "{} 的身体里流淌着毒药，造成了 {} 点伤害。".format(
                    self.owner.named, _dmg
                )
            )
```

要使 Buff 成为 Tick Buff，确保 `tickrate` 为 1 或更高，并且在其 `at_tick` 方法中有代码。一旦你将其添加到处理器，它就开始 Tick！

> **注意**：Tick Buff 在初始应用时始终触发一次，此时 `initial` 为 True。如果你不希望在那个时刻触发你的钩子，请确保在 `at_tick` 方法中检查 `initial` 的值。

### 上下文

每个重要的处理器方法可选接受一个 `context` 字典。

上下文是此处理器的重要概念。每个检查、触发或 Tick Buff 的方法都将此字典（默认为空）作为关键字参数（`**kwargs`）传递给 Buff 钩子方法。它不用于其他目的。这样，你可以通过将相关数据存储在传递给方法的字典中，使这些方法“事件意识”。

例如，假设你想要一个“荆刺” Buff，当攻击你时伤害敌人。在我们的 `take_damage` 方法中添加上下文：

```python
def take_damage(attacker, damage):
    context = {'attacker': attacker, 'damage': damage}
    _damage = self.buffs.check(damage, 'taken_damage', context=context)
    self.buffs.trigger('taken_damage', context=context)
    self.db.health -= _damage
```

现在我们使用上下文传递给 Buff kwargs 的值自定义我们的逻辑。

```python
class ThornsBuff(BaseBuff):
    ...
    triggers = ['taken_damage']
    def at_trigger(self, trigger, attacker=None, damage=0, **kwargs):
        if not attacker: 
            return
        attacker.db.health -= damage * 0.2
```

应用 Buff，承受伤害，看看荆棘 Buff 如何发挥作用！

### 查看信息

处理器上有两个辅助方法，使你能够获取有用的 Buff 信息。

- **`view`**: 返回格式为 `{buffkey: (buff.name, buff.flavor)}` 的元组字典。默认情况下查找所有 Buff，但可选接受过滤的 Buff 字典。用于基本 Buff 摘要。
- **`view_modifiers(stat)`**: 返回影响指定 stat 的修饰符信息的嵌套字典。第一层是修饰符类型（`add/mult/div`），第二层是值类型（`total/strongest`）。不会返回导致这些修饰符的 Buff，只有修饰符本身（类似于使用 `handler.check` 但不实际修改值）。对于属性表很有用。

你也可以通过各种处理器 getter 创建自己的自定义查看方法，这将始终返回整个 Buff 对象。

## 创建新 Buff

创建新的 Buff 非常简单：扩展 `BaseBuff` 为一个新类，填充所有相关的 Buff 细节。然而，Buff 有许多各自独立的移动部分。以下是重要内容的逐步说明。

### 基础知识

无论其他功能如何，所有 Buff 都具有以下类属性：

- 它们有可自定义的 `key`、`name` 和 `flavor` 字符串。
- 它们有一个 `duration`（浮点数），并在结束时自动清理。使用 -1 表示无限持续时间，0 立即清理。（默认：-1）
- 它们有一个 `tickrate`（浮点数），如果大于 1 则自动 Tick（默认：0）
- 如果 `maxstacks`（整数）不等于 1，则它们可以叠加。如果为 0，则 Buff 会无限叠加。（默认：1）
- 它们可以是 `unique`（布尔值），这决定了它们是否具有唯一的命名空间。（默认：True）
- 它们可以是 `refresh`（布尔值），当堆叠或重新应用时重新设置持续时间。（默认：True）
- 它们可以是 `playtime`（布尔值） Buff，持续时间仅在主动游戏期间倒计时。（默认：False）

Buff 还具有一些有用的属性：

- **`owner`**: 这个 Buff 附加到的对象
- **`ticknum`**: Buff 已经过的 Tick 次数
- **`timeleft`**: Buff 剩余的时间
- **`ticking`/`stacking`**: 此 Buff 是否 Tick/叠加（检查 `tickrate` 和 `maxstacks`）

#### Buff 缓存（高级）

Buff 始终在缓存中存储一些有用的可变信息（存储在拥有对象的数据库属性上）。Buff 的缓存对应于 `{buffkey: buffcache}`，其中 `buffcache` 是一个字典，至少包含以下信息：

- **`ref`**（类）：我们用来构造 Buff 的 Buff 类路径。
- **`start`**（浮点数）：应用 Buff 时的时间戳。
- **`source`**（对象）：如果指定；这允许你跟踪谁或什么应用了该 Buff。
- **`prevtick`**（浮点数）：上一个 Tick 的时间戳。
- **`duration`**（浮点数）：缓存的持续时间。这可能与类持续时间不同，具体取决于持续时间是否已修改（暂停、延长、缩短等）。
- **`tickrate`**（浮点数）：Buff 的 Tick 速率。不能低于 0。对已应用 Buff 更改 Tick 速率不会导致其开始 Tick，如果之前未 Tick （使用 `pause` 和 `unpause` 停止/开始现有 Buff 的 Tick）。
- **`stacks`**（整数）：它们有多少个堆叠。
- **`paused`**（布尔值）：暂停的 Buff 不会清理、修改值、Tick 或触发任何钩子方法。

有时你希望在运行时动态更新 Buff 的缓存，如在钩子方法中更改 Tick 速率或更改 Buff 的持续时间。你可以使用接口 `buff.cachekey`。只要属性名称与缓存字典中的键匹配，就会使用新值更新存储的缓存。

如果没有匹配键，它将不执行任何操作。如果你希望将新键添加到缓存中，必须使用 `buff.update_cache(dict)` 方法，该方法将使用提供的字典正确更新缓存（包括添加新键）。

> **示例**: 你希望将 Buff 的持续时间增加 30 秒。你使用 `buff.duration += 30`。此新持续时间现在会在实例和缓存上反映。

Buff 缓存还可以存储任意信息。为此，通过处理器的 `add` 方法传递一个字典（`handler.add(BuffClass, to_cache=dict)`）、设置 Buff 类上的 `cache` 字典属性，或使用上述 `buff.update_cache(dict)` 方法。

> **示例**: 你将 `damage` 作为值存储在 Buff 缓存中，并用于你的毒药 Buff。你希望随时间增长，因此在 Tick 方法中使用 `buff.damage += 1`。

### 修饰符

Mods 存储在 `mods` 列表属性中。具有一个或多个 Mod 对象的 Buff 可以修改属性。你可以使用处理器方法检查特定属性字符串的所有 mods，并将其修改应用于值；然而，鼓励在 getter/setter 中使用 `check`，以便轻松访问。

Mod 对象仅由构造函数按以下顺序分配的四个值：

- **`stat`**: 你希望修改的属性。当调用 `check` 时，此字符串用于查找所有要收集的 mods。
- **`mod`**: 修饰符。默认值为 `add`（相加/相减）、`mult`（乘以）和 `div`（除以）。修饰符是按加法计算的（见 `_calculate_mods`）。
- **`value`**: 修饰符提供的数值，不论堆叠情况如何。
- **`perstack`**: 修饰符为每个堆叠提供多少价值，包括第一次（默认：0）。

添加 Mod 到 Buff 的最基本方法是在 Buff 类定义中做到这一点，如下所示：

```python
class DamageBuff(BaseBuff):
    mods = [Mod('damage', 'add', 10)]
```

对值应用的任何 mods 都不是永久的。所有计算都是在运行时完成的，mod 值不会在 Buff 上永久存储。换句话说：你不需要跟踪特定属性修改的来源，并且永远不会永久更改由 Buff 修改的属性。要移除修改，只需将 Buff 从对象中移除。

> **注意**：你可以通过重载 `_calculate_mods` 方法来添加自己的修饰符类型，该方法包含基本的修饰符应用逻辑。

#### 生成 Mods（高级）

创建 Mods 的高级方式是当 Buff 初始化时生成它们。这使你能够创建响应游戏状态的 Mods。

```python
class GeneratedStatBuff(BaseBuff):
    ...
    def at_init(self, *args, **kwargs) -> None:
        # 查找我们的 "modgen" 缓存值，并从中生成一个 Mod
        modgen = list(self.cache.get("modgen"))
        if modgen:
            self.mods = [Mod(*modgen)]
```

### 触发器

具有一个或多个字符串的 Buff 触发器可以被事件触发。

当处理器的 `trigger` 方法被调用时，它搜索处理器上的所有 Buff，查找任何与匹配触发器，并调用它们的 `at_trigger` 钩子。Buff 可以具有多个触发器，你可以通过钩子中的 `trigger` 参数判断哪个触发器被使用。

```python 
class AmplifyBuff(BaseBuff):
    triggers = ['damage', 'heal'] 

    def at_trigger(self, trigger, **kwargs):
        if trigger == 'damage': print('Damage trigger called!')
        if trigger == 'heal': print('Heal trigger called!')
```

### Tick

Tick Buff 与触发 Buff 并无大差异。你仍然在 Buff 类上执行任意钩子。要 Tick，Buff 必须具有大于或等于 1 的 `tickrate`。

```python
class Poison(BaseBuff):
    ...
    # 此 Buff 在应用与清理之间将 Tick 6 次。
    duration = 30
    tickrate = 5
    def at_tick(self, initial, **kwargs):
        self.owner.take_damage(10)
```

> **注意**：Buff 在应用时总是执行一次 Tick。在此**第一次 Tick**中，`initial` 在 `at_tick` 钩子方法中为 True。后续的 Tick 中，`initial` 将为 False。

Tick 使用持久延迟，因此它们应该是可序列化的。只要你不向 Buff 类添加新属性，就不应该存在此问题。如果你确实添加了新属性，请确保它们不会出现在其对象或处理器的循环代码路径中，因为这将导致序列化错误。

### 额外功能

Buff 有一系列额外功能，可以使你的设计更加复杂。

#### 条件

你可以通过定义 `conditional` 钩子限制 Buff 是否将 `check`、`trigger` 或 `tick`。只要返回“真值”，Buff 就会自行应用。这对于使 Buff 依赖于游戏状态非常有用——例如，如果你想要一个让玩家在起火时受到更多伤害的 Buff：

```python
class FireSick(BaseBuff):
    ...
    def conditional(self, *args, **kwargs):
        if self.owner.buffs.has(FireBuff): 
            return True
        return False
```

`check`/`trigger` 的条件在 Buff 被处理器方法收集时检查；`Tick` 条件在每个 Tick 时检查。

#### 辅助方法

Buff 实例有一些辅助方法。

- **`remove`/`dispel`**: 允许你移除或解除 Buff。根据可选参数调用 `at_remove`/`at_dispel`。
- **`pause`/`unpause`**: 暂停和恢复 Buff。如果调用 `at_pause`/`at_unpause`。
- **`reset`**: 将 Buff 的开始重置为当前时间；与“刷新”相同。
- **`alter_cache`**: 使用提供的字典中的 `{key:value}` 对更新 Buff 的缓存。可以覆盖默认值，因此要小心！

#### 游戏时间持续时间

如果你的处理器启用了 `autopause`，任何具有真值 `playtime` 的 Buff 将在与其附加的对象被控制或未控制时自动暂停和恢复。这甚至适用于 Tick Buff，不过如果剩余的 Tick 持续时间少于 1 秒，它将向上舍入到 1 秒。

> **注意**：如果你希望对这个过程有更多控制，可以注释掉处理器上的信号订阅，并移动自动暂停逻辑到对象的 `at_pre/post_puppet/unpuppet` 钩子中。
