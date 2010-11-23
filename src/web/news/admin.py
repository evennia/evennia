#
# This makes the news model visible in the admin web interface
# so one can add/edit/delete news items etc. 
#

from django.contrib import admin
from src.web.news.models import NewsTopic, NewsEntry

class NewsTopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon')
admin.site.register(NewsTopic, NewsTopicAdmin)

class NewsEntryAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'topic', 'date_posted')
    list_filter = ('topic',)
    search_fields = ['title']
admin.site.register(NewsEntry, NewsEntryAdmin)
