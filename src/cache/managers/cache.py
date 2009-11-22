"""
Custom manager for Cache objects
"""
from django.db import models

# This is the (arbitrary, but consistent) name used by the
# global interval-saved (persistent) cache (this is
# used by initial_setup)
GLOBAL_PCACHE_NAME = "_global_persistent_cache"

class CacheManager(models.Manager):
    """
    Custom cache manager. 
    """
    def get_default_pcache(self):
        """
        Find and return the global pcache object.
        """
        return self.get(cache_name=GLOBAL_PCACHE_NAME)
        
