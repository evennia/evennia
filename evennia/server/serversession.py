"""
This defines a the Server's generic session object. This object represents
a connection to the outside world but don't know any details about how the
connection actually happens (so it's the same for telnet, web, ssh etc).

It is stored on the Server side (as opposed to protocol-specific sessions which
are stored on the Portal side)
"""
import weakref
import time
from django.utils import timezone
from django.conf import settings
from evennia.comms.models import ChannelDB
from evennia.utils import logger
from evennia.utils.utils import make_iter, lazy_property
from evennia.commands.cmdsethandler import CmdSetHandler
from evennia.server.session import Session
from evennia.scripts.monitorhandler import MONITOR_HANDLER

_GA = object.__getattribute__
_SA = object.__setattr__
_ObjectDB = None
_ANSI = None

# i18n
from django.utils.translation import ugettext as _

# Handlers for Session.db/ndb operation


class NDbHolder(object):
    """Holder for allowing property access of attributes"""

    def __init__(self, obj, name, manager_name="attributes"):
        _SA(self, name, _GA(obj, manager_name))
        _SA(self, "name", name)

    def __getattribute__(self, attrname):
        if attrname == "all":
            # we allow to overload our default .all
            attr = _GA(self, _GA(self, "name")).get("all")
            return attr if attr else _GA(self, "all")
        return _GA(self, _GA(self, "name")).get(attrname)

    def __setattr__(self, attrname, value):
        _GA(self, _GA(self, "name")).add(attrname, value)

    def __delattr__(self, attrname):
        _GA(self, _GA(self, "name")).remove(attrname)

    def get_all(self):
        return _GA(self, _GA(self, "name")).all()

    all = property(get_all)


class NAttributeHandler(object):
    """
    NAttributeHandler version without recache protection.
    This stand-alone handler manages non-database saving.
    It is similar to `AttributeHandler` and is used
    by the `.ndb` handler in the same way as `.db` does
    for the `AttributeHandler`.
    """

    def __init__(self, obj):
        """
        Initialized on the object
        """
        self._store = {}
        self.obj = weakref.proxy(obj)

    def has(self, key):
        """
        Check if object has this attribute or not.

        Args:
            key (str): The Nattribute key to check.

        Returns:
            has_nattribute (bool): If Nattribute is set or not.

        """
        return key in self._store

    def get(self, key, default=None):
        """
        Get the named key value.

        Args:
            key (str): The Nattribute key to get.

        Returns:
            the value of the Nattribute.

        """
        return self._store.get(key, default)

    def add(self, key, value):
        """
        Add new key and value.

        Args:
            key (str): The name of Nattribute to add.
            value (any): The value to store.

        """
        self._store[key] = value

    def remove(self, key):
        """
        Remove Nattribute from storage.

        Args:
            key (str): The name of the Nattribute to remove.

        """
        if key in self._store:
            del self._store[key]

    def clear(self):
        """
        Remove all NAttributes from handler.

        """
        self._store = {}

    def all(self, return_tuples=False):
        """
        List the contents of the handler.

        Args:
            return_tuples (bool, optional): Defines if the Nattributes
                are returns as a list of keys or as a list of `(key, value)`.

        Returns:
            nattributes (list): A list of keys `[key, key, ...]` or a
                list of tuples `[(key, value), ...]` depending on the
                setting of `return_tuples`.

        """
        if return_tuples:
            return [(key, value) for (key, value) in self._store.items() if not key.startswith("_")]
        return [key for key in self._store if not key.startswith("_")]


# -------------------------------------------------------------
# Server Session
# -------------------------------------------------------------


class ServerSession(Session):
    """
    This class represents an account's session and is a template for
    individual protocols to communicate with Evennia.

    Each account gets a session assigned to them whenever they connect
    to the game server. All communication between game and account goes
    through their session.

    """

    def __init__(self):
        """Initiate to avoid AttributeErrors down the line"""
        self.puppet = None
        self.account = None
        self.cmdset_storage_string = ""
        self.cmdset = CmdSetHandler(self, True)

    def __cmdset_storage_get(self):
        return [path.strip() for path in self.cmdset_storage_string.split(",")]

    def __cmdset_storage_set(self, value):
        self.cmdset_storage_string = ",".join(str(val).strip() for val in make_iter(value))

    cmdset_storage = property(__cmdset_storage_get, __cmdset_storage_set)

    def at_sync(self):
        """
        This is called whenever a session has been resynced with the
        portal.  At this point all relevant attributes have already
        been set and self.account been assigned (if applicable).

        Since this is often called after a server restart we need to
        set up the session as it was.

        """
        global _ObjectDB
        if not _ObjectDB:
            from evennia.objects.models import ObjectDB as _ObjectDB

        super(ServerSession, self).at_sync()
        if not self.logged_in:
            # assign the unloggedin-command set.
            self.cmdset_storage = settings.CMDSET_UNLOGGEDIN

        self.cmdset.update(init_mode=True)

        if self.puid:
            # reconnect puppet (puid is only set if we are coming
            # back from a server reload). This does all the steps
            # done in the default @ic command but without any
            # hooks, echoes or access checks.
            obj = _ObjectDB.objects.get(id=self.puid)
            obj.sessions.add(self)
            obj.account = self.account
            self.puid = obj.id
            self.puppet = obj
            # obj.scripts.validate()
            obj.locks.cache_lock_bypass(obj)

    def at_login(self, account):
        """
        Hook called by sessionhandler when the session becomes authenticated.

        Args:
            account (Account): The account associated with the session.

        """
        self.account = account
        self.uid = self.account.id
        self.uname = self.account.username
        self.logged_in = True
        self.conn_time = time.time()
        self.puid = None
        self.puppet = None
        self.cmdset_storage = settings.CMDSET_SESSION

        # Update account's last login time.
        self.account.last_login = timezone.now()
        self.account.save()

        # add the session-level cmdset
        self.cmdset = CmdSetHandler(self, True)

    def at_disconnect(self, reason=None):
        """
        Hook called by sessionhandler when disconnecting this session.

        """
        if self.logged_in:
            account = self.account
            if self.puppet:
                account.unpuppet_object(self)
            uaccount = account
            uaccount.last_login = timezone.now()
            uaccount.save()
            # calling account hook
            account.at_disconnect(reason)
            self.logged_in = False
            if not self.sessionhandler.sessions_from_account(account):
                # no more sessions connected to this account
                account.is_connected = False
            # this may be used to e.g. delete account after disconnection etc
            account.at_post_disconnect()
            # remove any webclient settings monitors associated with this
            # session
            MONITOR_HANDLER.remove(account, "_saved_webclient_options", self.sessid)

    def get_account(self):
        """
        Get the account associated with this session

        Returns:
            account (Account): The associated Account.

        """
        return self.logged_in and self.account

    def get_puppet(self):
        """
        Get the in-game character associated with this session.

        Returns:
            puppet (Object): The puppeted object, if any.

        """
        return self.logged_in and self.puppet

    get_character = get_puppet

    def get_puppet_or_account(self):
        """
        Get puppet or account.

        Returns:
            controller (Object or Account): The puppet if one exists,
                otherwise return the account.

        """
        if self.logged_in:
            return self.puppet if self.puppet else self.account
        return None

    def log(self, message, channel=True):
        """
        Emits session info to the appropriate outputs and info channels.

        Args:
            message (str): The message to log.
            channel (bool, optional): Log to the CHANNEL_CONNECTINFO channel
                in addition to the server log.

        """
        cchan = channel and settings.CHANNEL_CONNECTINFO
        if cchan:
            try:
                cchan = ChannelDB.objects.get_channel(cchan["key"])
                cchan.msg("[%s]: %s" % (cchan.key, message))
            except Exception:
                logger.log_trace()
        logger.log_info(message)

    def get_client_size(self):
        """
        Return eventual eventual width and height reported by the
        client. Note that this currently only deals with a single
        client window (windowID==0) as in a traditional telnet session.

        """
        flags = self.protocol_flags
        width = flags.get("SCREENWIDTH", {}).get(0, settings.CLIENT_DEFAULT_WIDTH)
        height = flags.get("SCREENHEIGHT", {}).get(0, settings.CLIENT_DEFAULT_HEIGHT)
        return width, height

    def update_session_counters(self, idle=False):
        """
        Hit this when the user enters a command in order to update
        idle timers and command counters.

        """
        # Idle time used for timeout calcs.
        self.cmd_last = time.time()

        # Store the timestamp of the user's last command.
        if not idle:
            # Increment the user's command counter.
            self.cmd_total += 1
            # Account-visible idle time, not used in idle timeout calcs.
            self.cmd_last_visible = self.cmd_last

    def update_flags(self, **kwargs):
        """
        Update the protocol_flags and sync them with Portal.

        Kwargs:
            key, value - A key:value pair to set in the
                protocol_flags dictionary.

        Notes:
            Since protocols can vary, no checking is done
            as to the existene of the flag or not. The input
            data should have been validated before this call.

        """
        if kwargs:
            self.protocol_flags.update(kwargs)
            self.sessionhandler.session_portal_sync(self)

    def data_out(self, **kwargs):
        """
        Sending data from Evennia->Client

        Kwargs:
            text (str or tuple)
            any (str or tuple): Send-commands identified
                by their keys. Or "options", carrying options
                for the protocol(s).

        """
        self.sessionhandler.data_out(self, **kwargs)

    def data_in(self, **kwargs):
        """
        Receiving data from the client, sending it off to
        the respective inputfuncs.

        Kwargs:
            kwargs (any): Incoming data from protocol on
                the form `{"commandname": ((args), {kwargs}),...}`
        Notes:
            This method is here in order to give the user
            a single place to catch and possibly process all incoming data from
            the client. It should usually always end by sending
            this data off to `self.sessionhandler.call_inputfuncs(self, **kwargs)`.
        """
        self.sessionhandler.call_inputfuncs(self, **kwargs)

    def msg(self, text=None, **kwargs):
        """
        Wrapper to mimic msg() functionality of Objects and Accounts.

        Args:
            text (str): String input.

        Kwargs:
            any (str or tuple): Send-commands identified
                by their keys. Or "options", carrying options
                for the protocol(s).

        """
        # this can happen if this is triggered e.g. a command.msg
        # that auto-adds the session, we'd get a kwarg collision.
        kwargs.pop("session", None)
        kwargs.pop("from_obj", None)
        if text is not None:
            self.data_out(text=text, **kwargs)
        else:
            self.data_out(**kwargs)

    def execute_cmd(self, raw_string, session=None, **kwargs):
        """
        Do something as this object. This method is normally never
        called directly, instead incoming command instructions are
        sent to the appropriate inputfunc already at the sessionhandler
        level. This method allows Python code to inject commands into
        this stream, and will lead to the text inputfunc be called.

        Args:
            raw_string (string): Raw command input
            session (Session): This is here to make API consistent with
                Account/Object.execute_cmd. If given, data is passed to
                that Session, otherwise use self.
        Kwargs:
            Other keyword arguments will be added to the found command
            object instace as variables before it executes.  This is
            unused by default Evennia but may be used to set flags and
            change operating paramaters for commands at run-time.

        """
        # inject instruction into input stream
        kwargs["text"] = ((raw_string,), {})
        self.sessionhandler.data_in(session or self, **kwargs)

    def __eq__(self, other):
        """Handle session comparisons"""
        try:
            return self.address == other.address
        except AttributeError:
            return False

    def __hash__(self):
        """
        Python 3 requires that any class which implements __eq__ must also
        implement __hash__ and that the corresponding hashes for equivalent
        instances are themselves equivalent.

        """
        return hash(self.address)

    def __ne__(self, other):
        try:
            return self.address != other.address
        except AttributeError:
            return True

    def __str__(self):
        """
        String representation of the user session class. We use
        this a lot in the server logs.

        """
        symbol = ""
        if self.logged_in and hasattr(self, "account") and self.account:
            symbol = "(#%s)" % self.account.id
        try:
            if hasattr(self.address, "__iter__"):
                address = ":".join([str(part) for part in self.address])
            else:
                address = self.address
        except Exception:
            address = self.address
        return "%s%s@%s" % (self.uname, symbol, address)

    def __repr__(self):
        return "%s" % str(self)

    # Dummy API hooks for use during non-loggedin operation

    def at_cmdset_get(self, **kwargs):
        """
        A dummy hook all objects with cmdsets need to have
        """

        pass

    # Mock db/ndb properties for allowing easy storage on the session
    # (note that no databse is involved at all here. session.db.attr =
    # value just saves a normal property in memory, just like ndb).

    @lazy_property
    def nattributes(self):
        return NAttributeHandler(self)

    @lazy_property
    def attributes(self):
        return self.nattributes

    # @property
    def ndb_get(self):
        """
        A non-persistent store (ndb: NonDataBase). Everything stored
        to this is guaranteed to be cleared when a server is shutdown.
        Syntax is same as for the _get_db_holder() method and
        property, e.g. obj.ndb.attr = value etc.

        """
        try:
            return self._ndb_holder
        except AttributeError:
            self._ndb_holder = NDbHolder(self, "nattrhandler", manager_name="nattributes")
            return self._ndb_holder

    # @ndb.setter
    def ndb_set(self, value):
        """
        Stop accidentally replacing the db object

        Args:
            value (any): A value to store in the ndb.

        """
        string = "Cannot assign directly to ndb object! "
        string += "Use ndb.attr=value instead."
        raise Exception(string)

    # @ndb.deleter
    def ndb_del(self):
        """Stop accidental deletion."""
        raise Exception("Cannot delete the ndb object!")

    ndb = property(ndb_get, ndb_set, ndb_del)
    db = property(ndb_get, ndb_set, ndb_del)

    # Mock access method for the session (there is no lock info
    # at this stage, so we just present a uniform API)
    def access(self, *args, **kwargs):
        """Dummy method to mimic the logged-in API."""
        return True
