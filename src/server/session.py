"""
This defines a generic session class. All connection instances (both
on Portal and Server side) should inherit from this class.

"""

import time

#------------------------------------------------------------
# Server Session
#------------------------------------------------------------

class Session(object):
    """
    This class represents a player's session and is a template for
    both portal- and server-side sessions.

    Each connection will see two session instances created:

     1) A Portal session. This is customized for the respective connection
        protocols that Evennia supports, like Telnet, SSH etc. The Portal session
        must call init_session() as part of its initialization. The respective
        hook methods should be connected to the methods unique for the respective
        protocol so that there is a unified interface to Evennia.
     2) A Server session. This is the same for all connected players, regardless
        of how they connect.

    The Portal and Server have their own respective sessionhandlers. These are synced
    whenever new connections happen or the Server restarts etc, which means much of the
    same information must be stored in both places e.g. the portal can re-sync with the
    server when the server reboots.

    """

    # names of attributes that should be affected by syncing.
    _attrs_to_sync = ('protocol_key', 'address', 'suid', 'sessid', 'uid', 'uname',
                      'logged_in', 'cid', 'encoding',
                      'conn_time', 'cmd_last', 'cmd_last_visible', 'cmd_total',
                      'server_data')

    def init_session(self, protocol_key, address, sessionhandler):
        """
        Initialize the Session. This should be called by the protocol when
        a new session is established.
        protocol_key - telnet, ssh, ssl or web
        address - client address
        sessionhandler - reference to the sessionhandler instance
        """
        # This is currently 'telnet', 'ssh', 'ssl' or 'web'
        self.protocol_key = protocol_key
        # Protocol address tied to this session
        self.address = address

        # suid is used by some protocols, it's a hex key.
        self.suid = None

        # unique id for this session
        self.sessid = 0 # no sessid yet
        # database id for the user connected to this session
        self.uid = None
        # user name, for easier tracking of sessions
        self.uname = None
        # if user has authenticated already or not
        self.logged_in = False

        # database id of character/object connected to this player session (if any)
        self.cid = None
        self.encoding = "utf-8"

        # session time statistics
        self.conn_time = time.time()
        self.cmd_last_visible = self.conn_time
        self.cmd_last = self.conn_time
        self.cmd_total = 0

        self.protocol_flags = {}
        self.server_data = {}

        # a back-reference to the relevant sessionhandler this
        # session is stored in.
        self.sessionhandler = sessionhandler

    def get_sync_data(self):
        """
        Return all data relevant to sync the session
        """
        return dict((key, value) for key, value in self.__dict__.items() if key in self._attrs_to_sync)

    def load_sync_data(self, sessdata):
        """
        Takes a session dictionary, as created by get_sync_data,
        and loads it into the correct properties of the session.
        """
        for propname, value in sessdata.items():
            self.__dict__[propname] = value

    def at_sync(self):
        """
        Called after a session has been fully synced (including
        secondary operations such as setting self.player based
        on uid etc).
        """
        pass

    # access hooks

    def disconnect(self, reason=None):
        """
        generic hook called from the outside to disconnect this session
        should be connected to the protocols actual disconnect mechanism.
        """
        pass

    def data_out(self, msg, data=None):
        """
        generic hook for sending data out through the protocol. Server
        protocols can use this right away. Portal sessions
        should overload this to format/handle the outgoing data as needed.
        """
        pass

    def data_in(self, msg, data=None):
        """
        hook for protocols to send incoming data to the engine.
        """
        pass

    def oob_data_out(self, data):
        """
        for Portal, this receives out-of-band data from Server across the AMP.
        for Server, this sends out-of-band data to Portal.

        data is a dictionary
        """
        pass

    def oob_data_in(self, data):
        """
        for Portal, this sends out-of-band requests to Server over the AMP.
        for Server, this receives data from Portal.

        data is a dictionary
        """
        pass
