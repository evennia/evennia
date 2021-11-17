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

- Components need to inherit the Component class directly and require a name
    Example:
    ```
    from evennia.contrib.components import Component

    class Health(Component):
        name = "health"
    ```

- Components may define DBFields at the class level
    Example:
    ```
    from evennia.contrib.components import Component, DBField
    class Health(Component):
        health = DBField(default=1)
    ```

    Note that default is optional

- Keep in mind that all components must be imported to be visible.
  As such, I recommend regrouping them in a package
  You can then import all your components in that package's __init__

  Because of how Evennia import typeclasses and the behavior of python imports
  I recommend placing the components package inside the typeclasses.
"""

from evennia.contrib.components.component import Component
from evennia.contrib.components.dbfield import DBField, NDBField
from evennia.contrib.components.holder import ComponentHolderMixin, ComponentProperty


def get_component_class(component_name):
    subclasses = Component.__subclasses__()
    component_class = next((sc for sc in subclasses if sc.name == component_name), None)
    if component_class is None:
        message = f"Component named {component_name} has not been found. " \
                  f"Make sure it has been imported before being used."
        raise Exception(message)

    return component_class
