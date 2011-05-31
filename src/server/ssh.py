"""
This module implements the ssh (Secure SHell) protocol for encrypted
connections.

This depends on a generic session module that implements
the actual login procedure of the game, tracks
sessions etc.

"""
import os

from twisted.cred.checkers import credentials
from twisted.cred.portal import Portal
from twisted.conch.ssh.keys import Key
from twisted.conch.interfaces import IConchUser
from twisted.conch.ssh.userauth import SSHUserAuthServer
from twisted.conch.ssh import common
from twisted.conch.insults import insults
from twisted.conch.manhole_ssh import TerminalRealm, _Glue, ConchFactory
from twisted.conch.manhole import Manhole, recvline
from twisted.internet import defer
from django.conf import settings
from src.server import session
from src.utils import ansi, utils, logger


ENCODINGS = settings.ENCODINGS

CTRL_C = '\x03'
CTRL_D = '\x04'
CTRL_BACKSLASH = '\x1c'
CTRL_L = '\x0c'

class SshProtocol(Manhole, session.Session):
    """
    Each player connecting over ssh gets this protocol assigned to
    them.  All communication between game and player goes through
    here.
    """

    def terminalSize(self, width, height):
        """
        Initialize the terminal and connect to the new session.
        """
        # Clear the previous input line, redraw it at the new
        # cursor position
        self.terminal.eraseDisplay()
        self.terminal.cursorHome()
        self.width = width
        self.height = height
        # initialize the session
        self.session_connect(self.getClientAddress())


    def connectionMade(self):
        """
        This is called when the connection is first
        established.
        """
        recvline.HistoricRecvLine.connectionMade(self)
        self.keyHandlers[CTRL_C] = self.handle_INT
        self.keyHandlers[CTRL_D] = self.handle_EOF
        self.keyHandlers[CTRL_L] = self.handle_FF
        self.keyHandlers[CTRL_BACKSLASH] = self.handle_QUIT


    def handle_INT(self):
        """
        Handle ^C as an interrupt keystroke by resetting the current input
        variables to their initial state.
        """
        self.lineBuffer = []
        self.lineBufferIndex = 0

        self.terminal.nextLine()
        self.terminal.write("KeyboardInterrupt")
        self.terminal.nextLine()


    def handle_EOF(self):
        """
        Handles EOF generally used to exit.
        """
        if self.lineBuffer:
            self.terminal.write('\a')
        else:
            self.handle_QUIT()


    def handle_FF(self):
        """
        Handle a 'form feed' byte - generally used to request a screen
        refresh/redraw.
        """
        self.terminal.eraseDisplay()
        self.terminal.cursorHome()


    def handle_QUIT(self):
        """
        Quit, end, and lose the connection.
        """
        self.terminal.loseConnection()


    def connectionLost(self, reason=None, step=1):
        """
        This is executed when the connection is lost for
        whatever reason.

        Closing the connection takes two steps

        step 1 - is the default and is used when this method is
                 called automatically. The method should then call self.session_disconnect().
        Step 2 - means this method is called from at_disconnect(). At this point
                 the sessions are assumed to have been handled, and so the transport can close
                 without further ado.
        """
        insults.TerminalProtocol.connectionLost(self, reason)
        if step == 1:
            self.session_disconnect()
        else:
            self.terminal.loseConnection()


    def getClientAddress(self):
        """
        Returns the client's address and port in a tuple. For example
        ('127.0.0.1', 41917)
        """

        return self.terminal.transport.getPeer()


    def lineReceived(self, string):

        """
        Communication Player -> Evennia. Any line return indicates a
        command for the purpose of the MUD.  So we take the user input
        and pass it on to the game engine.
        """
        self.at_data_in(string)

    def lineSend(self, string):
        """
        Communication Evennia -> Player
        Any string sent should already have been
        properly formatted and processed
        before reaching this point.

        """
        for line in string.split('\n'):
            self.terminal.write(line) #this is the telnet-specific method for sending
            self.terminal.nextLine()

    # session-general method hooks

    def at_connect(self):
        """
        Show the banner screen.
        """
        self.telnet_markup = True
        # show connection screen
        self.execute_cmd('look')

    def at_login(self, player):
        """
        Called after authentication. self.logged_in=True at this point.
        """
        if player.has_attribute('telnet_markup'):
            self.telnet_markup = player.get_attribute("telnet_markup")
        else:
            self.telnet_markup = True

    def at_disconnect(self, reason="Connection closed. Goodbye for now."):
        """
        Disconnect from server
        """
        char = self.get_character()
        if char:
            char.at_disconnect()
        self.at_data_out(reason)
        self.connectionLost(step=2)

    def at_data_out(self, string, data=None):
        """
        Data Evennia -> Player access hook. 'data' argument is ignored.
        """
        try:
            string = utils.to_str(string, encoding=self.encoding)
        except Exception, e:
            self.lineSend(str(e))
            return
        nomarkup = not self.telnet_markup
        raw = False
        if type(data) == dict:
            # check if we want escape codes to go through unparsed.
            raw = data.get("raw", self.telnet_markup)
            # check if we want to remove all markup
            nomarkup = data.get("nomarkup", not self.telnet_markup)
        if raw:
            self.lineSend(string)
        else:
            self.lineSend(ansi.parse_ansi(string, strip_ansi=nomarkup))

    def at_data_in(self, string, data=None):
        """
        Line from Player -> Evennia. 'data' argument is not used.

        """
        try:
            string = utils.to_unicode(string, encoding=self.encoding)
            self.execute_cmd(string)
            return
        except Exception, e:
            logger.log_errmsg(str(e))


class ExtraInfoAuthServer(SSHUserAuthServer):
    def auth_password(self, packet):
        """
        Password authentication.

        Used mostly for setting up the transport so we can query
        username and password later.
        """
        password = common.getNS(packet[1:])[0]
        c = credentials.UsernamePassword(self.user, password)
        c.transport = self.transport
        return self.portal.login(c, None, IConchUser).addErrback(
                                                        self._ebPassword)


class AnyAuth(object):
    """
    Special auth method that accepts any credentials.
    """
    credentialInterfaces = (credentials.IUsernamePassword,)

    def requestAvatarId(self, c):
        "Generic credentials"
        up = credentials.IUsernamePassword(c, None)
        username = up.username
        password = up.password
        src_ip = str(up.transport.transport.getPeer().host)
        return defer.succeed(username)


class TerminalSessionTransport_getPeer:
    """
    Taken from twisted's TerminalSessionTransport which doesn't
    provide getPeer to the transport.  This one does.
    """
    def __init__(self, proto, chainedProtocol, avatar, width, height):
        self.proto = proto
        self.avatar = avatar
        self.chainedProtocol = chainedProtocol

        session = self.proto.session

        self.proto.makeConnection(
            _Glue(write=self.chainedProtocol.dataReceived,
                  loseConnection=lambda: avatar.conn.sendClose(session),
                  name="SSH Proto Transport"))

        def loseConnection():
            self.proto.loseConnection()

        def getPeer():
            session.conn.transport.transport.getPeer()

        self.chainedProtocol.makeConnection(
            _Glue(getPeer=getPeer, write=self.proto.write,
                  loseConnection=loseConnection,
                  name="Chained Proto Transport"))

        self.chainedProtocol.terminalProtocol.terminalSize(width, height)

def getKeyPair(pubkeyfile, privkeyfile):
    """
    This function looks for RSA keypair files in the current directory. If they
    do not exist, the keypair is created. 
    """

    if not (os.path.exists(pubkeyfile) and os.path.exists(privkeyfile)):
        # No keypair exists. Generate a new RSA keypair
        print "  Generating SSH RSA keypair ...",
        from Crypto.PublicKey import RSA        

        KEY_LENGTH = 1024
        rsaKey = Key(RSA.generate(KEY_LENGTH))
        publicKeyString = rsaKey.public().toString(type="OPENSSH")
        privateKeyString = rsaKey.toString(type="OPENSSH")

        # save keys for the future.
        file(pubkeyfile, 'w+b').write(publicKeyString)
        file(privkeyfile, 'w+b').write(privateKeyString)
        print " done."
    else:
        publicKeyString = file(pubkeyfile).read()
        privateKeyString = file(privkeyfile).read()

    return Key.fromString(publicKeyString), Key.fromString(privateKeyString)

def makeFactory(configdict):
    """
    Creates the ssh server factory.
    """

    pubkeyfile = "ssh-public.key"
    privkeyfile = "ssh-private.key"

    def chainProtocolFactory():
        return insults.ServerProtocol(
            configdict['protocolFactory'],
            *configdict.get('protocolConfigdict', ()),
            **configdict.get('protocolKwArgs', {}))

    rlm = TerminalRealm()
    rlm.transportFactory = TerminalSessionTransport_getPeer
    rlm.chainedProtocolFactory = chainProtocolFactory
    factory = ConchFactory(Portal(rlm))
    
    try:
        # create/get RSA keypair    
        publicKey, privateKey = getKeyPair(pubkeyfile, privkeyfile)
        factory.publicKeys = {'ssh-rsa': publicKey}    
        factory.privateKeys = {'ssh-rsa': privateKey}
    except Exception, e:
        print " getKeyPair error: %s\n WARNING: Evennia could not auto-generate SSH keypair. Using conch default keys instead." % e
        print " If this error persists, create game/%s and game/%s yourself using third-party tools." % (pubkeyfile, privkeyfile)

    factory.services = factory.services.copy()
    factory.services['ssh-userauth'] = ExtraInfoAuthServer

    factory.portal.registerChecker(AnyAuth())

    return factory
