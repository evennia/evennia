
"""
This file contains the generic, assorted views that don't fall under one of
the other applications. Views are django's way of processing e.g. html
templates on the fly.

"""
from django.contrib.admin.sites import site
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.db.models.functions import Lower
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import View, TemplateView, ListView, DetailView, FormView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from evennia import SESSION_HANDLER
from evennia.objects.models import ObjectDB
from evennia.accounts.models import AccountDB
from evennia.utils import class_from_module, logger
from evennia.web.website.forms import *

from django.contrib.auth import login
from django.utils.text import slugify

_BASE_CHAR_TYPECLASS = settings.BASE_CHARACTER_TYPECLASS


def _shared_login(request):
    """
    Handle the shared login between website and webclient.

    """
    csession = request.session
    account = request.user
    website_uid = csession.get("website_authenticated_uid", None)
    webclient_uid = csession.get("webclient_authenticated_uid", None)

    if not csession.session_key:
        # this is necessary to build the sessid key
        csession.save()

    if account.is_authenticated():
        # Logged into website
        if not website_uid:
            # fresh website login (just from login page)
            csession["website_authenticated_uid"] = account.id
            if webclient_uid is None:
                # auto-login web client
                csession["webclient_authenticated_uid"] = account.id

    elif webclient_uid:
        # Not logged into website, but logged into webclient
        if not website_uid:
            csession["website_authenticated_uid"] = account.id
            account = AccountDB.objects.get(id=webclient_uid)
            try:
                # calls our custom authenticate, in web/utils/backend.py
                authenticate(autologin=account)
                login(request, account)
            except AttributeError:
                logger.log_trace()


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

    nobjs = ObjectDB.objects.all().count()
    nrooms = ObjectDB.objects.filter(db_location__isnull=True).exclude(db_typeclass_path=_BASE_CHAR_TYPECLASS).count()
    nexits = ObjectDB.objects.filter(db_location__isnull=False, db_destination__isnull=False).count()
    nchars = ObjectDB.objects.filter(db_typeclass_path=_BASE_CHAR_TYPECLASS).count()
    nothers = nobjs - nrooms - nchars - nexits

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
        "num_others": nothers or "no"
    }
    return pagevars


def page_index(request):
    """
    Main root page.
    """

    # handle webclient-website shared login
    _shared_login(request)

    # get game db stats
    pagevars = _gamestats()

    return render(request, 'index.html', pagevars)


def to_be_implemented(request):
    """
    A notice letting the user know that this particular feature hasn't been
    implemented yet.
    """

    pagevars = {
        "page_title": "To Be Implemented...",
    }

    return render(request, 'tbi.html', pagevars)


@staff_member_required
def evennia_admin(request):
    """
    Helpful Evennia-specific admin page.
    """
    return render(
        request, 'evennia_admin.html', {
            'accountdb': AccountDB})


def admin_wrapper(request):
    """
    Wrapper that allows us to properly use the base Django admin site, if needed.
    """
    return staff_member_required(site.index)(request)
    
#
# Class-based views
#

class EvenniaCreateView(CreateView):
    
    @property
    def page_title(self):
        return 'Create %s' % self.model._meta.verbose_name.title()

class EvenniaUpdateView(UpdateView):
    
    @property
    def page_title(self):
        return 'Update %s' % self.model._meta.verbose_name.title()

class EvenniaDeleteView(DeleteView):
    
    @property
    def page_title(self):
        return 'Delete %s' % self.model._meta.verbose_name.title()
        
#
# Object views
#
    
class ObjectDetailView(DetailView):
    
    model = ObjectDB
    
    def get_object(self, queryset=None):
        """
        Override of Django hook.
        
        Evennia does not natively store slugs, so where a slug is provided, 
        calculate the same for the object and make sure it matches.
        
        """
        obj = super(ObjectDetailView, self).get_object(queryset)
        if slugify(obj.name) != self.kwargs.get(self.slug_url_kwarg):
            raise Http404(u"No %(verbose_name)s found matching the query" %
                          {'verbose_name': queryset.model._meta.verbose_name})
        return obj
        
class ObjectCreateView(LoginRequiredMixin, EvenniaCreateView):
    
    model = ObjectDB
        
class ObjectDeleteView(LoginRequiredMixin, ObjectDetailView, EvenniaDeleteView):
    
    model = ObjectDB
    template_name = 'website/object_confirm_delete.html'
    
    def delete(self, request, *args, **kwargs):
        """
        Calls the delete() method on the fetched object and then
        redirects to the success URL.
        
        We extend this so we can capture the name for the sake of confirmation.
        """
        obj = str(self.get_object())
        response = super(ObjectDeleteView, self).delete(request, *args, **kwargs)
        messages.success(request, "Successfully deleted '%s'." % obj)
        return response
    
class ObjectUpdateView(LoginRequiredMixin, ObjectDetailView, EvenniaUpdateView):
    
    model = ObjectDB
    
    def get_initial(self):
        """
        Override of Django hook.
        
        Prepopulates form field values based on object db attributes as well as 
        model field values.
        
        """
        # Get the object we want to update
        obj = self.get_object()
        
        # Get attributes
        data = {k:getattr(obj.db, k, '') for k in self.form_class.base_fields}
        
        # Get model fields
        data.update({k:getattr(obj, k, '') for k in self.form_class.Meta.fields})
        
        return data
        
    def form_valid(self, form):
        """
        Override of Django hook.
        
        Updates object attributes based on values submitted.
        
        This method is only called if all values for the fields submitted
        passed form validation, so at this point we can assume the data is 
        validated and sanitized.
        
        """
        # Get the values submitted after they've been cleaned and validated
        data = {k:v for k,v in form.cleaned_data.items() if k not in self.form_class.Meta.fields}
        
        # Update the object attributes
        for key, value in data.items():
            setattr(self.object.db, key, value)
            messages.success(self.request, "Successfully updated '%s' for %s." % (key, self.object))
            
        # Do not return super().form_valid; we don't want to update the model
        # instance, just its attributes.
        return HttpResponseRedirect(self.success_url)
        
#
# Account views
#

class AccountMixin(object):
    
    model = class_from_module(settings.BASE_ACCOUNT_TYPECLASS)
    form_class = AccountForm

class AccountCreateView(AccountMixin, ObjectCreateView):
    
    template_name = 'website/registration/register.html'
    success_url = reverse_lazy('login')
    
    def form_valid(self, form):
        
        username = form.cleaned_data['username']
        password = form.cleaned_data['password1']
        email = form.cleaned_data.get('email', '')
        
        # Create a fake session object to intercept calls to the terminal
        from mock import Mock
        session = self.request
        session.address = self.request.META.get('REMOTE_ADDR', '')
        session.msg = Mock()
        
        # Create account
        from evennia.commands.default.unloggedin import _create_account
        permissions = settings.PERMISSION_ACCOUNT_DEFAULT
        account = _create_account(session, username, password, permissions)
        
        # If unsuccessful, get messages passed to session.msg
        if not account:
            [messages.error(self.request, call) for call in session.msg.call_args_list]
            return self.form_invalid(form)
            
        # Append email address if given
        account.email = email
        account.save()
        
        messages.success(self.request, "Your account '%s' was successfully created! You may log in using it now." % account.name)
        return HttpResponseRedirect(self.success_url)
        
#
# Character views
#
        
class CharacterMixin(object):
    
    model = class_from_module(settings.BASE_CHARACTER_TYPECLASS)
    form_class = CharacterForm
    
    def get_queryset(self):
        # Get IDs of characters owned by account
        ids = [getattr(x, 'id') for x in self.request.user.db._playable_characters if x]
        
        # Return a queryset consisting of those characters
        return self.model.objects.filter(id__in=ids).order_by(Lower('db_key'))
        
class CharacterManageView(LoginRequiredMixin, CharacterMixin, ListView):

    paginate_by = 10
    template_name = 'website/character_manage_list.html'
    page_title = 'Manage: Characters'
        
class CharacterUpdateView(CharacterMixin, ObjectUpdateView):
    
    form_class = CharacterUpdateForm
    template_name = 'website/character_form.html'
    
class CharacterDeleteView(CharacterMixin, ObjectDeleteView):
    pass
        
class CharacterCreateView(CharacterMixin, ObjectCreateView):
    
    template_name = 'website/character_form.html'
    
    def form_valid(self, form):
        # Get account ref
        account = self.request.user
        character = None
        
        # Get attributes from the form
        self.attributes = {k: form.cleaned_data[k] for k in form.cleaned_data.keys()}
        charname = self.attributes.pop('db_key')
        description = self.attributes.pop('desc')
        
        # Create a character
        permissions = settings.PERMISSION_ACCOUNT_DEFAULT
        typeclass = self.model
        default_home = ObjectDB.objects.get_id(settings.DEFAULT_HOME)
        
        from evennia.utils import create
        try:
            character = create.create_object(typeclass, key=charname, home=default_home, permissions=permissions)
            # set playable character list
            account.db._playable_characters.append(character)
    
            # allow only the character itself and the account to puppet this character (and Developers).
            character.locks.add("puppet:id(%i) or pid(%i) or perm(Developer) or pperm(Developer)" %
                                    (character.id, account.id))
    
            # If no description is set, set a default description
            if not description:
                character.db.desc = "This is a character."
            else:
                character.db.desc = description
                
            # We need to set this to have @ic auto-connect to this character
            account.db._last_puppet = character
            
            # Assign attributes from form
            [setattr(character.db, key, value) for key,value in self.attributes.items()]
            character.db.creator_id = account.id
            character.save()
            
        except Exception as e:
            messages.error(self.request, "There was an error creating your character. If this problem persists, contact an admin.")
            logger.log_trace()
            return self.form_invalid(form)
        
        if character:
            messages.success(self.request, "Your character '%s' was created!" % character.name)
            return HttpResponseRedirect(self.success_url)
        else:
            messages.error(self.request, "Your character could not be created. Please contact an admin.")
            return self.form_invalid(form)
