"""
These are mixins for class-based views, granting functionality.

"""
from django.views.generic import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView


class TypeclassMixin:
    """
    This is a "mixin", a modifier of sorts.

    Django views typically work with classes called "models." Evennia objects
    are an enhancement upon these Django models and are called "typeclasses."
    But Django itself has no idea what a "typeclass" is.

    For the sake of mitigating confusion, any view class with this in its
    inheritance list will be modified to work with Evennia Typeclass objects or
    Django models interchangeably.

    """

    @property
    def typeclass(self):
        return self.model

    @typeclass.setter
    def typeclass(self, value):
        self.model = value


class EvenniaCreateView(CreateView, TypeclassMixin):
    """
    This view extends Django's default CreateView.

    CreateView is used for creating new objects, be they Accounts, Characters or
    otherwise.

    """

    @property
    def page_title(self):
        # Makes sure the page has a sensible title.
        return "Create %s" % self.typeclass._meta.verbose_name.title()


class EvenniaDetailView(DetailView, TypeclassMixin):
    """
    This view extends Django's default DetailView.

    DetailView is used for displaying objects, be they Accounts, Characters or
    otherwise.

    """

    @property
    def page_title(self):
        # Makes sure the page has a sensible title.
        return "%s Detail" % self.typeclass._meta.verbose_name.title()


class EvenniaUpdateView(UpdateView, TypeclassMixin):
    """
    This view extends Django's default UpdateView.

    UpdateView is used for updating objects, be they Accounts, Characters or
    otherwise.

    """

    @property
    def page_title(self):
        # Makes sure the page has a sensible title.
        return "Update %s" % self.typeclass._meta.verbose_name.title()


class EvenniaDeleteView(DeleteView, TypeclassMixin):
    """
    This view extends Django's default DeleteView.

    DeleteView is used for deleting objects, be they Accounts, Characters or
    otherwise.

    """

    @property
    def page_title(self):
        # Makes sure the page has a sensible title.
        return "Delete %s" % self.typeclass._meta.verbose_name.title()
