
"""
This file contains the generic, assorted views that don't fall under one of
the other applications. Views are django's way of processing e.g. html
templates on the fly.

"""
from django.contrib.admin.sites import site
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from evennia import SESSION_HANDLER
from evennia.objects.models import ObjectDB
from evennia.accounts.models import AccountDB
from evennia.utils import logger

from django.contrib.auth import login

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
