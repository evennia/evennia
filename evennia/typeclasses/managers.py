"""
This implements the common managers that are used by the
abstract models in dbobjects.py (and which are thus shared by
all Attributes and TypedObjects).

"""
import shlex
from django.db.models import Q
from evennia.utils import idmapper
from evennia.utils.utils import make_iter, variable_from_module
from evennia.typeclasses.attributes import Attribute
from evennia.typeclasses.tags import Tag

__all__ = ("TypedObjectManager",)
_GA = object.__getattribute__
_Tag = None


# Managers


class TypedObjectManager(idmapper.manager.SharedMemoryManager):
    """
    Common ObjectManager for all dbobjects.

    """

    # common methods for all typed managers. These are used
    # in other methods. Returns querysets.

    # Attribute manager methods
    def get_attribute(
        self, key=None, category=None, value=None, strvalue=None, obj=None, attrtype=None
    ):
        """
        Return Attribute objects by key, by category, by value, by
        strvalue, by object (it is stored on) or with a combination of
        those criteria.

        Attrs:
            key (str, optional): The attribute's key to search for
            category (str, optional): The category of the attribute(s)
                to search for.
            value (str, optional): The attribute value to search for.
                Note that this is not a very efficient operation since it
                will query for a pickled entity. Mutually exclusive to
                `strvalue`.
            strvalue (str, optional): The str-value to search for.
                Most Attributes will not have strvalue set. This is
                mutually exclusive to the `value` keyword and will take
                precedence if given.
            obj (Object, optional): On which object the Attribute to
                search for is.
            attrype (str, optional): An attribute-type to search for.
                By default this is either `None` (normal Attributes) or
                `"nick"`.

        Returns:
            attributes (list): The matching Attributes.

        """
        dbmodel = self.model.__dbclass__.__name__.lower()
        query = [("attribute__db_attrtype", attrtype), ("attribute__db_model", dbmodel)]
        if obj:
            query.append(("%s__id" % self.model.__dbclass__.__name__.lower(), obj.id))
        if key:
            query.append(("attribute__db_key", key))
        if category:
            query.append(("attribute__db_category", category))
        if strvalue:
            query.append(("attribute__db_strvalue", strvalue))
        if value:
            # no reason to make strvalue/value mutually exclusive at this level
            query.append(("attribute__db_value", value))
        return Attribute.objects.filter(
            pk__in=self.model.db_attributes.through.objects.filter(**dict(query)).values_list(
                "attribute_id", flat=True
            )
        )

    def get_nick(self, key=None, category=None, value=None, strvalue=None, obj=None):
        """
        Get a nick, in parallel to `get_attribute`.

        Attrs:
            key (str, optional): The nicks's key to search for
            category (str, optional): The category of the nicks(s) to search for.
            value (str, optional): The attribute value to search for. Note that this
                is not a very efficient operation since it will query for a pickled
                entity. Mutually exclusive to `strvalue`.
            strvalue (str, optional): The str-value to search for. Most Attributes
                will not have strvalue set. This is mutually exclusive to the `value`
                keyword and will take precedence if given.
            obj (Object, optional): On which object the Attribute to search for is.

        Returns:
            nicks (list): The matching Nicks.

        """
        return self.get_attribute(
            key=key, category=category, value=value, strvalue=strvalue, obj=obj
        )

    def get_by_attribute(self, key=None, category=None, value=None, strvalue=None, attrtype=None):
        """
        Return objects having attributes with the given key, category,
        value, strvalue or combination of those criteria.

        Args:
            key (str, optional): The attribute's key to search for
            category (str, optional): The category of the attribute
                to search for.
            value (str, optional): The attribute value to search for.
                Note that this is not a very efficient operation since it
                will query for a pickled entity. Mutually exclusive to
                `strvalue`.
            strvalue (str, optional): The str-value to search for.
                Most Attributes will not have strvalue set. This is
                mutually exclusive to the `value` keyword and will take
                precedence if given.
            attrype (str, optional): An attribute-type to search for.
                By default this is either `None` (normal Attributes) or
                `"nick"`.

        Returns:
            obj (list): Objects having the matching Attributes.

        """
        dbmodel = self.model.__dbclass__.__name__.lower()
        query = [("db_attributes__db_attrtype", attrtype), ("db_attributes__db_model", dbmodel)]
        if key:
            query.append(("db_attributes__db_key", key))
        if category:
            query.append(("db_attributes__db_category", category))
        if strvalue:
            query.append(("db_attributes__db_strvalue", strvalue))
        elif value:
            # strvalue and value are mutually exclusive
            query.append(("db_attributes__db_value", value))
        return self.filter(**dict(query))

    def get_by_nick(self, key=None, nick=None, category="inputline"):
        """
        Get object based on its key or nick.

        Args:
            key (str, optional): The attribute's key to search for
            nick (str, optional): The nickname to search for
            category (str, optional): The category of the nick
                to search for.

        Returns:
            obj (list): Objects having the matching Nicks.

        """
        return self.get_by_attribute(key=key, category=category, strvalue=nick, attrtype="nick")

    # Tag manager methods

    def get_tag(self, key=None, category=None, obj=None, tagtype=None, global_search=False):
        """
        Return Tag objects by key, by category, by object (it is
        stored on) or with a combination of those criteria.

        Attrs:
            key (str, optional): The Tag's key to search for
            category (str, optional): The Tag of the attribute(s)
                to search for.
            obj (Object, optional): On which object the Tag to
                search for is.
            tagtype (str, optional): One of None (normal tags),
                "alias" or "permission"
            global_search (bool, optional): Include all possible tags,
                not just tags on this object

        Returns:
            tag (list): The matching Tags.

        """
        global _Tag
        if not _Tag:
            from evennia.typeclasses.models import Tag as _Tag
        dbmodel = self.model.__dbclass__.__name__.lower()
        if global_search:
            # search all tags using the Tag model
            query = [("db_tagtype", tagtype), ("db_model", dbmodel)]
            if obj:
                query.append(("id", obj.id))
            if key:
                query.append(("db_key", key))
            if category:
                query.append(("db_category", category))
            return _Tag.objects.filter(**dict(query))
        else:
            # search only among tags stored on on this model
            query = [("tag__db_tagtype", tagtype), ("tag__db_model", dbmodel)]
            if obj:
                query.append(("%s__id" % self.model.__name__.lower(), obj.id))
            if key:
                query.append(("tag__db_key", key))
            if category:
                query.append(("tag__db_category", category))
            return Tag.objects.filter(
                pk__in=self.model.db_tags.through.objects.filter(**dict(query)).values_list(
                    "tag_id", flat=True
                )
            )

    def get_permission(self, key=None, category=None, obj=None):
        """
        Get a permission from the database.

        Args:
            key (str, optional): The permission's identifier.
            category (str, optional): The permission's category.
            obj (object, optional): The object on which this Tag is set.

        Returns:
            permission (list): Permission objects.

        """
        return self.get_tag(key=key, category=category, obj=obj, tagtype="permission")

    def get_alias(self, key=None, category=None, obj=None):
        """
        Get an alias from the database.

        Args:
            key (str, optional): The permission's identifier.
            category (str, optional): The permission's category.
            obj (object, optional): The object on which this Tag is set.

        Returns:
            alias (list): Alias objects.

        """
        return self.get_tag(key=key, category=category, obj=obj, tagtype="alias")

    def get_by_tag(self, key=None, category=None, tagtype=None):
        """
        Return objects having tags with a given key or category or combination of the two.
        Also accepts multiple tags/category/tagtype

        Args:
            key (str or list, optional): Tag key or list of keys. Not case sensitive.
            category (str or list, optional): Tag category. Not case sensitive. If `key` is
                a list, a single category can either apply to all keys in that list or this
                must be a list matching the `key` list element by element. If no `key` is given,
                all objects with tags of this category are returned.
            tagtype (str, optional): 'type' of Tag, by default
                this is either `None` (a normal Tag), `alias` or
                `permission`. This always apply to all queried tags.

        Returns:
            objects (list): Objects with matching tag.

        Raises:
            IndexError: If `key` and `category` are both lists and `category` is shorter
                than `key`.

        """
        if not (key or category):
            return []

        keys = make_iter(key) if key else []
        categories = make_iter(category) if category else []
        n_keys = len(keys)
        n_categories = len(categories)

        dbmodel = self.model.__dbclass__.__name__.lower()
        query = (
            self.filter(db_tags__db_tagtype__iexact=tagtype, db_tags__db_model__iexact=dbmodel)
            .distinct()
            .order_by("id")
        )

        if n_keys > 0:
            # keys and/or categories given
            if n_categories == 0:
                categories = [None for _ in range(n_keys)]
            elif n_categories == 1 and n_keys > 1:
                cat = categories[0]
                categories = [cat for _ in range(n_keys)]
            elif 1 < n_categories < n_keys:
                raise IndexError(
                    "get_by_tag needs a single category or a list of categories "
                    "the same length as the list of tags."
                )
            for ikey, key in enumerate(keys):
                query = query.filter(
                    db_tags__db_key__iexact=key, db_tags__db_category__iexact=categories[ikey]
                )
        else:
            # only one or more categories given
            for category in categories:
                query = query.filter(db_tags__db_category__iexact=category)

        return query

    def get_by_permission(self, key=None, category=None):
        """
        Return objects having permissions with a given key or category or
        combination of the two.

        Args:
            key (str, optional): Permissions key. Not case sensitive.
            category (str, optional): Permission category. Not case sensitive.
        Returns:
            objects (list): Objects with matching permission.
        """
        return self.get_by_tag(key=key, category=category, tagtype="permission")

    def get_by_alias(self, key=None, category=None):
        """
        Return objects having aliases with a given key or category or
        combination of the two.

        Args:
            key (str, optional): Alias key. Not case sensitive.
            category (str, optional): Alias category. Not case sensitive.
        Returns:
            objects (list): Objects with matching alias.
        """
        return self.get_by_tag(key=key, category=category, tagtype="alias")

    def create_tag(self, key=None, category=None, data=None, tagtype=None):
        """
        Create a new Tag of the base type associated with this
        object.  This makes sure to create case-insensitive tags.
        If the exact same tag configuration (key+category+tagtype+dbmodel)
        exists on the model, a new tag will not be created, but an old
        one returned.


        Args:
            key (str, optional): Tag key. Not case sensitive.
            category (str, optional): Tag category. Not case sensitive.
            data (str, optional): Extra information about the tag.
            tagtype (str or None, optional): 'type' of Tag, by default
                this is either `None` (a normal Tag), `alias` or
                `permission`.
        Notes:
            The `data` field is not part of the uniqueness of the tag:
            Setting `data` on an existing tag will overwrite the old
            data field. It is intended only as a way to carry
            information about the tag (like a help text), not to carry
            any information about the tagged objects themselves.

        """
        data = str(data) if data is not None else None
        # try to get old tag

        dbmodel = self.model.__dbclass__.__name__.lower()
        tag = self.get_tag(key=key, category=category, tagtype=tagtype, global_search=True)
        if tag and data is not None:
            # get tag from list returned by get_tag
            tag = tag[0]
            # overload data on tag
            tag.db_data = data
            tag.save()
        elif not tag:
            # create a new tag
            global _Tag
            if not _Tag:
                from evennia.typeclasses.models import Tag as _Tag
            tag = _Tag.objects.create(
                db_key=key.strip().lower() if key is not None else None,
                db_category=category.strip().lower() if category and key is not None else None,
                db_data=data,
                db_model=dbmodel,
                db_tagtype=tagtype.strip().lower() if tagtype is not None else None,
            )
            tag.save()
        return make_iter(tag)[0]

    def dbref(self, dbref, reqhash=True):
        """
        Determing if input is a valid dbref.

        Args:
            dbref (str or int): A possible dbref.
            reqhash (bool, optional): If the "#" is required for this
                to be considered a valid hash.

        Returns:
            dbref (int or None): The integer part of the dbref.

        Notes:
            Valid forms of dbref (database reference number) are
            either a string '#N' or an integer N.

        """
        if reqhash and not (isinstance(dbref, str) and dbref.startswith("#")):
            return None
        if isinstance(dbref, str):
            dbref = dbref.lstrip("#")
        try:
            if int(dbref) < 0:
                return None
        except Exception:
            return None
        return dbref

    def get_id(self, dbref):
        """
        Find object with given dbref.

        Args:
            dbref (str or int): The id to search for.

        Returns:
            object (TypedObject): The matched object.

        """
        dbref = self.dbref(dbref, reqhash=False)
        try:
            return self.get(id=dbref)
        except self.model.DoesNotExist:
            pass
        return None

    def dbref_search(self, dbref):
        """
        Alias to get_id.

        Args:
            dbref (str or int): The id to search for.

        Returns:
            object (TypedObject): The matched object.

        """
        return self.get_id(dbref)

    def get_dbref_range(self, min_dbref=None, max_dbref=None):
        """
        Get objects within a certain range of dbrefs.

        Args:
            min_dbref (int): Start of dbref range.
            max_dbref (int): End of dbref range (inclusive)

        Returns:
            objects (list): TypedObjects with dbrefs within
                the given dbref ranges.

        """
        retval = super().all()
        if min_dbref is not None:
            retval = retval.filter(id__gte=self.dbref(min_dbref, reqhash=False))
        if max_dbref is not None:
            retval = retval.filter(id__lte=self.dbref(max_dbref, reqhash=False))
        return retval

    def object_totals(self):
        """
        Get info about database statistics.

        Returns:
            census (dict): A dictionary `{typeclass_path: number, ...}` with
                all the typeclasses active in-game as well as the number
                of such objects defined (i.e. the number of database
                object having that typeclass set on themselves).

        """
        dbtotals = {}
        typeclass_paths = set(self.values_list("db_typeclass_path", flat=True))
        for typeclass_path in typeclass_paths:
            dbtotals[typeclass_path] = self.filter(db_typeclass_path=typeclass_path).count()
        return dbtotals

    def typeclass_search(self, typeclass, include_children=False, include_parents=False):
        """
        Searches through all objects returning those which has a
        certain typeclass. If location is set, limit search to objects
        in that location.

        Args:
            typeclass (str or class): A typeclass class or a python path to a typeclass.
            include_children (bool, optional): Return objects with
                given typeclass *and* all children inheriting from this
                typeclass. Mutuall exclusive to `include_parents`.
            include_parents (bool, optional): Return objects with
                given typeclass *and* all parents to this typeclass.
                Mutually exclusive to `include_children`.

        Returns:
            objects (list): The objects found with the given typeclasses.

        """

        if callable(typeclass):
            cls = typeclass.__class__
            typeclass = "%s.%s" % (cls.__module__, cls.__name__)
        elif not isinstance(typeclass, str) and hasattr(typeclass, "path"):
            typeclass = typeclass.path

        # query objects of exact typeclass
        query = Q(db_typeclass_path__exact=typeclass)

        if include_children:
            # build requests for child typeclass objects
            clsmodule, clsname = typeclass.rsplit(".", 1)
            cls = variable_from_module(clsmodule, clsname)
            subclasses = cls.__subclasses__()
            if subclasses:
                for child in (child for child in subclasses if hasattr(child, "path")):
                    query = query | Q(db_typeclass_path__exact=child.path)
        elif include_parents:
            # build requests for parent typeclass objects
            clsmodule, clsname = typeclass.rsplit(".", 1)
            cls = variable_from_module(clsmodule, clsname)
            parents = cls.__mro__
            if parents:
                for parent in (parent for parent in parents if hasattr(parent, "path")):
                    query = query | Q(db_typeclass_path__exact=parent.path)
        # actually query the database
        return self.filter(query)


class TypeclassManager(TypedObjectManager):
    """
    Manager for the typeclasses. The main purpose of this manager is
    to limit database queries to the given typeclass despite all
    typeclasses technically being defined in the same core database
    model.

    """

    # object-manager methods
    def smart_search(self, query):
        """
        Search by supplying a string with optional extra search criteria to aid the query.

        Args:
            query (str): A search criteria that accepts extra search criteria on the

                following forms: [key|alias|#dbref...] [tag==<tagstr>[:category]...] [attr==<key>:<value>:category...]
                                          "                !=             "               !=      "
        Returns:
            matches (queryset): A queryset result matching all queries exactly. If wanting to use spaces or
            ==, != in tags or attributes, enclose them in quotes.

        Note:
            The flexibility of this method is limited by the input line format. Tag/attribute
            matching only works for matching primitives.  For even more complex queries, such as
            'in' operations or object field matching, use the full django query language.

        """
        # shlex splits by spaces unless escaped by quotes
        querysplit = shlex.split(query)
        queries, plustags, plusattrs, negtags, negattrs = [], [], [], [], []
        for ipart, part in enumerate(querysplit):
            key, rest = part, ""
            if ":" in part:
                key, rest = part.split(":", 1)
            # tags are on the form tag or tag:category
            if key.startswith("tag=="):
                plustags.append((key[5:], rest))
                continue
            elif key.startswith("tag!="):
                negtags.append((key[5:], rest))
                continue
            # attrs are on the form attr:value or attr:value:category
            elif rest:
                value, category = rest, ""
                if ":" in rest:
                    value, category = rest.split(":", 1)
                if key.startswith("attr=="):
                    plusattrs.append((key[7:], value, category))
                    continue
                elif key.startswith("attr!="):
                    negattrs.append((key[7:], value, category))
                    continue
            # if we get here, we are entering a key search criterion which
            # we assume is one word.
            queries.append(part)
        # build query from components
        query = " ".join(queries)
        # TODO

    def get(self, *args, **kwargs):
        """
        Overload the standard get. This will limit itself to only
        return the current typeclass.

        Args:
            args (any): These are passed on as arguments to the default
                django get method.
        Kwargs:
            kwargs (any): These are passed on as normal arguments
                to the default django get method
        Returns:
            object (object): The object found.

        Raises:
            ObjectNotFound: The exact name of this exception depends
                on the model base used.

        """
        kwargs.update({"db_typeclass_path": self.model.path})
        return super().get(**kwargs)

    def filter(self, *args, **kwargs):
        """
        Overload of the standard filter function. This filter will
        limit itself to only the current typeclass.

        Args:
            args (any): These are passed on as arguments to the default
                django filter method.
        Kwargs:
            kwargs (any): These are passed on as normal arguments
                to the default django filter method.
        Returns:
            objects (queryset): The objects found.

        """
        kwargs.update({"db_typeclass_path": self.model.path})
        return super().filter(*args, **kwargs)

    def all(self):
        """
        Overload method to return all matches, filtering for typeclass.

        Returns:
            objects (queryset): The objects found.

        """
        return super().all().filter(db_typeclass_path=self.model.path)

    def first(self):
        """
        Overload method to return first match, filtering for typeclass.

        Returns:
            object (object): The object found.

        Raises:
            ObjectNotFound: The exact name of this exception depends
                on the model base used.

        """
        return super().filter(db_typeclass_path=self.model.path).first()

    def last(self):
        """
        Overload method to return last match, filtering for typeclass.

        Returns:
            object (object): The object found.

        Raises:
            ObjectNotFound: The exact name of this exception depends
                on the model base used.

        """
        return super().filter(db_typeclass_path=self.model.path).last()

    def count(self):
        """
        Overload method to return number of matches, filtering for typeclass.

        Returns:
            integer : Number of objects found.

        """
        return super().filter(db_typeclass_path=self.model.path).count()

    def annotate(self, *args, **kwargs):
        """
        Overload annotate method to filter on typeclass before annotating.
        Args:
            *args (any): Positional arguments passed along to queryset annotate method.
            **kwargs (any): Keyword arguments passed along to queryset annotate method.

        Returns:
            Annotated queryset.
        """
        return (
            super(TypeclassManager, self)
            .filter(db_typeclass_path=self.model.path)
            .annotate(*args, **kwargs)
        )

    def values(self, *args, **kwargs):
        """
        Overload values method to filter on typeclass first.
        Args:
            *args (any): Positional arguments passed along to values method.
            **kwargs (any): Keyword arguments passed along to values method.

        Returns:
            Queryset of values dictionaries, just filtered by typeclass first.
        """
        return (
            super(TypeclassManager, self)
            .filter(db_typeclass_path=self.model.path)
            .values(*args, **kwargs)
        )

    def values_list(self, *args, **kwargs):
        """
        Overload values method to filter on typeclass first.
        Args:
            *args (any): Positional arguments passed along to values_list method.
            **kwargs (any): Keyword arguments passed along to values_list method.

        Returns:
            Queryset of value_list tuples, just filtered by typeclass first.
        """
        return (
            super(TypeclassManager, self)
            .filter(db_typeclass_path=self.model.path)
            .values_list(*args, **kwargs)
        )

    def _get_subclasses(self, cls):
        """
        Recursively get all subclasses to a class.

        Args:
            cls (classoject): A class to get subclasses from.
        """
        all_subclasses = cls.__subclasses__()
        for subclass in all_subclasses:
            all_subclasses.extend(self._get_subclasses(subclass))
        return all_subclasses

    def get_family(self, **kwargs):
        """
        Variation of get that not only returns the current typeclass
        but also all subclasses of that typeclass.

        Kwargs:
            kwargs (any): These are passed on as normal arguments
                to the default django get method.
        Returns:
            objects (list): The objects found.

        Raises:
            ObjectNotFound: The exact name of this exception depends
                on the model base used.

        """
        paths = [self.model.path] + [
            "%s.%s" % (cls.__module__, cls.__name__) for cls in self._get_subclasses(self.model)
        ]
        kwargs.update({"db_typeclass_path__in": paths})
        return super().get(**kwargs)

    def filter_family(self, *args, **kwargs):
        """
        Variation of filter that allows results both from typeclass
        and from subclasses of typeclass

        Args:
            args (any): These are passed on as arguments to the default
                django filter method.
        Kwargs:
            kwargs (any): These are passed on as normal arguments
                to the default django filter method.
        Returns:
            objects (list): The objects found.

        """
        # query, including all subclasses
        paths = [self.model.path] + [
            "%s.%s" % (cls.__module__, cls.__name__) for cls in self._get_subclasses(self.model)
        ]
        kwargs.update({"db_typeclass_path__in": paths})
        return super().filter(*args, **kwargs)

    def all_family(self):
        """
        Return all matches, allowing matches from all subclasses of
        the typeclass.

        Returns:
            objects (list): The objects found.

        """
        paths = [self.model.path] + [
            "%s.%s" % (cls.__module__, cls.__name__) for cls in self._get_subclasses(self.model)
        ]
        return super().all().filter(db_typeclass_path__in=paths)
