"""
This module defines the basic `DefaultObject` and its children
`DefaultCharacter`, `DefaultAccount`, `DefaultRoom` and `DefaultExit`.
These are the (default) starting points for all in-game visible
entities.

"""

import time
import typing
from collections import defaultdict

import evennia
import inflect
from django.conf import settings
from django.utils.translation import gettext as _
from evennia.commands import cmdset
from evennia.commands.cmdsethandler import CmdSetHandler
from evennia.objects.manager import ObjectManager
from evennia.objects.models import ObjectDB
from evennia.scripts.scripthandler import ScriptHandler
from evennia.server.signals import SIGNAL_EXIT_TRAVERSED
from evennia.typeclasses.attributes import ModelAttributeBackend, NickHandler
from evennia.typeclasses.models import TypeclassBase
from evennia.utils import ansi, create, funcparser, logger, search
from evennia.utils.utils import (
    class_from_module,
    compress_whitespace,
    dbref,
    is_iter,
    iter_to_str,
    lazy_property,
    make_iter,
    to_str,
    variable_from_module,
)

_INFLECT = inflect.engine()
_MULTISESSION_MODE = settings.MULTISESSION_MODE

_ScriptDB = None
_CMDHANDLER = None

_AT_SEARCH_RESULT = variable_from_module(*settings.SEARCH_AT_RESULT.rsplit(".", 1))
_COMMAND_DEFAULT_CLASS = class_from_module(settings.COMMAND_DEFAULT_CLASS)
# the sessid_max is based on the length of the db_sessid csv field (excluding commas)
_SESSID_MAX = 16 if _MULTISESSION_MODE in (1, 3) else 1

# init the actor-stance funcparser for msg_contents
_MSG_CONTENTS_PARSER = funcparser.FuncParser(funcparser.ACTOR_STANCE_CALLABLES)


class ObjectSessionHandler:
    """
    Handles the get/setting of the sessid comma-separated integer field

    """

    def __init__(self, obj):
        """
        Initializes the handler.

        Args:
            obj (DefaultObject): The object on which the handler is defined.

        """
        self.obj = obj
        self._sessid_cache = []
        self._recache()

    def _recache(self):
        self._sessid_cache = list(
            set(int(val) for val in (self.obj.db_sessid or "").split(",") if val)
        )
        if any(sessid for sessid in self._sessid_cache if sessid not in evennia.SESSION_HANDLER):
            # cache is out of sync with sessionhandler! Only retain the ones in the handler.
            self._sessid_cache = [
                sessid for sessid in self._sessid_cache if sessid in evennia.SESSION_HANDLER
            ]
            self.obj.db_sessid = ",".join(str(val) for val in self._sessid_cache)
            self.obj.save(update_fields=["db_sessid"])

    def get(self, sessid=None):
        """
        Get the sessions linked to this Object.

        Args:
            sessid (int, optional): A specific session id.

        Returns:
            list: The sessions connected to this object. If `sessid` is given,
                this is a list of one (or zero) elements.

        Notes:
            Aliased to `self.all()`.

        """

        if sessid:
            sessions = (
                [evennia.SESSION_HANDLER[sessid] if sessid in evennia.SESSION_HANDLER else None]
                if sessid in self._sessid_cache
                else []
            )
        else:
            sessions = [
                evennia.SESSION_HANDLER[ssid] if ssid in evennia.SESSION_HANDLER else None
                for ssid in self._sessid_cache
            ]
        if None in sessions:
            # this happens only if our cache has gone out of sync with the SessionHandler.
            self._recache()
            return self.get(sessid=sessid)
        return sessions

    def all(self):
        """
        Alias to get(), returning all sessions.

        Returns:
            list: All sessions.

        """
        return self.get()

    def add(self, session):
        """
        Add session to handler.

        Args:
            session (Session or int): Session or session id to add.

        Notes:
            We will only add a session/sessid if this actually also exists
            in the the core sessionhandler.

        """
        try:
            sessid = session.sessid
        except AttributeError:
            sessid = session

        sessid_cache = self._sessid_cache
        if sessid in evennia.SESSION_HANDLER and sessid not in sessid_cache:
            if len(sessid_cache) >= _SESSID_MAX:
                return
            sessid_cache.append(sessid)
            self.obj.db_sessid = ",".join(str(val) for val in sessid_cache)
            self.obj.save(update_fields=["db_sessid"])

    def remove(self, session):
        """
        Remove session from handler.

        Args:
            Session or int: Session or session id to remove.

        """
        try:
            sessid = session.sessid
        except AttributeError:
            sessid = session

        sessid_cache = self._sessid_cache
        if sessid in sessid_cache:
            sessid_cache.remove(sessid)
            self.obj.db_sessid = ",".join(str(val) for val in sessid_cache)
            self.obj.save(update_fields=["db_sessid"])

    def clear(self):
        """
        Clear all handled sessids.

        """
        self._sessid_cache = []
        self.obj.db_sessid = None
        self.obj.save(update_fields=["db_sessid"])

    def count(self):
        """
        Get amount of sessions connected.

        Returns:
            int: Number of sessions handled.

        """
        return len(self._sessid_cache)


#
# Base class to inherit from.


class DefaultObject(ObjectDB, metaclass=TypeclassBase):
    """
    This is the root Object typeclass, representing all entities that
    have an actual presence in-game. DefaultObjects generally have a
    location. They can also be manipulated and looked at. Game
    entities you define should inherit from DefaultObject at some distance.

    It is recommended to create children of this class using the
    `evennia.create_object()` function rather than to initialize the class
    directly - this will both set things up and efficiently save the object
    without `obj.save()` having to be called explicitly.

    Note: Check the autodocs for complete class members, this may not always
    be up-to date.

    * Base properties defined/available on all Objects

     key (string) - name of object
     name (string)- same as key
     dbref (int, read-only) - unique #id-number. Also "id" can be used.
     date_created (string) - time stamp of object creation

     account (Account) - controlling account (if any, only set together with
                       sessid below)
     sessid (int, read-only) - session id (if any, only set together with
                       account above). Use `sessions` handler to get the
                       Sessions directly.
     location (Object) - current location. Is None if this is a room
     home (Object) - safety start-location
     has_account (bool, read-only)- will only return *connected* accounts
     contents (list, read only) - returns all objects inside this object
     exits (list of Objects, read-only) - returns all exits from this
                       object, if any
     destination (Object) - only set if this object is an exit.
     is_superuser (bool, read-only) - True/False if this user is a superuser
     is_connected (bool, read-only) - True if this object is associated with
                            an Account with any connected sessions.
     has_account (bool, read-only) - True is this object has an associated account.
     is_superuser (bool, read-only): True if this object has an account and that
                        account is a superuser.
     plural_category (string) - Alias category for the plural strings of this object

    * Handlers available

     aliases - alias-handler: use aliases.add/remove/get() to use.
     permissions - permission-handler: use permissions.add/remove() to
                   add/remove new perms.
     locks - lock-handler: use locks.add() to add new lock strings
     scripts - script-handler. Add new scripts to object with scripts.add()
     cmdset - cmdset-handler. Use cmdset.add() to add new cmdsets to object
     nicks - nick-handler. New nicks with nicks.add().
     sessions - sessions-handler. Get Sessions connected to this
                object with sessions.get()
     attributes - attribute-handler. Use attributes.add/remove/get.
     db - attribute-handler: Shortcut for attribute-handler. Store/retrieve
            database attributes using self.db.myattr=val, val=self.db.myattr
     ndb - non-persistent attribute handler: same as db but does not create
            a database entry when storing data

    * Helper methods (see src.objects.objects.py for full headers)

     get_search_query_replacement(searchdata, **kwargs)
     get_search_direct_match(searchdata, **kwargs)
     get_search_candidates(searchdata, **kwargs)
     get_search_result(searchdata, attribute_name=None, typeclass=None,
                       candidates=None, exact=False, use_dbref=None, tags=None, **kwargs)
     get_stacked_result(results, **kwargs)
     handle_search_results(searchdata, results, **kwargs)
     search(searchdata, global_search=False, use_nicks=True, typeclass=None,
            location=None, attribute_name=None, quiet=False, exact=False,
            candidates=None, use_locks=True, nofound_string=None,
            multimatch_string=None, use_dbref=None, tags=None, stacked=0)
     search_account(searchdata, quiet=False)
     execute_cmd(raw_string, session=None, **kwargs))
     msg(text=None, from_obj=None, session=None, options=None, **kwargs)
     for_contents(func, exclude=None, **kwargs)
     msg_contents(message, exclude=None, from_obj=None, mapping=None,
                  raise_funcparse_errors=False, **kwargs)
     move_to(destination, quiet=False, emit_to_obj=None, use_destination=True)
     clear_contents()
     create(key, account, caller, method, **kwargs)
     copy(new_key=None)
     at_object_post_copy(new_obj, **kwargs)
     delete()
     is_typeclass(typeclass, exact=False)
     swap_typeclass(new_typeclass, clean_attributes=False, no_default=True)
     access(accessing_obj, access_type='read', default=False,
            no_superuser_bypass=False, **kwargs)
     filter_visible(obj_list, looker, **kwargs)
     get_default_lockstring()
     get_cmdsets(caller, current, **kwargs)
     check_permstring(permstring)
     get_cmdset_providers()
     get_display_name(looker=None, **kwargs)
     get_extra_display_name_info(looker=None, **kwargs)
     get_numbered_name(count, looker, **kwargs)
     get_display_header(looker, **kwargs)
     get_display_desc(looker, **kwargs)
     get_display_exits(looker, **kwargs)
     get_display_characters(looker, **kwargs)
     get_display_things(looker, **kwargs)
     get_display_footer(looker, **kwargs)
     format_appearance(appearance, looker, **kwargs)
     return_apperance(looker, **kwargs)

    * Hooks (these are class methods, so args should start with self):

     basetype_setup()     - only called once, used for behind-the-scenes
                            setup. Normally not modified.
     basetype_posthook_setup() - customization in basetype, after the object
                            has been created; Normally not modified.

     at_object_creation() - only called once, when object is first created.
                            Object customizations go here.
     at_object_post_creation() - only called once, when object is first created.
                            Additional setup involving e.g. prototype-set attributes can go here.
     at_object_delete() - called just before deleting an object. If returning
                            False, deletion is aborted. Note that all objects
                            inside a deleted object are automatically moved
                            to their <home>, they don't need to be removed here.
     at_object_post_spawn() - called when object is spawned from a prototype or updated
                            by the spawner to apply prototype changes.
     at_init()            - called whenever typeclass is cached from memory,
                            at least once every server restart/reload
     at_first_save()
     at_cmdset_get(**kwargs) - this is called just before the command handler
                            requests a cmdset from this object. The kwargs are
                            not normally used unless the cmdset is created
                            dynamically (see e.g. Exits).
     at_pre_puppet(account)- (account-controlled objects only) called just
                            before puppeting
     at_post_puppet()     - (account-controlled objects only) called just
                            after completing connection account<->object
     at_pre_unpuppet()    - (account-controlled objects only) called just
                            before un-puppeting
     at_post_unpuppet(account) - (account-controlled objects only) called just
                            after disconnecting account<->object link
     at_server_reload()   - called before server is reloaded
     at_server_shutdown() - called just before server is fully shut down

     at_access(result, accessing_obj, access_type) - called with the result
                            of a lock access check on this object. Return value
                            does not affect check result.

     at_pre_move(destination)             - called just before moving object
                        to the destination. If returns False, move is cancelled.
     announce_move_from(destination)         - called in old location, just
                        before move, if obj.move_to() has quiet=False
     announce_move_to(source_location)       - called in new location, just
                        after move, if obj.move_to() has quiet=False
     at_post_move(source_location)          - always called after a move has
                        been successfully performed.
     at_pre_object_leave(leaving_object, destination, **kwargs)
     at_object_leave(obj, target_location, move_type="move", **kwargs)
     at_object_leave(obj, target_location)   - called when an object leaves
                        this object in any fashion
     at_pre_object_receive(obj, source_location)
     at_object_receive(obj, source_location, move_type="move", **kwargs) - called when this object
                       receives another object
     at_post_move(source_location, move_type="move", **kwargs)

     at_traverse(traversing_object, target_location, **kwargs) - (exit-objects only)
                              handles all moving across the exit, including
                              calling the other exit hooks. Use super() to retain
                              the default functionality.
     at_post_traverse(traversing_object, source_location) - (exit-objects only)
                              called just after a traversal has happened.
     at_failed_traverse(traversing_object)      - (exit-objects only) called if
                       traversal fails and property err_traverse is not defined.

     at_msg_receive(self, msg, from_obj=None, **kwargs) - called when a message
                             (via self.msg()) is sent to this obj.
                             If returns false, aborts send.
     at_msg_send(self, msg, to_obj=None, **kwargs) - called when this objects
                             sends a message to someone via self.msg().

     return_appearance(looker) - describes this object. Used by "look"
                                 command by default
     at_desc(looker=None)      - called by 'look' whenever the
                                 appearance is requested.
     at_pre_get(getter, **kwargs)
     at_get(getter)            - called after object has been picked up.
                                 Does not stop pickup.
     at_pre_give(giver, getter, **kwargs)
     at_give(giver, getter, **kwargs)
     at_pre_drop(dropper, **kwargs)
     at_drop(dropper, **kwargs)          - called when this object has been dropped.
     at_pre_say(speaker, message, **kwargs)
     at_say(message, msg_self=None, msg_location=None, receivers=None, msg_receivers=None, **kwargs)

     at_look(target, **kwargs)
     at_desc(looker=None)
     at_rename(oldname, newname)


    """

    # Determines which order command sets begin to be assembled from.
    # Objects are usually third.
    cmdset_provider_order = 100
    cmdset_provider_error_order = 100
    cmdset_provider_type = "object"

    # Used for sorting / filtering in inventories / room contents.
    _content_types = ("object",)

    objects = ObjectManager()

    # Used by get_display_desc when self.db.desc is None
    default_description = _("You see nothing special.")

    # populated by `return_appearance`
    appearance_template = """
{header}
|c{name}{extra_name_info}|n
{desc}
{exits}
{characters}
{things}
{footer}
    """

    plural_category = "plural_key"
    # on-object properties

    @lazy_property
    def cmdset(self):
        """CmdSetHandler"""
        return CmdSetHandler(self, True)

    @lazy_property
    def scripts(self):
        """ScriptHandler"""
        return ScriptHandler(self)

    @lazy_property
    def nicks(self):
        """NickHandler"""
        return NickHandler(self, ModelAttributeBackend)

    @lazy_property
    def sessions(self):
        """SessionHandler"""
        return ObjectSessionHandler(self)

    @property
    def is_connected(self):
        """True if this object is associated with an Account with any connected sessions."""
        if self.account:  # seems sane to pass on the account
            return self.account.is_connected
        else:
            return False

    @property
    def has_account(self):
        """True is this object has an associated account."""
        return self.sessions.count()

    def get_cmdset_providers(self) -> dict[str, "CmdSetProvider"]:
        """
        Overrideable method which returns a dictionary of every kind of object which
        has a cmdsethandler linked to this Object, and should participate in cmdset
        merging.

        Objects might be aware of an Account. Otherwise, just themselves, by default.

        Returns:
            dict[str, CmdSetProvider]: The CmdSetProviders linked to this Object.
        """
        out = {"object": self}
        if self.account:
            out["account"] = self.account
        return out

    @property
    def is_superuser(self):
        """True if this object has an account and that account is a superuser."""
        return (
            self.db_account
            and self.db_account.is_superuser
            and not self.db_account.attributes.get("_quell")
        )

    def contents_get(self, exclude=None, content_type=None):
        """
        Returns the contents of this object, i.e. all
        objects that has this object set as its location.
        This should be publically available.

        Args:
            exclude (DefaultObject): Object to exclude from returned
                contents list
            content_type (str): A content_type to filter by. None for no
                filtering.

        Returns:
            list: List of contents of this Object.

        Notes:
            Also available as the `.contents` property, but that doesn't allow for exclusion and
            filtering on content-types.

        """
        return self.contents_cache.get(exclude=exclude, content_type=content_type)

    def contents_set(self, *args):
        "Makes sure `.contents` is read-only. Raises `AttributeError` if trying to set it."
        raise AttributeError(
            "{}.contents is read-only. Use obj.move_to or "
            "obj.location to move an object here.".format(self.__class__)
        )

    contents = property(contents_get, contents_set, contents_set)

    @property
    def exits(self):
        """
        Returns all exits from this object, i.e. all objects at this
        location having the property .destination != `None`.

        """
        return [exi for exi in self.contents if exi.destination]

    # search methods and hooks

    def get_search_query_replacement(self, searchdata, **kwargs):
        """
        This method is called by the search method to allow for direct
        replacements of the search string before it is used in the search.

        Args:
            searchdata (str): The search string to replace.
            **kwargs (any): These are the same as passed to the `search` method.

        Returns:
            str: The (potentially modified) search string.

        """
        if kwargs.get("use_nicks"):
            return self.nicks.nickreplace(
                searchdata, categories=("object", "account"), include_account=True
            )
        return searchdata

    def get_search_direct_match(self, searchdata, **kwargs):
        """
        This method is called by the search method to allow for direct
        replacements, such as 'me' always being an alias for this object.

        Args:
            searchdata (str): The search string to replace.
            **kwargs (any): These are the same as passed to the `search` method.

        Returns:
            tuple: A tuple `(should_return, str or Obj)`, where `should_return` is a boolean
            indicating the `.search` method should return the result immediately without further
            processing. If `should_return` is `True`, the second element of the tuple is the result
            that is returned.

        """
        if isinstance(searchdata, str):
            candidates = kwargs.get("candidates") or []
            global_search = kwargs.get("global_search", False)
            match searchdata.lower():
                case "me" | "self":
                    return global_search or self in candidates, self
                case "here":
                    return global_search or self.location in candidates, self.location
        return False, searchdata

    def get_search_candidates(self, searchdata, **kwargs):
        """
        Helper for the `.search` method. Get the candidates for a search. Also the `candidates`
        provided to the search function is included, and could be modified in-place here.

        Args:
            searchdata (str): The search criterion (could be modified by
                `get_search_query_replacement`).
            **kwargs (any): These are the same as passed to the `search` method.

        Returns:
            list: A list of objects possibly relevant for the search.

        Notes:
            If `searchdata` is a #dbref, this method should always return `None`. This is because
            the search should always be global in this case. If `candidates` were already given,
            they should be used as is. If `location` was given, the candidates should be based on
            that.

        """
        if kwargs.get("global_search") or dbref(searchdata):
            # global searches (dbref-searches are always global too) should not have any candidates
            return None

        # if candidates were already given, use them
        candidates = kwargs.get("candidates")
        if candidates is not None:
            return candidates

        # find candidates based on location
        location = kwargs.get("location")

        if location:
            # location(s) were given
            candidates = []
            for obj in make_iter(location):
                candidates.extend(obj.contents)
        else:
            # local search. Candidates are taken from
            # self.contents, self.location and
            # self.location.contents
            location = self.location
            candidates = self.contents
            if location:
                candidates = candidates + [location] + location.contents
            else:
                # normally we don't need this since we are
                # included in location.contents
                candidates.append(self)
        return candidates

    def get_search_result(
        self,
        searchdata,
        attribute_name=None,
        typeclass=None,
        candidates=None,
        exact=False,
        use_dbref=None,
        tags=None,
        **kwargs,
    ):
        """
        Helper for the `.search` method. This is a wrapper for actually searching for objects, used
        by the `search` method. This is broken out into a separate method to allow for easier
        overriding in child classes.

        Args:
            searchdata (str): The search criterion.
            attribute_name (str): The attribute to search on (default is `.
            typeclass (Typeclass or list): The typeclass to search for.
            candidates (list): A list of objects to search between.
            exact (bool): Require exact match.
            use_dbref (bool): Allow dbref search.
            tags (list): Tags to search for.

        Returns:
            queryset or iterable: The result of the search.

        """

        return ObjectDB.objects.search_object(
            searchdata,
            attribute_name=attribute_name,
            typeclass=typeclass,
            candidates=candidates,
            exact=exact,
            use_dbref=use_dbref,
            tags=tags,
        )

    def get_stacked_results(self, results, **kwargs):
        """
        This method is called by the search method to allow for handling of multi-match
        results that should be stacked.

        Args:
            results (list): The list of results from the search.

        Returns:
            tuple: A tuple `(stacked, results)`, where `stacked` is a boolean indicating if the
            result is stacked and `results` is the list of results to return. If `stacked`
            is True, the ".search" method will return `results` immediately without further
            processing (it will not result in a multimatch-error).

        Notes:
            The `stacked` keyword argument is an integer that controls the max size of each stack
            (if >0). It's important to make sure to only stack _identical_ objects, otherwise we
            risk losing track of objects.

        """
        nresults = len(results)
        max_stack_size = kwargs.get("stacked", 0)
        typeclass = kwargs.get("typeclass")
        exact = kwargs.get("exact", False)

        if max_stack_size > 0 and nresults > 1:
            nstack = nresults
            if not exact:
                # we re-run exact match against one of the matches to make sure all are indeed
                # equal and we were not catching partial matches not belonging to the stack
                nstack = len(
                    ObjectDB.objects.get_objs_with_key_or_alias(
                        results[0].key,
                        exact=True,
                        candidates=list(results),
                        typeclasses=[typeclass] if typeclass else None,
                    )
                )
            if nstack == nresults:
                # a valid stack of identical items, return multiple results
                return True, list(results)[:max_stack_size]

        return False, results

    def handle_search_results(self, searchdata, results, **kwargs):
        """
        This method is called by the search method to allow for handling of the final search result.

        Args:
            searchdata (str): The original search criterion (potentially modified by
                `get_search_query_replacement`).
            results (list): The list of results from the search.
            **kwargs (any): These are the same as passed to the `search` method.

        Returns:
            Object, None or list: Normally this is a single object, but if `quiet=True` it should be
            a list.  If quiet=False and we have to handle a no/multi-match error (directly messaging
            the user), this should return `None`.

        """
        if kwargs.get("quiet"):
            # don't care about no/multi-match errors, just return list of whatever we have
            return list(results)

        # handle any error messages, otherwise return a single result

        nofound_string = kwargs.get("nofound_string")
        multimatch_string = kwargs.get("multimatch_string")

        return _AT_SEARCH_RESULT(
            results,
            self,
            query=searchdata,
            nofound_string=nofound_string,
            multimatch_string=multimatch_string,
        )

    def search(
        self,
        searchdata,
        global_search=False,
        use_nicks=True,
        typeclass=None,
        location=None,
        attribute_name=None,
        quiet=False,
        exact=False,
        candidates=None,
        use_locks=True,
        nofound_string=None,
        multimatch_string=None,
        use_dbref=None,
        tags=None,
        stacked=0,
    ):
        """
        Returns an Object matching a search string/condition

        Perform a standard object search in the database, handling
        multiple results and lack thereof gracefully. By default, only
        objects in the current `location` of `self` or its inventory are searched for.

        Args:
            searchdata (str or obj): Primary search criterion. Will be matched
                against `object.key` (with `object.aliases` second) unless
                the keyword attribute_name specifies otherwise.

                Special keywords:

                - `#<num>`: search by unique dbref. This is always a global search.
                - `me,self`: self-reference to this object
                - `<num>-<string>` - can be used to differentiate
                   between multiple same-named matches. The exact form of this input
                   is given by `settings.SEARCH_MULTIMATCH_REGEX`.

            global_search (bool): Search all objects globally. This overrules 'location' data.
            use_nicks (bool): Use nickname-replace (nicktype "object") on `searchdata`.
            typeclass (str or Typeclass, or list of either): Limit search only
                to `Objects` with this typeclass. May be a list of typeclasses
                for a broader search.
            location (Object or list): Specify a location or multiple locations
                to search. Note that this is used to query the *contents* of a
                location and will not match for the location itself -
                if you want that, don't set this or use `candidates` to specify
                exactly which objects should be searched. If this nor candidates are
                given, candidates will include caller's inventory, current location and
                all objects in the current location.
            attribute_name (str): Define which property to search. If set, no
                key+alias search will be performed. This can be used
                to search database fields (db_ will be automatically
                prepended), and if that fails, it will try to return
                objects having Attributes with this name and value
                equal to searchdata. A special use is to search for
                "key" here if you want to do a key-search without
                including aliases.
            quiet (bool): don't display default error messages - this tells the
                search method that the user wants to handle all errors
                themselves. It also changes the return value type, see
                below.
            exact (bool): if unset (default) - prefers to match to beginning of
                string rather than not matching at all. If set, requires
                exact matching of entire string.
            candidates (list of objects): this is an optional custom list of objects
                to search (filter) between. It is ignored if `global_search`
                is given. If not set, this list will automatically be defined
                to include the location, the contents of location and the
                caller's contents (inventory).
            use_locks (bool): If True (default) - removes search results which
                fail the "search" lock.
            nofound_string (str):  optional custom string for not-found error message.
            multimatch_string (str): optional custom string for multimatch error header.
            use_dbref (bool or None, optional): If `True`, allow to enter e.g. a query "#123"
                to find an object (globally) by its database-id 123. If `False`, the string "#123"
                will be treated like a normal string. If `None` (default), the ability to query by
                #dbref is turned on if `self` has the permission 'Builder' and is turned off
                otherwise.
            tags (list or tuple): Find objects matching one or more Tags. This should be one or
                more tag definitions on the form `tagname` or `(tagname, tagcategory)`.
            stacked (int, optional): If > 0, multimatches will be analyzed to determine if they
                only contains identical objects; these are then assumed 'stacked' and no multi-match
                error will be generated, instead `stacked` number of matches will be returned as a
                list. If `stacked` is larger than number of matches, returns that number of matches.
                If the found stack is a mix of objects, return None and handle the multi-match error
                depending on the value of `quiet`.

        Returns:
            Object, None or list: Will return an `Object` or `None` if `quiet=False`. Will return
            a `list` with 0, 1 or more matches if `quiet=True`. If `stacked` is a positive integer,
            this list may contain all stacked identical matches.

        Notes:
            To find Accounts, use eg. `evennia.account_search`. If
            `quiet=False`, error messages will be handled by
            `settings.SEARCH_AT_RESULT` and echoed automatically (on
            error, return will be `None`). If `quiet=True`, the error
            messaging is assumed to be handled by the caller.

        """
        # store input kwargs for sub-methods (this must be done first in this method)
        input_kwargs = {
            key: value for key, value in locals().items() if key not in ("self", "searchdata")
        }

        # replace incoming searchdata string with a potentially modified version
        searchdata = self.get_search_query_replacement(searchdata, **input_kwargs)

        # get candidates
        candidates = self.get_search_candidates(searchdata, **input_kwargs)

        # handle special input strings, like "me" or "here".
        # we also want to include the identified candidates here instead of input, to account for defaults
        should_return, searchdata = self.get_search_direct_match(
            searchdata, **(input_kwargs | {"candidates": candidates})
        )
        if should_return:
            # we got an actual result, return it immediately
            return [searchdata] if quiet else searchdata

        # if use_dbref is None, we use a lock to determine if dbref search is allowed
        use_dbref = (
            self.locks.check_lockstring(self, "_dummy:perm(Builder)")
            if use_dbref is None
            else use_dbref
        )

        # convert tags into tag tuples suitable for query
        tags = [
            (tagkey, tagcat[0] if tagcat else None) for tagkey, *tagcat in make_iter(tags or [])
        ]

        # always use exact match for dbref/global searches
        exact = True if global_search or dbref(searchdata) else exact

        # do the actual search
        results = self.get_search_result(
            searchdata,
            attribute_name=attribute_name,
            typeclass=typeclass,
            candidates=candidates,
            exact=exact,
            use_dbref=use_dbref,
            tags=tags,
        )

        # filter out objects we are not allowed to search
        if use_locks:
            results = [x for x in list(results) if x.access(self, "search", default=True)]

        # handle stacked objects
        is_stacked, results = self.get_stacked_results(results, **input_kwargs)
        if is_stacked:
            # we have a stacked result, return it immediately (a list)
            return results

        # handle the end (unstacked) results, returning a single object, a list or None
        return self.handle_search_results(searchdata, results, **input_kwargs)

    def search_account(self, searchdata, quiet=False):
        """
        Simple shortcut wrapper to search for accounts, not characters.

        Args:
            searchdata (str): Search criterion - the key or dbref of the account
                to search for. If this is "here" or "me", search
                for the account connected to this object.
            quiet (bool): Returns the results as a list rather than
                echo eventual standard error messages. Default `False`.

        Returns:
            DefaultAccount, None or list: What is returned depends on
            the `quiet` setting:

            - `quiet=False`: No match or multumatch auto-echoes errors
              to self.msg, then returns `None`. The esults are passed
              through `settings.SEARCH_AT_RESULT` and
              `settings.SEARCH_AT_MULTIMATCH_INPUT`. If there is a
              unique match, this will be returned.
            - `quiet=True`: No automatic error messaging is done, and
              what is returned is always a list with 0, 1 or more
              matching Accounts.

        """
        if isinstance(searchdata, str):
            # searchdata is a string; wrap some common self-references
            if searchdata.lower() in ("me", "self"):
                return [self.account] if quiet else self.account

        results = search.search_account(searchdata)

        if quiet:
            return results
        return _AT_SEARCH_RESULT(results, self, query=searchdata)

    def execute_cmd(self, raw_string, session=None, **kwargs):
        """
        Do something as this object. This is never called normally,
        it's only used when wanting specifically to let an object be
        the caller of a command. It makes use of nicks of eventual
        connected accounts as well.

        Args:
            raw_string (string): Raw command input
            session (Session, optional): Session to
                return results to

        Keyword Args:
            Other keyword arguments will be added to the found command
            object instace as variables before it executes.  This is
            unused by default Evennia but may be used to set flags and
            change operating paramaters for commands at run-time.

        Returns:
            Deferred: This is an asynchronous Twisted object that
            will not fire until the command has actually finished
            executing. To overload this one needs to attach
            callback functions to it, with addCallback(function).
            This function will be called with an eventual return
            value from the command execution. This return is not
            used at all by Evennia by default, but might be useful
            for coders intending to implement some sort of nested
            command structure.

        """
        # break circular import issues
        global _CMDHANDLER
        if not _CMDHANDLER:
            from evennia.commands.cmdhandler import cmdhandler as _CMDHANDLER

        # nick replacement - we require full-word matching.
        # do text encoding conversion
        raw_string = self.nicks.nickreplace(
            raw_string, categories=("inputline", "channel"), include_account=True
        )
        return _CMDHANDLER(self, raw_string, callertype="object", session=session, **kwargs)

    def msg(self, text=None, from_obj=None, session=None, options=None, **kwargs):
        """
        Emits something to a session attached to the object.

        Keyword Args:
            text (str or tuple): The message to send. This
                is treated internally like any send-command, so its
                value can be a tuple if sending multiple arguments to
                the `text` oob command.
            from_obj (DefaultObject, DefaultAccount, Session, or list): object that is sending. If
                given, at_msg_send will be called. This value will be
                passed on to the protocol. If iterable, will execute hook
                on all entities in it.
            session (Session or list): Session or list of
                Sessions to relay data to, if any. If set, will force send
                to these sessions. If unset, who receives the message
                depends on the MULTISESSION_MODE.
            options (dict): Message-specific option-value
                pairs. These will be applied at the protocol level.
            **kwargs (string or tuples): All kwarg keys not listed above
                will be treated as send-command names and their arguments
                (which can be a string or a tuple).

        Notes:
            The `at_msg_receive` method will be called on this Object.
            All extra kwargs will be passed on to the protocol.

        """
        # try send hooks
        if from_obj:
            for obj in make_iter(from_obj):
                try:
                    obj.at_msg_send(text=text, to_obj=self, **kwargs)
                except Exception:
                    logger.log_trace()
        kwargs["options"] = options
        try:
            if not self.at_msg_receive(text=text, from_obj=from_obj, **kwargs):
                # if at_msg_receive returns false, we abort message to this object
                return
        except Exception:
            logger.log_trace()

        if text is not None:
            if not (isinstance(text, str) or isinstance(text, tuple)):
                # sanitize text before sending across the wire
                try:
                    text = to_str(text)
                except Exception:
                    text = repr(text)
            kwargs["text"] = text

        # relay to session(s)
        sessions = make_iter(session) if session else self.sessions.all()
        for session in sessions:
            session.data_out(**kwargs)

    def for_contents(self, func, exclude=None, **kwargs):
        """
        Runs a function on every object contained within this one.

        Args:
            func (callable): Function to call. This must have the
                formal call sign func(obj, **kwargs), where obj is the
                object currently being processed and `**kwargs` are
                passed on from the call to `for_contents`.
            exclude (list, optional): A list of object not to call the
                function on.

        Keyword Args:
            Keyword arguments will be passed to the function for all objects.

        """
        contents = self.contents
        if exclude:
            exclude = make_iter(exclude)
            contents = [obj for obj in contents if obj not in exclude]
        for obj in contents:
            func(obj, **kwargs)

    def msg_contents(
        self,
        text=None,
        exclude=None,
        from_obj=None,
        mapping=None,
        raise_funcparse_errors=False,
        **kwargs,
    ):
        """
        Emits a message to all objects inside this object.

        Args:
            text (str or tuple): Message to send. If a tuple, this should be
                on the valid OOB outmessage form `(message, {kwargs})`,
                where kwargs are optional data passed to the `text`
                outputfunc. The message will be parsed for `{key}` formatting and
                `$You/$you()/$You()`, `$obj(name)`, `$conj(verb)` and `$pron(pronoun, option)`
                inline function callables.
                The `name` is taken from the `mapping` kwarg {"name": object, ...}`.
                The `mapping[key].get_display_name(looker=recipient)` will be called
                for that key for every recipient of the string.
            exclude (list, optional): A list of objects not to send to.
            from_obj (Object, optional): An object designated as the
                "sender" of the message. See `DefaultObject.msg()` for
                more info. This will be used for `$You/you` if using funcparser inlines.
            mapping (dict, optional): A mapping of formatting keys
                `{"key":<object>, "key2":<object2>,...}.
                The keys must either match `{key}` or `$You(key)/$you(key)` markers
                in the `text` string. If `<object>` doesn't have a `get_display_name`
                method, it will be returned as a string. Pass "you" to represent the caller,
                this can be skipped if `from_obj` is provided (that will then act as 'you').
            raise_funcparse_errors (bool, optional): If set, a failing `$func()` will
                lead to an outright error. If unset (default), the failing `$func()`
                will instead appear in output unparsed.

            **kwargs: Keyword arguments will be passed on to `obj.msg()` for all
                messaged objects.

        Notes:
            For 'actor-stance' reporting (You say/Name says), use the
            `$You()/$you()/$You(key)` and `$conj(verb)` (verb-conjugation)
            inline callables. This will use the respective `get_display_name()`
            for all onlookers except for `from_obj or self`, which will become
            'You/you'. If you use `$You/you(key)`, the key must be in `mapping`.

            For 'director-stance' reporting (Name says/Name says), use {key}
            syntax directly. For both `{key}` and `You/you(key)`,
            `mapping[key].get_display_name(looker=recipient)` may be called
            depending on who the recipient is.

        Examples:

            Let's assume:

            - `player1.key` -> "Player1",
            - `player1.get_display_name(looker=player2)` -> "The First girl"
            - `player2.key` -> "Player2",
            - `player2.get_display_name(looker=player1)` -> "The Second girl"

            Actor-stance:
            ::

                char.location.msg_contents(
                    "$You() $conj(attack) $you(defender).",
                    from_obj=player1,
                    mapping={"defender": player2})

            - player1 will see `You attack The Second girl.`
            - player2 will see 'The First girl attacks you.'

            Director-stance:
            ::

                char.location.msg_contents(
                    "{attacker} attacks {defender}.",
                    mapping={"attacker":player1, "defender":player2})

            - player1 will see: 'Player1 attacks The Second girl.'
            - player2 will see: 'The First girl attacks Player2'

        """
        # we also accept an outcommand on the form (message, {kwargs})
        is_outcmd = text and is_iter(text)
        inmessage = text[0] if is_outcmd else text
        outkwargs = text[1] if is_outcmd and len(text) > 1 else {}
        mapping = mapping or {}
        you = from_obj or self

        if "you" not in mapping:
            mapping["you"] = you

        contents = self.contents
        if exclude:
            exclude = make_iter(exclude)
            contents = [obj for obj in contents if obj not in exclude]

        for receiver in contents:
            # actor-stance replacements
            outmessage = _MSG_CONTENTS_PARSER.parse(
                inmessage,
                raise_errors=raise_funcparse_errors,
                return_string=True,
                caller=you,
                receiver=receiver,
                mapping=mapping,
            )

            # director-stance replacements
            outmessage = outmessage.format_map(
                {
                    key: (
                        obj.get_display_name(looker=receiver)
                        if hasattr(obj, "get_display_name")
                        else str(obj)
                    )
                    for key, obj in mapping.items()
                }
            )

            receiver.msg(text=(outmessage, outkwargs), from_obj=from_obj, **kwargs)

    def move_to(
        self,
        destination,
        quiet=False,
        emit_to_obj=None,
        use_destination=True,
        to_none=False,
        move_hooks=True,
        move_type="move",
        **kwargs,
    ):
        """
        Moves this object to a new location.

        Args:
            destination (DefaultObject): Reference to the object to move to. This
                can also be an exit object, in which case the
                destination property is used as destination.
            quiet (bool): If true, turn off the calling of the emit hooks
                (announce_move_to/from etc)
            emit_to_obj (DefaultObject): object to receive error messages
            use_destination (bool): Default is for objects to use the "destination"
                 property of destinations as the target to move to. Turning off this
                 keyword allows objects to move "inside" exit objects.
            to_none (bool): Allow destination to be None. Note that no hooks are run when
                 moving to a None location. If you want to run hooks, run them manually
                 (and make sure they can manage None locations).
            move_hooks (bool): If False, turn off the calling of move-related hooks
                (at_pre/post_move etc) with quiet=True, this is as quiet a move
                as can be done.
            move_type (str): The "kind of move" being performed, such as "teleport", "traverse",
                "get", "give", or "drop". The value can be arbitrary. By default, it only affects
                the text message generated by announce_move_to and announce_move_from by defining
                their {"type": move_type} for outgoing text. This can be used for altering
                messages and/or overloaded hook behaviors.
            **kwargs: Passed on to all movement- and announcement hooks. Use in your game to let
                hooks know about any special condition of the move (such as running or sneaking).
                Exits will pass an "exit_obj" kwarg.

        Returns:
            bool: True/False depending on if there were problems with the move. This method may also
            return various error messages to the `emit_to_obj`.

        Notes:
            No access checks are done in this method, these should be handled before
            calling `move_to`.

        The `DefaultObject` hooks called (if `move_hooks=True`) are, in order:

        1. `self.at_pre_move(destination)` (abort if return False)
        2. `source_location.at_pre_object_leave(self, destination)` (abort if return False)
        3. `destination.at_pre_object_receive(self, source_location)` (abort if return False)
        4. `source_location.at_object_leave(self, destination)`
        5. `self.announce_move_from(destination)`
        6. (move happens here)
        7. `self.announce_move_to(source_location)`
        8. `destination.at_object_receive(self, source_location)`
        9. `self.at_post_move(source_location)`

        """

        def logerr(string="", err=None):
            """Simple log helper method"""
            logger.log_trace()
            self.msg("%s%s" % (string, "" if err is None else " (%s)" % err))
            return

        errtxt = _("Couldn't perform move ({err}). Contact an admin.")
        if not emit_to_obj:
            emit_to_obj = self

        if not destination:
            if to_none:
                # immediately move to None. There can be no hooks called since
                # there is no destination to call them with.
                self.location = None
                return True
            emit_to_obj.msg(_("The destination doesn't exist."))
            return False
        if destination.destination and use_destination:
            # traverse exits
            destination = destination.destination

        # Save the old location
        source_location = self.location

        # Before the move, call pre-hooks
        if move_hooks:
            # check if we are okay to move
            try:
                if not self.at_pre_move(destination, move_type=move_type, **kwargs):
                    return False
            except Exception as err:
                logerr(errtxt.format(err="at_pre_move()"), err)
                return False
            # check if source location lets us go
            try:
                if source_location and not source_location.at_pre_object_leave(
                    self, destination, move_type=move_type, **kwargs
                ):
                    return False
            except Exception as err:
                logerr(errtxt.format(err="at_pre_object_leave()"), err)
                return False
            # check if destination accepts us
            try:
                if destination and not destination.at_pre_object_receive(
                    self, source_location, move_type=move_type, **kwargs
                ):
                    return False
            except Exception as err:
                logerr(errtxt.format(err="at_pre_object_receive()"), err)
                return False

        # Call hook on source location
        if move_hooks and source_location:
            try:
                source_location.at_object_leave(self, destination, move_type=move_type, **kwargs)
            except Exception as err:
                logerr(errtxt.format(err="at_object_leave()"), err)
                return False

        if not quiet:
            # tell the old room we are leaving
            try:
                self.announce_move_from(destination, move_type=move_type, **kwargs)
            except Exception as err:
                logerr(errtxt.format(err="announce_move_from()"), err)
                return False

        # Perform move
        try:
            self.location = destination
        except Exception as err:
            logerr(errtxt.format(err="location change"), err)
            return False

        if not quiet:
            # Tell the new room we are there.
            try:
                self.announce_move_to(source_location, move_type=move_type, **kwargs)
            except Exception as err:
                logerr(errtxt.format(err="announce_move_to()"), err)
                return False

        if move_hooks:
            # Perform eventual extra commands on the receiving location
            # (the object has already arrived at this point)
            try:
                destination.at_object_receive(self, source_location, move_type=move_type, **kwargs)
            except Exception as err:
                logerr(errtxt.format(err="at_object_receive()"), err)
                return False

        # Execute eventual extra commands on this object after moving it
        # (usually calling 'look')
        if move_hooks:
            try:
                self.at_post_move(source_location, move_type=move_type, **kwargs)
            except Exception as err:
                logerr(errtxt.format(err="at_post_move"), err)
                return False
        return True

    def clear_exits(self):
        """
        Destroys all of the exits and any exits pointing to this
        object as a destination.

        """
        for out_exit in [exi for exi in ObjectDB.objects.get_contents(self) if exi.db_destination]:
            out_exit.delete()
        for in_exit in ObjectDB.objects.filter(db_destination=self):
            in_exit.delete()

    def clear_contents(self):
        """
        Moves all objects (accounts/things) to their home location or
        to default home.

        """
        # Gather up everything that thinks this is its location.
        default_home_id = int(settings.DEFAULT_HOME.lstrip("#"))
        try:
            default_home = ObjectDB.objects.get(id=default_home_id)
            if default_home.dbid == self.dbid:
                # we are deleting default home!
                default_home = None
        except Exception:
            string = _("Could not find default home '(#{dbid})'.")
            logger.log_err(string.format(dbid=default_home_id))
            default_home = None

        for obj in self.contents:
            home = obj.home
            # Obviously, we can't send it back to here.
            if not home or (home and home.dbid == self.dbid):
                obj.home = default_home
                home = default_home

            # If for some reason it's still None...
            if not home:
                obj.location = None
                obj.msg(_("Something went wrong! You are dumped into nowhere. Contact an admin."))
                logger.log_err(
                    "Missing default home - '{name}(#{dbid})' now has a null location.".format(
                        name=obj.name, dbid=obj.dbid
                    )
                )
                return

            if obj.has_account:
                if home:
                    string = _(
                        "Your current location has ceased to exist, moving you to (#{dbid})."
                    )
                    obj.msg(string.format(dbid=home.dbid))
                else:
                    # Famous last words: The account should never see this.
                    obj.msg(_("This place should not exist ... contact an admin."))
            obj.move_to(home, move_type="teleport")

    @classmethod
    def get_default_lockstring(
        cls, account: "DefaultAccount" = None, caller: "DefaultObject" = None, **kwargs
    ):
        """
        Classmethod called during .create() to determine default locks for the object.

        Args:
            account (DefaultAccount): Account to attribute this object to.
            caller (DefaultObject): The object which is creating this one.
            **kwargs: Arbitrary input.

        Returns:
            str: A lockstring to use for this object.
        """
        pid = f"pid({account.id})" if account else None
        cid = f"id({caller.id})" if caller else None
        admin = "perm(Admin)"
        trio = " or ".join([x for x in [pid, cid, admin] if x])
        return ";".join([f"{x}:{trio}" for x in ["control", "delete", "edit"]])

    @classmethod
    def create(
        cls,
        key: str,
        account: "DefaultAccount" = None,
        caller: "DefaultObject" = None,
        method: str = "create",
        **kwargs,
    ):
        """
        Creates a basic object with default parameters, unless otherwise
        specified or extended.

        Provides a friendlier interface to the utils.create_object() function.

        Args:
            key (str): Name of the new object.


        Keyword Args:
            account (DefaultAccount): Account to attribute this object to.
            caller (DefaultObject): The object which is creating this one.
            description (str): Brief description for this object.
            ip (str): IP address of creator (for object auditing).
            method (str): The method of creation. Defaults to "create".

        Returns:
            tuple: A tuple (Object, errors): A newly created object of the given typeclass. This
            will be `None` if there are errors. The second element is then a list of errors that
            occurred during creation. If this is empty, it's safe to assume the object was created
            successfully.

        """
        errors = []
        obj = None

        # Get IP address of creator, if available
        ip = kwargs.pop("ip", "")

        # If no typeclass supplied, use this class
        kwargs["typeclass"] = kwargs.pop("typeclass", cls)

        # Set the supplied key as the name of the intended object
        kwargs["key"] = key

        # Get a supplied description, if any
        description = kwargs.pop("description", "")

        # Create a sane lockstring if one wasn't supplied
        lockstring = kwargs.get("locks")
        if (account or caller) and not lockstring:
            lockstring = cls.get_default_lockstring(account=account, caller=caller, **kwargs)
            kwargs["locks"] = lockstring

        # Create object
        try:
            obj = create.create_object(**kwargs)

            # Record creator id and creation IP
            if ip:
                obj.db.creator_ip = ip
            if account:
                obj.db.creator_id = account.id

            # Set description if provided
            if description:
                obj.db.desc = description

        except Exception as e:
            errors.append(f"An error occurred while creating '{key}' object: {e}")
            logger.log_trace()

        return obj, errors

    def copy(self, new_key=None, **kwargs):
        """
        Makes an identical copy of this object, identical except for a
        new dbref in the database. If you want to customize the copy
        by changing some settings, use ObjectDB.object.copy_object()
        directly.

        Args:
            new_key (string): New key/name of copied object. If new_key is not
                specified, the copy will be named <old_key>_copy by default.
        Returns:
            Object: A copy of this object.

        """

        def find_clone_key():
            """
            Append 01, 02 etc to obj.key. Checks next higher number in the
            same location, then adds the next number available

            returns the new clone name on the form keyXX
            """
            key = self.key
            num = sum(
                1
                for obj in self.location.contents
                if obj.key.startswith(key) and obj.key.lstrip(key).isdigit()
            )
            return "%s%03i" % (key, num)

        new_key = new_key or find_clone_key()
        new_obj = ObjectDB.objects.copy_object(self, new_key=new_key, **kwargs)
        self.at_object_post_copy(new_obj, **kwargs)
        return new_obj

    def at_object_post_copy(self, new_obj, **kwargs):
        """
        Called by DefaultObject.copy(). Meant to be overloaded. In case there's extra data not
        covered by .copy(), this can be used to deal with it.

        Args:
            new_obj (DefaultObject): The new Copy of this object.

        """
        pass

    def delete(self):
        """
        Deletes this object.  Before deletion, this method makes sure
        to move all contained objects to their respective home
        locations, as well as clean up all exits to/from the object.

        Returns:
            bool: Whether or not the delete completed successfully or not.

        """
        global _ScriptDB
        if not _ScriptDB:
            from evennia.scripts.models import ScriptDB as _ScriptDB

        if not self.pk or not self.at_object_delete():
            # This object has already been deleted,
            # or the pre-delete check return False
            return False

        # See if we need to kick the account off.

        for session in self.sessions.all():
            session.msg(_("Your character {key} has been destroyed.").format(key=self.key))
            # no need to disconnect, Account just jumps to OOC mode.
        # sever the connection (important!)
        if self.account:
            # Remove the object from playable characters list
            self.account.characters.remove(self)
            for session in self.sessions.all():
                self.account.unpuppet_object(session)

        # unlink account/home to avoid issues with saving
        self.db_account = None
        self.db_home = None

        for script in _ScriptDB.objects.get_all_scripts_on_obj(self):
            script.delete()

        # Destroy any exits to and from this room, if any
        self.clear_exits()
        # Clear out any non-exit objects located within the object
        self.clear_contents()
        self.attributes.clear()
        self.nicks.clear()
        self.aliases.clear()
        self.location = None  # this updates contents_cache for our location

        # Perform the deletion of the object
        super().delete()
        return True

    def access(
        self, accessing_obj, access_type="read", default=False, no_superuser_bypass=False, **kwargs
    ):
        """
        Determines if another object has permission to access this object
        in whatever way.

        Args:
          accessing_obj (DefaultObject): Object trying to access this one.
          access_type (str, optional): Type of access sought.
          default (bool, optional): What to return if no lock of access_type was found.
          no_superuser_bypass (bool, optional): If `True`, don't skip
            lock check for superuser (be careful with this one).
          **kwargs: Passed on to the at_access hook along with the result of the access check.

        """
        result = super().access(
            accessing_obj,
            access_type=access_type,
            default=default,
            no_superuser_bypass=no_superuser_bypass,
        )
        self.at_access(result, accessing_obj, access_type, **kwargs)
        return result

    def filter_visible(self, obj_list, looker, **kwargs):
        """
        Filter a list of objects to only include those that are visible to the looker.

        Args:
            obj_list (list): List of objects to filter.
            looker (DefaultObject): Object doing the looking.
            **kwargs: Arbitrary data for use when overriding.
        Returns:
            list: The filtered list of visible objects.
        Notes:
            By default this simply checks the 'view' and 'search' locks on each object in the list.
            Override this
            method to implement custom visibility mechanics.

        """
        return [
            obj
            for obj in obj_list
            if obj != looker
            and (obj.access(looker, "view") and obj.access(looker, "search", default=True))
        ]

    # name and return_appearance hooks

    def get_display_name(self, looker=None, **kwargs):
        """
        Displays the name of the object in a viewer-aware manner.

        Args:
            looker (DefaultObject): The object or account that is looking at or getting information
                for this object.

        Returns:
            str: A name to display for this object. By default this returns the `.name` of the object.

        Notes:
            This function can be extended to change how object names appear to users in character,
            but it does not change an object's keys or aliases when searching.

        """
        return self.name

    def get_extra_display_name_info(self, looker=None, **kwargs):
        """
        Adds any extra display information to the object's name. By default this is is the
        object's dbref in parentheses, if the looker has permission to see it.

        Args:
            looker (DefaultObject): The object looking at this object.

        Returns:
            str: The dbref of this object, if the looker has permission to see it. Otherwise, an
            empty string is returned.

        Notes:
            By default, this becomes a string (#dbref) attached to the object's name.

        """
        if looker and self.locks.check_lockstring(looker, "perm(Builder)"):
            return f"(#{self.id})"
        return ""

    def get_numbered_name(self, count, looker, **kwargs):
        """
        Return the numbered (singular, plural) forms of this object's key. This is by default called
        by return_appearance and is used for grouping multiple same-named of this object. Note that
        this will be called on *every* member of a group even though the plural name will be only
        shown once. Also the singular display version, such as 'an apple', 'a tree' is determined
        from this method.

        Args:
            count (int): Number of objects of this type
            looker (DefaultObject): Onlooker. Not used by default.

        Keyword Args:
            key (str): Optional key to pluralize. If not given, the object's `.get_display_name()`
                method is used.
            return_string (bool): If `True`, return only the singular form if count is 0,1 or
                the plural form otherwise. If `False` (default), return both forms as a tuple.
            no_article (bool): If `True`, do not return an article if `count` is 1.

        Returns:
            tuple: This is a tuple `(str, str)` with the singular and plural forms of the key
            including the count.

        Examples:
        ::

            obj.get_numbered_name(3, looker, key="foo")
                  -> ("a foo", "three foos")
            obj.get_numbered_name(1, looker, key="Foobert", return_string=True)
                  -> "a Foobert"
            obj.get_numbered_name(1, looker, key="Foobert", return_string=True, no_article=True)
                  -> "Foobert"
        """
        key = kwargs.get("key", self.get_display_name(looker))
        raw_key = self.name
        key = ansi.ANSIString(key)  # this is needed to allow inflection of colored names
        try:
            plural = _INFLECT.plural(key, count)
            plural = "{} {}".format(_INFLECT.number_to_words(count, threshold=12), plural)
        except IndexError:
            # this is raised by inflect if the input is not a proper noun
            plural = key
        singular = _INFLECT.an(key)
        if not self.aliases.get(plural, category=self.plural_category):
            # we need to wipe any old plurals/an/a in case key changed in the interrim
            self.aliases.clear(category=self.plural_category)
            self.aliases.add(plural, category=self.plural_category)
            # save the singular form as an alias here too so we can display "an egg" and also
            # look at 'an egg'.
            self.aliases.add(singular, category=self.plural_category)

        if kwargs.get("no_article") and count == 1:
            if kwargs.get("return_string"):
                return key
            return key, key

        if kwargs.get("return_string"):
            return singular if count == 1 else plural

        return singular, plural

    def get_display_header(self, looker, **kwargs):
        """
        Get the 'header' component of the object description. Called by `return_appearance`.

        Args:
            looker (DefaultObject): Object doing the looking.
            **kwargs: Arbitrary data for use when overriding.
        Returns:
            str: The header display string.

        """
        return ""

    def get_display_desc(self, looker, **kwargs):
        """
        Get the 'desc' component of the object description. Called by `return_appearance`.

        Args:
            looker (DefaultObject): Object doing the looking.
            **kwargs: Arbitrary data for use when overriding.
        Returns:
            str: The desc display string.

        """
        return self.db.desc or self.default_description

    def get_display_exits(self, looker, **kwargs):
        """
        Get the 'exits' component of the object description. Called by `return_appearance`.

        Args:
            looker (DefaultObject): Object doing the looking.
            **kwargs: Arbitrary data for use when overriding.

        Keyword Args:
            exit_order (iterable of str): The order in which exits should be listed, with
                unspecified exits appearing at the end, alphabetically.

        Returns:
            str: The exits display data.

        Examples:
        ::

            For a room with exits in the order 'portal', 'south', 'north', and 'out':
                obj.get_display_name(looker, exit_order=('north', 'south'))
                    -> "Exits: north, south, out, and portal."  (markup not shown here)
        """

        def _sort_exit_names(names):
            exit_order = kwargs.get("exit_order")
            if not exit_order:
                return names
            sort_index = {name: key for key, name in enumerate(exit_order)}
            names = sorted(names)
            end_pos = len(sort_index)
            names.sort(key=lambda name: sort_index.get(name, end_pos))
            return names

        exits = self.filter_visible(self.contents_get(content_type="exit"), looker, **kwargs)
        exit_names = (exi.get_display_name(looker, **kwargs) for exi in exits)
        exit_names = iter_to_str(_sort_exit_names(exit_names), endsep=_(", and"))
        e = _("Exits")
        return f"|w{e}:|n {exit_names}" if exit_names else ""

    def get_display_characters(self, looker, **kwargs):
        """
        Get the 'characters' component of the object description. Called by `return_appearance`.

        Args:
            looker (DefaultObject): Object doing the looking.
            **kwargs: Arbitrary data for use when overriding.
        Returns:
            str: The character display data.

        """
        characters = self.filter_visible(
            self.contents_get(content_type="character"), looker, **kwargs
        )
        character_names = iter_to_str(
            (char.get_display_name(looker, **kwargs) for char in characters), endsep=_(", and")
        )
        c = _("Characters")
        return f"|w{c}:|n {character_names}" if character_names else ""

    def get_display_things(self, looker, **kwargs):
        """
        Get the 'things' component of the object description. Called by `return_appearance`.

        Args:
            looker (DefaultObject): Object doing the looking.
            **kwargs: Arbitrary data for use when overriding.
        Returns:
            str: The things display data.

        """
        # sort and handle same-named things
        things = self.filter_visible(self.contents_get(content_type="object"), looker, **kwargs)

        grouped_things = defaultdict(list)
        for thing in things:
            grouped_things[thing.get_display_name(looker, **kwargs)].append(thing)

        thing_names = []
        for thingname, thinglist in sorted(grouped_things.items()):
            nthings = len(thinglist)
            thing = thinglist[0]
            singular, plural = thing.get_numbered_name(nthings, looker, key=thingname)
            thing_names.append(singular if nthings == 1 else plural)
        thing_names = iter_to_str(thing_names, endsep=_(", and"))
        s = _("You see")
        return f"|w{s}:|n {thing_names}" if thing_names else ""

    def get_display_footer(self, looker, **kwargs):
        """
        Get the 'footer' component of the object description. Called by `return_appearance`.

        Args:
            looker (DefaultObject): Object doing the looking.
            **kwargs: Arbitrary data for use when overriding.
        Returns:
            str: The footer display string.

        """
        return ""

    def format_appearance(self, appearance, looker, **kwargs):
        """
        Final processing of the entire appearance string. Called by `return_appearance`.

        Args:
            appearance (str): The compiled appearance string.
            looker (DefaultObject): Object doing the looking.
            **kwargs: Arbitrary data for use when overriding.
        Returns:
            str: The final formatted output.

        """
        return compress_whitespace(appearance).strip()

    def return_appearance(self, looker, **kwargs):
        """
        Main callback used by 'look' for the object to describe itself.
        This formats a description. By default, this looks for the `appearance_template`
        string set on this class and populates it with formatting keys
        'name', 'desc', 'exits', 'characters', 'things' as well as
        (currently empty) 'header'/'footer'. Each of these values are
        retrieved by a matching method `.get_display_*`, such as `get_display_name`,
        `get_display_footer` etc.

        Args:
            looker (DefaultObject): Object doing the looking. Passed into all helper methods.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call. This is passed into all helper methods.

        Returns:
            str: The description of this entity. By default this includes
            the entity's name, description and any contents inside it.

        Notes:
            To simply change the layout of how the object displays itself (like
            adding some line decorations or change colors of different sections),
            you can simply edit `.appearance_template`. You only need to override
            this method (and/or its helpers) if you want to change what is passed
            into the template or want the most control over output.

        """

        if not looker:
            return ""

        # populate the appearance_template string.
        return self.format_appearance(
            self.appearance_template.format(
                name=self.get_display_name(looker, **kwargs),
                extra_name_info=self.get_extra_display_name_info(looker, **kwargs),
                desc=self.get_display_desc(looker, **kwargs),
                header=self.get_display_header(looker, **kwargs),
                footer=self.get_display_footer(looker, **kwargs),
                exits=self.get_display_exits(looker, **kwargs),
                characters=self.get_display_characters(looker, **kwargs),
                things=self.get_display_things(looker, **kwargs),
            ),
            looker,
            **kwargs,
        )

    #
    # Hook methods
    #

    def at_first_save(self):
        """
        This is called by the typeclass system whenever an instance of
        this class is saved for the first time. It is a generic hook
        for calling the startup hooks for the various game entities.
        When overloading you generally don't overload this but
        overload the hooks called by this method.

        """
        self.basetype_setup()
        self.at_object_creation()
        # initialize Attribute/TagProperties
        self.init_evennia_properties()

        if hasattr(self, "_createdict"):
            # this will be set if the object was created by the utils.create function
            # or the spawner. We want these kwargs to override the values set by
            # the initial hooks.
            cdict = self._createdict
            updates = []
            if not cdict.get("key"):
                if not self.db_key:
                    self.db_key = "#%i" % self.dbid
                    updates.append("db_key")
            elif self.key != cdict.get("key"):
                updates.append("db_key")
                self.db_key = cdict["key"]
            if cdict.get("location") and self.location != cdict["location"]:
                self.db_location = cdict["location"]
                updates.append("db_location")
            if cdict.get("home") and self.home != cdict["home"]:
                self.home = cdict["home"]
                updates.append("db_home")
            if cdict.get("destination") and self.destination != cdict["destination"]:
                self.destination = cdict["destination"]
                updates.append("db_destination")
            if updates:
                self.save(update_fields=updates)

            if cdict.get("permissions"):
                self.permissions.batch_add(*cdict["permissions"])
            if cdict.get("locks"):
                self.locks.add(cdict["locks"])
            if cdict.get("aliases"):
                self.aliases.batch_add(*cdict["aliases"])
            if cdict.get("location"):
                cdict["location"].at_object_receive(self, None)
                self.at_post_move(None)
            if cdict.get("tags"):
                # this should be a list of tags, tuples (key, category) or (key, category, data)
                self.tags.batch_add(*cdict["tags"])
            if cdict.get("attributes"):
                # this should be tuples (key, val, ...)
                self.attributes.batch_add(*cdict["attributes"])
            if cdict.get("nattributes"):
                # this should be a dict of nattrname:value
                for key, value in cdict["nattributes"].items():
                    self.nattributes.add(key, value)

            del self._createdict

        # run the post-setup hook
        self.at_object_post_creation()

        self.basetype_posthook_setup()

    # hooks called by the game engine #

    def basetype_setup(self):
        """
        This sets up the default properties of an Object, just before
        the more general at_object_creation.

        You normally don't need to change this unless you change some
        fundamental things like names of permission groups.

        """
        # the default security setup fallback for a generic
        # object. Overload in child for a custom setup. Also creation
        # commands may set this (create an item and you should be its
        # controller, for example)

        self.locks.add(
            ";".join(
                [
                    "control:perm(Developer)",  # edit locks/permissions, delete
                    "examine:perm(Builder)",  # examine properties
                    "view:all()",  # look at object (visibility)
                    "edit:perm(Admin)",  # edit properties/attributes
                    "delete:perm(Admin)",  # delete object
                    "get:all()",  # pick up object
                    "drop:holds()",  # drop only that which you hold
                    "call:true()",  # allow to call commands on this object
                    "tell:perm(Admin)",  # allow emits to this object
                    "puppet:pperm(Developer)",
                    "teleport:true()",
                    "teleport_here:true()",
                ]
            )
        )  # lock down puppeting only to staff by default

    def basetype_posthook_setup(self):
        """
        Called once, after basetype_setup and at_object_creation. This
        should generally not be overloaded unless you are redefining
        how a room/exit/object works. It allows for basetype-like
        setup after the object is created. An example of this is
        EXITs, who need to know keys, aliases, locks etc to set up
        their exit-cmdsets.

        """
        pass

    def at_object_creation(self):
        """
        Called once, when this object is first created. This is the
        normal hook to overload for most object types.

        """
        pass

    def at_object_post_creation(self):
        """
        Called once, when this object is first created and after any attributes, tags, etc.
        that were passed to the `create_object` function or defined in a prototype have been
        applied.

        """
        pass

    def at_object_delete(self):
        """
        Called just before the database object is persistently
        delete()d from the database. If this method returns False,
        deletion is aborted.

        """
        return True

    def at_object_post_spawn(self, prototype=None):
        """
        Called when this object is spawned or updated from a prototype, after all other
        hooks have been run.

        Keyword Args:
            prototype (dict):  The prototype that was used to spawn or update this object.
        """
        pass

    def at_init(self):
        """
        This is always called whenever this object is initiated --
        that is, whenever it its typeclass is cached from memory. This
        happens on-demand first time the object is used or activated
        in some way after being created but also after each server
        restart or reload.

        """
        pass

    def at_cmdset_get(self, **kwargs):
        """
        Called just before cmdsets on this object are requested by the
        command handler. If changes need to be done on the fly to the
        cmdset before passing them on to the cmdhandler, this is the
        place to do it. This is called also if the object currently
        have no cmdsets.

        Keyword Args:
            caller (DefaultObject, DefaultAccount or Session): The object requesting the cmdsets.
            current (CmdSet): The current merged cmdset.
            force_init (bool): If `True`, force a re-build of the cmdset. (seems unused)
            **kwargs: Arbitrary input for overloads.

        """
        pass

    def get_cmdsets(self, caller, current, **kwargs):
        """
        Called by the CommandHandler to get a list of cmdsets to merge.

        Args:
            caller (DefaultObject): The object requesting the cmdsets.
            current (cmdset): The current merged cmdset.
            **kwargs: Arbitrary input for overloads.

        Returns:
            tuple: A tuple of (current, cmdsets), which is probably self.cmdset.current and self.cmdset.cmdset_stack
        """
        return self.cmdset.current, list(self.cmdset.cmdset_stack)

    def at_pre_puppet(self, account, session=None, **kwargs):
        """
        Called just before an Account connects to this object to puppet
        it.

        Args:
            account (DefaultAccount): This is the connecting account.
            session (Session): Session controlling the connection.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        pass

    def at_post_puppet(self, **kwargs):
        """
        Called just after puppeting has been completed and all
        Account<->Object links have been established.

        Args:
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).
        Notes:
            You can use `self.account` and `self.sessions.get()` to get account and sessions at this
            point; the last entry in the list from `self.sessions.get()` is the latest Session
            puppeting this Object.

        """
        self.msg(_("You become |w{key}|n.").format(key=self.key))
        self.account.db._last_puppet = self

    def at_pre_unpuppet(self, **kwargs):
        """
        Called just before beginning to un-connect a puppeting from
        this Account.

        Args:
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).
        Notes:
            You can use `self.account` and `self.sessions.get()` to get
            account and sessions at this point; the last entry in the
            list from `self.sessions.get()` is the latest Session
            puppeting this Object.

        """
        pass

    def at_post_unpuppet(self, account=None, session=None, **kwargs):
        """
        Called just after the Account successfully disconnected from
        this object, severing all connections.

        Args:
            account (DefaultAccount): The account object that just disconnected
                from this object. This can be `None` if this is called
                automatically (such as after a cleanup operation).
            session (Session): Session id controlling the connection that
                just disconnected.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        pass

    def at_server_reload(self):
        """
        This hook is called whenever the server is shutting down for
        restart/reboot. If you want to, for example, save non-persistent
        properties across a restart, this is the place to do it.

        """
        pass

    def at_server_shutdown(self):
        """
        This hook is called whenever the server is shutting down fully
        (i.e. not for a restart).

        """
        pass

    def at_access(self, result, accessing_obj, access_type, **kwargs):
        """
        This is called with the result of an access call, along with
        any kwargs used for that call. The return of this method does
        not affect the result of the lock check. It can be used e.g. to
        customize error messages in a central location or other effects
        based on the access result.

        Args:
            result (bool): The outcome of the access call.
            accessing_obj (Object or Account): The entity trying to gain access.
            access_type (str): The type of access that was requested.
            **kwargs: Arbitrary, optional arguments. Unused by default.

        """
        pass

    # hooks called when moving the object

    def at_pre_move(self, destination, move_type="move", **kwargs):
        """
        Called just before starting to move this object to
        destination. Return False to abort move.

        Args:
            destination (DefaultObject): The object we are moving to
            move_type (str): The type of move. "give", "traverse", etc.
                This is an arbitrary string provided to obj.move_to().
                Useful for altering messages or altering logic depending
                on the kind of movement.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            bool: If we should move or not.

        Notes:
            If this method returns `False` or `None`, the move is cancelled
            before it is even started.

        """
        return True

    def at_pre_object_leave(self, leaving_object, destination, **kwargs):
        """
        Called just before this object is about lose an object that was
        previously 'inside' it. Return False to abort move.

        Args:
            leaving_object (DefaultObject): The object that is about to leave.
            destination (DefaultObject): Where object is going to.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).
        Returns:
            bool: If `leaving_object` should be allowed to leave or not.

        Notes:

            If this method returns `False` or `None`, the move is canceled before
            it even started.

        """
        return True

    def at_pre_object_receive(self, arriving_object, source_location, **kwargs):
        """
        Called just before this object received another object. If this
        method returns `False`, the move is aborted and the moved entity
        remains where it was.

        Args:
            arriving_object (DefaultObject): The object moved into this one
            source_location (DefaultObject): Where `moved_object` came from.
                Note that this could be `None`.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            bool: If False, abort move and `moved_obj` remains where it was.

        Notes:

            If this method returns `False` or `None`, the move is canceled before
            it even started.

        """
        return True

    # deprecated alias
    at_before_move = at_pre_move

    def announce_move_from(self, destination, msg=None, mapping=None, move_type="move", **kwargs):
        """
        Called if the move is to be announced. This is
        called while we are still standing in the old
        location.

        Args:
            destination (DefaultObject): The place we are going to.
            msg (str, optional): a replacement message.
            mapping (dict, optional): additional mapping objects.
            move_type (str): The type of move. "give", "traverse", etc.
                This is an arbitrary string provided to obj.move_to().
                Useful for altering messages or altering logic depending
                on the kind of movement.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Notes:

            You can override this method and call its parent with a
            message to simply change the default message.  In the string,
            you can use the following as mappings:

            - `{object}`: the object which is moving.
            - `{exit}`: the exit from which the object is moving (if found).
            - `{origin}`: the location of the object before the move.
            - `{destination}`: the location of the object after moving.

        """
        if not self.location:
            return
        if msg:
            string = msg
        else:
            string = _("{object} is leaving {origin}, heading for {destination}.")

        location = self.location
        exits = [
            o for o in location.contents if o.location is location and o.destination is destination
        ]
        if not mapping:
            mapping = {}

        mapping.update(
            {
                "object": self,
                "exit": exits[0] if exits else _("somewhere"),
                "origin": location or _("nowhere"),
                "destination": destination or _("nowhere"),
            }
        )

        location.msg_contents(
            (string, {"type": move_type}), exclude=(self,), from_obj=self, mapping=mapping
        )

    def announce_move_to(self, source_location, msg=None, mapping=None, move_type="move", **kwargs):
        """
        Called after the move if the move was not quiet. At this point
        we are standing in the new location.

        Args:
            source_location (DefaultObject): The place we came from
            msg (str, optional): the replacement message if location.
            mapping (dict, optional): additional mapping objects.
            move_type (str): The type of move. "give", "traverse", etc.
                This is an arbitrary string provided to obj.move_to().
                Useful for altering messages or altering logic depending
                on the kind of movement.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Notes:

            You can override this method and call its parent with a
            message to simply change the default message.  In the string,
            you can use the following as mappings (between braces):


            - `{object}`: the object which is moving.
            - `{exit}`: the exit from which the object is moving (if found).
            - `{origin}`: the location of the object before the move.
            - `{destination}`: the location of the object after moving.

        """

        if not source_location and self.location.has_account:
            # This was created from nowhere and added to an account's
            # inventory; it's probably the result of a create command.
            string = _("You now have {name} in your possession.").format(
                name=self.get_display_name(self.location)
            )
            self.location.msg(string)
            return

        if source_location:
            if msg:
                string = msg
            else:
                string = _("{object} arrives to {destination} from {origin}.")
        else:
            string = _("{object} arrives to {destination}.")

        origin = source_location
        destination = self.location
        exits = []
        if origin:
            exits = [
                o
                for o in destination.contents
                if o.location is destination and o.destination is origin
            ]

        if not mapping:
            mapping = {}

        mapping.update(
            {
                "object": self,
                "exit": exits[0] if exits else _("somewhere"),
                "origin": origin or _("nowhere"),
                "destination": destination or _("nowhere"),
            }
        )

        destination.msg_contents(
            (string, {"type": move_type}), exclude=(self,), from_obj=self, mapping=mapping
        )

    def at_post_move(self, source_location, move_type="move", **kwargs):
        """
        Called after move has completed, regardless of quiet mode or
        not.  Allows changes to the object due to the location it is
        now in.

        Args:
            source_location (DefaultObject): Where we came from. This may be `None`.
            move_type (str): The type of move. "give", "traverse", etc.
                This is an arbitrary string provided to obj.move_to().
                Useful for altering messages or altering logic depending
                on the kind of movement.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        pass

    # deprecated
    at_after_move = at_post_move

    def at_object_leave(self, moved_obj, target_location, move_type="move", **kwargs):
        """
        Called just before an object leaves from inside this object

        Args:
            moved_obj (DefaultObject): The object leaving
            target_location (DefaultObject): Where `moved_obj` is going.
            move_type (str): The type of move. "give", "traverse", etc.
                This is an arbitrary string provided to obj.move_to().
                Useful for altering messages or altering logic depending
                on the kind of movement.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        pass

    def at_object_receive(self, moved_obj, source_location, move_type="move", **kwargs):
        """
        Called after an object has been moved into this object.

        Args:
            moved_obj (DefaultObject): The object moved into this one
            source_location (DefaultObject): Where `moved_object` came from.
                Note that this could be `None`.
            move_type (str): The type of move. "give", "traverse", etc.
                This is an arbitrary string provided to obj.move_to().
                Useful for altering messages or altering logic depending
                on the kind of movement.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        pass

    def at_traverse(self, traversing_object, target_location, **kwargs):
        """
        This hook is responsible for handling the actual traversal,
        normally by calling
        `traversing_object.move_to(target_location)`. It is normally
        only implemented by Exit objects. If it returns False (usually
        because `move_to` returned False), `at_post_traverse` below
        should not be called and instead `at_failed_traverse` should be
        called.

        Args:
            traversing_object (DefaultObject): Object traversing us.
            target_location (DefaultObject): Where target is going.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        pass

    def at_post_traverse(self, traversing_object, source_location, **kwargs):
        """
        Called just after an object successfully used this object to
        traverse to another object (i.e. this object is a type of
        Exit)

        Args:
            traversing_object (DefaultObject): The object traversing us.
            source_location (DefaultObject): Where `traversing_object` came from.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Notes:
            The target location should normally be available as `self.destination`.
        """
        pass

    # deprecated
    at_after_traverse = at_post_traverse

    def at_failed_traverse(self, traversing_object, **kwargs):
        """
        This is called if an object fails to traverse this object for
        some reason.

        Args:
            traversing_object (DefaultObject): The object that failed traversing us.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Notes:
            Using the default exits, this hook will not be called if an
            Attribute `err_traverse` is defined - this will in that case be
            read for an error string instead.

        """
        pass

    def at_msg_receive(self, text=None, from_obj=None, **kwargs):
        """
        This hook is called whenever someone sends a message to this
        object using the `msg` method.

        Note that from_obj may be None if the sender did not include
        itself as an argument to the obj.msg() call - so you have to
        check for this. .

        Consider this a pre-processing method before msg is passed on
        to the user session. If this method returns False, the msg
        will not be passed on.

        Args:
            text (str, optional): The message received.
            from_obj (any, optional): The object sending the message.
            **kwargs: This includes any keywords sent to the `msg` method.

        Returns:
            receive (bool): If this message should be received.

        Notes:
            If this method returns False, the `msg` operation
            will abort without sending the message.

        """
        return True

    def at_msg_send(self, text=None, to_obj=None, **kwargs):
        """
        This is a hook that is called when *this* object sends a
        message to another object with `obj.msg(text, to_obj=obj)`.

        Args:
            text (str, optional): Text to send.
            to_obj (any, optional): The object to send to.
            **kwargs: Keywords passed from msg().

        Notes:
            Since this method is executed by `from_obj`, if no `from_obj`
            was passed to `DefaultCharacter.msg` this hook will never
            get called.

        """
        pass

    # hooks called by the default cmdset.

    def get_visible_contents(self, looker, **kwargs):
        """
        DEPRECATED
        Get all contents of this object that a looker can see (whatever that means, by default it
        checks the 'view' and 'search' locks and excludes the looker themselves), grouped by type.
        Helper method to return_appearance.

        Args:
            looker (DefaultObject): The entity looking.
            **kwargs: Passed from `return_appearance`. Unused by default.

        Returns:
            dict: A dict of lists categorized by type. Byt default this
            contains 'exits', 'characters' and 'things'. The elements of these
            lists are the actual objects.

        """

        def _filter_visible(obj_list):
            return [obj for obj in self.filter_visible(obj_list, looker, **kwargs) if obj != looker]

        return {
            "exits": _filter_visible(self.contents_get(content_type="exit")),
            "characters": _filter_visible(self.contents_get(content_type="character")),
            "things": _filter_visible(self.contents_get(content_type="object")),
        }

    def get_content_names(self, looker, **kwargs):
        """
        DEPRECATED
        Get the proper names for all contents of this object. Helper method
        for return_appearance.

        Args:
            looker (DefaultObject): The entity looking.
            **kwargs: Passed from `return_appearance`. Passed into
                `get_display_name` for each found entity.

        Returns:
            dict: A dict of lists categorized by type. Byt default this
            contains 'exits', 'characters' and 'things'. The elements
            of these lists are strings - names of the objects that
            can depend on the looker and also be grouped in the case
            of multiple same-named things etc.

        Notes:
            This method shouldn't add extra coloring to the names beyond what is
            already given by the .get_display_name() (and the .name field) already.
            Per-type coloring can be applied in `return_appearance`.

        """
        # a mapping {'exits': [...], 'characters': [...], 'things': [...]}
        contents_map = self.get_visible_contents(looker, **kwargs)

        character_names = [
            char.get_display_name(looker, **kwargs) for char in contents_map["characters"]
        ]
        exit_names = [exi.get_display_name(looker, **kwargs) for exi in contents_map["exits"]]

        # group all same-named things under one name
        things = defaultdict(list)
        for thing in contents_map["things"]:
            things[thing.get_display_name(looker, **kwargs)].append(thing)

        # pluralize same-named things
        thing_names = []
        for thingname, thinglist in sorted(things.items()):
            nthings = len(thinglist)
            thing = thinglist[0]
            singular, plural = thing.get_numbered_name(nthings, looker, key=thingname)
            thing_names.append(singular if nthings == 1 else plural)

        return {"exits": exit_names, "characters": character_names, "things": thing_names}

    def at_look(self, target, **kwargs):
        """
        Called when this object performs a look. It allows to
        customize just what this means. It will not itself
        send any data.

        Args:
            target (DefaultObject): The target being looked at. This is
                commonly an object or the current location. It will
                be checked for the "view" type access.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call. This will be passed into
                return_appearance, get_display_name and at_desc but is not used
                by default.

        Returns:
            str: A ready-processed look string potentially ready to return to the looker.

        """
        if not target.access(self, "view"):
            try:
                return _("Could not view '{target_name}'.").format(
                    target_name=target.get_display_name(self, **kwargs)
                )
            except AttributeError:
                return _("Could not view '{target_name}'.").format(target_name=target.key)

        description = target.return_appearance(self, **kwargs)

        # the target's at_desc() method.
        # this must be the last reference to target so it may delete itself when acted on.
        target.at_desc(looker=self, **kwargs)

        return description

    def at_desc(self, looker=None, **kwargs):
        """
        This is called whenever someone looks at this object.

        Args:
            looker (Object, optional): The object requesting the description.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        pass

    def at_pre_get(self, getter, **kwargs):
        """
        Called by the default `get` command before this object has been
        picked up.

        Args:
            getter (DefaultObject): The object about to get this object.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            bool: If the object should be gotten or not.

        Notes:
            If this method returns False/None, the getting is cancelled
            before it is even started.
        """
        return True

    # deprecated
    at_before_get = at_pre_get

    def at_get(self, getter, **kwargs):
        """
        Called by the default `get` command when this object has been
        picked up.

        Args:
            getter (DefaultObject): The object getting this object.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Notes:
            This hook cannot stop the pickup from happening. Use
            permissions or the at_pre_get() hook for that.

        """
        pass

    def at_pre_give(self, giver, getter, **kwargs):
        """
        Called by the default `give` command before this object has been
        given.

        Args:
            giver (DefaultObject): The object about to give this object.
            getter (DefaultObject): The object about to get this object.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            shouldgive (bool): If the object should be given or not.

        Notes:
            If this method returns `False` or `None`, the giving is cancelled
            before it is even started.

        """
        return True

    # deprecated
    at_before_give = at_pre_give

    def at_give(self, giver, getter, **kwargs):
        """
        Called by the default `give` command when this object has been
        given.

        Args:
            giver (DefaultObject): The object giving this object.
            getter (DefaultObject): The object getting this object.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Notes:
            This hook cannot stop the give from happening. Use
            permissions or the at_pre_give() hook for that.

        """
        pass

    def at_pre_drop(self, dropper, **kwargs):
        """
        Called by the default `drop` command before this object has been
        dropped.

        Args:
            dropper (DefaultObject): The object which will drop this object.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            bool: If the object should be dropped or not.

        Notes:
            If this method returns `False` or `None`, the dropping is cancelled
            before it is even started.

        """
        if not self.locks.get("drop"):
            # TODO: This if-statment will be removed in Evennia 1.0
            return True
        if not self.access(dropper, "drop", default=False):
            dropper.msg(_("You cannot drop {obj}").format(obj=self.get_display_name(dropper)))
            return False
        return True

    # deprecated
    at_before_drop = at_pre_drop

    def at_drop(self, dropper, **kwargs):
        """
        Called by the default `drop` command when this object has been
        dropped.

        Args:
            dropper (DefaultObject): The object which just dropped this object.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Notes:
            This hook cannot stop the drop from happening. Use
            permissions or the at_pre_drop() hook for that.

        """
        pass

    def at_pre_say(self, message, **kwargs):
        """
        Before the object says something.

        This hook is by default used by the 'say' and 'whisper'
        commands as used by this command it is called before the text
        is said/whispered and can be used to customize the outgoing
        text from the object. Returning `None` aborts the command.

        Args:
            message (str): The suggested say/whisper text spoken by self.
        Keyword Args:
            whisper (bool): If True, this is a whisper rather than
                a say. This is sent by the whisper command by default.
                Other verbal commands could use this hook in similar
                ways.
            receivers (DefaultObject or iterable): If set, this is the target or targets for the
                say/whisper.

        Returns:
            str: The (possibly modified) text to be spoken.

        """
        return message

    # deprecated
    at_before_say = at_pre_say

    def at_say(
        self,
        message,
        msg_self=None,
        msg_location=None,
        receivers=None,
        msg_receivers=None,
        **kwargs,
    ):
        """
        Display the actual say (or whisper) of self.

        This hook should display the actual say/whisper of the object in its
        location.  It should both alert the object (self) and its
        location that some text is spoken.  The overriding of messages or
        `mapping` allows for simple customization of the hook without
        re-writing it completely.

        Args:
            message (str): The message to convey.
            msg_self (bool or str, optional): If boolean True, echo `message` to self. If a string,
                return that message. If False or unset, don't echo to self.
            msg_location (str, optional): The message to echo to self's location.
            receivers (DefaultObject or iterable, optional): An eventual receiver or receivers of the
                message (by default only used by whispers).
            msg_receivers(str): Specific message to pass to the receiver(s). This will parsed
                with the {receiver} placeholder replaced with the given receiver.
        Keyword Args:
            whisper (bool): If this is a whisper rather than a say. Kwargs
                can be used by other verbal commands in a similar way.
            mapping (dict): Pass an additional mapping to the message.

        Notes:


            Messages can contain {} markers. These are substituted against the values
            passed in the `mapping` argument.
            ::

                msg_self = 'You say: "{speech}"'
                msg_location = '{object} says: "{speech}"'
                msg_receivers = '{object} whispers: "{speech}"'

            Supported markers by default:

            - {self}: text to self-reference with (default 'You')
            - {speech}: the text spoken/whispered by self.
            - {object}: the object speaking.
            - {receiver}: replaced with a single receiver only for strings meant for a specific
              receiver (otherwise 'None').
            - {all_receivers}: comma-separated list of all receivers,
              if more than one, otherwise same as receiver
            - {location}: the location where object is.

        """
        msg_type = "say"
        if kwargs.get("whisper", False):
            # whisper mode
            msg_type = "whisper"
            msg_self = (
                _('{self} whisper to {all_receivers}, "|n{speech}|n"')
                if msg_self is True
                else msg_self
            )
            msg_receivers = msg_receivers or _('{object} whispers: "|n{speech}|n"')
            msg_location = None
        else:
            msg_self = _('{self} say, "|n{speech}|n"') if msg_self is True else msg_self
            msg_location = msg_location or _('{object} says, "{speech}"')
            msg_receivers = msg_receivers or message

        custom_mapping = kwargs.get("mapping", {})
        receivers = make_iter(receivers) if receivers else None
        location = self.location

        if msg_self:
            self_mapping = {
                "self": _("You"),
                "object": self.get_display_name(self),
                "location": location.get_display_name(self) if location else None,
                "receiver": None,
                "all_receivers": (
                    ", ".join(recv.get_display_name(self) for recv in receivers)
                    if receivers
                    else None
                ),
                "speech": message,
            }
            self_mapping.update(custom_mapping)
            self.msg(text=(msg_self.format_map(self_mapping), {"type": msg_type}), from_obj=self)

        if receivers and msg_receivers:
            receiver_mapping = {
                "self": _("You"),
                "object": None,
                "location": None,
                "receiver": None,
                "all_receivers": None,
                "speech": message,
            }
            for receiver in make_iter(receivers):
                individual_mapping = {
                    "object": self.get_display_name(receiver),
                    "location": location.get_display_name(receiver),
                    "receiver": receiver.get_display_name(receiver),
                    "all_receivers": (
                        ", ".join(recv.get_display_name(recv) for recv in receivers)
                        if receivers
                        else None
                    ),
                }
                receiver_mapping.update(individual_mapping)
                receiver_mapping.update(custom_mapping)
                receiver.msg(
                    text=(msg_receivers.format_map(receiver_mapping), {"type": msg_type}),
                    from_obj=self,
                )

        if self.location and msg_location:
            location_mapping = {
                "self": _("You"),
                "object": self,
                "location": location,
                "all_receivers": ", ".join(str(recv) for recv in receivers) if receivers else None,
                "receiver": None,
                "speech": message,
            }
            location_mapping.update(custom_mapping)
            exclude = []
            if msg_self:
                exclude.append(self)
            if receivers:
                exclude.extend(receivers)
            self.location.msg_contents(
                text=(msg_location, {"type": msg_type}),
                from_obj=self,
                exclude=exclude,
                mapping=location_mapping,
            )

    def at_rename(self, oldname, newname):
        """
        This Hook is called by @name on a successful rename.

        Args:
            oldname (str): The instance's original name.
            newname (str): The new name for the instance.

        """

        # Clear plural aliases set by DefaultObject.get_numbered_name
        self.aliases.clear(category=self.plural_category)


#
# Base Character object
#


class DefaultCharacter(DefaultObject):
    """
    This implements an Object puppeted by a Session - that is,
    a character avatar controlled by an account.

    """

    # Tuple of types used for indexing inventory contents. Characters generally wouldn't be in
    # anyone's inventory, but this also governs displays in room contents.
    _content_types = ("character",)
    # lockstring of newly created rooms, for easy overloading.
    # Will be formatted with the appropriate attributes.
    lockstring = (
        "puppet:id({character_id}) or pid({account_id}) or perm(Developer) or pperm(Developer);"
        "delete:id({account_id}) or perm(Admin);"
        "edit:pid({account_id}) or perm(Admin)"
    )

    # Used by get_display_desc when self.db.desc is None
    default_description = _("This is a character.")

    @classmethod
    def get_default_lockstring(
        cls, account: "DefaultAccount" = None, caller: "DefaultObject" = None, **kwargs
    ):
        """
        Classmethod called during .create() to determine default locks for the object.

        Args:
            account (DefaultAccount): Account to attribute this object to.
            caller (DefaultObject): The object which is creating this one.
            **kwargs: Arbitrary input.

        Returns:
            str: A lockstring to use for this object.

        """
        pid = f"pid({account.id})" if account else None
        character = kwargs.get("character", None)
        cid = f"id({character})" if character else None

        puppet = "puppet:" + " or ".join(
            [x for x in [pid, cid, "perm(Developer)", "pperm(Developer)"] if x]
        )
        delete = "delete:" + " or ".join([x for x in [pid, "perm(Admin)"] if x])
        edit = "edit:" + " or ".join([x for x in [pid, "perm(Admin)"] if x])

        return ";".join([puppet, delete, edit])

    @classmethod
    def create(
        cls,
        key,
        account: "DefaultAccount" = None,
        caller: "DefaultObject" = None,
        method: str = "create",
        **kwargs,
    ):
        """
        Creates a basic Character with default parameters, unless otherwise
        specified or extended.

        Provides a friendlier interface to the utils.create_character() function.

        Args:
            key (str): Name of the new Character.
            account (obj, optional): Account to associate this Character with.
                If unset supplying None-- it will
                change the default lockset and skip creator attribution.

        Keyword Args:
            description (str): Brief description for this object.
            ip (str): IP address of creator (for object auditing).
            All other kwargs will be passed into the create_object call.

        Returns:
            tuple: `(new_character, errors)`. On error, the `new_character` is `None` and
            `errors` is a `list` of error strings (an empty list otherwise).

        """
        errors = []
        obj = None
        # Get IP address of creator, if available
        ip = kwargs.pop("ip", "")

        # If no typeclass supplied, use this class
        kwargs["typeclass"] = kwargs.pop("typeclass", cls)

        # Normalize to latin characters and validate, if necessary, the supplied key
        key = cls.normalize_name(key)

        if val_err := cls.validate_name(key, account=account):
            errors.append(val_err)
            return obj, errors

        # Set the supplied key as the name of the intended object
        kwargs["key"] = key

        # Get permissions
        kwargs["permissions"] = kwargs.get("permissions", settings.PERMISSION_ACCOUNT_DEFAULT)

        # Get description if provided
        description = kwargs.pop("description", "")

        # Get locks if provided
        locks = kwargs.pop("locks", "")

        try:
            # Check to make sure account does not have too many chars
            if account:
                avail = account.check_available_slots()
                if avail:
                    errors.append(avail)
                    return obj, errors

            # Create the Character
            obj = create.create_object(**kwargs)

            # Record creator id and creation IP
            if ip:
                obj.db.creator_ip = ip
            if account:
                obj.db.creator_id = account.id
                account.characters.add(obj)

            # Add locks
            if not locks:
                # Allow only the character itself and the creator account to puppet this character
                # (and Developers).
                locks = cls.get_default_lockstring(account=account, character=obj)

            if locks:
                obj.locks.add(locks)

            # Set description if provided
            if description:
                obj.db.desc = description

        except Exception as e:
            errors.append(f"An error occurred while creating '{key}' object: {e}")
            logger.log_trace()

        return obj, errors

    @classmethod
    def normalize_name(cls, name):
        """
        Normalize the character name prior to creating.

        Args:
            name (str) : The name of the character

        Returns:
            str : A valid, latinized name.

        Notes:

            The main purpose of this is to make sure that character names are not created with
            special unicode characters that look visually identical to latin charaters. This could
            be used to impersonate other characters.

            This method should be refactored to support i18n for non-latin names, but as we
            (currently) have no bug reports requesting better support of non-latin character sets,
            requiring character names to be latinified is an acceptable default option.

        """

        from evennia.utils.utils import latinify

        latin_name = latinify(name, default="X")
        return latin_name

    @classmethod
    def validate_name(cls, name, account=None) -> typing.Optional[str]:
        """
        Validate the character name prior to creating. Overload this function to add custom validators

        Args:
            name (str) : The name of the character
        Keyword Args:
            account (DefaultAccount, optional) : The account creating the character.
        Returns:
            str or None: A non-empty error message if there is a problem, otherwise `None`.

        """
        if account and cls.objects.filter_family(db_key__iexact=name):
            return _("|rA character named '|w{name}|r' already exists.|n").format(name=name)

    def basetype_setup(self):
        """
        Setup character-specific security.

        You should normally not need to overload this, but if you do,
        make sure to reproduce at least the two last commands in this
        method (unless you want to fundamentally change how a
        Character object works).

        """
        super().basetype_setup()
        self.locks.add(
            ";".join(
                [
                    "get:false()",
                    "call:false()",
                    "teleport:perm(Admin)",
                    "teleport_here:perm(Admin)",
                ]
            )  # noone can pick up the character
        )  # no commands can be called on character from outside
        # add the default cmdset
        self.cmdset.add_default(settings.CMDSET_CHARACTER, persistent=True)

    def at_post_move(self, source_location, move_type="move", **kwargs):
        """
        We make sure to look around after a move.

        """
        if self.location.access(self, "view"):
            self.msg(text=(self.at_look(self.location), {"type": "look"}))

    # deprecated
    at_after_move = at_post_move

    def at_pre_puppet(self, account, session=None, **kwargs):
        """
        Return the character from storage in None location in `at_post_unpuppet`.
        Args:
            account (DefaultAccount): This is the connecting account.
            session (Session): Session controlling the connection.

        """
        if self.location is None:
            # Make sure character's location is never None before being puppeted.
            # Return to last location (or home, which should always exist)
            location = self.db.prelogout_location if self.db.prelogout_location else self.home
            if location:
                self.location = location
                self.location.at_object_receive(self, None)

        if self.location:
            self.db.prelogout_location = self.location  # save location again to be sure.
        else:
            account.msg(
                _("|r{obj} has no location and no home is set.|n").format(obj=self), session=session
            )

    def at_post_puppet(self, **kwargs):
        """
        Called just after puppeting has been completed and all
        Account<->Object links have been established.

        Args:
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).
        Notes:

            You can use `self.account` and `self.sessions.get()` to get
            account and sessions at this point; the last entry in the
            list from `self.sessions.get()` is the latest Session
            puppeting this Object.

        """
        self.msg(_("\nYou become |c{name}|n.\n").format(name=self.key))
        self.msg((self.at_look(self.location), {"type": "look"}), options=None)

        def message(obj, from_obj):
            obj.msg(
                _("{name} has entered the game.").format(name=self.get_display_name(obj)),
                from_obj=from_obj,
            )

        self.location.for_contents(message, exclude=[self], from_obj=self)

    def at_post_unpuppet(self, account=None, session=None, **kwargs):
        """
        We stove away the character when the account goes ooc/logs off,
        otherwise the character object will remain in the room also
        after the account logged off ("headless", so to say).

        Args:
            account (DefaultAccount): The account object that just disconnected
                from this object.
            session (Session): Session controlling the connection that
                just disconnected.
        Keyword Args:
            reason (str): If given, adds a reason for the unpuppet. This
                is set when the user is auto-unpuppeted due to being link-dead.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        if not self.sessions.count():
            # only remove this char from grid if no sessions control it anymore.
            if self.location:

                def message(obj, from_obj):
                    obj.msg(
                        _("{name} has left the game{reason}.").format(
                            name=self.get_display_name(obj),
                            reason=kwargs.get("reason", ""),
                        ),
                        from_obj=from_obj,
                    )

                self.location.for_contents(message, exclude=[self], from_obj=self)
                self.db.prelogout_location = self.location
                self.location = None

    @property
    def idle_time(self):
        """
        Returns the idle time of the least idle session in seconds. If
        no sessions are connected it returns nothing.

        """
        idle = [session.cmd_last_visible for session in self.sessions.all()]
        if idle:
            return time.time() - float(max(idle))
        return None

    @property
    def connection_time(self):
        """
        Returns the maximum connection time of all connected sessions
        in seconds. Returns nothing if there are no sessions.

        """
        conn = [session.conn_time for session in self.sessions.all()]
        if conn:
            return time.time() - float(min(conn))
        return None


#
# Base Room object


class DefaultRoom(DefaultObject):
    """
    This is the base room object. It's just like any Object except its
    location is always `None`.
    """

    # A tuple of strings used for indexing this object inside an inventory.
    # Generally, a room isn't expected to HAVE a location, but maybe in some games?
    _content_types = ("room",)

    # Used by get_display_desc when self.db.desc is None
    default_description = _("This is a room.")

    @classmethod
    def create(
        cls,
        key: str,
        account: "DefaultAccount" = None,
        caller: DefaultObject = None,
        method: str = "create",
        **kwargs,
    ):
        """
        Creates a basic Room with default parameters, unless otherwise
        specified or extended.

        Provides a friendlier interface to the utils.create_object() function.

        Args:
            key (str): Name of the new Room.

        Keyword Args:
            account (DefaultAccount, optional): Account to associate this Room with. If
                given, it will be given specific control/edit permissions to this
                object (along with normal Admin perms). If not given, default
            caller (DefaultObject): The object which is creating this one.
            description (str): Brief description for this object.
            ip (str): IP address of creator (for object auditing).
            method (str): The method used to create the room. Defaults to "create".

        Returns:
            tuple: A tuple `(Object, error)` with the newly created Room of the given typeclass,
            or `None` if there was an error. If there was an error, `error` will be a list of
            error strings.

        """
        errors = []
        obj = None

        # Get IP address of creator, if available
        ip = kwargs.pop("ip", "")

        # If no typeclass supplied, use this class
        kwargs["typeclass"] = kwargs.pop("typeclass", cls)

        # Set the supplied key as the name of the intended object
        kwargs["key"] = key

        # Get who to send errors to
        kwargs["report_to"] = kwargs.pop("report_to", account)

        # Get description, if provided
        description = kwargs.pop("description", "")

        # get locks if provided
        locks = kwargs.pop("locks", "")

        try:
            # Create the Room
            obj = create.create_object(**kwargs)

            # Add locks
            if not locks:
                locks = cls.get_default_lockstring(account=account, caller=caller, room=obj)
            if locks:
                obj.locks.add(locks)

            # Record creator id and creation IP
            if ip:
                obj.db.creator_ip = ip
            if account:
                obj.db.creator_id = account.id

            # Set description if provided
            if description:
                obj.db.desc = description

        except Exception as e:
            errors.append(f"An error occurred while creating '{key}' object: {e}")
            logger.log_trace()

        return obj, errors

    def basetype_setup(self):
        """
        Simple room setup setting locks to make sure the room cannot be picked up.

        """

        super().basetype_setup()
        self.locks.add(
            ";".join(["get:false()", "puppet:false()", "teleport:false()", "teleport_here:true()"])
        )  # would be weird to puppet a room ...
        self.location = None


#
# Default Exit command, used by the base exit object
#


class ExitCommand(_COMMAND_DEFAULT_CLASS):
    """
    This is a command that simply cause the caller to traverse
    the object it is attached to.

    """

    obj = None

    def func(self):
        """
        Default exit traverse if no syscommand is defined.
        """

        if self.obj.access(self.caller, "traverse"):
            # we may traverse the exit.
            self.obj.at_traverse(self.caller, self.obj.destination)
            SIGNAL_EXIT_TRAVERSED.send(sender=self.obj, traverser=self.caller)
        else:
            # exit is locked
            if self.obj.db.err_traverse:
                # if exit has a better error message, let's use it.
                self.caller.msg(self.obj.db.err_traverse)
            else:
                # No shorthand error message. Call hook.
                self.obj.at_failed_traverse(self.caller)

    def get_extra_info(self, caller, **kwargs):
        """
        Shows a bit of information on where the exit leads.

        Args:
            caller (DefaultObject): The object (usually a character) that entered an ambiguous command.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            str: A string with identifying information to disambiguate the command, conventionally
            with a preceding space.

        """
        if self.obj.destination:
            return _(" (exit to {destination})").format(
                destination=self.obj.destination.get_display_name(caller, **kwargs)
            )
        else:
            return " (%s)" % self.obj.get_display_name(caller, **kwargs)


#
# Base Exit object


class DefaultExit(DefaultObject):
    """
    This is the base exit object - it connects a location to another.
    This is done by the exit assigning a "command" on itself with the
    same name as the exit object (to do this we need to remember to
    re-create the command when the object is cached since it must be
    created dynamically depending on what the exit is called). This
    command (which has a high priority) will thus allow us to traverse
    exits simply by giving the exit-object's name on its own.

    """

    _content_types = ("exit",)
    exit_command = ExitCommand
    priority = 101

    # Used by get_display_desc when self.db.desc is None
    default_description = _("This is an exit.")

    # Helper classes and methods to implement the Exit. These need not
    # be overloaded unless one want to change the foundation for how
    # Exits work. See the end of the class for hook methods to overload.

    def create_exit_cmdset(self, exidbobj):
        """
        Helper function for creating an exit command set + command.

        The command of this cmdset has the same name as the Exit
        object and allows the exit to react when the account enter the
        exit's name, triggering the movement between rooms.

        Args:
            exidbobj (DefaultObject): The DefaultExit object to base the command on.

        """

        # create an exit command. We give the properties here,
        # to always trigger metaclass preparations
        cmd = self.exit_command(
            key=exidbobj.db_key.strip().lower(),
            aliases=exidbobj.aliases.all(),
            locks=str(exidbobj.locks),
            auto_help=False,
            destination=exidbobj.db_destination,
            arg_regex=r"^$",
            is_exit=True,
            obj=exidbobj,
        )
        # create a cmdset
        exit_cmdset = cmdset.CmdSet(None)
        exit_cmdset.key = "ExitCmdSet"
        exit_cmdset.priority = self.priority
        exit_cmdset.duplicates = True
        # add command to cmdset
        exit_cmdset.add(cmd)
        return exit_cmdset

    # Command hooks

    @classmethod
    def create(
        cls,
        key: str,
        location: DefaultRoom = None,
        destination: DefaultRoom = None,
        account: "DefaultAccount" = None,
        caller: DefaultObject = None,
        method: str = "create",
        **kwargs,
    ) -> tuple[typing.Optional["DefaultExit"], list[str]]:
        """
        Creates a basic Exit with default parameters, unless otherwise
        specified or extended.

        Provides a friendlier interface to the utils.create_object() function.

        Args:
            key (str): Name of the new Exit, as it should appear from the
                source room.
            location (Room): The room to create this exit in.

        Keyword Args:
            account (DefaultAccountDB): Account to associate this Exit with.
            caller (DefaultObject): The Object creating this Object.
            description (str): Brief description for this object.
            ip (str): IP address of creator (for object auditing).
            destination (Room): The room to which this exit should go.

        Returns:
            tuple: A tuple `(Object, errors)`, where the object is the newly
            created exit of the given typeclass, or `None` if there was an error.
            If there was an error, `errors` will be a list of error strings.

        """
        errors = []
        obj = None

        # Get IP address of creator, if available
        ip = kwargs.pop("ip", "")

        # If no typeclass supplied, use this class
        kwargs["typeclass"] = kwargs.pop("typeclass", cls)

        # Set the supplied key as the name of the intended object
        kwargs["key"] = key

        # Get who to send errors to
        kwargs["report_to"] = kwargs.pop("report_to", account)

        # Set to/from rooms
        kwargs["location"] = location
        kwargs["destination"] = destination

        description = kwargs.pop("description", "")

        locks = kwargs.get("locks", "")

        try:
            # Create the Exit
            obj = create.create_object(**kwargs)

            # Set appropriate locks
            if not locks:
                locks = cls.get_default_lockstring(account=account, caller=caller, exit=obj)
            if locks:
                obj.locks.add(locks)

            # Record creator id and creation IP
            if ip:
                obj.db.creator_ip = ip
            if account:
                obj.db.creator_id = account.id

            # Set description if provided
            if description:
                obj.db.desc = description

        except Exception as e:
            errors.append(f"An error occurred while creating this '{key}' object: {e}")
            logger.log_err(e)

        return obj, errors

    def basetype_setup(self):
        """
        Setup exit-security.

        You should normally not need to overload this - if you do make
        sure you include all the functionality in this method.

        """
        super().basetype_setup()

        # setting default locks (overload these in at_object_creation()
        self.locks.add(
            ";".join(
                [
                    "puppet:false()",  # would be weird to puppet an exit ...
                    "traverse:all()",  # who can pass through exit by default
                    "get:false()",  # noone can pick up the exit
                    "teleport:false()",
                    "teleport_here:false()",
                ]
            )
        )

        # an exit should have a destination - try to make sure it does
        if self.location and not self.destination:
            self.destination = self.location

    def at_cmdset_get(self, **kwargs):
        """
        Called just before cmdsets on this object are requested by the
        command handler. If changes need to be done on the fly to the
        cmdset before passing them on to the cmdhandler, this is the
        place to do it. This is called also if the object currently
        has no cmdsets.

        Keyword Args:
            caller (DefaultObject, DefaultAccount or Session): The object requesting the cmdsets.
            current (CmdSet): The current merged cmdset.
            force_init (bool): If `True`, force a re-build of the cmdset
                (for example to update aliases).

        """

        if "force_init" in kwargs or not self.cmdset.has_cmdset("ExitCmdSet", must_be_default=True):
            # we are resetting, or no exit-cmdset was set. Create one dynamically.
            self.cmdset.add_default(self.create_exit_cmdset(self), persistent=False)

    def at_init(self):
        """
        This is called when this objects is re-loaded from cache. When
        that happens, we make sure to remove any old ExitCmdSet cmdset
        (this most commonly occurs when renaming an existing exit)

        """
        self.cmdset.remove_default()

    def at_traverse(self, traversing_object, target_location, **kwargs):
        """
        This implements the actual traversal. The traverse lock has
        already been checked (in the Exit command) at this point.

        Args:
            traversing_object (DefaultObject): Object traversing us.
            target_location (DefaultObject): Where target is going.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        source_location = traversing_object.location
        if traversing_object.move_to(target_location, move_type="traverse", exit_obj=self):
            self.at_post_traverse(traversing_object, source_location)
        else:
            if self.db.err_traverse:
                # if exit has a better error message, let's use it.
                traversing_object.msg(self.db.err_traverse)
            else:
                # No shorthand error message. Call hook.
                self.at_failed_traverse(traversing_object)

    def at_failed_traverse(self, traversing_object, **kwargs):
        """
        Overloads the default hook to implement a simple default error message.

        Args:
            traversing_object (DefaultObject): The object that failed traversing us.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Notes:
            Using the default exits, this hook will not be called if an
            Attribute `err_traverse` is defined - this will in that case be
            read for an error string instead.

        """
        traversing_object.msg(_("You cannot go there."))

    def get_return_exit(self, return_all=False):
        """
        Get the exits that pair with this one in its destination room
        (i.e. returns to its location)

        Args:
            return_all (bool): Whether to return available results as a
                               queryset or single matching exit.

        Returns:
            Exit or queryset: The matching exit(s). If `return_all` is `True`, this
            will be a queryset of all matching exits. Otherwise, it will be the first Exit matched.

        """
        query = ObjectDB.objects.filter(db_location=self.destination, db_destination=self.location)
        if return_all:
            return query
        return query.first()
