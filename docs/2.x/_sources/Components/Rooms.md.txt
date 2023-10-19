
# Rooms

**Inheritance Tree:**
```
┌─────────────┐
│DefaultObject│
└─────▲───────┘
      │
┌─────┴─────┐
│DefaultRoom│
└─────▲─────┘
      │       ┌────────────┐
      │ ┌─────►ObjectParent│
      │ │     └────────────┘
    ┌─┴─┴┐
    │Room│
    └────┘
```

[Rooms](evennia.objects.objects.DefaultRoom) are in-game [Objects](./Objects.md) representing the root containers of all other objects. 

The only thing technically separating a room from any other object is that they have no `location` of their own and that default commands like `dig` creates objects of this class - so if you want to expand your rooms with more functionality, just inherit from `evennia.DefaultRoom`. 

To change the default room created by `dig`, `tunnel` and other default commands, change it in settings: 

    BASE_ROOM_TYPECLASS = "typeclases.rooms.Room"

The empty class in `mygame/typeclasses/rooms.py` is a good place to start! 

While the default Room is very simple, there are several Evennia [contribs](../Contribs/Contribs-Overview.md) customizing and extending rooms with more functionality. 