"""
Views for managing a specific object)

"""

from collections import OrderedDict

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.utils.text import slugify

from evennia.utils import class_from_module

from .mixins import (
    EvenniaCreateView,
    EvenniaDeleteView,
    EvenniaDetailView,
    EvenniaUpdateView,
)


class ObjectDetailView(EvenniaDetailView):
    """
    This is an important view.

    Any view you write that deals with displaying, updating or deleting a
    specific object will want to inherit from this. It provides the mechanisms
    by which to retrieve the object and make sure the user requesting it has
    permissions to actually *do* things to it.

    """

    # -- Django constructs --
    #
    # Choose what class of object this view will display. Note that this should
    # be an actual Python class (i.e. do `from typeclasses.characters import
    # Character`, then put `Character`), not an Evennia typeclass path
    # (i.e. `typeclasses.characters.Character`).
    #
    # So when you extend it, this line should look simple, like:
    # model = Object
    model = class_from_module(
        settings.BASE_OBJECT_TYPECLASS, fallback=settings.FALLBACK_OBJECT_TYPECLASS
    )

    # What HTML template you wish to use to display this page.
    template_name = "website/object_detail.html"

    # -- Evennia constructs --
    #
    # What lock type to check for the requesting user, authenticated or not.
    # https://github.com/evennia/evennia/wiki/Locks#valid-access_types
    access_type = "view"

    # What attributes of the object you wish to display on the page. Model-level
    # attributes will take precedence over identically-named db.attributes!
    # The order you specify here will be followed.
    attributes = ["name", "desc"]

    def get_context_data(self, **kwargs):
        """
        Adds an 'attributes' list to the request context consisting of the
        attributes specified at the class level, and in the order provided.

        Django views do not provide a way to reference dynamic attributes, so
        we have to grab them all before we render the template.

        Returns:
            context (dict): Django context object

        """
        # Get the base Django context object
        context = super().get_context_data(**kwargs)

        # Get the object in question
        obj = self.get_object()

        # Create an ordered dictionary to contain the attribute map
        attribute_list = OrderedDict()

        for attribute in self.attributes:
            # Check if the attribute is a core fieldname (name, desc)
            if attribute in self.typeclass._meta._property_names:
                attribute_list[attribute.title()] = getattr(obj, attribute, "")

            # Check if the attribute is a db attribute (char1.db.favorite_color)
            else:
                attribute_list[attribute.title()] = getattr(obj.db, attribute, "")

        # Add our attribute map to the Django request context, so it gets
        # displayed on the template
        context["attribute_list"] = attribute_list

        # Return the comprehensive context object
        return context

    def get_object(self, queryset=None):
        """
        Override of Django hook that provides some important Evennia-specific
        functionality.

        Evennia does not natively store slugs, so where a slug is provided,
        calculate the same for the object and make sure it matches.

        This also checks to make sure the user has access to view/edit/delete
        this object!

        """
        # A queryset can be provided to pre-emptively limit what objects can
        # possibly be returned. For example, you can supply a queryset that
        # only returns objects whose name begins with "a".
        if not queryset:
            queryset = self.get_queryset()

        # Get the object, ignoring all checks and filters for now
        obj = self.typeclass.objects.get(pk=self.kwargs.get("pk"))

        # Check if this object was requested in a valid manner
        if slugify(obj.name) != self.kwargs.get(self.slug_url_kwarg):
            raise HttpResponseBadRequest(
                "No %(verbose_name)s found matching the query"
                % {"verbose_name": queryset.model._meta.verbose_name}
            )

        # Check if the requestor account has permissions to access object
        account = self.request.user
        if not obj.access(account, self.access_type):
            raise PermissionDenied("You are not authorized to %s this object." % self.access_type)

        # Get the object, if it is in the specified queryset
        obj = super().get_object(queryset)

        return obj


class ObjectCreateView(LoginRequiredMixin, EvenniaCreateView):
    """
    This is an important view.

    Any view you write that deals with creating a specific object will want to
    inherit from this. It provides the mechanisms by which to make sure the user
    requesting creation of an object is authenticated, and provides a sane
    default title for the page.

    """

    model = class_from_module(
        settings.BASE_OBJECT_TYPECLASS, fallback=settings.FALLBACK_OBJECT_TYPECLASS
    )


class ObjectDeleteView(LoginRequiredMixin, ObjectDetailView, EvenniaDeleteView):
    """
    This is an important view for obvious reasons!

    Any view you write that deals with deleting a specific object will want to
    inherit from this. It provides the mechanisms by which to make sure the user
    requesting deletion of an object is authenticated, and that they have
    permissions to delete the requested object.

    """

    # -- Django constructs --
    model = class_from_module(
        settings.BASE_OBJECT_TYPECLASS, fallback=settings.FALLBACK_OBJECT_TYPECLASS
    )
    template_name = "website/object_confirm_delete.html"

    # -- Evennia constructs --
    access_type = "delete"


class ObjectUpdateView(LoginRequiredMixin, ObjectDetailView, EvenniaUpdateView):
    """
    This is an important view.

    Any view you write that deals with updating a specific object will want to
    inherit from this. It provides the mechanisms by which to make sure the user
    requesting editing of an object is authenticated, and that they have
    permissions to edit the requested object.

    This functions slightly different from default Django UpdateViews in that
    it does not update core model fields, *only* object attributes!

    """

    # -- Django constructs --
    model = class_from_module(
        settings.BASE_OBJECT_TYPECLASS, fallback=settings.FALLBACK_OBJECT_TYPECLASS
    )

    # -- Evennia constructs --
    access_type = "edit"

    def get_success_url(self):
        """
        Django hook.

        Can be overridden to return any URL you want to redirect the user to
        after the object is successfully updated, but by default it goes to the
        object detail page so the user can see their changes reflected.

        """
        if self.success_url:
            return self.success_url
        return self.object.web_get_detail_url()

    def get_initial(self):
        """
        Django hook, modified for Evennia.

        Prepopulates the update form field values based on object db attributes.

        Returns:
            data (dict): Dictionary of key:value pairs containing initial form
                data.

        """
        # Get the object we want to update
        obj = self.get_object()

        # Get attributes
        data = {k: getattr(obj.db, k, "") for k in self.form_class.base_fields}

        # Get model fields
        data.update({k: getattr(obj, k, "") for k in self.form_class.Meta.fields})

        return data

    def form_valid(self, form):
        """
        Override of Django hook.

        Updates object attributes based on values submitted.

        This is run when the form is submitted and the data on it is deemed
        valid-- all values are within expected ranges, all strings contain
        valid characters and lengths, etc.

        This method is only called if all values for the fields submitted
        passed form validation, so at this point we can assume the data is
        validated and sanitized.

        """
        # Get the attributes after they've been cleaned and validated
        data = {k: v for k, v in form.cleaned_data.items() if k not in self.form_class.Meta.fields}

        # Update the object attributes
        for key, value in data.items():
            self.object.attributes.add(key, value)
            messages.success(self.request, "Successfully updated '%s' for %s." % (key, self.object))

        # Do not return super().form_valid; we don't want to update the model
        # instance, just its attributes.
        return HttpResponseRedirect(self.get_success_url())
