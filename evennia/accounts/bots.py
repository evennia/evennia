"""
Bots are a special child typeclasses of
Account that are  controlled by the server.

"""

import time

from django.conf import settings
from django.utils.translation import gettext as _

from evennia.accounts.accounts import DefaultAccount
from evennia.scripts.scripts import DefaultScript
from evennia.utils import logger, search, utils
from evennia.utils.ansi import strip_ansi

_IDLE_TIMEOUT = settings.IDLE_TIMEOUT

_IRC_ENABLED = settings.IRC_ENABLED
_RSS_ENABLED = settings.RSS_ENABLED
_GRAPEVINE_ENABLED = settings.GRAPEVINE_ENABLED
_DISCORD_ENABLED = settings.DISCORD_ENABLED and hasattr(settings, "DISCORD_BOT_TOKEN")

_SESSIONS = None


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

    def at_server_start(self):
        self.at_start()

    def at_start(self):
        """
        Kick bot into gear.

        """
        if not self.account.sessions.all():
            self.account.start()

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
        self.scripts.add(BotStarter, key="bot_starter")
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

        Keyword Args:
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
        Keyword Args:
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
                    obj.msg("Nicks at {chstr}:\n {nicklist}".format(chstr=chstr, nicklist=nicklist))
                self._nicklist_callers = []
            return

        elif kwargs["type"] == "ping":
            # the return of a ping
            if hasattr(self, "_ping_callers") and self._ping_callers:
                chstr = f"{self.db.irc_channel} ({self.db.irc_network}:{self.db.irc_port})"
                for obj in self._ping_callers:
                    obj.msg(
                        "IRC ping return from {chstr} took {time}s.".format(
                            chstr=chstr, time=kwargs["timing"]
                        )
                    )
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
#


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

        Keyword Args:
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

                text = text[0] if isinstance(text, (tuple, list)) else text

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


# Discord


class DiscordBot(Bot):
    """
    Discord bot relay. You will need to set up your own bot
    (https://discord.com/developers/applications) and add the bot token as `DISCORD_BOT_TOKEN` to
    `secret_settings.py` to use
    """

    factory_path = "evennia.server.portal.discord.DiscordWebsocketServerFactory"

    def at_init(self):
        """
        Load required channels back into memory

        """
        if channel_links := self.db.channels:
            # this attribute contains a list of evennia<->discord links in the form
            # of ("evennia_channel", "discord_chan_id")
            # grab Evennia channels, cache and connect
            channel_set = {evchan for evchan, dcid in channel_links}
            self.ndb.ev_channels = {}
            for channel_name in list(channel_set):
                channel = search.search_channel(channel_name)
                if not channel:
                    raise RuntimeError(f"Evennia Channel {channel_name} not found.")
                channel = channel[0]
                self.ndb.ev_channels[channel_name] = channel

    def start(self):
        """
        Tell the Discord protocol to connect.

        """
        if not _DISCORD_ENABLED:
            self.delete()
            return

        if self.ndb.ev_channels:
            for channel in self.ndb.ev_channels.values():
                channel.connect(self)

        elif channel_links := self.db.channels:
            # this attribute contains a list of evennia<->discord links in the form
            # of ("evennia_channel", "discord_chan_id")
            # grab Evennia channels, cache and connect
            channel_set = {evchan for evchan, dcid in channel_links}
            self.ndb.ev_channels = {}
            for channel_name in list(channel_set):
                channel = search.search_channel(channel_name)
                if not channel:
                    raise RuntimeError(f"Evennia Channel {channel_name} not found.")
                channel = channel[0]
                self.ndb.ev_channels[channel_name] = channel
                channel.connect(self)

        # connect
        global _SESSIONS
        if not _SESSIONS:
            from evennia.server.sessionhandler import SESSIONS as _SESSIONS
        # these will be made available as properties on the protocol factory
        configdict = {"uid": self.dbid}
        _SESSIONS.start_bot_session(self.factory_path, configdict)

    def at_pre_channel_msg(self, message, channel, senders=None, **kwargs):
        """
        Called by the Channel just before passing a message into `channel_msg`.

        We overload this to set the channel tag prefix.

        """
        kwargs["no_prefix"] = not self.db.tag_channel
        return super().at_pre_channel_msg(message, channel, senders=senders, **kwargs)

    def channel_msg(self, message, channel, senders=None, relayed=False, **kwargs):
        """
        Passes channel messages received on to discord

        Args:
            message (str) - Incoming text from channel.
            channel (Channel) - The channel the message is being received from

        Keyword Args:
            senders (list or None) - Object(s) sending the message
            relayed (bool) - A flag identifying whether the message was relayed by the bot.

        """
        if relayed:
            # don't relay our own relayed messages
            return
        if channel_list := self.db.channels:
            # get all the discord channels connected to this evennia channel
            channel_name = channel.name
            for dc_chan in [dcid for evchan, dcid in channel_list if evchan == channel_name]:
                # send outputfunc channel(msg, discord channel)
                super().msg(channel=(strip_ansi(message.strip()), dc_chan))

    def direct_msg(self, message, sender, **kwargs):
        """
        Called when the Discord bot receives a direct message on Discord.

        Args:
            message (str)  - Incoming text from Discord.
            sender (tuple) - The Discord info for the sender in the form (id, nickname)

        Keyword args:
            **kwargs (optional) - Unused by default, but can carry additional data from the protocol.

        """
        pass

    def relay_to_channel(
        self, message, to_channel, sender=None, from_channel=None, from_server=None, **kwargs
    ):
        """
        Formats and sends a Discord -> Evennia message. Called when the Discord bot receives a
        channel message on Discord.

        Args:
            message (str)  - Incoming text from Discord.
            to_channel (Channel) - The Evennia channel receiving the message

        Keyword args:
            sender (tuple) - The Discord info for the sender in the form `(id, nickname)`
            from_channel (str) - The Discord channel name
            from_server (str) - The Discord server name
            kwargs - Any additional keywords. Unused by default, but available for adding additional
                flags or parameters.

        """

        tag_str = ""
        if from_channel and self.db.tag_channel:
            tag_str = f"#{from_channel}"
        if from_server and self.db.tag_guild:
            if tag_str:
                tag_str += f"@{from_server}"
            else:
                tag_str = from_server

        if tag_str:
            tag_str = f"[{tag_str}] "

        if sender:
            sender_name = f"|c{sender[1]}|n: "

        message = f"{tag_str}{sender_name}{message}"
        to_channel.msg(message, senders=None, relayed=True)

    def execute_cmd(
        self,
        txt=None,
        session=None,
        type=None,
        sender=None,
        **kwargs,
    ):
        """
        Take incoming data from protocol and send it to connected channel. This is
        triggered by the bot_data_in Inputfunc.

        Keyword args:
            txt (str) - The content of the message from Discord.
            session (Session) - The protocol session this command came from.
            type (str, optional) - Indicates the type of activity from Discord, if
                the protocol pre-processed it.
            sender (tuple) - Identifies the author of the Discord activity in a tuple of two
                strings, in the form of (id, nickname)

            kwargs - Any additional data specific to a particular type of actions. The data for
                any Discord actions not pre-processed by the protocol will also be passed via kwargs.

        """
        # normal channel message
        if type == "channel":
            channel_id = kwargs.get("channel_id")
            channel_name = self.db.discord_channels.get(channel_id, {}).get("name", channel_id)
            guild_id = kwargs.get("guild_id")
            guild = self.db.guilds.get(guild_id)

            if channel_links := self.db.channels:
                for ev_channel in [
                    ev_chan for ev_chan, dc_id in channel_links if dc_id == channel_id
                ]:
                    channel = search.channel_search(ev_channel)
                    if not channel:
                        continue
                    channel = channel[0]
                    self.relay_to_channel(txt, channel, sender, channel_name, guild)

        # direct message
        elif type == "direct":
            # pass on to the DM hook
            self.direct_msg(txt, sender, **kwargs)

        # guild info update
        elif type == "guild":
            if guild_id := kwargs.get("guild_id"):
                if not self.db.guilds:
                    self.db.guilds = {}
                self.db.guilds[guild_id] = kwargs.get("guild_name", "Unidentified")
                if not self.db.discord_channels:
                    self.db.discord_channels = {}
                self.db.discord_channels.update(kwargs.get("channels", {}))
