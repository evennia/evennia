"""
Default Typeclass for Comms.

See objects.objects for more information on Typeclassing.
"""
from src.comms import Msg, TempMsg
from src.typeclasses.typeclass import TypeClass
from src.utils import logger
from src.utils.utils import make_iter


class Channel(TypeClass):
    """
    This is the base class for all Comms. Inherit from this to create different
    types of communication channels.
    """

    # helper methods, for easy overloading

    def channel_prefix(self, msg=None, emit=False):
        """
        How the channel should prefix itself for users. Return a string.
        """
        return '[%s] ' % self.key

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
        pose = False
        message = msg.message
        message_start = message.lstrip()
        if message_start.startswith((':', ';')):
            pose = True
            message = message[1:]
            if not message.startswith((':', "'", ',')):
                if not message.startswith(' '):
                    message = ' ' + message
        if pose:
            return '%s%s' % (sender_string, message)
        else:
            return '%s: %s' % (sender_string, message)

    def format_external(self, msg, senders, emit=False):
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
                          sender_strings=None, external=False):
        """
        Generates the formatted string sent to listeners on a channel.
        """
        if sender_strings or external:
            body = self.format_external(msg, sender_strings, emit=emit)
        else:
            body = self.format_message(msg, emit=emit)
        if prefix:
            body = "%s%s" % (self.channel_prefix(msg, emit=emit), body)
        msg.message = body
        return msg

    def at_channel_create(self):
        """
        Run at channel creation.
        """
        pass

    def pre_join_channel(self, joiner):
        """
        Run right before a channel is joined. If this returns a false value,
        channel joining is aborted.
        """
        return True

    def post_join_channel(self, joiner):
        """
        Run right after an object or player joins a channel.
        """
        return True

    def pre_leave_channel(self, leaver):
        """
        Run right before a user leaves a channel. If this returns a false
        value, leaving the channel will be aborted.
        """
        return True

    def post_leave_channel(self, leaver):
        """
        Run right after an object or player leaves a channel.
        """
        pass

    def pre_send_message(self, msg):
        """
        Run before a message is sent to the channel.

        This should return the message object, after any transformations.
        If the message is to be discarded, return a false value.
        """
        return msg

    def post_send_message(self, msg):
        """
        Run after a message is sent to the channel.
        """
        pass

    def at_init(self):
        """
        This is always called whenever this channel is initiated --
        that is, whenever it its typeclass is cached from memory. This
        happens on-demand first time the channel is used or activated
        in some way after being created but also after each server
        restart or reload.
        """
        pass

    def distribute_message(self, msg, online=False):
        """
        Method for grabbing all listeners that a message should be sent to on
        this channel, and sending them a message.
        """
        # get all players connected to this channel and send to them
        for player in self.dbobj.db_subscriptions.all():
            player = player.typeclass
            try:
                # note our addition of the from_channel keyword here. This could be checked
                # by a custom player.msg() to treat channel-receives differently.
                player.msg(msg.message, from_obj=msg.senders, from_channel=self.id)
            except AttributeError, e:
                logger.log_trace("%s\nCannot send msg to player '%s'." % (e, player))

    def msg(self, msgobj, header=None, senders=None, sender_strings=None,
            persistent=False, online=False, emit=False, external=False):
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
                                        external=external)
        self.distribute_message(msgobj, online=online)
        self.post_send_message(msgobj)
        return True

    def tempmsg(self, message, header=None, senders=None):
        """
        A wrapper for sending non-persistent messages.
        """
        self.msg(message, senders=senders, header=header, persistent=False)

