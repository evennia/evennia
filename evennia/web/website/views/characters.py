"""
Views for manipulating Characters (children of Objects often used for
puppeting).

"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.functions import Lower
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.views.generic.base import RedirectView

from evennia.utils import class_from_module
from evennia.web.website import forms

from .mixins import TypeclassMixin
from .objects import (
    ObjectCreateView,
    ObjectDeleteView,
    ObjectDetailView,
    ObjectUpdateView,
)


class CharacterMixin(TypeclassMixin):
    """
    This is a "mixin", a modifier of sorts.

    Any view class with this in its inheritance list will be modified to work
    with Character objects instead of generic Objects or otherwise.

    """

    # -- Django constructs --
    model = class_from_module(
        settings.BASE_CHARACTER_TYPECLASS, fallback=settings.FALLBACK_CHARACTER_TYPECLASS
    )
    form_class = forms.CharacterForm
    success_url = reverse_lazy("character-manage")

    def get_queryset(self):
        """
        This method will override the Django get_queryset method to only
        return a list of characters associated with the current authenticated
        user.

        Returns:
            queryset (QuerySet): Django queryset for use in the given view.

        """
        # Get IDs of characters owned by account
        account = self.request.user
        ids = [getattr(x, "id") for x in account.characters if x]

        # Return a queryset consisting of those characters
        return self.typeclass.objects.filter(id__in=ids).order_by(Lower("db_key"))


class CharacterListView(LoginRequiredMixin, CharacterMixin, ListView):
    """
    This view provides a mechanism by which a logged-in player can view a list
    of all other characters.

    This view requires authentication by default as a nominal effort to prevent
    human stalkers and automated bots/scrapers from harvesting data on your users.

    """

    # -- Django constructs --
    template_name = "website/character_list.html"
    paginate_by = 100

    # -- Evennia constructs --
    page_title = "Character List"
    access_type = "view"

    def get_queryset(self):
        """
        This method will override the Django get_queryset method to return a
        list of all characters (filtered/sorted) instead of just those limited
        to the account.

        Returns:
            queryset (QuerySet): Django queryset for use in the given view.

        """
        account = self.request.user

        # Return a queryset consisting of characters the user is allowed to
        # see.
        ids = [
            obj.id for obj in self.typeclass.objects.all() if obj.access(account, self.access_type)
        ]

        return self.typeclass.objects.filter(id__in=ids).order_by(Lower("db_key"))


class CharacterPuppetView(LoginRequiredMixin, CharacterMixin, RedirectView, ObjectDetailView):
    """
    This view provides a mechanism by which a logged-in player can "puppet" one
    of their characters within the context of the website.

    It also ensures that any user attempting to puppet something is logged in,
    and that their intended puppet is one that they own.

    """

    def get_redirect_url(self, *args, **kwargs):
        """
        Django hook.

        This view returns the URL to which the user should be redirected after
        a passed or failed puppet attempt.

        Returns:
            url (str): Path to post-puppet destination.

        """
        # Get the requested character, if it belongs to the authenticated user
        char = self.get_object()

        # Get the page the user came from
        next_page = self.request.GET.get("next", self.success_url)

        if char:
            # If the account owns the char, store the ID of the char in the
            # Django request's session (different from Evennia session!).
            # We do this because characters don't serialize well.
            self.request.session["puppet"] = int(char.pk)
            messages.success(self.request, "You become '%s'!" % char)
        else:
            # If the puppeting failed, clear out the cached puppet value
            self.request.session["puppet"] = None
            messages.error(self.request, "You cannot become '%s'." % char)

        return next_page


class CharacterManageView(LoginRequiredMixin, CharacterMixin, ListView):
    """
    This view provides a mechanism by which a logged-in player can browse,
    edit, or delete their own characters.

    """

    # -- Django constructs --
    paginate_by = 10
    template_name = "website/character_manage_list.html"

    # -- Evennia constructs --
    page_title = "Manage Characters"


class CharacterUpdateView(CharacterMixin, ObjectUpdateView):
    """
    This view provides a mechanism by which a logged-in player (enforced by
    ObjectUpdateView) can edit the attributes of a character they own.

    """

    # -- Django constructs --
    form_class = forms.CharacterUpdateForm
    template_name = "website/character_form.html"


class CharacterDetailView(CharacterMixin, ObjectDetailView):
    """
    This view provides a mechanism by which a user can view the attributes of
    a character, owned by them or not.

    """

    # -- Django constructs --
    template_name = "website/object_detail.html"

    # -- Evennia constructs --
    # What attributes to display for this object
    attributes = ["name", "desc"]
    access_type = "view"

    def get_queryset(self):
        """
        This method will override the Django get_queryset method to return a
        list of all characters the user may access.

        Returns:
            queryset (QuerySet): Django queryset for use in the given view.

        """
        account = self.request.user

        # Return a queryset consisting of characters the user is allowed to
        # see.
        ids = [
            obj.id for obj in self.typeclass.objects.all() if obj.access(account, self.access_type)
        ]

        return self.typeclass.objects.filter(id__in=ids).order_by(Lower("db_key"))


class CharacterDeleteView(CharacterMixin, ObjectDeleteView):
    """
    This view provides a mechanism by which a logged-in player (enforced by
    ObjectDeleteView) can delete a character they own.

    """

    # using the character form fails there
    form_class = forms.EvenniaForm


class CharacterCreateView(CharacterMixin, ObjectCreateView):
    """
    This view provides a mechanism by which a logged-in player (enforced by
    ObjectCreateView) can create a new character.

    """

    # -- Django constructs --
    template_name = "website/character_form.html"

    def form_valid(self, form):
        """
        Django hook, modified for Evennia.

        This hook is called after a valid form is submitted.

        When an character creation form is submitted and the data is deemed valid,
        proceeds with creating the Character object.

        """
        # Get account object creating the character
        account = self.request.user
        character = None

        # Get attributes from the form
        self.attributes = {k: form.cleaned_data[k] for k in form.cleaned_data.keys()}
        charname = self.attributes.pop("db_key")
        description = self.attributes.pop("desc")
        # Create a character
        character, errors = self.typeclass.create(charname, account, description=description)

        if errors:
            # Echo error messages to the user
            [messages.error(self.request, x) for x in errors]

        if character:
            # Assign attributes from form
            for key, value in self.attributes.items():
                setattr(character.db, key, value)

            # Return the user to the character management page, unless overridden
            messages.success(self.request, "Your character '%s' was created!" % character.name)
            return HttpResponseRedirect(self.success_url)

        else:
            # Call the Django "form failed" hook
            messages.error(self.request, "Your character could not be created.")
            return self.form_invalid(form)
