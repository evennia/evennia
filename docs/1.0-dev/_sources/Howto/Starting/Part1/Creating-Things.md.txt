# Creating things


We have already created some things - dragons for example. There are many different things to create
in Evennia though. In the last lesson we learned about typeclasses, the way to make objects persistent in the database.

Given the path to a Typeclass, there are three ways to create an instance of it:

- Firstly, you can call the class directly, and then `.save()` it:

        obj = SomeTypeClass(db_key=...)
        obj.save()

   This has the drawback of being two operations; you must also import the class and have to pass 
   the actual database field names, such as `db_key`  instead of `key` as keyword arguments.
- Secondly you can use the Evennia creation helpers:

        obj = evennia.create_object(SomeTypeClass, key=...)

   This is the recommended way if you are trying to create things in Python. The first argument can either be 
   the class _or_ the python-path to the typeclass, like `"path.to.SomeTypeClass"`. It can also be `None` in which 
   case the Evennia default will be used. While all the creation methods
   are available on `evennia`, they are actually implemented in [evennia/utils/create.py](api:evennia.utils.create).
- Finally, you can create objects using an in-game command, such as

        create/drop obj:path.to.SomeTypeClass

  As a developer you are usually best off using the two other methods, but a command is usually the only way 
  to let regular players or builders without Python-access help build the game world. 
  
## Creating Objects

This is one of the most common creation-types. These are entities that inherits from `DefaultObject` at any distance.
They have an existence in the game world and includes rooms, characters, exits, weapons, flower pots and castles.

    > py
    > import evennia 
    > rose = evennia.create_object(key="rose")

Since we didn't specify the `typeclass` as the first argument, the default given by `settings.BASE_OBJECT_TYPECLASS` 
(`typeclasses.objects.Object`) will be used. 

## Creating Accounts

An _Account_ is an out-of-character (OOC) entity, with no existence in the game world. 
You can find the parent class for Accounts in `typeclasses/accounts.py`. 

_TODO_

