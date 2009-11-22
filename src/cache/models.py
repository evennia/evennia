"""
This implements a database storage cache for storing global 
cache data persistently.
It is intended to be used with an event timer for updating
semi-regularly (otherwise, object attributes are better to use
if full persistency is needed).
"""

from django.db import models
from django.conf import settings

from src.cache.managers.cache import CacheManager

# 091120 - there is a bug in cPickle for importing the
# custom cache objects; only normal pickle works. /Griatch
import pickle
#try:
#    import cPickle as pickle
#except ImportError:
#    import pickle

class PersistentCache(models.Model):
    """
    Implements a simple pickled database object, without
    using the in-game object attribute model.
    """
    cache_name = models.CharField(max_length=255)
    cache_data = models.TextField(blank=True)

    objects = CacheManager()

    class Meta:
        permissions = settings.PERM_CACHE

    def load_cache(self):
        """
        Recovers cache from database storage.
        """
        cache_data = str(self.cache_data)
        #print "loading cache: %s" % cache_data
        if cache_data:            
            cache_data = pickle.loads(cache_data)
            cache_data.pickle_no()
            return cache_data
        else:
            return None
        
    def save_cache(self, cache_obj):
        """
        Stores a cache as a pickle. 
        """
        #print "saving ... '%s': %s" % (cache_obj,cache_obj.show())        
        cache_obj.pickle_yes()                
        self.cache_data = pickle.dumps(cache_obj)        
        cache_obj.pickle_no()
        self.save()
