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
import re

from twisted.cred.checkers import credentials
from twisted.cred.portal import Portal
from twisted.conch.interfaces import IConchUser

_SSH_IMPORT_ERROR = """
ERROR: Missing crypto library for SSH. Install it with

       pip install cryptography

(On older Twisted versions you may have to do 'pip install pycrypto pyasn1 instead).

If you get a compilation error you must install a C compiler and the
SSL dev headers (On Debian-derived systems this is the gcc and libssl-dev
packages).
"""

try:
    from twisted.conch.ssh.keys import Key
except ImportError:
    raise ImportError(_SSH_IMPORT_ERROR)

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
from evennia.utils import ansi
from evennia.utils.utils import to_str

_RE_N = re.compile(r"\|n$")
_RE_SCREENREADER_REGEX = re.compile(r"%s" % settings.SCREENREADER_REGEX_STRIP, re.DOTALL + re.MULTILINE)
_GAME_DIR = settings.GAME_DIR

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
        client_address = client_address.host if client_address else None
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
        self.sessionhandler.data_in(self, text=string)

    def sendLine(self, string):
        """
        Communication Evennia -> User.  Any string sent should
        already have been properly formatted and processed before
        reaching this point.

        Args:
            string (str): Output text.

        """
        for line in string.split('\n'):
            # the telnet-specific method for sending
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
            self.data_out(text=reason)
        self.connectionLost(reason)

    def data_out(self, **kwargs):
        """
        Data Evennia -> User

        Kwargs:
            kwargs (any): Options to the protocol.

        """
        self.sessionhandler.data_out(self, **kwargs)

    def send_text(self, *args, **kwargs):
        """
        Send text data. This is an in-band telnet operation.

        Args:
            text (str): The first argument is always the text string to send. No other arguments
                are considered.
        Kwargs:
            options (dict): Send-option flags
                   - mxp: Enforce MXP link support.
                   - ansi: Enforce no ANSI colors.
                   - xterm256: Enforce xterm256 colors, regardless of TTYPE setting.
                   - nocolor: Strip all colors.
                   - raw: Pass string through without any ansi processing
                        (i.e. include Evennia ansi markers but do not
                        convert them into ansi tokens)
                   - echo: Turn on/off line echo on the client. Turn
                        off line echo for client, for example for password.
                        Note that it must be actively turned back on again!

        """
        # print "telnet.send_text", args,kwargs  # DEBUG
        text = args[0] if args else ""
        if text is None:
            return
        text = to_str(text, force_string=True)

        # handle arguments
        options = kwargs.get("options", {})
        flags = self.protocol_flags
        xterm256 = options.get("xterm256", flags.get('XTERM256', True))
        useansi = options.get("ansi", flags.get('ANSI', True))
        raw = options.get("raw", flags.get("RAW", False))
        nocolor = options.get("nocolor", flags.get("NOCOLOR") or not (xterm256 or useansi))
        # echo = options.get("echo", None)  # DEBUG
        screenreader = options.get("screenreader", flags.get("SCREENREADER", False))

        if screenreader:
            # screenreader mode cleans up output
            text = ansi.parse_ansi(text, strip_ansi=True, xterm256=False, mxp=False)
            text = _RE_SCREENREADER_REGEX.sub("", text)

        if raw:
            # no processing
            self.sendLine(text)
            return
        else:
            # we need to make sure to kill the color at the end in order
            # to match the webclient output.
            linetosend = ansi.parse_ansi(_RE_N.sub("", text) + ("||n" if text.endswith("|") else "|n"),
                                         strip_ansi=nocolor, xterm256=xterm256, mxp=False)
            self.sendLine(linetosend)

    def send_prompt(self, *args, **kwargs):
        self.send_text(*args, **kwargs)

    def send_default(self, *args, **kwargs):
        pass


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
        if player and player.check_password(password):
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
            return session.conn.transport.transport.getPeer()

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

    pubkeyfile = os.path.join(_GAME_DIR, "server", "ssh-public.key")
    privkeyfile = os.path.join(_GAME_DIR, "server", "ssh-private.key")

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
    except Exception as err:
        print("getKeyPair error: {err}\n WARNING: Evennia could not "
              "auto-generate SSH keypair. Using conch default keys instead.\n"
              "If this error persists, create {pub} and "
              "{priv} yourself using third-party tools.".format(err=err, pub=pubkeyfile, priv=privkeyfile))

    factory.services = factory.services.copy()
    factory.services['ssh-userauth'] = ExtraInfoAuthServer

    factory.portal.registerChecker(PlayerDBPasswordChecker(factory))

    return factory
