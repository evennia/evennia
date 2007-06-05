from django.shortcuts import render_to_response, get_object_or_404
from django.db import connection
from django.template import RequestContext
from django import newforms as forms
from django.newforms.util import ValidationError
import django.views.generic.list_detail as list_detail
from django.contrib.auth.models import User
from django.utils import simplejson

from apps.news.models import NewsEntry

"""
This file contains the generic, assorted views that don't fall under one of
the other applications.
"""

def page_index(request):
   """
   Main root page.
   """
   news_entries = NewsEntry.objects.all().order_by('-date_posted')[:2]

   pagevars = {
      "page_title": "Front Page",
      "news_entries": news_entries,
   }

   context_instance = RequestContext(request)
   return render_to_response('index.html', pagevars, context_instance)