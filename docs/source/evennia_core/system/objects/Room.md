# Rooms

*Rooms* are the root containers of all other objects. The only thing really separating a room from any other object is that they have no `location` of their own and that default commands like `@dig` creates objects of this class - so if you want to expand your rooms with more functionality, just inherit from `ev.DefaultRoom`. In `mygame/typeclasses/rooms.py` is an empty `Room` class ready for you to modify.
