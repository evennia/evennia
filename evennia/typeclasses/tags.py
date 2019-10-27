"""
Tags are entities that are attached to objects in the same way as
Attributes. But contrary to Attributes, which are unique to an
individual object, a single Tag can be attached to any number of
objects at the same time.

Tags are used for tagging, obviously, but the data structure is also
used for storing Aliases and Permissions. This module contains the
respective handlers.

"""
from collections import defaultdict

from django.conf import settings
from django.db import models
from evennia.utils.utils import to_str, make_iter


_TYPECLASS_AGGRESSIVE_CACHE = settings.TYPECLASS_AGGRESSIVE_CACHE

# ------------------------------------------------------------
#
# Tags
#
# ------------------------------------------------------------


class Tag(models.Model):
    """
    Tags are quick markers for objects in-game. An typeobject can have
    any number of tags, stored via its db_tags property.  Tagging
    similar objects will make it easier to quickly locate the group
    later (such as when implementing zones). The main advantage of
    tagging as opposed to using tags is speed; a tag is very
    limited in what data it can hold, and the tag key+category is
    indexed for efficient lookup in the database. Tags are shared
    between objects - a new tag is only created if the key+category
    combination did not previously exist, making them unsuitable for
    storing object-related data (for this a full tag should be
    used).

    The 'db_data' field is intended as a documentation field for the
    tag itself, such as to document what this tag+category stands for
    and display that in a web interface or similar.

    The main default use for Tags is to implement Aliases for objects.
    this uses the 'aliases' tag category, which is also checked by the
    default search functions of Evennia to allow quick searches by alias.

    """

    db_key = models.CharField(
        "key", max_length=255, null=True, help_text="tag identifier", db_index=True
    )
    db_category = models.CharField(
        "category", max_length=64, null=True, help_text="tag category", db_index=True
    )
    db_data = models.TextField(
        "data",
        null=True,
        blank=True,
        help_text="optional data field with extra information. This is not searched for.",
    )
    # this is "objectdb" etc. Required behind the scenes
    db_model = models.CharField(
        "model", max_length=32, null=True, help_text="database model to Tag", db_index=True
    )
    # this is None, alias or permission
    db_tagtype = models.CharField(
        "tagtype",
        max_length=16,
        null=True,
        blank=True,
        help_text="overall type of Tag",
        db_index=True,
    )

    class Meta(object):
        "Define Django meta options"
        verbose_name = "Tag"
        unique_together = (("db_key", "db_category", "db_tagtype", "db_model"),)
        index_together = (("db_key", "db_category", "db_tagtype", "db_model"),)

    def __lt__(self, other):
        return str(self) < str(other)

    def __str__(self):
        return str(
            "<Tag: %s%s>"
            % (self.db_key, "(category:%s)" % self.db_category if self.db_category else "")
        )


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
        self._cache = {}
        # store category names fully cached
        self._catcache = {}
        # full cache was run on all tags
        self._cache_complete = False

    def _fullcache(self):
        "Cache all tags of this object"
        query = {
            "%s__id" % self._model: self._objid,
            "tag__db_model": self._model,
            "tag__db_tagtype": self._tagtype,
        }
        tags = [
            conn.tag
            for conn in getattr(self.obj, self._m2m_fieldname).through.objects.filter(**query)
        ]
        self._cache = dict(
            (
                "%s-%s"
                % (
                    to_str(tag.db_key).lower(),
                    tag.db_category.lower() if tag.db_category else None,
                ),
                tag,
            )
            for tag in tags
        )
        self._cache_complete = True

    def _getcache(self, key=None, category=None):
        """
        Retrieve from cache or database (always caches)

        Args:
            key (str, optional): Tag key to query for
            category (str, optional): Tag category

        Returns:
            args (list): Returns a list of zero or more matches
                found from cache or database.
        Notes:
            When given a category only, a search for all objects
            of that category is done and a the category *name* is is
            stored. This tells the system on subsequent calls that the
            list of cached tags of this category is up-to-date
            and that the cache can be queried for category matches
            without missing any.
            The TYPECLASS_AGGRESSIVE_CACHE=False setting will turn off
            caching, causing each tag access to trigger a
            database lookup.

        """
        key = key.strip().lower() if key else None
        category = category.strip().lower() if category else None
        if key:
            cachekey = "%s-%s" % (key, category)
            tag = _TYPECLASS_AGGRESSIVE_CACHE and self._cache.get(cachekey, None)
            if tag and (not hasattr(tag, "pk") and tag.pk is None):
                # clear out Tags deleted from elsewhere. We must search this anew.
                tag = None
                del self._cache[cachekey]
            if tag:
                return [tag]  # return cached entity
            else:
                query = {
                    "%s__id" % self._model: self._objid,
                    "tag__db_model": self._model,
                    "tag__db_tagtype": self._tagtype,
                    "tag__db_key__iexact": key.lower(),
                    "tag__db_category__iexact": category.lower() if category else None,
                }
                conn = getattr(self.obj, self._m2m_fieldname).through.objects.filter(**query)
                if conn:
                    tag = conn[0].tag
                    self._cache[cachekey] = tag
                    return [tag]
        else:
            # only category given (even if it's None) - we can't
            # assume the cache to be complete unless we have queried
            # for this category before
            catkey = "-%s" % category
            if _TYPECLASS_AGGRESSIVE_CACHE and catkey in self._catcache:
                return [tag for key, tag in self._cache.items() if key.endswith(catkey)]
            else:
                # we have to query to make this category up-date in the cache
                query = {
                    "%s__id" % self._model: self._objid,
                    "tag__db_model": self._model,
                    "tag__db_tagtype": self._tagtype,
                    "tag__db_category__iexact": category.lower() if category else None,
                }
                tags = [
                    conn.tag
                    for conn in getattr(self.obj, self._m2m_fieldname).through.objects.filter(
                        **query
                    )
                ]
                for tag in tags:
                    cachekey = "%s-%s" % (tag.db_key, category)
                    self._cache[cachekey] = tag
                # mark category cache as up-to-date
                self._catcache[catkey] = True
                return tags
        return []

    def _setcache(self, key, category, tag_obj):
        """
        Update cache.

        Args:
            key (str): A cleaned key string
            category (str or None): A cleaned category name
            tag_obj (tag): The newly saved tag

        """
        if not key:  # don't allow an empty key in cache
            return
        key, category = key.strip().lower(), category.strip().lower() if category else category
        cachekey = "%s-%s" % (key, category)
        catkey = "-%s" % category
        self._cache[cachekey] = tag_obj
        # mark that the category cache is no longer up-to-date
        self._catcache.pop(catkey, None)
        self._cache_complete = False

    def _delcache(self, key, category):
        """
        Remove tag from cache

        Args:
            key (str): A cleaned key string
            category (str or None): A cleaned category name

        """
        key, category = key.strip().lower(), category.strip().lower() if category else category
        catkey = "-%s" % category
        if key:
            cachekey = "%s-%s" % (key, category)
            self._cache.pop(cachekey, None)
        else:
            [self._cache.pop(key, None) for key in self._cache if key.endswith(catkey)]
        # mark that the category cache is no longer up-to-date
        self._catcache.pop(catkey, None)
        self._cache_complete = False

    def reset_cache(self):
        """
        Reset the cache from the outside.
        """
        self._cache_complete = False
        self._cache = {}
        self._catcache = {}

    def add(self, tag=None, category=None, data=None):
        """
        Add a new tag to the handler.

        Args:
            tag (str or list): The name of the tag to add. If a list,
                add several Tags.
            category (str, optional): Category of Tag. `None` is the default category.
            data (str, optional): Info text about the tag(s) added.
                This can not be used to store object-unique info but only
                eventual info about the tag itself.

        Notes:
            If the tag + category combination matches an already
            existing Tag object, this will be re-used and no new Tag
            will be created.

        """
        if not tag:
            return
        if not self._cache_complete:
            self._fullcache()
        for tagstr in make_iter(tag):
            if not tagstr:
                continue
            tagstr = str(tagstr).strip().lower()
            category = str(category).strip().lower() if category else category
            data = str(data) if data is not None else None
            # this will only create tag if no matches existed beforehand (it
            # will overload data on an existing tag since that is not
            # considered part of making the tag unique)
            tagobj = self.obj.__class__.objects.create_tag(
                key=tagstr, category=category, data=data, tagtype=self._tagtype
            )
            getattr(self.obj, self._m2m_fieldname).add(tagobj)
            self._setcache(tagstr, category, tagobj)

    def get(self, key=None, default=None, category=None, return_tagobj=False, return_list=False):
        """
        Get the tag for the given key, category or combination of the two.

        Args:
            key (str or list, optional): The tag or tags to retrieve.
            default (any, optional): The value to return in case of no match.
            category (str, optional): The Tag category to limit the
                request to. Note that `None` is the valid, default
                category. If no `key` is given, all tags of this category will be
                returned.
            return_tagobj (bool, optional): Return the Tag object itself
                instead of a string representation of the Tag.
            return_list (bool, optional): Always return a list, regardless
                of number of matches.

        Returns:
            tags (list): The matches, either string
                representations of the tags or the Tag objects themselves
                depending on `return_tagobj`. If 'default' is set, this
                will be a list with the default value as its only element.

        """
        ret = []
        for keystr in make_iter(key):
            # note - the _getcache call removes case sensitivity for us
            ret.extend(
                [
                    tag if return_tagobj else to_str(tag.db_key)
                    for tag in self._getcache(keystr, category)
                ]
            )
        if return_list:
            return ret if ret else [default] if default is not None else []
        return ret[0] if len(ret) == 1 else (ret if ret else default)

    def remove(self, key=None, category=None):
        """
        Remove a tag from the handler based ond key and/or category.

        Args:
            key (str or list, optional): The tag or tags to retrieve.
            category (str, optional): The Tag category to limit the
                request to. Note that `None` is the valid, default
                category
        Notes:
            If neither key nor category is specified, this acts
            as .clear().

        """
        if not key:
            # only category
            self.clear(category=category)
            return

        for key in make_iter(key):
            if not (key or key.strip()):  # we don't allow empty tags
                continue
            tagstr = key.strip().lower()
            category = category.strip().lower() if category else category

            # This does not delete the tag object itself. Maybe it should do
            # that when no objects reference the tag anymore (but how to check)?
            # For now, tags are never deleted, only their connection to objects.
            tagobj = getattr(self.obj, self._m2m_fieldname).filter(
                db_key=tagstr, db_category=category, db_model=self._model, db_tagtype=self._tagtype
            )
            if tagobj:
                getattr(self.obj, self._m2m_fieldname).remove(tagobj[0])
            self._delcache(key, category)

    def clear(self, category=None):
        """
        Remove all tags from the handler.

        Args:
            category (str, optional): The Tag category to limit the
                request to. Note that `None` is the valid, default
                category.

        """
        if not self._cache_complete:
            self._fullcache()
        query = {
            "%s__id" % self._model: self._objid,
            "tag__db_model": self._model,
            "tag__db_tagtype": self._tagtype,
        }
        if category:
            query["tag__db_category"] = category.strip().lower()
        getattr(self.obj, self._m2m_fieldname).through.objects.filter(**query).delete()
        self._cache = {}
        self._catcache = {}
        self._cache_complete = False

    def all(self, return_key_and_category=False, return_objs=False):
        """
        Get all tags in this handler, regardless of category.

        Args:
            return_key_and_category (bool, optional): Return a list of
                tuples `[(key, category), ...]`.
            return_objs (bool, optional): Return tag objects.

        Returns:
            tags (list): A list of tag keys `[tagkey, tagkey, ...]` or
                a list of tuples `[(key, category), ...]` if
                `return_key_and_category` is set.

        """
        if not self._cache_complete:
            self._fullcache()
        tags = sorted(self._cache.values())
        if return_key_and_category:
            # return tuple (key, category)
            return [(to_str(tag.db_key), tag.db_category) for tag in tags]
        elif return_objs:
            return tags
        else:
            return [to_str(tag.db_key) for tag in tags]

    def batch_add(self, *args):
        """
        Batch-add tags from a list of tuples.

        Args:
            tuples (tuple or str): Any number of `tagstr` keys, `(keystr, category)` or
                `(keystr, category, data)` tuples.

        Notes:
            This will generate a mimimal number of self.add calls,
            based on the number of categories involved (including
            `None`) (data is not unique and may be overwritten by the content
            of a latter tuple with the same category).

        """
        keys = defaultdict(list)
        data = {}
        for tup in args:
            tup = make_iter(tup)
            nlen = len(tup)
            if nlen == 1:  # just a key
                keys[None].append(tup[0])
            elif nlen == 2:
                keys[tup[1]].append(tup[0])
            else:
                keys[tup[1]].append(tup[0])
                data[tup[1]] = tup[2]  # overwrite previous
        for category, key in keys.items():
            self.add(tag=key, category=category, data=data.get(category, None))

    def __str__(self):
        return ",".join(self.all())


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
