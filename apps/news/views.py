#
# News display.
#
from django.shortcuts import render_to_response, get_object_or_404
from django.db import connection
from django.template import RequestContext
from django import newforms as forms
from django.newforms.util import ValidationError
import django.views.generic.list_detail as list_detail
from django.contrib.auth.models import User
from django.utils import simplejson

import frontier.settings as settings
from frontier.apps.player.models import UserProfile
from frontier.apps.news.models import NewsTopic, NewsEntry

nav_block = """
<div>
</div>
"""

def index(request):
   """
   News index.
   """
   news_entries = NewsEntry.objects.all().order_by('-date_posted')[:10]

   pagevars = {
      "page_title": "Front Page",
      "nav_block": nav_block,
      "news_entries": news_entries,
   }

   context_instance = RequestContext(request)
   return render_to_response('news/index.html', pagevars, context_instance)
