"""
Contains the protocols, commands, and client factory needed for the server
to service the MUD portal proxy.

The separation works like this:

Portal - (AMP client) handles protocols. It contains a list of connected sessions in a 
         dictionary for identifying the respective player connected. If it looses the AMP connection
         it will automatically try to reconnect. 
         
Server - (AMP server) Handles all mud operations. The server holds its own list 
         of sessions tied to player objects. This is synced against the portal at startup
         and when a session connects/disconnects

"""
import os

try:
    import cPickle as pickle
except ImportError:
    import pickle
from twisted.protocols import amp
from twisted.internet import protocol, defer
from django.conf import settings
from src.utils.utils import to_str

from src.server.models import ServerConfig
from src.scripts.models import ScriptDB
from src.players.models import PlayerDB
from src.server.serversession import ServerSession

PORTAL_RESTART = os.path.join(settings.GAME_DIR, "portal.restart")
SERVER_RESTART = os.path.join(settings.GAME_DIR, "server.restart")

# communication bits 

PCONN = chr(1)       # portal session connect
PDISCONN = chr(2)    # portal session disconnect
PSYNC = chr(3)       # portal session sync
SLOGIN = chr(4)      # server session login
SDISCONN = chr(5)    # server session disconnect  
SDISCONNALL = chr(6) # server session disconnect all
SSHUTD = chr(7)      # server shutdown 
SSYNC = chr(8)       # server session sync

# i18n
from django.utils.translation import ugettext as _


def get_restart_mode(restart_file):
    """
    Parse the server/portal restart status
    """
    if os.path.exists(restart_file):
        flag = open(restart_file, 'r').read()
        return flag == "True"
    return False 

class AmpServerFactory(protocol.ServerFactory):
    """
    This factory creates new AMPProtocol protocol instances to use for accepting
    connections from TCPServer.
    """
    def __init__(self, server):
        """
        server: The Evennia server service instance
        protocol: The protocol the factory creates instances of.
        """
        self.server = server 
        self.protocol = AMPProtocol        

    def buildProtocol(self, addr):
        """
        Start a new connection, and store it on the service object
        """
        #print "Evennia Server connected to Portal at %s." % addr
        self.server.amp_protocol = AMPProtocol()
        self.server.amp_protocol.factory = self
        return self.server.amp_protocol

class AmpClientFactory(protocol.ReconnectingClientFactory):
    """
    This factory creates new AMPProtocol protocol instances to use to connect
    to the MUD server. It also maintains the portal attribute
    on the ProxyService instance, which is used for piping input
    from Telnet to the MUD server.
    """
    # Initial reconnect delay in seconds.
    initialDelay = 1
    #factor = 1.5
    maxDelay = 1

    def __init__(self, portal):
        self.portal = portal 
        self.protocol = AMPProtocol

    def startedConnecting(self, connector):
        """
        Called when starting to try to connect to the MUD server.
        """
        pass
        #print 'AMP started to connect:', connector
        
    def buildProtocol(self, addr):
        """
        Creates an AMPProtocol instance when connecting to the server. 
        """
        #print "Portal connected to Evennia server at %s." % addr
        self.resetDelay()
        self.portal.amp_protocol = AMPProtocol()
        self.portal.amp_protocol.factory = self
        return self.portal.amp_protocol

    def clientConnectionLost(self, connector, reason):
        """
        Called when the AMP connection to the MUD server is lost.
        """        
        if not get_restart_mode(SERVER_RESTART):
            self.portal.sessions.announce_all(_(" Portal lost connection to Server."))
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        """
        Called when an AMP connection attempt to the MUD server fails.
        """
        self.portal.sessions.announce_all(" ...")
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)


class MsgPortal2Server(amp.Command):
    """ 
    Message portal -> server
    """
    arguments = [('sessid', amp.Integer()),
                 ('msg', amp.String()),
                 ('data', amp.String())]
    errors = [(Exception, 'EXCEPTION')]
    response = []

class MsgServer2Portal(amp.Command):
    """ 
    Message server -> portal
    """
    arguments = [('sessid', amp.Integer()),
                 ('msg', amp.String()),
                 ('data', amp.String())]
    errors = [(Exception, 'EXCEPTION')]
    response = []

class OOBPortal2Server(amp.Command):
    """
    OOB data portal -> server
    """
    arguments = [('sessid', amp.Integer()),
                 ('data', amp.String())]
    errors = [(Exception, "EXCEPTION")]
    response = []
    
class OOBServer2Portal(amp.Command):
    """
    OOB data server -> portal
    """
    arguments = [('sessid', amp.Integer()),
                 ('data', amp.String())]
    errors = [(Exception, "EXCEPTION")]
    response = []
    
class ServerAdmin(amp.Command):
    """
    Portal -> Server

    Sent when the portal needs to perform admin
     operations on the server, such as when a new 
     session connects or resyncs
    """
    arguments = [('sessid', amp.Integer()),
                 ('operation', amp.String()),
                 ('data', amp.String())]
    errors = [(Exception, 'EXCEPTION')]
    response = []
    
class PortalAdmin(amp.Command):
    """
    Server -> Portal

    Sent when the server needs to perform admin
     operations on the portal. 
    """
    arguments = [('sessid', amp.Integer()),
                 ('operation', amp.String()),
                 ('data', amp.String())]
    errors = [(Exception, 'EXCEPTION')]
    response = []

dumps = lambda data: to_str(pickle.dumps(data, pickle.HIGHEST_PROTOCOL))
loads = lambda data: pickle.loads(to_str(data))

#------------------------------------------------------------
# Core AMP protocol for communication Server <-> Portal
#------------------------------------------------------------

class AMPProtocol(amp.AMP):
    """
    This is the protocol that the MUD server and the proxy server
    communicate to each other with. AMP is a bi-directional protocol, so
    both the proxy and the MUD use the same commands and protocol.

    AMP specifies responder methods here and connect them to amp.Command
    subclasses that specify the datatypes of the input/output of these methods.
    """

    # helper methods 

    def connectionMade(self):
        """
        This is called when a connection is established
        between server and portal. It is called on both sides,
        so we need to make sure to only trigger resync from the
        server side. 
        """
        if hasattr(self.factory, "portal"):
            sessdata = self.factory.portal.sessions.get_all_sync_data()
            #print sessdata
            self.call_remote_ServerAdmin(0, 
                                         PSYNC, 
                                         data=sessdata)
            if get_restart_mode(SERVER_RESTART):
                msg = _(" ... Server restarted.")
                self.factory.portal.sessions.announce_all(msg)
            self.factory.portal.sessions.at_server_connection()
          
    # Error handling 

    def errback(self, e, info):
        "error handler, to avoid dropping connections on server tracebacks."
        e.trap(Exception)
        print _("AMP Error for %(info)s: %(e)s") % {'info': info, 'e': e.getErrorMessage()}


    # Message definition + helper methods to call/create each message type

    # Portal -> Server Msg
    
    def amp_msg_portal2server(self, sessid, msg, data):        
        """
        Relays message to server. This method is executed on the Server.
        """
        #print "msg portal -> server (server side):", sessid, msg
        self.factory.server.sessions.data_in(sessid, msg, loads(data))
        return {}
    MsgPortal2Server.responder(amp_msg_portal2server)

    def call_remote_MsgPortal2Server(self, sessid, msg, data=""):
        """
        Access method called by the Portal and executed on the Portal.
        """        
        #print "msg portal->server (portal side):", sessid, msg
        self.callRemote(MsgPortal2Server,
                        sessid=sessid,
                        msg=msg,
                        data=dumps(data)).addErrback(self.errback, "MsgPortal2Server")

    # Server -> Portal message 

    def amp_msg_server2portal(self, sessid, msg, data):
        """
        Relays message to Portal. This method is executed on the Portal.
        """
        #print "msg server->portal (portal side):", sessid, msg
        self.factory.portal.sessions.data_out(sessid, msg, loads(data))
        return {}
    MsgServer2Portal.responder(amp_msg_server2portal)

    def call_remote_MsgServer2Portal(self, sessid, msg, data=""):
        """
        Access method called by the Server and executed on the Server.
        """
        #print "msg server->portal (server side):", sessid, msg, data
        self.callRemote(MsgServer2Portal,
                        sessid=sessid,
                        msg=to_str(msg),
                        data=dumps(data)).addErrback(self.errback, "OOBServer2Portal")

    # OOB Portal -> Server 
        
    # Portal -> Server Msg
    
    def amp_oob_portal2server(self, sessid, data):        
        """
        Relays out-of-band data to server. This method is executed on the Server.
        """
        #print "oob portal -> server (server side):", sessid, loads(data)
        self.factory.server.sessions.oob_data_in(sessid, loads(data))
        return {}
    OOBPortal2Server.responder(amp_oob_portal2server)

    def call_remote_OOBPortal2Server(self, sessid, data=""):
        """
        Access method called by the Portal and executed on the Portal.
        """        
        #print "oob portal->server (portal side):", sessid, data
        self.callRemote(OOBPortal2Server,
                        sessid=sessid,                        
                        data=dumps(data)).addErrback(self.errback, "OOBPortal2Server")

    # Server -> Portal message 

    def amp_oob_server2portal(self, sessid, data):
        """
        Relays out-of-band data to Portal. This method is executed on the Portal.
        """
        #print "oob server->portal (portal side):", sessid, data
        self.factory.portal.sessions.oob_data_out(sessid, loads(data))
        return {}
    OOBServer2Portal.responder(amp_oob_server2portal)

    def call_remote_OOBServer2Portal(self, sessid, data=""):
        """
        Access method called by the Server and executed on the Server.
        """
        #print "oob server->portal (server side):", sessid, data        
        self.callRemote(OOBServer2Portal,
                        sessid=sessid,                        
                        data=dumps(data)).addErrback(self.errback, "OOBServer2Portal")
        

    # Server administration from the Portal side 
    def amp_server_admin(self, sessid, operation, data):
        """
        This allows the portal to perform admin
        operations on the server.  This is executed on the Server.

        """
        data = loads(data)

        #print "serveradmin (server side):", sessid, operation, data
        
        if operation == PCONN: #portal_session_connect
            # create a new session and sync it
            sess = ServerSession()
            sess.sessionhandler = self.factory.server.sessions
            sess.load_sync_data(data)            
            if sess.logged_in and sess.uid:
                # this can happen in the case of auto-authenticating protocols like SSH
                sess.player = PlayerDB.objects.get_player_from_uid(sess.uid)
            sess.at_sync() # this runs initialization without acr

            self.factory.server.sessions.portal_connect(sessid, sess)

        elif operation == PDISCONN: #'portal_session_disconnect'
            # session closed from portal side 
            self.factory.server.sessions.portal_disconnect(sessid)

        elif operation == PSYNC: #'portal_session_sync'
            # force a resync of sessions when portal reconnects to server (e.g. after a server reboot)            
            # the data kwarg contains a dict {sessid: {arg1:val1,...}} representing the attributes
            # to sync for each session.
            sesslist = []
            server_sessionhandler = self.factory.server.sessions
            for sessid, sessdict in data.items():                
                sess = ServerSession()
                sess.sessionhandler = server_sessionhandler
                sess.load_sync_data(sessdict)
                if sess.uid:
                    sess.player = PlayerDB.objects.get_player_from_uid(sess.uid)
                sesslist.append(sess)                                
            # replace sessions on server
            server_sessionhandler.portal_session_sync(sesslist)            
            # after sync is complete we force-validate all scripts (this starts everything)
            init_mode = ServerConfig.objects.conf("server_restart_mode", default=None)
            ScriptDB.objects.validate(init_mode=init_mode)
            ServerConfig.objects.conf("server_restart_mode", delete=True)

        else:
            raise Exception(_("operation %(op)s not recognized.") % {'op': operation})
            
        return {}
    ServerAdmin.responder(amp_server_admin)

    def call_remote_ServerAdmin(self, sessid, operation="", data=""):
        """
        Access method called by the Portal and Executed on the Portal.
        """
        #print "serveradmin (portal side):", sessid, operation, data
        data = dumps(data)

        self.callRemote(ServerAdmin,
                        sessid=sessid,
                        operation=operation,
                        data=data).addErrback(self.errback, "ServerAdmin")

    # Portal administraton from the Server side

    def amp_portal_admin(self, sessid, operation, data):
        """
        This allows the server to perform admin 
        operations on the portal. This is executed on the Portal.
        """
        data = loads(data)

        #print "portaladmin (portal side):", sessid, operation, data
        if operation == SLOGIN: # 'server_session_login'
            # a session has authenticated; sync it.
            sess = self.factory.portal.sessions.get_session(sessid)            
            sess.load_sync_data(data)

        elif operation == SDISCONN: #'server_session_disconnect'
            # the server is ordering to disconnect the session
            self.factory.portal.sessions.server_disconnect(sessid, reason=data)

        elif operation == SDISCONNALL: #'server_session_disconnect_all'
            # server orders all sessions to disconnect
            self.factory.portal.sessions.server_disconnect_all(reason=data)

        elif operation == SSHUTD: #server_shutdown'
            # the server orders the portal to shut down
            self.factory.portal.shutdown(restart=False)
            
        elif operation == SSYNC: #'server_session_sync'
            # server wants to save session data to the portal, maybe because
            # it's about to shut down. We don't overwrite any sessions, 
            # just update data on them and remove eventual ones that are 
            # out of sync (shouldn't happen normally). 

            portal_sessionhandler = self.factory.portal.sessions.sessions            

            to_save = [sessid for sessid in data if sessid in portal_sessionhandler.sessions]
            to_delete = [sessid for sessid in data if sessid not in to_save]

            # save protocols
            for sessid in to_save:
                portal_sessionhandler.sessions[sessid].load_sync_data(data[sessid])
            # disconnect missing protocols
            for sessid in to_delete:
                portal_sessionhandler.server_disconnect(sessid)
        else:
            raise Exception(_("operation %(op)s not recognized.") % {'op': operation})
        return {}
    PortalAdmin.responder(amp_portal_admin)

    def call_remote_PortalAdmin(self, sessid, operation="", data=""):
        """
        Access method called by the server side.
        """
        #print "portaladmin (server side):", sessid, operation, data
        data = dumps(data)

        self.callRemote(PortalAdmin,
                        sessid=sessid,
                        operation=operation,
                        data=data).addErrback(self.errback, "PortalAdmin")







