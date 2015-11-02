"""
Tags are entities that are attached to objects in the same way as
Attributes. But contrary to Attributes, which are unique to an
individual object, a single Tag can be attached to any number of
objects at the same time.

Tags are used for tagging, obviously, but the data structure is also
used for storing Aliases and Permissions. This module contains the
respective handlers.

"""
from builtins import object

from django.conf import settings
from django.db import models
from evennia.utils.utils import to_str, make_iter


_TYPECLASS_AGGRESSIVE_CACHE = settings.TYPECLASS_AGGRESSIVE_CACHE

#------------------------------------------------------------
#
# Tags
#
#------------------------------------------------------------

class Tag(models.Model):
    """
    Tags are quick markers for objects in-game. An typeobject can have
    any number of tags, stored via its db_tags property.  Tagging
    similar objects will make it easier to quickly locate the group
    later (such as when implementing zones). The main advantage of
    tagging as opposed to using Attributes is speed; a tag is very
    limited in what data it can hold, and the tag key+category is
    indexed for efficient lookup in the database. Tags are shared
    between objects - a new tag is only created if the key+category
    combination did not previously exist, making them unsuitable for
    storing object-related data (for this a full Attribute should be
    used).

    The 'db_data' field is intended as a documentation field for the
    tag itself, such as to document what this tag+category stands for
    and display that in a web interface or similar.

    The main default use for Tags is to implement Aliases for objects.
    this uses the 'aliases' tag category, which is also checked by the
    default search functions of Evennia to allow quick searches by alias.

    """
    db_key = models.CharField('key', max_length=255, null=True,
                              help_text="tag identifier", db_index=True)
    db_category = models.CharField('category', max_length=64, null=True,
                                   help_text="tag category", db_index=True)
    db_data = models.TextField('data', null=True, blank=True,
                               help_text="optional data field with extra information. This is not searched for.")
    # this is "objectdb" etc. Required behind the scenes
    db_model = models.CharField('model', max_length=32, null=True, help_text="database model to Tag", db_index=True)
    # this is None, alias or permission
    db_tagtype = models.CharField('tagtype', max_length=16, null=True, help_text="overall type of Tag", db_index=True)

    class Meta(object):
        "Define Django meta options"
        verbose_name = "Tag"
        unique_together = (('db_key', 'db_category', 'db_tagtype'),)
        index_together = (('db_key', 'db_category', 'db_tagtype'),)

    def __unicode__(self):
        return u"%s" % self.db_key

    def __str__(self):
        return str(self.db_key)


#
# Handlers making use of the Tags model
#

class TagHandler(object):
    """
    Generic tag-handler. Accessed via TypedObject.tags.

    """
    _m2m_fieldname = "db_tags"
    _tagtype = None

    def __init__(self, obj):
        """
        Tags are stored internally in the TypedObject.db_tags m2m
        field with an tag.db_model based on the obj the taghandler is
        stored on and with a tagtype given by self.handlertype

        Args:
            obj (object): The object on which the handler is set.

        """
        self.obj = obj
        self._objid = obj.id
        self._model = obj.__dbclass__.__name__.lower()
        self._cache = None

    def _recache(self):
        """
        Cache all tags of this object.

        """
        query = {"%s__id" % self._model : self._objid,
                 "tag__db_tagtype" : self._tagtype}
        tagobjs = [conn.tag for conn in getattr(self.obj, self._m2m_fieldname).through.objects.filter(**query)]
        self._cache = dict(("%s-%s" % (to_str(tagobj.db_key).lower(),
                                       tagobj.db_category.lower() if tagobj.db_category else None),
                            tagobj) for tagobj in tagobjs)

    def add(self, tag=None, category=None, data=None):
        """
        Add a new tag to the handler.

        Args:
            tag (str or list): The name of the tag to add. If a list,
                add several Tags.
            category (str, optional): Category of Tag. `None` is the default category.
            data (str, optional): Info text about the tag(s) added.
                This can not be used to store object-unique info but only
                eventual info about the text itself.

        Notes:
            If the tag + category combination matches an already
            existing Tag object, this will be re-used and no new Tag
            will be created.

        """
        if not tag:
            return
        for tagstr in make_iter(tag):
            if not tagstr:
                continue
            tagstr = tagstr.strip().lower()
            category = category.strip().lower() if category is not None else None
            data = str(data) if data is not None else None
            # this will only create tag if no matches existed beforehand (it
            # will overload data on an existing tag since that is not
            # considered part of making the tag unique)
            tagobj = self.obj.__class__.objects.create_tag(key=tagstr, category=category, data=data,
                                            tagtype=self._tagtype)
            getattr(self.obj, self._m2m_fieldname).add(tagobj)
            if self._cache is None:
                self._recache()
            cachestring = "%s-%s" % (tagstr, category)
            self._cache[cachestring] = tagobj

    def get(self, key, default=None, category=None, return_tagobj=False):
        """
        Get the tag for the given key or list of tags.

        Args:
            key (str or list): The tag or tags to retrieve.
            default (any, optional): The value to return in case of no match.
            category (str, optional): The Tag category to limit the
                request to. Note that `None` is the valid, default
                category.
            return_tagobj (bool, optional): Return the Tag object itself
                instead of a string representation of the Tag.

        Returns:
            tags (str, TagObject or list): The matches, either string
                representations of the tags or the Tag objects themselves
                depending on `return_tagobj`.

        """
        if self._cache is None or not _TYPECLASS_AGGRESSIVE_CACHE:
            self._recache()
        ret = []
        category = category.strip().lower() if category is not None else None
        searchkey = ["%s-%s" % (key.strip().lower(), category) if key is not None else None for key in make_iter(key)]
        ret = [val for val in (self._cache.get(keystr) for keystr in searchkey) if val]
        ret = [to_str(tag.db_data) for tag in ret] if return_tagobj else ret
        return ret[0] if len(ret) == 1 else (ret if ret else default)

    def remove(self, key, category=None):
        """
        Remove a tag from the handler based ond key and category.

        Args:
            key (str or list): The tag or tags to retrieve.
            category (str, optional): The Tag category to limit the
                request to. Note that `None` is the valid, default
                category.

        """
        for key in make_iter(key):
            if not (key or key.strip()):  # we don't allow empty tags
                continue
            tagstr = key.strip().lower()
            category = category.strip().lower() if category is not None else None

            # This does not delete the tag object itself. Maybe it should do
            # that when no objects reference the tag anymore (how to check)?
            tagobj = self.obj.db_tags.filter(db_key=tagstr, db_category=category)
            if tagobj:
                getattr(self.obj, self._m2m_fieldname).remove(tagobj[0])
        self._recache()

    def clear(self, category=None):
        """
        Remove all tags from the handler.

        Args:
            category (str, optional): The Tag category to limit the
                request to. Note that `None` is the valid, default
                category.

        """
        if not category:
            getattr(self.obj, self._m2m_fieldname).clear()
        else:
            getattr(self.obj, self._m2m_fieldname).filter(db_category=category).delete()
        self._recache()

    def all(self, category=None, return_key_and_category=False):
        """
        Get all tags in this handler.

        Args:
            category (str, optional): The Tag category to limit the
                request to. Note that `None` is the valid, default
                category.
            return_key_and_category (bool, optional): Return a list of
                tuples `[(key, category), ...]`.

        Returns:
            tags (list): A list of tag keys `[tagkey, tagkey, ...]` or
                a list of tuples `[(key, category), ...]` if
                `return_key_and_category` is set.

        """
        if self._cache is None or not _TYPECLASS_AGGRESSIVE_CACHE:
            self._recache()
        if category:
            category = category.strip().lower() if category is not None else None
            matches = [tag for tag in self._cache.values() if tag.db_category == category]
        else:
            matches = self._cache.values()

        if matches:
            matches = sorted(matches, key=lambda o: o.id)
            if return_key_and_category:
                # return tuple (key, category)
                return [(to_str(p.db_key), to_str(p.db_category)) for p in matches]
            else:
                return [to_str(p.db_key) for p in matches]
        return []

    def __str__(self):
        return ",".join(self.all())

    def __unicode(self):
        return u",".join(self.all())


class AliasHandler(TagHandler):
    """
    A handler for the Alias Tag type.

    """
    _tagtype = "alias"


class PermissionHandler(TagHandler):
    """
    A handler for the Permission Tag type.

    """
    _tagtype = "permission"

