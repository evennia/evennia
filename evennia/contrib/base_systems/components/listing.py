from evennia.contrib.base_systems.components import exceptions

COMPONENT_LISTING = {}


def get_component_class(name):
    component_class = COMPONENT_LISTING.get(name)
    if component_class is None:
        message = (
            f"Component with name {name} has not been found. "
            f"Make sure it has been imported before being used."
        )
        raise exceptions.ComponentDoesNotExist(message)

    return component_class
