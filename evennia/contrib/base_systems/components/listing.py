from . import exceptions

COMPONENT_LISTING = {}


def get_component_class(name):
    """
    Retrieves a component from the listing using a name
    Args:
        name (str): The unique name of the component
    """
    component_class = COMPONENT_LISTING.get(name)
    if component_class is None:
        message = (
            f"Component with name {name} has not been found. "
            "Make sure it has been imported before being used."
        )
        raise exceptions.ComponentDoesNotExist(message)

    return component_class
