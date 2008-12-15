from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.models import User

from src.objects.models import Object
from game.web.apps.news.models import NewsEntry

"""
This file contains the generic, assorted views that don't fall under one of
the other applications.
"""

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
    # Dictionary containing database statistics.
    objstats = Object.objects.object_totals()
    # A QuerySet of the most recently connected players.
    recent_players = Object.objects.get_recently_connected_users()[:fpage_player_limit]
    
    pagevars = {
        "page_title": "Front Page",
        "news_entries": news_entries,
        "players_connected_recent": recent_players,
        "num_players_connected": Object.objects.get_connected_players().count(),
        "num_players_registered": Object.objects.num_total_players(),
        "num_players_connected_recent": Object.objects.get_recently_connected_users().count(),
        "num_players_registered_recent": Object.objects.get_recently_created_users().count(),
        "num_players": objstats["players"],
        "num_rooms": objstats["rooms"],
        "num_things": objstats["things"],
        "num_exits": objstats["exits"],
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
