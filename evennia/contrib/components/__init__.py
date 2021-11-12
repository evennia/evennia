"""
Components - ChrisLR 2021

This is a basic Component System.
It allows you to use components on typeclasses using a simple syntax.
This helps writing isolated code and reusing it over multiple objects.

## Installation

- To enable component support for a typeclass,
   import and inherit the ComponentHolderMixin, similar to this
  ```
  from evennia.contrib.components import ComponentHolderMixin
  class Character(ComponentHolderMixin, DefaultCharacter):
  ```

- Components need to inherit the Component class and must be registered to the listing
    Example:
    ```
    from evennia.contrib.components import Component, listing
    @listing.register
    class Health(Component):
        name = "health"
    ```

- Components may define DBFields at the class level
    Example:
    ```
    from evennia.contrib.components import Component, listing, DBField
    @listing.register
    class Health(Component):
        health = DBField('health', default_value=1)
    ```

    Note that default_value is optional and may be a callable such as `dict`

- Keep in mind that all components must be imported to be visible in the listing
  As such, I recommend regrouping them in a package
  You can then import all your components in that package's __init__
  The plug the import of that package early, for example in your typeclasses's __init__

"""


from . import listing
from .listing import register
from evennia.contrib.components.dbfield import DBField
from evennia.contrib.components.component import Component
from evennia.contrib.components.holder import ComponentHolderMixin
