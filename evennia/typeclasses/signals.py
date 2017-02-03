from .models import TypedObject
from django.db.models.signals import pre_delete


def get_subclasses(cls):
    result = []
    classes_to_inspect = [cls]
    while classes_to_inspect:
        class_to_inspect = classes_to_inspect.pop()
        for subclass in class_to_inspect.__subclasses__():
            if subclass not in result:
                result.append(subclass)
                classes_to_inspect.append(subclass)
    return result


def remove_attributes_on_delete(sender, instance, **kwargs):
    print "remove_attribtes_on_delete called in instance %s" % instance
    instance.permissions.clear()
    instance.attributes.clear()
    instance.aliases.clear()
    if hasattr(instance, "nicks"):
        instance.nicks.clear()


for subclass in get_subclasses(TypedObject):
    pre_delete.connect(remove_attributes_on_delete, subclass)
    print "connected to subclass %s" % subclass