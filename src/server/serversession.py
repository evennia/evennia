"""
This defines a the Server's generic session object. This object represents
a connection to the outside world but don't know any details about how the
connection actually happens (so it's the same for telnet, web, ssh etc).

It is stored on the Server side (as opposed to protocol-specific sessions which
are stored on the Portal side)
"""

import time
from datetime import datetime
from django.conf import settings
#from src.scripts.models import ScriptDB
from src.comms.models import ChannelDB
from src.utils import logger, utils
from src.utils.inlinefunc import parse_inlinefunc
from src.utils.utils import make_iter
from src.commands.cmdhandler import cmdhandler
from src.commands.cmdsethandler import CmdSetHandler
from src.server.session import Session

IDLE_COMMAND = settings.IDLE_COMMAND
_GA = object.__getattribute__
_ObjectDB = None
_OOB_HANDLER = None

# load optional out-of-band function module (this acts as a verification)
OOB_PLUGIN_MODULES = [utils.mod_import(mod)
                      for mod in make_iter(settings.OOB_PLUGIN_MODULES) if mod]
INLINEFUNC_ENABLED = settings.INLINEFUNC_ENABLED

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
            from src.objects.models import ObjectDB as _ObjectDB

        if not self.logged_in:
            # assign the unloggedin-command set.
            self.cmdset_storage = settings.CMDSET_UNLOGGEDIN

        self.cmdset.update(init_mode=True)

        if self.puid:
            # reconnect puppet (puid is only set if we are coming
            # back from a server reload)
            obj = _ObjectDB.objects.get(id=self.puid)
            self.player.puppet_object(self.sessid, obj, normal_mode=False)

    def at_login(self, player):
        """
        Hook called by sessionhandler when the session becomes authenticated.

        player - the player associated with the session
        """
        self.player = player
        self.uid = self.player.id
        self.uname = self.player.username
        self.logged_in = True
        self.conn_time = time.time()
        self.puid = None
        self.puppet = None
        self.cmdset_storage = settings.CMDSET_SESSION

        # Update account's last login time.
        self.player.last_login = datetime.now()
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
            _GA(player.dbobj, "unpuppet_object")(sessid)
            uaccount = player.dbobj
            uaccount.last_login = datetime.now()
            uaccount.save()
            # calling player hook
            _GA(player.typeclass, "at_disconnect")()
            self.logged_in = False
            if not self.sessionhandler.sessions_from_player(player):
                # no more sessions connected to this player
                player.is_connected = False
            # this may be used to e.g. delete player after disconnection etc
            _GA(player.typeclass, "at_post_disconnect")()

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
        self.cmd_last = time.time()
        if not idle:
            # Increment the user's command counter.
            self.cmd_total += 1
            # Player-visible idle time, not used in idle timeout calcs.
            self.cmd_last_visible = time.time()

    def data_in(self, text=None, **kwargs):
        """
        Send User->Evennia. This will in effect
        execute a command string on the server.

        Especially handled keywords:

        oob - this should hold a dictionary of oob command calls from
              the oob-supporting protocol.
        """
        #explicitly check for None since text can be an empty string, which is
        #also valid
        if text is not None:
            # this is treated as a command input
            #text = to_unicode(escape_control_sequences(text), encoding=self.encoding)
            # handle the 'idle' command
            if text.strip() == IDLE_COMMAND:
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
        if "oob" in kwargs:
            # handle oob instructions
            global _OOB_HANDLER
            if not _OOB_HANDLER:
                from src.server.oobhandler import OOB_HANDLER as _OOB_HANDLER
            oobstruct = self.sessionhandler.oobstruct_parser(kwargs.pop("oob", None))
            #print "session.data_in: oobstruct:",oobstruct
            for (funcname, args, kwargs) in oobstruct:
                if funcname:
                    _OOB_HANDLER.execute_cmd(self, funcname, *args, **kwargs)

    execute_cmd = data_in  # alias

    def data_out(self, text=None, **kwargs):
        """
        Send Evennia -> User
        """
        text = text if text else ""
        if INLINEFUNC_ENABLED and not "raw" in kwargs:
            text = parse_inlinefunc(text, strip="strip_inlinefunc" in kwargs, session=self)
        self.sessionhandler.data_out(self, text=text, **kwargs)

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

    # easy-access functions

    #def login(self, player):
    #    "alias for at_login"
    #    self.session_login(player)
    #def disconnect(self):
    #    "alias for session_disconnect"
    #    self.session_disconnect()
    def msg(self, text='', **kwargs):
        "alias for at_data_out"
        self.data_out(text=text, **kwargs)

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
