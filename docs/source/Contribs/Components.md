# Components

_Contrib by ChrisLR 2021_

# The Components Contrib

This contrib allows you to develop your mud with more composition and less inheritance.

Why would you want to do this?
It allows you to keep your code clean and focused to one feature at a time.

For example, a 'health' component which contains the current and max health
but also the damage/heals method and various logic about dying.
Then all you have to do is give this component to any object that can be damaged.
After that you could filter any targets for the presence of the .health component

if not target.health:
    return "You cannot attack this!"
else:
    damage = roll_damage()
    target.damage(damage)

Another advantage is runtime components, allowing you to give and remove
components to your objects to extend them at any time.


# How to install

To enable component support for a typeclass,
import and inherit the ComponentHolderMixin, similar to this
```
from evennia.contrib.components import ComponentHolderMixin
class Character(ComponentHolderMixin, DefaultCharacter):
```

Components need to inherit the Component class and must be registered to the listing
Example:
```
from evennia.contrib.components import Component, listing
@listing.register
class Health(Component):
    name = "health"
```

Components may define DBFields or NDBFields at the class level
Example:
```
from evennia.contrib.components import Component, listing, DBField
@listing.register
class Health(Component):
    health = DBField(default_value=1)
```

Note that default_value is optional and may be a callable such as `dict`


Each typeclass using the ComponentHolderMixin can declare its class components.
These are components that will always be present in a typeclass.
The components listed may be a class or an instance to be used as a template.
Example
```
from evennia.contrib.components import ComponentHolderMixin
class Character(ComponentHolderMixin, DefaultCharacter):
    class_components = (
            components.Health,
            components.Mana.as_template(max=100),
        )
```

Runtime Components on the other hand are the components that can be
added or removed by using a template's duplicate() or a new instance's create()

Example
```
character = self
vampirism = components.Vampirism.create(character)
```

Keep in mind that all components must be imported to be visible in the listing
As such, I recommend regrouping them in a package
You can then import all your components in that package's __init__

Because of how Evennia import typeclasses and the behavior of python imports
I recommend placing the components package inside the typeclass package.


# Technical Stuff you should know about

There is both an DBField and a NDBField for components.
They wrap to use the .db and .ndb of typeclasses.
This means that DBField will store its value in the database
but NDBField will only store it in memory.


You can make Components stand-alone as a template.
To do this, call the component's as_template() method and pass it
values as kwargs to override the component's defaults.

You can then apply this template by calling the component's duplicate method
to have the new instance created and registered to the new host.
Something like
```
character = self
health_template = components.Health(hp=100)
new_instance = health_template.duplicate(character)
```

Note that duplicate can also accept not having a host,
this lets it store values that it will later copy to its future host.
This is a bit slower than giving it the host straight away.
You will have to call the register_component from the host.

Components use Evennia's attributes behind the scene so adding too many at once can slow down your game.
To help with that, default_values are not saved to the database straight away.
