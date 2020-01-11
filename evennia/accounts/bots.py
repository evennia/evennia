"""
Bots are a special child typeclasses of
Account that are  controlled by the server.

"""

import time
from django.conf import settings
from evennia.accounts.accounts import DefaultAccount
from evennia.scripts.scripts import DefaultScript
from evennia.utils import search
from evennia.utils import utils

_IDLE_TIMEOUT = settings.IDLE_TIMEOUT

_IRC_ENABLED = settings.IRC_ENABLED
_RSS_ENABLED = settings.RSS_ENABLED
_GRAPEVINE_ENABLED = settings.GRAPEVINE_ENABLED


_SESSIONS = None


# Bot helper utilities


class BotStarter(DefaultScript):
    """
    This non-repeating script has the
    sole purpose of kicking its bot
    into gear when it is initialized.

    """

    def at_script_creation(self):
        """
        Called once, when script is created.

        """
        self.key = "botstarter"
        self.desc = "bot start/keepalive"
        self.persistent = True
        self.db.started = False

    def at_start(self):
        """
        Kick bot into gear.

        """
        if not self.db.started:
            self.account.start()
            self.db.started = True

    def at_repeat(self):
        """
        Called self.interval seconds to keep connection. We cannot use
        the IDLE command from inside the game since the system will
        not catch it (commands executed from the server side usually
        has no sessions). So we update the idle counter manually here
        instead. This keeps the bot getting hit by IDLE_TIMEOUT.

        """
        global _SESSIONS
        if not _SESSIONS:
            from evennia.server.sessionhandler import SESSIONS as _SESSIONS
        for session in _SESSIONS.sessions_from_account(self.account):
            session.update_session_counters(idle=True)

    def at_server_reload(self):
        """
        If server reloads we don't need to reconnect the protocol
        again, this is handled by the portal reconnect mechanism.

        """
        self.db.started = True

    def at_server_shutdown(self):
        """
        Make sure we are shutdown.

        """
        self.db.started = False


#
# Bot base class


class Bot(DefaultAccount):
    """
    A Bot will start itself when the server starts (it will generally
    not do so on a reload - that will be handled by the normal Portal
    session resync)

    """

    def basetype_setup(self):
        """
        This sets up the basic properties for the bot.

        """
        # the text encoding to use.
        self.db.encoding = "utf-8"
        # A basic security setup (also avoid idle disconnects)
        lockstring = (
            "examine:perm(Admin);edit:perm(Admin);delete:perm(Admin);"
            "boot:perm(Admin);msg:false();noidletimeout:true()"
        )
        self.locks.add(lockstring)
        # set the basics of being a bot
        script_key = str(self.key)
        self.scripts.add(BotStarter, key=script_key)
        self.is_bot = True

    def start(self, **kwargs):
        """
        This starts the bot, whatever that may mean.

        """
        pass

    def msg(self, text=None, from_obj=None, session=None, options=None, **kwargs):
        """
        Evennia -> outgoing protocol

        """
        super().msg(text=text, from_obj=from_obj, session=session, options=options, **kwargs)

    def execute_cmd(self, raw_string, session=None):
        """
        Incoming protocol -> Evennia

        """
        super().msg(raw_string, session=session)

    def at_server_shutdown(self):
        """
        We need to handle this case manually since the shutdown may be
        a reset.

        """
        for session in self.sessions.all():
            session.sessionhandler.disconnect(session)


# Bot implementations

# IRC


class IRCBot(Bot):
    """
    Bot for handling IRC connections.

    """

    # override this on a child class to use custom factory
    factory_path = "evennia.server.portal.irc.IRCBotFactory"

    def start(
        self,
        ev_channel=None,
        irc_botname=None,
        irc_channel=None,
        irc_network=None,
        irc_port=None,
        irc_ssl=None,
    ):
        """
        Start by telling the portal to start a new session.

        Args:
            ev_channel (str): Key of the Evennia channel to connect to.
            irc_botname (str): Name of bot to connect to irc channel. If
                not set, use `self.key`.
            irc_channel (str): Name of channel on the form `#channelname`.
            irc_network (str): URL of the IRC network, like `irc.freenode.net`.
            irc_port (str): Port number of the irc network, like `6667`.
            irc_ssl (bool): Indicates whether to use SSL connection.

        """
        if not _IRC_ENABLED:
            # the bot was created, then IRC was turned off. We delete
            # ourselves (this will also kill the start script)
            self.delete()
            return

        global _SESSIONS
        if not _SESSIONS:
            from evennia.server.sessionhandler import SESSIONS as _SESSIONS

        # if keywords are given, store (the BotStarter script
        # will not give any keywords, so this should normally only
        # happen at initialization)
        if irc_botname:
            self.db.irc_botname = irc_botname
        elif not self.db.irc_botname:
            self.db.irc_botname = self.key
        if ev_channel:
            # connect to Evennia channel
            channel = search.channel_search(ev_channel)
            if not channel:
                raise RuntimeError(f"Evennia Channel '{ev_channel}' not found.")
            channel = channel[0]
            channel.connect(self)
            self.db.ev_channel = channel
        if irc_channel:
            self.db.irc_channel = irc_channel
        if irc_network:
            self.db.irc_network = irc_network
        if irc_port:
            self.db.irc_port = irc_port
        if irc_ssl:
            self.db.irc_ssl = irc_ssl

        # instruct the server and portal to create a new session with
        # the stored configuration
        configdict = {
            "uid": self.dbid,
            "botname": self.db.irc_botname,
            "channel": self.db.irc_channel,
            "network": self.db.irc_network,
            "port": self.db.irc_port,
            "ssl": self.db.irc_ssl,
        }
        _SESSIONS.start_bot_session(self.factory_path, configdict)

    def at_msg_send(self, **kwargs):
        "Shortcut here or we can end up in infinite loop"
        pass

    def get_nicklist(self, caller):
        """
        Retrive the nick list from the connected channel.

        Args:
            caller (Object or Account): The requester of the list. This will
                be stored and echoed to when the irc network replies with the
                requested info.

        Notes: Since the return is asynchronous, the caller is stored internally
            in a list; all callers in this list will get the nick info once it
            returns (it is a custom OOB inputfunc option). The callback will not
            survive a reload (which should be fine, it's very quick).
        """
        if not hasattr(self, "_nicklist_callers"):
            self._nicklist_callers = []
        self._nicklist_callers.append(caller)
        super().msg(request_nicklist="")
        return

    def ping(self, caller):
        """
        Fire a ping to the IRC server.

        Args:
            caller (Object or Account): The requester of the ping.

        """
        if not hasattr(self, "_ping_callers"):
            self._ping_callers = []
        self._ping_callers.append(caller)
        super().msg(ping="")

    def reconnect(self):
        """
        Force a protocol-side reconnect of the client without
        having to destroy/recreate the bot "account".

        """
        super().msg(reconnect="")

    def msg(self, text=None, **kwargs):
        """
        Takes text from connected channel (only).

        Args:
            text (str, optional): Incoming text from channel.

        Kwargs:
            options (dict): Options dict with the following allowed keys:
                - from_channel (str): dbid of a channel this text originated from.
                - from_obj (list): list of objects sending this text.

        """
        from_obj = kwargs.get("from_obj", None)
        options = kwargs.get("options", None) or {}

        if not self.ndb.ev_channel and self.db.ev_channel:
            # cache channel lookup
            self.ndb.ev_channel = self.db.ev_channel

        if (
            "from_channel" in options
            and text
            and self.ndb.ev_channel.dbid == options["from_channel"]
        ):
            if not from_obj or from_obj != [self]:
                super().msg(channel=text)

    def execute_cmd(self, session=None, txt=None, **kwargs):
        """
        Take incoming data and send it to connected channel. This is
        triggered by the bot_data_in Inputfunc.

        Args:
            session (Session, optional): Session responsible for this
                command. Note that this is the bot.
            txt (str, optional):  Command string.
        Kwargs:
            user (str): The name of the user who sent the message.
            channel (str): The name of channel the message was sent to.
            type (str): Nature of message. Either 'msg', 'action', 'nicklist'
                or 'ping'.
            nicklist (list, optional): Set if `type='nicklist'`. This is a list
                of nicks returned by calling the `self.get_nicklist`. It must look
                for a list `self._nicklist_callers` which will contain all callers
                waiting for the nicklist.
            timings (float, optional): Set if `type='ping'`. This is the return
                (in seconds) of a ping request triggered with `self.ping`. The
                return must look for a list `self._ping_callers` which will contain
                all callers waiting for the ping return.

        """
        if kwargs["type"] == "nicklist":
            # the return of a nicklist request
            if hasattr(self, "_nicklist_callers") and self._nicklist_callers:
                chstr = f"{self.db.irc_channel} ({self.db.irc_network}:{self.db.irc_port})"
                nicklist = ", ".join(sorted(kwargs["nicklist"], key=lambda n: n.lower()))
                for obj in self._nicklist_callers:
                    obj.msg(f"Nicks at {chstr}:\n {nicklist}")
                self._nicklist_callers = []
            return

        elif kwargs["type"] == "ping":
            # the return of a ping
            if hasattr(self, "_ping_callers") and self._ping_callers:
                chstr = f"{self.db.irc_channel} ({self.db.irc_network}:{self.db.irc_port})"
                for obj in self._ping_callers:
                    obj.msg(f"IRC ping return from {chstr} took {kwargs['timing']}s.")
                self._ping_callers = []
            return

        elif kwargs["type"] == "privmsg":
            # A private message to the bot - a command.
            user = kwargs["user"]

            if txt.lower().startswith("who"):
                # return server WHO list (abbreviated for IRC)
                global _SESSIONS
                if not _SESSIONS:
                    from evennia.server.sessionhandler import SESSIONS as _SESSIONS
                whos = []
                t0 = time.time()
                for sess in _SESSIONS.get_sessions():
                    delta_cmd = t0 - sess.cmd_last_visible
                    delta_conn = t0 - session.conn_time
                    account = sess.get_account()
                    whos.append(
                        "%s (%s/%s)"
                        % (
                            utils.crop("|w%s|n" % account.name, width=25),
                            utils.time_format(delta_conn, 0),
                            utils.time_format(delta_cmd, 1),
                        )
                    )
                text = f"Who list (online/idle): {', '.join(sorted(whos, key=lambda w: w.lower()))}"
            elif txt.lower().startswith("about"):
                # some bot info
                text = f"This is an Evennia IRC bot connecting from '{settings.SERVERNAME}'."
            else:
                text = "I understand 'who' and 'about'."
            super().msg(privmsg=((text,), {"user": user}))
        else:
            # something to send to the main channel
            if kwargs["type"] == "action":
                # An action (irc pose)
                text = f"{kwargs['user']}@{kwargs['channel']} {txt}"
            else:
                # msg - A normal channel message
                text = f"{kwargs['user']}@{kwargs['channel']}: {txt}"

            if not self.ndb.ev_channel and self.db.ev_channel:
                # cache channel lookup
                self.ndb.ev_channel = self.db.ev_channel

            if self.ndb.ev_channel:
                self.ndb.ev_channel.msg(text, senders=self)


#
# RSS


class RSSBot(Bot):
    """
    An RSS relayer. The RSS protocol itself runs a ticker to update
    its feed at regular intervals.

    """

    def start(self, ev_channel=None, rss_url=None, rss_rate=None):
        """
        Start by telling the portal to start a new RSS session

        Args:
            ev_channel (str): Key of the Evennia channel to connect to.
            rss_url (str): Full URL to the RSS feed to subscribe to.
            rss_rate (int): How often for the feedreader to update.

        Raises:
            RuntimeError: If `ev_channel` does not exist.

        """
        if not _RSS_ENABLED:
            # The bot was created, then RSS was turned off. Delete ourselves.
            self.delete()
            return

        global _SESSIONS
        if not _SESSIONS:
            from evennia.server.sessionhandler import SESSIONS as _SESSIONS

        if ev_channel:
            # connect to Evennia channel
            channel = search.channel_search(ev_channel)
            if not channel:
                raise RuntimeError(f"Evennia Channel '{ev_channel}' not found.")
            channel = channel[0]
            self.db.ev_channel = channel
        if rss_url:
            self.db.rss_url = rss_url
        if rss_rate:
            self.db.rss_rate = rss_rate
        # instruct the server and portal to create a new session with
        # the stored configuration
        configdict = {"uid": self.dbid, "url": self.db.rss_url, "rate": self.db.rss_rate}
        _SESSIONS.start_bot_session("evennia.server.portal.rss.RSSBotFactory", configdict)

    def execute_cmd(self, txt=None, session=None, **kwargs):
        """
        Take incoming data and send it to connected channel. This is
        triggered by the bot_data_in Inputfunc.

        Args:
            session (Session, optional): Session responsible for this
                command.
            txt (str, optional):  Command string.
            kwargs (dict, optional): Additional Information passed from bot.
                Not used by the RSSbot by default.

        """
        if not self.ndb.ev_channel and self.db.ev_channel:
            # cache channel lookup
            self.ndb.ev_channel = self.db.ev_channel
        if self.ndb.ev_channel:
            self.ndb.ev_channel.msg(txt, senders=self.id)


# Grapevine bot


class GrapevineBot(Bot):
    """
    g Grapevine (https://grapevine.haus) relayer. The channel to connect to is the first
    name in the settings.GRAPEVINE_CHANNELS list.

    """

    factory_path = "evennia.server.portal.grapevine.RestartingWebsocketServerFactory"

    def start(self, ev_channel=None, grapevine_channel=None):
        """
        Start by telling the portal to connect to the grapevine network.

        """
        if not _GRAPEVINE_ENABLED:
            self.delete()
            return

        global _SESSIONS
        if not _SESSIONS:
            from evennia.server.sessionhandler import SESSIONS as _SESSIONS

        # connect to Evennia channel
        if ev_channel:
            # connect to Evennia channel
            channel = search.channel_search(ev_channel)
            if not channel:
                raise RuntimeError(f"Evennia Channel '{ev_channel}' not found.")
            channel = channel[0]
            channel.connect(self)
            self.db.ev_channel = channel

        if grapevine_channel:
            self.db.grapevine_channel = grapevine_channel

        # these will be made available as properties on the protocol factory
        configdict = {"uid": self.dbid, "grapevine_channel": self.db.grapevine_channel}

        _SESSIONS.start_bot_session(self.factory_path, configdict)

    def at_msg_send(self, **kwargs):
        "Shortcut here or we can end up in infinite loop"
        pass

    def msg(self, text=None, **kwargs):
        """
        Takes text from connected channel (only).

        Args:
            text (str, optional): Incoming text from channel.

        Kwargs:
            options (dict): Options dict with the following allowed keys:
                - from_channel (str): dbid of a channel this text originated from.
                - from_obj (list): list of objects sending this text.

        """
        from_obj = kwargs.get("from_obj", None)
        options = kwargs.get("options", None) or {}

        if not self.ndb.ev_channel and self.db.ev_channel:
            # cache channel lookup
            self.ndb.ev_channel = self.db.ev_channel

        if (
            "from_channel" in options
            and text
            and self.ndb.ev_channel.dbid == options["from_channel"]
        ):
            if not from_obj or from_obj != [self]:
                # send outputfunc channel(msg, chan, sender)

                # TODO we should refactor channel formatting to operate on the
                # account/object level instead. For now, remove the channel/name
                # prefix since we pass that explicitly anyway
                prefix, text = text.split(":", 1)

                super().msg(
                    channel=(
                        text.strip(),
                        self.db.grapevine_channel,
                        ", ".join(obj.key for obj in from_obj),
                        {},
                    )
                )

    def execute_cmd(
        self,
        txt=None,
        session=None,
        event=None,
        grapevine_channel=None,
        sender=None,
        game=None,
        **kwargs,
    ):
        """
        Take incoming data from protocol and send it to connected channel. This is
        triggered by the bot_data_in Inputfunc.
        """
        if event == "channels/broadcast":
            # A private message to the bot - a command.

            text = f"{sender}@{game}: {txt}"

            if not self.ndb.ev_channel and self.db.ev_channel:
                # simple cache of channel lookup
                self.ndb.ev_channel = self.db.ev_channel
            if self.ndb.ev_channel:
                self.ndb.ev_channel.msg(text, senders=self)
