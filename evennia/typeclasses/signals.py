

# signal receivers. Assigned in __new__
def post_save(sender, instance, created, **kwargs):
    """
    Receives a signal just after the object is saved.
    """
    if created:
        instance.at_first_save()


def remove_attributes_on_delete(sender, instance, **kwargs):
    instance.db_attributes.all().delete()



