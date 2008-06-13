"""
The ReloadMixin class is meant as an example, but should work
for basic purposes as a mixin inheritance.
"""
class ReloadMixin():
     """
     This class is a generic reload mixin providing the two 
     methods required to cache and reload an object.
     """
     def cache(self, reloader, do_save=True):
          if do_save:
                if self.save and callable(self.save):
                     self.save()
                else:
                     raise ValueError("This object does not have a save function, you must pass do_save=False for this object type.")

          reloader.cache_object(self)

     def reload(self, cache):
          for key, value in cache.iteritems():
                if self.__dict__[key] != value:
                     self.__dict__[key] = value
