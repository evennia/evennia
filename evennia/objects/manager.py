"""
Custom manager for Objects.
"""
import re
from itertools import chain
from django.db.models import Q
from django.conf import settings
from django.db.models.fields import exceptions
from evennia.typeclasses.managers import TypedObjectManager, TypeclassManager
from evennia.utils.utils import is_iter, make_iter, string_partial_matching

__all__ = ("ObjectManager",)
_GA = object.__getattribute__

# delayed import
_ATTR = None

_MULTIMATCH_REGEX = re.compile(settings.SEARCH_MULTIMATCH_REGEX, re.I + re.U)

# Try to use a custom way to parse id-tagged multimatches.


class ObjectDBManager(TypedObjectManager):
    """
    This ObjectManager implements methods for searching
    and manipulating Objects directly from the database.

    Evennia-specific search methods (will return Typeclasses or
    lists of Typeclasses, whereas Django-general methods will return
    Querysets or database objects).

    dbref (converter)
    get_id (alias: dbref_search)
    get_dbref_range
    object_totals
    typeclass_search
    get_object_with_account
    get_objs_with_key_and_typeclass
    get_objs_with_attr
    get_objs_with_attr_match
    get_objs_with_db_property
    get_objs_with_db_property_match
    get_objs_with_key_or_alias
    get_contents
    object_search (interface to many of the above methods,
                   equivalent to evennia.search_object)
    copy_object

    """

    #
    # ObjectManager Get methods
    #

    # account related

    def get_object_with_account(self, ostring, exact=True, candidates=None):
        """
        Search for an object based on its account's name or dbref.

        Args:
            ostring (str or int): Search criterion or dbref. Searching
                for an account is sometimes initiated by appending an `*` to
                the beginning of the search criterion (e.g. in
                local_and_global_search). This is stripped here.
            exact (bool, optional): Require an exact account match.
            candidates (list, optional): Only search among this list of possible
                object candidates.

        Return:
            match (query): Matching query.

        """
        ostring = str(ostring).lstrip("*")
        # simplest case - search by dbref
        dbref = self.dbref(ostring)
        if dbref:
            try:
                return self.get(db_account__id=dbref)
            except self.model.DoesNotExist:
                pass

        # not a dbref. Search by name.
        cand_restriction = (
            candidates is not None
            and Q(pk__in=[_GA(obj, "id") for obj in make_iter(candidates) if obj])
            or Q()
        )
        if exact:
            return self.filter(cand_restriction & Q(db_account__username__iexact=ostring)).order_by(
                "id"
            )
        else:  # fuzzy matching
            obj_cands = self.select_related().filter(
                cand_restriction & Q(db_account__username__istartswith=ostring)
            )
            acct_cands = [obj.account for obj in obj_cands]

            if obj_cands:
                index_matches = string_partial_matching(
                    [acct.key for acct in acct_cands], ostring, ret_index=True
                )
                acct_cands = [acct_cands[i].id for i in index_matches]
                return obj_cands.filter(db_account__id__in=acct_cands).order_by("id")

    def get_objs_with_key_and_typeclass(self, oname, otypeclass_path, candidates=None):
        """
        Returns objects based on simultaneous key and typeclass match.

        Args:
            oname (str): Object key to search for
            otypeclass_path (str): Full Python path to tyepclass to search for
            candidates (list, optional): Only match among the given list of candidates.

        Returns:
            matches (query): The matching objects.
        """
        cand_restriction = (
            candidates is not None
            and Q(pk__in=[_GA(obj, "id") for obj in make_iter(candidates) if obj])
            or Q()
        )
        return self.filter(
            cand_restriction & Q(db_key__iexact=oname, db_typeclass_path__exact=otypeclass_path)
        ).order_by("id")

    # attr/property related

    def get_objs_with_attr(self, attribute_name, candidates=None):
        """
        Get objects based on having a certain Attribute defined.

        Args:
            attribute_name (str): Attribute name to search for.
            candidates (list, optional): Only match among the given list of object
                candidates.

        Returns:
            matches (query):  All objects having the given attribute_name defined at all.

        """
        cand_restriction = (
            candidates is not None and Q(id__in=[obj.id for obj in candidates]) or Q()
        )
        return self.filter(cand_restriction & Q(db_attributes__db_key=attribute_name)).order_by(
            "id"
        )

    def get_objs_with_attr_value(
        self, attribute_name, attribute_value, candidates=None, typeclasses=None
    ):
        """
        Get all objects having the given attrname set to the given value.

        Args:
            attribute_name (str): Attribute key to search for.
            attribute_value (str):  Attribute value to search for.
            candidates (list, optional): Candidate objects to limit search to.
            typeclasses (list, optional): Python pats to restrict matches with.

        Returns:
            matches (list): Objects fullfilling both the `attribute_name` and
            `attribute_value` criterions.

        Notes:
            This uses the Attribute's PickledField to transparently search the database by matching
            the internal representation. This is reasonably effective but since Attribute values
            cannot be indexed, searching by Attribute key is to be preferred whenever possible.

        """
        cand_restriction = (
            candidates is not None
            and Q(pk__in=[_GA(obj, "id") for obj in make_iter(candidates) if obj])
            or Q()
        )
        type_restriction = typeclasses and Q(db_typeclass_path__in=make_iter(typeclasses)) or Q()

        # This doesn't work if attribute_value is an object. Workaround below

        if isinstance(attribute_value, (str, int, float, bool)):
            return self.filter(
                cand_restriction
                & type_restriction
                & Q(db_attributes__db_key=attribute_name, db_attributes__db_value=attribute_value)
            ).order_by("id")
        else:
            # We must loop for safety since the referenced lookup gives deepcopy error if attribute value is an object.
            global _ATTR
            if not _ATTR:
                from evennia.typeclasses.models import Attribute as _ATTR
            cands = list(
                self.filter(
                    cand_restriction & type_restriction & Q(db_attributes__db_key=attribute_name)
                )
            )
            results = [
                attr.objectdb_set.all()
                for attr in _ATTR.objects.filter(
                    objectdb__in=cands, db_value=attribute_value
                ).order_by("id")
            ]
            return chain(*results)

    def get_objs_with_db_property(self, property_name, candidates=None):
        """
        Get all objects having a given db field property.

        Args:
            property_name (str): The name of the field to match for.
            candidates (list, optional): Only search among th egiven candidates.

        Returns:
            matches (list): The found matches.

        """
        property_name = "db_%s" % property_name.lstrip("db_")
        cand_restriction = (
            candidates is not None
            and Q(pk__in=[_GA(obj, "id") for obj in make_iter(candidates) if obj])
            or Q()
        )
        querykwargs = {property_name: None}
        try:
            return list(self.filter(cand_restriction).exclude(Q(**querykwargs)).order_by("id"))
        except exceptions.FieldError:
            return []

    def get_objs_with_db_property_value(
        self, property_name, property_value, candidates=None, typeclasses=None
    ):
        """
        Get objects with a specific field name and value.

        Args:
            property_name (str): Field name to search for.
            property_value (any): Value required for field with `property_name` to have.
            candidates (list, optional): List of objects to limit search to.
            typeclasses (list, optional): List of typeclass-path strings to restrict matches with

        """
        if isinstance(property_name, str):
            if not property_name.startswith("db_"):
                property_name = "db_%s" % property_name
        querykwargs = {property_name: property_value}
        cand_restriction = (
            candidates is not None
            and Q(pk__in=[_GA(obj, "id") for obj in make_iter(candidates) if obj])
            or Q()
        )
        type_restriction = typeclasses and Q(db_typeclass_path__in=make_iter(typeclasses)) or Q()
        try:
            return list(
                self.filter(cand_restriction & type_restriction & Q(**querykwargs)).order_by("id")
            )
        except exceptions.FieldError:
            return []
        except ValueError:
            from evennia.utils import logger

            logger.log_err(
                "The property '%s' does not support search criteria of the type %s."
                % (property_name, type(property_value))
            )
            return []

    def get_contents(self, location, excludeobj=None):
        """
        Get all objects that has a location set to this one.

        Args:
            location (Object): Where to get contents from.
            excludeobj (Object or list, optional): One or more objects
                to exclude from the match.

        Returns:
            contents (list): Matching contents, without excludeobj, if given.
        """
        exclude_restriction = (
            Q(pk__in=[_GA(obj, "id") for obj in make_iter(excludeobj)]) if excludeobj else Q()
        )
        return self.filter(db_location=location).exclude(exclude_restriction).order_by("id")

    def get_objs_with_key_or_alias(self, ostring, exact=True, candidates=None, typeclasses=None):
        """
        Args:
            ostring (str): A search criterion.
            exact (bool, optional): Require exact match of ostring
                (still case-insensitive). If `False`, will do fuzzy matching
                using `evennia.utils.utils.string_partial_matching` algorithm.
            candidates (list): Only match among these candidates.
            typeclasses (list): Only match objects with typeclasses having thess path strings.

        Returns:
            matches (list): A list of matches of length 0, 1 or more.
        """
        if not isinstance(ostring, str):
            if hasattr(ostring, "key"):
                ostring = ostring.key
            else:
                return []
        if is_iter(candidates) and not len(candidates):
            # if candidates is an empty iterable there can be no matches
            # Exit early.
            return []

        # build query objects
        candidates_id = [_GA(obj, "id") for obj in make_iter(candidates) if obj]
        cand_restriction = candidates is not None and Q(pk__in=candidates_id) or Q()
        type_restriction = typeclasses and Q(db_typeclass_path__in=make_iter(typeclasses)) or Q()
        if exact:
            # exact match - do direct search
            return (
                (
                    self.filter(
                        cand_restriction
                        & type_restriction
                        & (
                            Q(db_key__iexact=ostring)
                            | Q(db_tags__db_key__iexact=ostring)
                            & Q(db_tags__db_tagtype__iexact="alias")
                        )
                    )
                )
                .distinct()
                .order_by("id")
            )
        elif candidates:
            # fuzzy with candidates
            search_candidates = (
                self.filter(cand_restriction & type_restriction).distinct().order_by("id")
            )
        else:
            # fuzzy without supplied candidates - we select our own candidates
            search_candidates = (
                self.filter(
                    type_restriction
                    & (Q(db_key__istartswith=ostring) | Q(db_tags__db_key__istartswith=ostring))
                )
                .distinct()
                .order_by("id")
            )
        # fuzzy matching
        key_strings = search_candidates.values_list("db_key", flat=True).order_by("id")

        index_matches = string_partial_matching(key_strings, ostring, ret_index=True)
        if index_matches:
            # a match by key
            return [obj for ind, obj in enumerate(search_candidates) if ind in index_matches]
        else:
            # match by alias rather than by key
            search_candidates = search_candidates.filter(
                db_tags__db_tagtype__iexact="alias", db_tags__db_key__icontains=ostring
            ).distinct()
            alias_strings = []
            alias_candidates = []
            # TODO create the alias_strings and alias_candidates lists more efficiently?
            for candidate in search_candidates:
                for alias in candidate.aliases.all():
                    alias_strings.append(alias)
                    alias_candidates.append(candidate)
            index_matches = string_partial_matching(alias_strings, ostring, ret_index=True)
            if index_matches:
                # it's possible to have multiple matches to the same Object, we must weed those out
                return list({alias_candidates[ind] for ind in index_matches})
            return []

    # main search methods and helper functions

    def search_object(
        self,
        searchdata,
        attribute_name=None,
        typeclass=None,
        candidates=None,
        exact=True,
        use_dbref=True,
    ):
        """
        Search as an object globally or in a list of candidates and
        return results. The result is always an Object. Always returns
        a list.

        Args:
            searchdata (str or Object): The entity to match for. This is
                usually a key string but may also be an object itself.
                By default (if no `attribute_name` is set), this will
                search `object.key` and `object.aliases` in order.
                Can also be on the form #dbref, which will (if
                `exact=True`) be matched against primary key.
            attribute_name (str): Use this named Attribute to
                match searchdata against, instead of the defaults. If
                this is the name of a database field (with or without
                the `db_` prefix), that will be matched too.
            typeclass (str or TypeClass): restrict matches to objects
                having this typeclass. This will help speed up global
                searches.
            candidates (list): If supplied, search will
                only be performed among the candidates in this list. A
                common list of candidates is the contents of the
                current location searched.
            exact (bool): Match names/aliases exactly or partially.
                Partial matching matches the beginning of words in the
                names/aliases, using a matching routine to separate
                multiple matches in names with multiple components (so
                "bi sw" will match "Big sword"). Since this is more
                expensive than exact matching, it is recommended to be
                used together with the `candidates` keyword to limit the
                number of possibilities. This value has no meaning if
                searching for attributes/properties.
            use_dbref (bool): If False, bypass direct lookup of a string
                on the form #dbref and treat it like any string.

        Returns:
            matches (list): Matching objects

        """

        def _searcher(searchdata, candidates, typeclass, exact=False):
            """
            Helper method for searching objects. `typeclass` is only used
            for global searching (no candidates)
            """
            if attribute_name:
                # attribute/property search (always exact).
                matches = self.get_objs_with_db_property_value(
                    attribute_name, searchdata, candidates=candidates, typeclasses=typeclass
                )
                if matches:
                    return matches
                return self.get_objs_with_attr_value(
                    attribute_name, searchdata, candidates=candidates, typeclasses=typeclass
                )
            else:
                # normal key/alias search
                return self.get_objs_with_key_or_alias(
                    searchdata, exact=exact, candidates=candidates, typeclasses=typeclass
                )

        if not searchdata and searchdata != 0:
            return []

        if typeclass:
            # typeclass may also be a list
            typeclasses = make_iter(typeclass)
            for i, typeclass in enumerate(make_iter(typeclasses)):
                if callable(typeclass):
                    typeclasses[i] = "%s.%s" % (typeclass.__module__, typeclass.__name__)
                else:
                    typeclasses[i] = "%s" % typeclass
            typeclass = typeclasses

        if candidates is not None:
            if not candidates:
                # candidates is the empty list. This should mean no matches can ever be acquired.
                return []
            # Convenience check to make sure candidates are really dbobjs
            candidates = [cand for cand in make_iter(candidates) if cand]
            if typeclass:
                candidates = [
                    cand for cand in candidates if _GA(cand, "db_typeclass_path") in typeclass
                ]

        dbref = not attribute_name and exact and use_dbref and self.dbref(searchdata)
        if dbref:
            # Easiest case - dbref matching (always exact)
            dbref_match = self.dbref_search(dbref)
            if dbref_match:
                if not candidates or dbref_match in candidates:
                    return [dbref_match]
                else:
                    return []

        # Search through all possibilities.
        match_number = None
        # always run first check exact - we don't want partial matches
        # if on the form of 1-keyword etc.
        matches = _searcher(searchdata, candidates, typeclass, exact=True)
        if not matches:
            # no matches found - check if we are dealing with N-keyword
            # query - if so, strip it.
            match = _MULTIMATCH_REGEX.match(str(searchdata))
            match_number = None
            if match:
                # strips the number
                match_number, searchdata = match.group("number"), match.group("name")
                match_number = int(match_number) - 1
                match_number = match_number if match_number >= 0 else None
            if match_number is not None or not exact:
                # run search again, with the exactness set by call
                matches = _searcher(searchdata, candidates, typeclass, exact=exact)

        # deal with result
        if len(matches) > 1 and match_number is not None:
            # multiple matches, but a number was given to separate them
            try:
                matches = [matches[match_number]]
            except IndexError:
                # match number not matching anything
                pass
        # return a list (possibly empty)
        return matches

    # alias for backwards compatibility
    object_search = search_object
    search = search_object

    #
    # ObjectManager Copy method

    def copy_object(
        self,
        original_object,
        new_key=None,
        new_location=None,
        new_home=None,
        new_permissions=None,
        new_locks=None,
        new_aliases=None,
        new_destination=None,
    ):
        """
        Create and return a new object as a copy of the original object. All
        will be identical to the original except for the arguments given
        specifically to this method. Object contents will not be copied.

        Args:
            original_object (Object): The object to make a copy from.
            new_key (str, optional): Name of the copy, if different
                from the original.
            new_location (Object, optional): Alternate location.
            new_home (Object, optional): Change the home location
            new_aliases (list, optional): Give alternate object
                aliases as a list of strings.
            new_destination (Object, optional): Used only by exits.

        Returns:
            copy (Object or None): The copy of `original_object`,
                optionally modified as per the ingoing keyword
                arguments.  `None` if an error was encountered.

        """

        # get all the object's stats
        typeclass_path = original_object.typeclass_path
        if not new_key:
            new_key = original_object.key
        if not new_location:
            new_location = original_object.location
        if not new_home:
            new_home = original_object.home
        if not new_aliases:
            new_aliases = original_object.aliases.all()
        if not new_locks:
            new_locks = original_object.db_lock_storage
        if not new_permissions:
            new_permissions = original_object.permissions.all()
        if not new_destination:
            new_destination = original_object.destination

        # create new object
        from evennia.utils import create
        from evennia.scripts.models import ScriptDB

        new_object = create.create_object(
            typeclass_path,
            key=new_key,
            location=new_location,
            home=new_home,
            permissions=new_permissions,
            locks=new_locks,
            aliases=new_aliases,
            destination=new_destination,
        )
        if not new_object:
            return None

        # copy over all attributes from old to new.
        for attr in original_object.attributes.all():
            new_object.attributes.add(attr.key, attr.value)

        # copy over all cmdsets, if any
        for icmdset, cmdset in enumerate(original_object.cmdset.all()):
            if icmdset == 0:
                new_object.cmdset.add_default(cmdset)
            else:
                new_object.cmdset.add(cmdset)

        # copy over all scripts, if any
        for script in original_object.scripts.all():
            ScriptDB.objects.copy_script(script, new_obj=new_object)

        # copy over all tags, if any
        for tag in original_object.tags.get(return_tagobj=True, return_list=True):
            new_object.tags.add(tag=tag.db_key, category=tag.db_category, data=tag.db_data)

        return new_object

    def clear_all_sessids(self):
        """
        Clear the db_sessid field of all objects having also the
        db_account field set.
        """
        self.filter(db_sessid__isnull=False).update(db_sessid=None)


class ObjectManager(ObjectDBManager, TypeclassManager):
    pass
