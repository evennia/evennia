# Components

_Contrib by ChrisLR 2021_

# The Components Contrib

This contrib allows you to develop your mud with more composition and less inheritance.

Why would you want to do this?
It allows you to keep your code clean and focused to one feature at a time.

For example, you want to add Health to most of your objects, but not all.
If you were to do this via inheritance, adding it to the base typeclass,
you would very quickly end up with a very long and cluttered file, having to sift through
every unrelated methods to get to that particular feature.
What if one typeclass does not inherit from your base one and requires health?
Would you copy paste it, adding further spaghetti or add in a new base typeclass and restructure the whole tree?

You could also create a mixin to avoid some of these issues while retaining a small readable file.
It works well at first when you have just a few of them but the more you add the more unpredictable they become,
requiring great care when naming methods, calling supers and ordering well in the init.

In both scenarios, you will have to continuously filter out objects that do not possess this feature,
probably using a variation of getattr, hasattr, or even tags.

The components on the other hand allow you to create a self contained feature that can be added to any object
or typeclass, containing every thing the feature requires and serving as an interface to interact with.
In this case, you would add in the current, max health as DBFields and damage/heal as regular methods.

This component could then be added as ComponentProperty to any typeclass, providing the feature or simply added
to the object at runtime, giving you a one-off destructible object.

Then at any point where you want to try to damage something you can check for the feature like

target_health = target.cmp.health
if not target_health:
    return "You cannot attack this!"
else:
    damage_value = roll_damage()
    target_health.damage(damage_value)

Components are also accessible directly from the typeclass if defined via ComponentProperty.


# How to install

To enable component support for a typeclass,
import and inherit the ComponentHolderMixin, similar to this
```
from evennia.contrib.base_systems.components import ComponentHolderMixin
class Character(ComponentHolderMixin, DefaultCharacter):
# ...
```

Components need to inherit the Component class directly and require a name
Example:
```
from evennia.contrib.components import Component

class Health(Component):
    name = "health"
```

Components may define DBFields or NDBFields at the class level.
DBField will store its values in the host's DB with a prefixed key.
NDBField will store its values in the host's NDB and will not persist.
The key used will be component_name__field_name.
They use AttributeProperty under the hood.

Example:
```
from evennia.contrib.base_systems.components import Component, DBField

class Health(Component):
    health = DBField(default=1)
```

Note that default is optional and will default to None


Each typeclass using the ComponentHolderMixin can declare its components
in the class via the ComponentProperty.
These are components that will always be present in a typeclass.
You can also pass kwargs to override the default values
Example
```
from evennia.contrib.base_systems.components import ComponentHolderMixin
class Character(ComponentHolderMixin, DefaultCharacter):
    health = ComponentProperty("health", hp=10, max_hp=50)
```

You can then use character.health to access the components.

Alternatively you can add those components at runtime.
You will have to access those via the component handler.
Example
```
character = self
vampirism = components.Vampirism.create(character)
character.components.add(vampirism)

...

vampirism_from_elsewhere = character.components.get("vampirism")
```

Keep in mind that all components must be imported to be visible in the listing
As such, I recommend regrouping them in a package
You can then import all your components in that package's __init__

Because of how Evennia import typeclasses and the behavior of python imports
I recommend placing the components package inside the typeclass package.


# Technical Stuff you should know about

You can make Components stand-alone as a template.
To do this, call the component's as_template() method and pass it
values as kwargs to override the component's defaults.

You can then apply this template by calling the component's duplicate method
to have the new instance created and registered to the new host.
Something like
```
character = self
health_template = components.Health.create(hp=100)
new_instance = health_template.duplicate(character)
character.components.add(new_instance)
```

Note that duplicate can also accept not having a host,
this lets it store values that it will later copy to its future host.
This is a bit slower than giving it the host straight away.
