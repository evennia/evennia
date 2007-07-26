#
# News display.
#
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
import django.views.generic.list_detail as list_detail
from django.contrib.auth.models import User

from apps.news.models import NewsTopic, NewsEntry

def show_news(request, entry_id):
   """
   Show an individual news entry.
   """
   news_entry = get_object_or_404(NewsEntry, id=entry_id)

   pagevars = {
      "page_title": "News Entry",
      "news_entry": news_entry
   }

   context_instance = RequestContext(request)
   return render_to_response('news/show_entry.html', pagevars, context_instance)
