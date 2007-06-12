from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.models import User

from apps.news.models import NewsEntry
import functions_db

"""
This file contains the generic, assorted views that don't fall under one of
the other applications.
"""

def page_index(request):
   """
   Main root page.
   """
   # Some misc. configurable stuff.
   fpage_player_limit = 4   
   fpage_news_entries = 2
   
   # A QuerySet of recent news entries.
   news_entries = NewsEntry.objects.all().order_by('-date_posted')[:fpage_news_entries]
   # Dictionary containing database statistics.
   objstats = functions_db.object_totals()
   # A QuerySet of the most recently connected players.
   recent_players = functions_db.get_recently_connected_players()[:fpage_player_limit]
   
   pagevars = {
      "page_title": "Front Page",
      "news_entries": news_entries,
      "players_connected_recent": recent_players,
      "num_players_connected": functions_db.get_connected_players().count(),
      "num_players_registered": functions_db.num_total_players(),
      "num_players_connected_recent": functions_db.get_recently_connected_players().count(),
      "num_players_registered_recent": functions_db.get_recently_created_players().count(),
      "num_players": objstats["players"],
      "num_rooms": objstats["rooms"],
      "num_things": objstats["things"],
      "num_exits": objstats["exits"],
   }

   context_instance = RequestContext(request)
   return render_to_response('index.html', pagevars, context_instance)