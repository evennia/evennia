"""
This file contains the generic, assorted views that don't fall under one of the other applications.
Views are django's way of processing e.g. html templates on the fly.

"""

from collections import OrderedDict

from django.contrib.admin.sites import site
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.db.models.functions import Lower
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, DetailView
from django.views.generic.base import RedirectView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from evennia import SESSION_HANDLER
from evennia.help.models import HelpEntry
from evennia.objects.models import ObjectDB
from evennia.accounts.models import AccountDB
from evennia.utils import class_from_module
from evennia.utils.logger import tail_log_file
from evennia.web.website import forms as website_forms

from django.utils.text import slugify

_BASE_CHAR_TYPECLASS = settings.BASE_CHARACTER_TYPECLASS


def _gamestats():
    # Some misc. configurable stuff.
    # TODO: Move this to either SQL or settings.py based configuration.
    fpage_account_limit = 4

    # A QuerySet of the most recently connected accounts.
    recent_users = AccountDB.objects.get_recently_connected_accounts()[:fpage_account_limit]
    nplyrs_conn_recent = len(recent_users) or "none"
    nplyrs = AccountDB.objects.num_total_accounts() or "none"
    nplyrs_reg_recent = len(AccountDB.objects.get_recently_created_accounts()) or "none"
    nsess = SESSION_HANDLER.account_count()
    # nsess = len(AccountDB.objects.get_connected_accounts()) or "no one"

    nobjs = ObjectDB.objects.count()
    nobjs = nobjs or 1  # fix zero-div error with empty database
    Character = class_from_module(settings.BASE_CHARACTER_TYPECLASS)
    nchars = Character.objects.all_family().count()
    Room = class_from_module(settings.BASE_ROOM_TYPECLASS)
    nrooms = Room.objects.all_family().count()
    Exit = class_from_module(settings.BASE_EXIT_TYPECLASS)
    nexits = Exit.objects.all_family().count()
    nothers = nobjs - nchars - nrooms - nexits

    pagevars = {
        "page_title": "Front Page",
        "accounts_connected_recent": recent_users,
        "num_accounts_connected": nsess or "no one",
        "num_accounts_registered": nplyrs or "no",
        "num_accounts_connected_recent": nplyrs_conn_recent or "no",
        "num_accounts_registered_recent": nplyrs_reg_recent or "no one",
        "num_rooms": nrooms or "none",
        "num_exits": nexits or "no",
        "num_objects": nobjs or "none",
        "num_characters": nchars or "no",
        "num_others": nothers or "no",
    }
    return pagevars


def to_be_implemented(request):
    """
    A notice letting the user know that this particular feature hasn't been
    implemented yet.
    """

    pagevars = {"page_title": "To Be Implemented..."}

    return render(request, "tbi.html", pagevars)


@staff_member_required
def evennia_admin(request):
    """
    Helpful Evennia-specific admin page.
    """
    return render(request, "evennia_admin.html", {"accountdb": AccountDB})


def admin_wrapper(request):
    """
    Wrapper that allows us to properly use the base Django admin site, if needed.
    """
    return staff_member_required(site.index)(request)


#
# Class-based views
#


class EvenniaIndexView(TemplateView):
    """
    This is a basic example of a Django class-based view, which are functionally
    very similar to Evennia Commands but differ in structure. Commands are used
    to interface with users using a terminal client. Views are used to interface
    with users using a web browser.

    To use a class-based view, you need to have written a template in HTML, and
    then you write a view like this to tell Django what values to display on it.

    While there are simpler ways of writing views using plain functions (and
    Evennia currently contains a few examples of them), just like Commands,
    writing views as classes provides you with more flexibility-- you can extend
    classes and change things to suit your needs rather than having to copy and
    paste entire code blocks over and over. Django also comes with many default
    views for displaying things, all of them implemented as classes.

    This particular example displays the index page.

    """

    # Tell the view what HTML template to use for the page
    template_name = "website/index.html"

    # This method tells the view what data should be displayed on the template.
    def get_context_data(self, **kwargs):
        """
        This is a common Django method. Think of this as the website
        equivalent of the Evennia Command.func() method.

        If you just want to display a static page with no customization, you
        don't need to define this method-- just create a view, define
        template_name and you're done.

        The only catch here is that if you extend or overwrite this method,
        you'll always want to make sure you call the parent method to get a
        context object. It's just a dict, but it comes prepopulated with all
        sorts of background data intended for display on the page.

        You can do whatever you want to it, but it must be returned at the end
        of this method.

        Kwargs:
            any (any): Passed through.

        Returns:
            context (dict): Dictionary of data you want to display on the page.

        """
        # Always call the base implementation first to get a context object
        context = super(EvenniaIndexView, self).get_context_data(**kwargs)

        # Add game statistics and other pagevars
        context.update(_gamestats())

        return context


class TypeclassMixin(object):
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


#
# Object views
#


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
    model = class_from_module(settings.BASE_OBJECT_TYPECLASS)

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
        context = super(ObjectDetailView, self).get_context_data(**kwargs)

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
        obj = super(ObjectDetailView, self).get_object(queryset)

        return obj


class ObjectCreateView(LoginRequiredMixin, EvenniaCreateView):
    """
    This is an important view.

    Any view you write that deals with creating a specific object will want to
    inherit from this. It provides the mechanisms by which to make sure the user
    requesting creation of an object is authenticated, and provides a sane
    default title for the page.

    """

    model = class_from_module(settings.BASE_OBJECT_TYPECLASS)


class ObjectDeleteView(LoginRequiredMixin, ObjectDetailView, EvenniaDeleteView):
    """
    This is an important view for obvious reasons!

    Any view you write that deals with deleting a specific object will want to
    inherit from this. It provides the mechanisms by which to make sure the user
    requesting deletion of an object is authenticated, and that they have
    permissions to delete the requested object.

    """

    # -- Django constructs --
    model = class_from_module(settings.BASE_OBJECT_TYPECLASS)
    template_name = "website/object_confirm_delete.html"

    # -- Evennia constructs --
    access_type = "delete"

    def delete(self, request, *args, **kwargs):
        """
        Calls the delete() method on the fetched object and then
        redirects to the success URL.

        We extend this so we can capture the name for the sake of confirmation.

        """
        # Get the object in question. ObjectDetailView.get_object() will also
        # check to make sure the current user (authenticated or not) has
        # permission to delete it!
        obj = str(self.get_object())

        # Perform the actual deletion (the parent class handles this, which will
        # in turn call the delete() method on the object)
        response = super(ObjectDeleteView, self).delete(request, *args, **kwargs)

        # Notify the user of the deletion
        messages.success(request, "Successfully deleted '%s'." % obj)
        return response


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
    model = class_from_module(settings.BASE_OBJECT_TYPECLASS)

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


#
# Account views
#


class AccountMixin(TypeclassMixin):
    """
    This is a "mixin", a modifier of sorts.

    Any view class with this in its inheritance list will be modified to work
    with Account objects instead of generic Objects or otherwise.

    """

    # -- Django constructs --
    model = class_from_module(settings.BASE_ACCOUNT_TYPECLASS)
    form_class = website_forms.AccountForm


class AccountCreateView(AccountMixin, EvenniaCreateView):
    """
    Account creation view.

    """

    # -- Django constructs --
    template_name = "website/registration/register.html"
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        """
        Django hook, modified for Evennia.

        This hook is called after a valid form is submitted.

        When an account creation form is submitted and the data is deemed valid,
        proceeds with creating the Account object.

        """
        # Get values provided
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password1"]
        email = form.cleaned_data.get("email", "")

        # Create account
        account, errs = self.typeclass.create(username=username, password=password, email=email)

        # If unsuccessful, display error messages to user
        if not account:
            [messages.error(self.request, err) for err in errs]

            # Call the Django "form failure" hook
            return self.form_invalid(form)

        # Inform user of success
        messages.success(
            self.request,
            "Your account '%s' was successfully created! "
            "You may log in using it now." % account.name,
        )

        # Redirect the user to the login page
        return HttpResponseRedirect(self.success_url)


#
# Character views
#


class CharacterMixin(TypeclassMixin):
    """
    This is a "mixin", a modifier of sorts.

    Any view class with this in its inheritance list will be modified to work
    with Character objects instead of generic Objects or otherwise.

    """

    # -- Django constructs --
    model = class_from_module(settings.BASE_CHARACTER_TYPECLASS)
    form_class = website_forms.CharacterForm
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
    form_class = website_forms.CharacterUpdateForm
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

    pass


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


#
# Channel views
#


class ChannelMixin(TypeclassMixin):
    """
    This is a "mixin", a modifier of sorts.

    Any view class with this in its inheritance list will be modified to work
    with HelpEntry objects instead of generic Objects or otherwise.

    """

    # -- Django constructs --
    model = class_from_module(settings.BASE_CHANNEL_TYPECLASS)

    # -- Evennia constructs --
    page_title = "Channels"

    # What lock type to check for the requesting user, authenticated or not.
    # https://github.com/evennia/evennia/wiki/Locks#valid-access_types
    access_type = "listen"

    def get_queryset(self):
        """
        Django hook; here we want to return a list of only those Channels
        and other documentation that the current user is allowed to see.

        Returns:
            queryset (QuerySet): List of Channels available to the user.

        """
        account = self.request.user

        # Get list of all Channels
        channels = self.typeclass.objects.all().iterator()

        # Now figure out which ones the current user is allowed to see
        bucket = [channel.id for channel in channels if channel.access(account, "listen")]

        # Re-query and set a sorted list
        filtered = self.typeclass.objects.filter(id__in=bucket).order_by(Lower("db_key"))

        return filtered


class ChannelListView(ChannelMixin, ListView):
    """
    Returns a list of channels that can be viewed by a user, authenticated
    or not.

    """

    # -- Django constructs --
    paginate_by = 100
    template_name = "website/channel_list.html"

    # -- Evennia constructs --
    page_title = "Channel Index"

    max_popular = 10

    def get_context_data(self, **kwargs):
        """
        Django hook; we override it to calculate the most popular channels.

        Returns:
            context (dict): Django context object

        """
        context = super(ChannelListView, self).get_context_data(**kwargs)

        # Calculate which channels are most popular
        context["most_popular"] = sorted(
            list(self.get_queryset()),
            key=lambda channel: len(channel.subscriptions.all()),
            reverse=True,
        )[: self.max_popular]

        return context


class ChannelDetailView(ChannelMixin, ObjectDetailView):
    """
    Returns the log entries for a given channel.

    """

    # -- Django constructs --
    template_name = "website/channel_detail.html"

    # -- Evennia constructs --
    # What attributes of the object you wish to display on the page. Model-level
    # attributes will take precedence over identically-named db.attributes!
    # The order you specify here will be followed.
    attributes = ["name"]

    # How many log entries to read and display.
    max_num_lines = 10000

    def get_context_data(self, **kwargs):
        """
        Django hook; before we can display the channel logs, we need to recall
        the logfile and read its lines.

        Returns:
            context (dict): Django context object

        """
        # Get the parent context object, necessary first step
        context = super(ChannelDetailView, self).get_context_data(**kwargs)

        # Get the filename this Channel is recording to
        filename = self.object.attributes.get(
            "log_file", default="channel_%s.log" % self.object.key
        )

        # Split log entries so we can filter by time
        bucket = []
        for log in (x.strip() for x in tail_log_file(filename, 0, self.max_num_lines)):
            if not log:
                continue
            time, msg = log.split(" [-] ")
            time_key = time.split(":")[0]

            bucket.append({"key": time_key, "timestamp": time, "message": msg})

        # Add the processed entries to the context
        context["object_list"] = bucket

        # Get a list of unique timestamps by hour and sort them
        context["object_filters"] = sorted(set([x["key"] for x in bucket]))

        return context

    def get_object(self, queryset=None):
        """
        Override of Django hook that retrieves an object by slugified channel
        name.

        Returns:
            channel (Channel): Channel requested in the URL.

        """
        # Get the queryset for the help entries the user can access
        if not queryset:
            queryset = self.get_queryset()

        # Find the object in the queryset
        channel = slugify(self.kwargs.get("slug", ""))
        obj = next((x for x in queryset if slugify(x.db_key) == channel), None)

        # Check if this object was requested in a valid manner
        if not obj:
            raise HttpResponseBadRequest(
                "No %(verbose_name)s found matching the query"
                % {"verbose_name": queryset.model._meta.verbose_name}
            )

        return obj


#
# Help views
#


class HelpMixin(TypeclassMixin):
    """
    This is a "mixin", a modifier of sorts.

    Any view class with this in its inheritance list will be modified to work
    with HelpEntry objects instead of generic Objects or otherwise.

    """

    # -- Django constructs --
    model = HelpEntry

    # -- Evennia constructs --
    page_title = "Help"

    def get_queryset(self):
        """
        Django hook; here we want to return a list of only those HelpEntries
        and other documentation that the current user is allowed to see.

        Returns:
            queryset (QuerySet): List of Help entries available to the user.

        """
        account = self.request.user

        # Get list of all HelpEntries
        entries = self.typeclass.objects.all().iterator()

        # Now figure out which ones the current user is allowed to see
        bucket = [entry.id for entry in entries if entry.access(account, "view")]

        # Re-query and set a sorted list
        filtered = (
            self.typeclass.objects.filter(id__in=bucket)
            .order_by(Lower("db_key"))
            .order_by(Lower("db_help_category"))
        )

        return filtered


class HelpListView(HelpMixin, ListView):
    """
    Returns a list of help entries that can be viewed by a user, authenticated
    or not.

    """

    # -- Django constructs --
    paginate_by = 500
    template_name = "website/help_list.html"

    # -- Evennia constructs --
    page_title = "Help Index"


class HelpDetailView(HelpMixin, EvenniaDetailView):
    """
    Returns the detail page for a given help entry.

    """

    # -- Django constructs --
    template_name = "website/help_detail.html"

    def get_context_data(self, **kwargs):
        """
        Adds navigational data to the template to let browsers go to the next
        or previous entry in the help list.

        Returns:
            context (dict): Django context object

        """
        context = super(HelpDetailView, self).get_context_data(**kwargs)

        # Get the object in question
        obj = self.get_object()

        # Get queryset and filter out non-related categories
        queryset = (
            self.get_queryset()
            .filter(db_help_category=obj.db_help_category)
            .order_by(Lower("db_key"))
        )
        context["topic_list"] = queryset

        # Find the index position of the given obj in the queryset
        objs = list(queryset)
        for i, x in enumerate(objs):
            if obj is x:
                break

        # Find the previous and next topics, if either exist
        try:
            assert i + 1 <= len(objs) and objs[i + 1] is not obj
            context["topic_next"] = objs[i + 1]
        except:
            context["topic_next"] = None

        try:
            assert i - 1 >= 0 and objs[i - 1] is not obj
            context["topic_previous"] = objs[i - 1]
        except:
            context["topic_previous"] = None

        # Format the help entry using HTML instead of newlines
        text = obj.db_entrytext
        text = text.replace("\r\n\r\n", "\n\n")
        text = text.replace("\r\n", "\n")
        text = text.replace("\n", "<br />")
        context["entry_text"] = text

        return context

    def get_object(self, queryset=None):
        """
        Override of Django hook that retrieves an object by category and topic
        instead of pk and slug.

        Returns:
            entry (HelpEntry): HelpEntry requested in the URL.

        """
        # Get the queryset for the help entries the user can access
        if not queryset:
            queryset = self.get_queryset()

        # Find the object in the queryset
        category = slugify(self.kwargs.get("category", ""))
        topic = slugify(self.kwargs.get("topic", ""))
        obj = next(
            (
                x
                for x in queryset
                if slugify(x.db_help_category) == category and slugify(x.db_key) == topic
            ),
            None,
        )

        # Check if this object was requested in a valid manner
        if not obj:
            raise HttpResponseBadRequest(
                "No %(verbose_name)s found matching the query"
                % {"verbose_name": queryset.model._meta.verbose_name}
            )

        return obj
