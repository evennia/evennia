"""
This file serves as a central module level location to retrieve
 and register components
"""

components_by_name = {}
all_components = []


def register(component_class):
    components_by_name[component_class.name] = component_class
    all_components.append(component_class)

    return component_class


def get(component_name):
    return components_by_name.get(component_name)
