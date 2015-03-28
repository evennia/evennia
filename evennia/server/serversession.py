"""
This defines a the Server's generic session object. This object represents
a connection to the outside world but don't know any details about how the
connection actually happens (so it's the same for telnet, web, ssh etc).

It is stored on the Server side (as opposed to protocol-specific sessions which
are stored on the Portal side)
"""

import re
from time import time
from django.utils import timezone
from django.conf import settings
from evennia.comms.models import ChannelDB
from evennia.utils import logger
from evennia.utils.inlinefunc import parse_inlinefunc
from evennia.utils.utils import make_iter
from evennia.commands.cmdhandler import cmdhandler
from evennia.commands.cmdsethandler import CmdSetHandler
from evennia.server.session import Session

_IDLE_COMMAND = settings.IDLE_COMMAND
_GA = object.__getattribute__
_ObjectDB = None
_ANSI = None
_INLINEFUNC_ENABLED = settings.INLINEFUNC_ENABLED
_RE_SCREENREADER_REGEX = re.compile(r"%s" % settings.SCREENREADER_REGEX_STRIP, re.DOTALL + re.MULTILINE)

# i18n
from django.utils.translation import ugettext as _


#------------------------------------------------------------
# Server Session
#------------------------------------------------------------

class ServerSession(Session):
    """
    This class represents a player's session and is a template for
    individual protocols to communicate with Evennia.

    Each player gets a session assigned to them whenever they connect
    to the game server. All communication between game and player goes
    through their session.

    """
    def __init__(self):
        "Initiate to avoid AttributeErrors down the line"
        self.puppet = None
        self.player = None
        self.cmdset_storage_string = ""
        self.cmdset = CmdSetHandler(self, True)

    def __cmdset_storage_get(self):
        return [path.strip() for path in self.cmdset_storage_string.split(',')]

    def __cmdset_storage_set(self, value):
        self.cmdset_storage_string = ",".join(str(val).strip() for val in make_iter(value))
    cmdset_storage = property(__cmdset_storage_get, __cmdset_storage_set)

    def at_sync(self):
        """
        This is called whenever a session has been resynced with the portal.
        At this point all relevant attributes have already been set and
        self.player been assigned (if applicable).

        Since this is often called after a server restart we need to set up
        the session as it was.
        """
        global _ObjectDB
        if not _ObjectDB:
            from evennia.objects.models import ObjectDB as _ObjectDB

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
            obj.sessid.add(self.sessid)
            obj.player = self.player
            self.puid = obj.id
            self.puppet = obj
            obj.scripts.validate()
            obj.locks.cache_lock_bypass(obj)

    def at_login(self, player):
        """
        Hook called by sessionhandler when the session becomes authenticated.

        player - the player associated with the session
        """
        self.player = player
        self.uid = self.player.id
        self.uname = self.player.username
        self.logged_in = True
        self.conn_time = time()
        self.puid = None
        self.puppet = None
        self.cmdset_storage = settings.CMDSET_SESSION

        # Update account's last login time.
        self.player.last_login = timezone.now()
        self.player.save()

        # add the session-level cmdset
        self.cmdset = CmdSetHandler(self, True)

    def at_disconnect(self):
        """
        Hook called by sessionhandler when disconnecting this session.
        """
        if self.logged_in:
            sessid = self.sessid
            player = self.player
            if self.puppet:
                player.unpuppet_object(sessid)
            uaccount = player
            uaccount.last_login = timezone.now()
            uaccount.save()
            # calling player hook
            player.at_disconnect()
            self.logged_in = False
            if not self.sessionhandler.sessions_from_player(player):
                # no more sessions connected to this player
                player.is_connected = False
            # this may be used to e.g. delete player after disconnection etc
            player.at_post_disconnect()

    def get_player(self):
        """
        Get the player associated with this session
        """
        return self.logged_in and self.player

    def get_puppet(self):
        """
        Returns the in-game character associated with this session.
        This returns the typeclass of the object.
        """
        return self.logged_in and self.puppet
    get_character = get_puppet

    def get_puppet_or_player(self):
        """
        Returns session if not logged in; puppet if one exists,
        otherwise return the player.
        """
        if self.logged_in:
            return self.puppet if self.puppet else self.player
        return None

    def log(self, message, channel=True):
        """
        Emits session info to the appropriate outputs and info channels.
        """
        if channel:
            try:
                cchan = settings.CHANNEL_CONNECTINFO
                cchan = ChannelDB.objects.get_channel(cchan[0])
                cchan.msg("[%s]: %s" % (cchan.key, message))
            except Exception:
                pass
        logger.log_infomsg(message)

    def get_client_size(self):
        """
        Return eventual eventual width and height reported by the
        client. Note that this currently only deals with a single
        client window (windowID==0) as in traditional telnet session
        """
        flags = self.protocol_flags
        width = flags.get('SCREENWIDTH', {}).get(0, settings.CLIENT_DEFAULT_WIDTH)
        height = flags.get('SCREENHEIGHT', {}).get(0, settings.CLIENT_DEFAULT_HEIGHT)
        return width, height

    def update_session_counters(self, idle=False):
        """
        Hit this when the user enters a command in order to update idle timers
        and command counters.
        """
        # Store the timestamp of the user's last command.
        if not idle:
            # Increment the user's command counter.
            self.cmd_total += 1
            # Player-visible idle time, not used in idle timeout calcs.
            self.cmd_last_visible = time()

    def data_in(self, text=None, **kwargs):
        """
        Send User->Evennia. This will in effect
        execute a command string on the server.

        Note that oob data is already sent to the
        oobhandler at this point.

        """
        #explicitly check for None since text can be an empty string, which is
        #also valid
        if text is not None:
            # this is treated as a command input
            #text = to_unicode(escape_control_sequences(text), encoding=self.encoding)
            # handle the 'idle' command
            if text.strip() == _IDLE_COMMAND:
                self.update_session_counters(idle=True)
                return
            if self.player:
                # nick replacement
                puppet = self.player.get_puppet(self.sessid)
                if puppet:
                    text = puppet.nicks.nickreplace(text,
                                  categories=("inputline", "channel"), include_player=True)
                else:
                    text = self.player.nicks.nickreplace(text,
                                categories=("inputline", "channels"), include_player=False)
            cmdhandler(self, text, callertype="session", sessid=self.sessid)
            self.update_session_counters()

    execute_cmd = data_in  # alias

    def data_out(self, text=None, **kwargs):
        """
        Send Evennia -> User
        """
        text = text if text else ""
        if _INLINEFUNC_ENABLED and not "raw" in kwargs:
            text = parse_inlinefunc(text, strip="strip_inlinefunc" in kwargs, session=self)
        if self.screenreader:
            global _ANSI
            if not _ANSI:
                from evennia.utils import ansi as _ANSI
            text = _ANSI.parse_ansi(text, strip_ansi=True, xterm256=False, mxp=False)
            text = _RE_SCREENREADER_REGEX.sub("", text)
        session = kwargs.pop('session', None)
        session = session or self
        self.sessionhandler.data_out(session, text=text, **kwargs)
    # alias
    msg = data_out

    def __eq__(self, other):
        return self.address == other.address

    def __str__(self):
        """
        String representation of the user session class. We use
        this a lot in the server logs.
        """
        symbol = ""
        if self.logged_in and hasattr(self, "player") and self.player:
            symbol = "(#%s)" % self.player.id
        try:
            if hasattr(self.address, '__iter__'):
                address = ":".join([str(part) for part in self.address])
            else:
                address = self.address
        except Exception:
            address = self.address
        return "%s%s@%s" % (self.uname, symbol, address)

    def __unicode__(self):
        """
        Unicode representation
        """
        return u"%s" % str(self)

    # Dummy API hooks for use during non-loggedin operation

    def at_cmdset_get(self, **kwargs):
        "dummy hook all objects with cmdsets need to have"
        pass

    # Mock db/ndb properties for allowing easy storage on the session
    # (note that no databse is involved at all here. session.db.attr =
    # value just saves a normal property in memory, just like ndb).

    #@property
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
            class NdbHolder(object):
                "Holder for storing non-persistent attributes."
                def all(self):
                    return [val for val in self.__dict__.keys()
                            if not val.startswith['_']]

                def __getattribute__(self, key):
                    # return None if no matching attribute was found.
                    try:
                        return object.__getattribute__(self, key)
                    except AttributeError:
                        return None
            self._ndb_holder = NdbHolder()
            return self._ndb_holder

    #@ndb.setter
    def ndb_set(self, value):
        "Stop accidentally replacing the db object"
        string = "Cannot assign directly to ndb object! "
        string = "Use ndb.attr=value instead."
        raise Exception(string)

    #@ndb.deleter
    def ndb_del(self):
        "Stop accidental deletion."
        raise Exception("Cannot delete the ndb object!")
    ndb = property(ndb_get, ndb_set, ndb_del)
    db = property(ndb_get, ndb_set, ndb_del)

    # Mock access method for the session (there is no lock info
    # at this stage, so we just present a uniform API)
    def access(self, *args, **kwargs):
        "Dummy method."
        return True
