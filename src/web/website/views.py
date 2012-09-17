
"""
This file contains the generic, assorted views that don't fall under one of
the other applications. Views are django's way of processing e.g. html
templates on the fly.

"""
from django.shortcuts import render_to_response
from django.template import RequestContext
#from django.contrib.auth.models import User
from django.conf import settings

from src.objects.models import ObjectDB
#from src.typeclasses.models import TypedObject
from src.players.models import PlayerDB
from src.web.news.models import NewsEntry

_BASE_CHAR_TYPECLASS = settings.BASE_CHARACTER_TYPECLASS

def page_index(request):
    """
    Main root page.
    """
    # Some misc. configurable stuff.
    # TODO: Move this to either SQL or settings.py based configuration.
    fpage_player_limit = 4
    fpage_news_entries = 2

    # A QuerySet of recent news entries.
    news_entries = NewsEntry.objects.all().order_by('-date_posted')[:fpage_news_entries]
    # A QuerySet of the most recently connected players.
    recent_users = PlayerDB.objects.get_recently_connected_players()[:fpage_player_limit]
    nplyrs_conn_recent = len(recent_users) or "none"
    nplyrs = PlayerDB.objects.num_total_players() or "none"
    nplyrs_reg_recent = len(PlayerDB.objects.get_recently_created_players()) or "none"
    nsess = len(PlayerDB.objects.get_connected_players()) or "noone"

    nobjs = ObjectDB.objects.all().count()
    nrooms = ObjectDB.objects.filter(db_location__isnull=True).exclude(db_typeclass_path=_BASE_CHAR_TYPECLASS).count()
    nexits = ObjectDB.objects.filter(db_location__isnull=False, db_destination__isnull=False).count()
    nchars = ObjectDB.objects.filter(db_typeclass_path=_BASE_CHAR_TYPECLASS).count()
    nothers = nobjs - nrooms - nchars - nexits

    pagevars = {
        "page_title": "Front Page",
        "news_entries": news_entries,
        "players_connected_recent": recent_users,
        "num_players_connected": nsess or "noone",
        "num_players_registered": nplyrs or "no",
        "num_players_connected_recent": nplyrs_conn_recent or "no",
        "num_players_registered_recent": nplyrs_reg_recent or "noone",
        "num_rooms": nrooms or "none",
        "num_exits": nexits or "no",
        "num_objects" : nobjs or "none",
        "num_characters": nchars or "no",
        "num_others": nothers or "no"
    }

    context_instance = RequestContext(request)
    return render_to_response('index.html', pagevars, context_instance)

def to_be_implemented(request):
    """
    A notice letting the user know that this particular feature hasn't been
    implemented yet.
    """

    pagevars = {
        "page_title": "To Be Implemented...",
    }

    context_instance = RequestContext(request)
    return render_to_response('tbi.html', pagevars, context_instance)


