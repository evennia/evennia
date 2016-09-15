
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
from evennia.players.models import PlayerDB
from evennia.utils import logger

from django.contrib.auth import login

_BASE_CHAR_TYPECLASS = settings.BASE_CHARACTER_TYPECLASS


def _shared_login(request):
    """
    Handle the shared login between website and webclient.

    """
    csession = request.session
    player = request.user
    sesslogin = csession.get("logged_in", None)

    if csession.session_key is None:
        # this is necessary to build the sessid key
        csession.save()
    elif player.is_authenticated():
        if not sesslogin:
            csession["logged_in"] = player.id
    elif sesslogin:
        # The webclient has previously registered a login to this csession
        player = PlayerDB.objects.get(id=sesslogin)
        try:
            # calls our custom authenticate, in web/utils/backend.py
            authenticate(autologin=player)
            login(request, player)
        except AttributeError:
            logger.log_trace()


def _gamestats():
    # Some misc. configurable stuff.
    # TODO: Move this to either SQL or settings.py based configuration.
    fpage_player_limit = 4

    # A QuerySet of the most recently connected players.
    recent_users = PlayerDB.objects.get_recently_connected_players()[:fpage_player_limit]
    nplyrs_conn_recent = len(recent_users) or "none"
    nplyrs = PlayerDB.objects.num_total_players() or "none"
    nplyrs_reg_recent = len(PlayerDB.objects.get_recently_created_players()) or "none"
    nsess = SESSION_HANDLER.player_count()
    # nsess = len(PlayerDB.objects.get_connected_players()) or "no one"

    nobjs = ObjectDB.objects.all().count()
    nrooms = ObjectDB.objects.filter(db_location__isnull=True).exclude(db_typeclass_path=_BASE_CHAR_TYPECLASS).count()
    nexits = ObjectDB.objects.filter(db_location__isnull=False, db_destination__isnull=False).count()
    nchars = ObjectDB.objects.filter(db_typeclass_path=_BASE_CHAR_TYPECLASS).count()
    nothers = nobjs - nrooms - nchars - nexits

    pagevars = {
        "page_title": "Front Page",
        "players_connected_recent": recent_users,
        "num_players_connected": nsess or "no one",
        "num_players_registered": nplyrs or "no",
        "num_players_connected_recent": nplyrs_conn_recent or "no",
        "num_players_registered_recent": nplyrs_reg_recent or "no one",
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
            'playerdb': PlayerDB})


def admin_wrapper(request):
    """
    Wrapper that allows us to properly use the base Django admin site, if needed.
    """
    return staff_member_required(site.index)(request)
