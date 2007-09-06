import functions_general

class ReloadManager(object):
    objects_cache = {}
    failed = []

    models = {}

    def __init__(self, server):
        self.server = server

    def do_cache(self):
        for module, info in self.models.iteritems():
            module_obj = __import__(module)
            for ituple in info:
                mclass = getattr(module_obj, info[0])
                for instance in mclass.__instances__():
                    instance.cache(self, do_save=ituple[1])

    def do_reload(self):
        self.do_cache()
        self.server.reload()
        self.reload_objects()

    def cache_object(self, obj):
        obj_dict = {}
        for key, value in obj.__dict__.iteritems():
            if not callable(obj[key]):
                obj_dict[key] = value

        self.objects_cache[obj] = obj_dict

    def reload_objects(self):
        for obj, cache in self.objects_cache.iteritems():
            try:
                obj.reload(cache)
            except:
                functions_general.log_errmsg("Failed to reload cache for object: %s." % (obj,))
                self.failed.append(obj)
                raise

        self.objects_cache = {}

        for obj in self.failed:
            try:
                obj.__dict__.update(cache)
            except:
                functions_general.log_errmsg("Failed to update object %s, giving up." %s (obj,))
                raise

        self.failed = []
