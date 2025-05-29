# 角色

**继承树:**
```
┌─────────────┐
│DefaultObject│
└─────▲───────┘
      │
┌─────┴──────────┐
│DefaultCharacter│
└─────▲──────────┘
      │           ┌────────────┐
      │ ┌─────────►ObjectParent│
      │ │         └────────────┘
  ┌───┴─┴───┐
  │Character│
  └─────────┘
```

_角色_ 是代表玩家游戏角色的游戏内 [对象](./Objects.md)。空的 `Character` 类位于 `mygame/typeclasses/characters.py`。它继承自 [DefaultCharacter](evennia.objects.objects.DefaultCharacter) 和（默认为空的）`ObjectParent` 类（如果希望在所有游戏对象之间共享属性时使用）。

当新的 [帐户](./Accounts.md) 第一次登录到 Evennia 时，会创建一个新的 `Character` 对象，并且该 [帐户](./Accounts.md) 将被设置为 _操纵_ 它。默认情况下，这第一个角色将与账户同名（但如果需要，Evennia 支持 [替代连接样式](../Concepts/Connection-Styles.md)）。

`Character` 对象通常在创建时会有一个 [默认命令集](./Command-Sets.md) 设置，否则帐户将无法发出任何游戏内命令！

如果您希望更改由默认命令创建的默认角色，可以在设置中进行更改：

```
BASE_CHARACTER_TYPECLASS = "typeclasses.characters.Character"
```

此默认设置指向位于 `mygame/typeclasses/characters.py` 中的空类，您可以根据需要修改。
