"""
This module implements the ssh (Secure SHell) protocol for encrypted
connections.

This depends on a generic session module that implements the actual
login procedure of the game, tracks sessions etc.

Using standard ssh client,

"""
from __future__ import print_function
from builtins import object
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
from twisted.conch import interfaces as iconch
from twisted.python import components
from django.conf import settings
from evennia.server import session
from evennia.players.models import PlayerDB
from evennia.utils import ansi, utils

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
    def __init__(self, starttuple):
        """
        For setting up the player.  If player is not None then we'll
        login automatically.

        Args:
            starttuple (tuple): A (player, factory) tuple.

        """
        self.authenticated_player = starttuple[0]
        # obs must not be called self.factory, that gets overwritten!
        self.cfactory = starttuple[1]

    def terminalSize(self, width, height):
        """
        Initialize the terminal and connect to the new session.

        Args:
            width (int): Width of terminal.
            height (int): Height of terminal.

        """
        # Clear the previous input line, redraw it at the new
        # cursor position
        self.terminal.eraseDisplay()
        self.terminal.cursorHome()
        self.width = width
        self.height = height

        # initialize the session
        client_address = self.getClientAddress()
        self.init_session("ssh", client_address, self.cfactory.sessionhandler)

        # since we might have authenticated already, we might set this here.
        if self.authenticated_player:
            self.logged_in = True
            self.uid = self.authenticated_player.user.id
        self.sessionhandler.connect(self)

    def connectionMade(self):
        """
        This is called when the connection is first established.

        """
        recvline.HistoricRecvLine.connectionMade(self)
        self.keyHandlers[CTRL_C] = self.handle_INT
        self.keyHandlers[CTRL_D] = self.handle_EOF
        self.keyHandlers[CTRL_L] = self.handle_FF
        self.keyHandlers[CTRL_BACKSLASH] = self.handle_QUIT

        # initalize

    def handle_INT(self):
        """
        Handle ^C as an interrupt keystroke by resetting the current
        input variables to their initial state.

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

    def connectionLost(self, reason=None):
        """
        This is executed when the connection is lost for whatever
        reason. It can also be called directly, from the disconnect
        method.

        Args:
            reason (str): Motivation for loosing connection.

        """
        insults.TerminalProtocol.connectionLost(self, reason)
        self.sessionhandler.disconnect(self)
        self.terminal.loseConnection()

    def getClientAddress(self):
        """
        Get client address.

        Returns:
            address_and_port (tuple): The client's address and port in
                a tuple. For example `('127.0.0.1', 41917)`.

        """
        return self.terminal.transport.getPeer()

    def lineReceived(self, string):
        """
        Communication User -> Evennia. Any line return indicates a
        command for the purpose of the MUD.  So we take the user input
        and pass it on to the game engine.

        Args:
            string (str): Input text.

        """
        self.sessionhandler.data_in(self, string)

    def lineSend(self, string):
        """
        Communication Evennia -> User.  Any string sent should
        already have been properly formatted and processed before
        reaching this point.

        Args:
            string (str): Output text.

        """
        for line in string.split('\n'):
            #this is the telnet-specific method for sending
            self.terminal.write(line)
            self.terminal.nextLine()

    # session-general method hooks

    def disconnect(self, reason="Connection closed. Goodbye for now."):
        """
        Disconnect from server.

        Args:
            reason (str): Motivation for disconnect.

        """
        if reason:
            self.data_out(reason)
        self.connectionLost(reason)

    def data_out(self, text=None, **kwargs):
        """
        Data Evennia -> User access hook. 'data' argument is a dict
        parsed for string settings.

        Kwargs:
            text (str): Text to send.
            raw (bool): Leave all ansi markup and tokens unparsed
            nomarkup (bool): Remove all ansi markup.

        """
        try:
            text = utils.to_str(text if text else "", encoding=self.encoding)
        except Exception as e:
            self.lineSend(str(e))
            return
        raw = kwargs.get("raw", False)
        nomarkup = kwargs.get("nomarkup", False)
        if raw:
            self.lineSend(text)
        else:
            self.lineSend(ansi.parse_ansi(text.strip("{r") + "{r", strip_ansi=nomarkup))


class ExtraInfoAuthServer(SSHUserAuthServer):
    def auth_password(self, packet):
        """
        Password authentication.

        Used mostly for setting up the transport so we can query
        username and password later.

        Args:
            packet (Packet): Auth packet.

        """
        password = common.getNS(packet[1:])[0]
        c = credentials.UsernamePassword(self.user, password)
        c.transport = self.transport
        return self.portal.login(c, None, IConchUser).addErrback(
                                                        self._ebPassword)


class PlayerDBPasswordChecker(object):
    """
    Checks the django db for the correct credentials for
    username/password otherwise it returns the player or None which is
    useful for the Realm.

    """
    credentialInterfaces = (credentials.IUsernamePassword,)

    def __init__(self, factory):
        """
        Initialize the factory.

        Args:
            factory (SSHFactory): Checker factory.

        """
        self.factory = factory
        super(PlayerDBPasswordChecker, self).__init__()

    def requestAvatarId(self, c):
        """
        Generic credentials.

        """
        up = credentials.IUsernamePassword(c, None)
        username = up.username
        password = up.password
        player = PlayerDB.objects.get_player_from_name(username)
        res = (None, self.factory)
        if player and player.user.check_password(password):
            res = (player, self.factory)
        return defer.succeed(res)


class PassAvatarIdTerminalRealm(TerminalRealm):
    """
    Returns an avatar that passes the avatarId through to the
    protocol.  This is probably not the best way to do it.

    """

    def _getAvatar(self, avatarId):
        comp = components.Componentized()
        user = self.userFactory(comp, avatarId)
        sess = self.sessionFactory(comp)

        sess.transportFactory = self.transportFactory
        sess.chainedProtocolFactory = lambda: self.chainedProtocolFactory(avatarId)

        comp.setComponent(iconch.IConchUser, user)
        comp.setComponent(iconch.ISession, sess)

        return user


class TerminalSessionTransport_getPeer(object):
    """
    Taken from twisted's TerminalSessionTransport which doesn't
    provide getPeer to the transport.  This one does.
    j
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
        print("  Generating SSH RSA keypair ...", end=' ')
        from Crypto.PublicKey import RSA

        KEY_LENGTH = 1024
        rsaKey = Key(RSA.generate(KEY_LENGTH))
        publicKeyString = rsaKey.public().toString(type="OPENSSH")
        privateKeyString = rsaKey.toString(type="OPENSSH")

        # save keys for the future.
        file(pubkeyfile, 'w+b').write(publicKeyString)
        file(privkeyfile, 'w+b').write(privateKeyString)
        print(" done.")
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

    def chainProtocolFactory(username=None):
        return insults.ServerProtocol(
            configdict['protocolFactory'],
            *configdict.get('protocolConfigdict', (username,)),
            **configdict.get('protocolKwArgs', {}))

    rlm = PassAvatarIdTerminalRealm()
    rlm.transportFactory = TerminalSessionTransport_getPeer
    rlm.chainedProtocolFactory = chainProtocolFactory
    factory = ConchFactory(Portal(rlm))
    factory.sessionhandler = configdict['sessions']

    try:
        # create/get RSA keypair
        publicKey, privateKey = getKeyPair(pubkeyfile, privkeyfile)
        factory.publicKeys = {'ssh-rsa': publicKey}
        factory.privateKeys = {'ssh-rsa': privateKey}
    except Exception as e:
        print(" getKeyPair error: %(e)s\n WARNING: Evennia could not auto-generate SSH keypair. Using conch default keys instead." % {'e': e})
        print(" If this error persists, create game/%(pub)s and game/%(priv)s yourself using third-party tools." % {'pub': pubkeyfile, 'priv': privkeyfile})

    factory.services = factory.services.copy()
    factory.services['ssh-userauth'] = ExtraInfoAuthServer

    factory.portal.registerChecker(PlayerDBPasswordChecker(factory))

    return factory
