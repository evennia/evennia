#
# News display.
#
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
import django.views.generic.list_detail as gv_list_detail
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from django import newforms as forms

from apps.news.models import NewsTopic, NewsEntry

# The sidebar text to be included as a variable on each page. There's got to
# be a better, cleaner way to include this on every page.
sidebar = """
   <p class='doNotDisplay doNotPrint'>This page&rsquo;s menu:</p>
   <ul id='side-bar'>
     <li><a href='/news/archive'>News Archive</a></li>
     <li><a href='/news/search'>Search News</a></li>
   </ul>
"""

class SearchForm(forms.Form):
   """
   Class to represent a news search form under Django's newforms.
   """
   search_terms = forms.CharField(max_length=100, min_length=3, required=True)

def show_news(request, entry_id):
   """
   Show an individual news entry.
   """
   news_entry = get_object_or_404(NewsEntry, id=entry_id)

   pagevars = {
      "page_title": "News Entry",
      "news_entry": news_entry,
      "sidebar": sidebar
   }

   context_instance = RequestContext(request)
   return render_to_response('news/show_entry.html', pagevars, context_instance)

def news_archive(request):
   """
   Shows an archive of news entries.
   """
   news_entries = NewsEntry.objects.all().order_by('-date_posted')
   # TODO: Move this to either settings.py or the SQL configuration.
   entries_per_page = 15

   pagevars = {
      "page_title": "News Archive",
      "browse_url": "/news/archive",
      "sidebar": sidebar
   }
   
   return gv_list_detail.object_list(request, news_entries, template_name='news/archive.html', extra_context=pagevars, paginate_by=entries_per_page)

def search_form(request):
   """
   Render the news search form.
   """
   debug =""

   if request.method == 'GET':
      debug = "GET"
      search_form = SearchForm(request.GET)
      if search_form.is_valid():
         return HttpResponseRedirect('/news/search/results/?search_terms='+ search_form.cleaned_data['search_terms'])
   else:
      debug = "NOTHING"
      search_form = SearchForm()

   pagevars = {
      "page_title": "Search News",
      "search_form": search_form,
      "debug": debug,
      "sidebar": sidebar
   }

   context_instance = RequestContext(request)
   return render_to_response('news/search_form.html', pagevars, context_instance)

def search_results(request):
   """
   Shows an archive of news entries.
   """
   # TODO: Move this to either settings.py or the SQL configuration.
   entries_per_page = 15

   search_form = SearchForm(request.GET)
   valid_search = search_form.is_valid()
   cleaned_get = search_form.cleaned_data

   news_entries = NewsEntry.objects.filter(title__contains=cleaned_get['search_terms'])

   pagevars = {
      "page_title": "Search Results",
      "searchtext": cleaned_get['search_terms'],
      "browse_url": "/news/search/results",
      "sidebar": sidebar
   }
   
   return gv_list_detail.object_list(request, news_entries, template_name='news/archive.html', extra_context=pagevars, paginate_by=entries_per_page)