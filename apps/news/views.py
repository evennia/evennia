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
   #news_entries = NewsEntry.objects.all().order_by('-date_posted')[:10]

   pagevars = {
      "page_title": "Front Page",
   }

   context_instance = RequestContext(request)
   return render_to_response('base.html', pagevars, context_instance)
