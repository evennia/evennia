
class ReloadMixin():
    def cache(self, callback, do_save=True):
        cache_dict = {}
        if do_save:
            if self.save and callable(self.save):
                self.save()
            else:
                raise ValueError("This object does not have a save function, you must pass save=False for this object type.")

        for key, value in self.__dict__.iteritems():
            if not callable(value):
                cache_dict[key] = value

        callback(cache_dict)

    def reload(self, cache):
        for key, value in cache.iteritems():
            if self.__dict__[key] != value:
                self.__dict__[key] = value
