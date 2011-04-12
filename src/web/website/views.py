
"""
This file contains the generic, assorted views that don't fall under one of
the other applications. Views are django's way of processing e.g. html 
templates on the fly.

"""

from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.models import User
from django.conf import settings

from src.server.models import ServerConfig
from src.objects.models import ObjectDB
from src.typeclasses.models import TypedObject
from src.players.models import PlayerDB
from src.web.news.models import NewsEntry

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

    exits = ObjectDB.objects.filter(db_destination__isnull=False)
    rooms = [room for room in ObjectDB.objects.filter(db_home__isnull=True) if room not in exits]

    pagevars = {
        "page_title": "Front Page",
        "news_entries": news_entries,
        "players_connected_recent": recent_users,
        "num_players_connected": ServerConfig.objects.conf('nr_sessions'),#len(PlayerDB.objects.get_connected_players()),
        "num_players_registered": PlayerDB.objects.num_total_players(),
        "num_players_connected_recent": len(PlayerDB.objects.get_recently_connected_players()),
        "num_players_registered_recent": len(PlayerDB.objects.get_recently_created_players()),
        "num_rooms": len(rooms),
        "num_exits": len(exits),
        "num_objects" : ObjectDB.objects.all().count()
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


