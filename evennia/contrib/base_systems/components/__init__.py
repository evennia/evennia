"""
Components - ChrisLR 2022

This is a basic Component System.
It allows you to use components on typeclasses using a simple syntax.
This helps writing isolated code and reusing it over multiple objects.

See the docs for more information.
"""

from evennia.contrib.base_systems.components.component import Component
from evennia.contrib.base_systems.components.dbfield import DBField, NDBField, TagField
from evennia.contrib.base_systems.components.holder import (
    ComponentHolderMixin,
    ComponentProperty,
)


def get_component_class(component_name):
    subclasses = Component.__subclasses__()
    component_class = next((sc for sc in subclasses if sc.name == component_name), None)
    if component_class is None:
        message = (
            f"Component named {component_name} has not been found. "
            f"Make sure it has been imported before being used."
        )
        raise Exception(message)

    return component_class
