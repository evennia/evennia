from ev import Player, Character
from src.comms.comms import Channel
from . lib.penn import speak
from src.utils.utils import make_iter
from src.comms import Msg, TempMsg, ChannelDB

CHANNEL_PLAYER_DEFAULTS = {'title': None, 'muzzled': None, 'muzzledby': None}
CHANNEL_CHARACTER_DEFAULTS = CHANNEL_PLAYER_DEFAULTS

class MainPlayer(Player):

    def get_comm_play_conf(self,channel,key):
        if not self.db.comm_play_config:
            self.db.comm_play_config = {}
        if not isinstance(self.db.comm_play_config,dict):
            self.db.comm_play_config = {}
        if not channel in self.db.comm_play_config:
            self.db.comm_play_config[channel] = {}
            self.db.comm_play_config[channel].update(CHANNEL_PLAYER_DEFAULTS)
        return self.db.comm_play_config[channel].setdefault(key,default=CHANNEL_PLAYER_DEFAULTS.get(key))
    
    def set_comm_play_conf(self,channel,key,value):
        if not self.db.comm_play_config:
            self.db.comm_play_config = {}
        if not isinstance(self.db.comm_play_config,dict):
            self.db.comm_play_config = {}
        if not channel in self.db.comm_play_config:
            self.db.comm_play_config[channel] = {}
            self.db.comm_play_config[channel].update(CHANNEL_PLAYER_DEFAULTS)
        self.db.comm_play_config[channel].update({key: value})

    def get_comm_char_conf(self,character,channel,key):
        if not self.db.comm_char_config:
            self.db.comm_char_config = {}
        if not isinstance(self.db.comm_char_config,dict):
            self.db.comm_char_config = {}
        if not character in self.db.comm_char_config:
            self.db.comm_char_config[character] = {}
        if not channel in self.db.comm_char_config[character]:
            self.db.comm_char_config[character][channel] = {}
            self.db.comm_char_config[character][channel].update(CHANNEL_CHARACTER_DEFAULTS)
        return self.db.comm_char_config[character][channel].setdefault(key,default=CHANNEL_CHARACTER_DEFAULTS.get(key))
    
    def set_comm_char_conf(self,character,channel,key,value):
        if not self.db.comm_char_config:
            self.db.comm_char_config = {}
        if not isinstance(self.db.comm_char_config,dict):
            self.db.comm_char_config = {}
        if not character in self.db.comm_char_config:
            self.db.comm_char_config[character] = {}
        if not channel in self.db.comm_char_config[character]:
            self.db.comm_char_config[character][channel] = {}
        self.db.comm_char_config[channel].update({key: value})

class MainCharacter(Character):
    """
    This class forms the backbone of the codesuite's character class.
    """

class MainChannel(Channel):
    """
    "This class attempts to mimic the aesthetic of PennMUSH's Channels.
    """
    
    def get_conf(self,key):
        """
        This retrieves configuration data from the channel's db attributes.
        """
        if not self.attributes.has('config'):
            self.db.config = {}
        if not isinstance(self.db.config,dict):
            self.db.config = {}
        setdef = {'displaymode': 0, 'color': 'n', 'titles': True}.get(key)
        return self.db.config.setdefault(key,default=setdef)
    
    def channel_prefix(self, msg=None, emit=False):
        """
        How the channel should prefix itself for users. Return a string.
        """
        return '<{%s%s{n> ' % (self.get_conf('color'), self.key)
    
    def channel_title(self,title):
        return title

    def format_senders(self, senders=None):
        """
        Function used to format a list of sender names.

        This function exists separately so that external sources can use
        it to format source names in the same manner as normal object/player
        names.
        """
        if not senders:
            return ''
        return ', '.join(senders)

    def pose_transform(self, msg, sender_string):
        """
        Detects if the sender is posing, and modifies the message accordingly.
        """
        return speak(sender_string,msg.message,fancy=True)

    def format_external(self, msg, senders, emit=False, sender_string=None):
        """
        Used for formatting external messages. This is needed as a separate
        operation because the senders of external messages may not be in-game
        objects/players, and so cannot have things like custom user
        preferences.

        senders should be a list of strings, each containing a sender.
        msg should contain the body of the message to be sent.
        """
        if not senders:
            emit = True
        if emit:
            return msg.message
        if not isinstance(senders,basestring):
            senders = ', '.join(senders)
        return self.pose_transform(msg, senders)

    def format_message(self, msg, emit=False):
        """
        Formats a message body for display.

        If emit is True, it means the message is intended to be posted detached
        from an identity.
        """
        # We don't want to count things like external sources as senders for
        # the purpose of constructing the message string.
        senders = [sender for sender in msg.senders if hasattr(sender, 'key')]
        if not senders:
            emit = True
        if emit:
            return msg.message
        else:
            senders = [sender.key for sender in msg.senders]
            senders = ', '.join(senders)
            return self.pose_transform(msg, senders)

    def message_transform(self, msg, emit=False, prefix=True,
                          sender_strings=None, external=False,title=None):
        """
        Generates the formatted string sent to listeners on a channel.
        """
        if sender_strings or external:
            body = self.format_external(msg, sender_strings, emit=emit)
        else:
            body = self.format_message(msg, emit=emit)
        if prefix and not title:
            body = "%s%s" % (self.channel_prefix(msg, emit=emit), body)
        elif prefix and title:
            body = "%s%s%s" % (self.channel_prefix(msg, emit=emit), self.channel_title(title), body)
        msg.message = body
        return msg


    def msg(self, msgobj, header=None, senders=None, sender_strings=None,
            persistent=False, online=False, emit=False, external=False, title=None):
        """
        Send the given message to all players connected to channel. Note that
        no permission-checking is done here; it is assumed to have been
        done before calling this method. The optional keywords are not used if
        persistent is False.

        msgobj - a Msg/TempMsg instance or a message string. If one of the
                 former, the remaining keywords will be ignored. If a string,
                 this will either be sent as-is (if persistent=False) or it
                 will be used together with header and senders keywords to
                 create a Msg instance on the fly.
        senders - an object, player or a list of objects or players.
                 Optional if persistent=False.
        sender_strings - Name strings of senders. Used for external
                connections where the sender is not a player or object. When
                this is defined, external will be assumed.
        external - Treat this message agnostic of its sender.
        persistent (default False) - ignored if msgobj is a Msg or TempMsg.
                If True, a Msg will be created, using header and senders
                keywords. If False, other keywords will be ignored.
        online (bool) - If this is set true, only messages people who are
                online. Otherwise, messages all players connected. This can
                make things faster, but may not trigger listeners on players
                that are offline.
        emit (bool) - Signals to the message formatter that this message is
                not to be directly associated with a name.
        title - A prefix to the message.
        """
        if senders:
            senders = make_iter(senders)
        else:
            senders = []
        if isinstance(msgobj, basestring):
            # given msgobj is a string
            msg = msgobj
            if persistent and self.db.keep_log:
                msgobj = Msg()
                msgobj.save()
            else:
                # Use TempMsg, so this message is not stored.
                msgobj = TempMsg()
            msgobj.header = header
            msgobj.message = msg
            msgobj.channels = [self.dbobj]  # add this channel

        if not msgobj.senders:
            msgobj.senders = senders
        msgobj = self.pre_send_message(msgobj)
        if not msgobj:
            return False
        msgobj = self.message_transform(msgobj, emit=emit,
                                        sender_strings=sender_strings,
                                        external=external,
                                        title=title)
        self.distribute_message(msgobj, online=online)
        self.post_send_message(msgobj)
        return True

    def tempmsg(self, message, header=None, senders=None):
        """
        A wrapper for sending non-persistent messages.
        """
        self.msg(message, senders=senders, header=header, persistent=False)
        