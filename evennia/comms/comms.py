"""
Base typeclass for in-game Channels.

"""

from evennia.typeclasses.models import TypeclassBase
from evennia.comms.models import TempMsg, ChannelDB
from evennia.comms.managers import ChannelManager
from evennia.utils import logger
from evennia.utils.utils import make_iter
from future.utils import with_metaclass


class DefaultChannel(with_metaclass(TypeclassBase, ChannelDB)):
    """
    This is the base class for all Channel Comms. Inherit from this to
    create different types of communication channels.

    """
    objects = ChannelManager()

    def at_first_save(self):
        """
        Called by the typeclass system the very first time the channel
        is saved to the database. Generally, don't overload this but
        the hooks called by this method.

        """
        self.at_channel_creation()
        self.attributes.add("log_file", "channel_%s.log" % self.key)
        if hasattr(self, "_createdict"):
            # this is only set if the channel was created
            # with the utils.create.create_channel function.
            cdict = self._createdict
            if not cdict.get("key"):
                if not self.db_key:
                    self.db_key = "#i" % self.dbid
            elif cdict["key"] and self.key != cdict["key"]:
                self.key = cdict["key"]
            if cdict.get("aliases"):
                self.aliases.add(cdict["aliases"])
            if cdict.get("locks"):
                self.locks.add(cdict["locks"])
            if cdict.get("keep_log"):
                self.attributes.add("keep_log", cdict["keep_log"])
            if cdict.get("desc"):
                self.attributes.add("desc", cdict["desc"])

    def at_channel_creation(self):
        """
        Called once, when the channel is first created.

        """
        pass

    # helper methods, for easy overloading

    def has_connection(self, subscriber):
        """
        Checks so this player is actually listening
        to this channel.

        Args:
            subscriber (Player or Object): Entity to check.

        Returns:
            has_sub (bool): Whether the subscriber is subscribing to
                this channel or not.

        Notes:
            This will first try Player subscribers and only try Object
                if the Player fails.

        """
        has_sub = self.subscriptions.has(subscriber)
        if not has_sub and hasattr(subscriber, "player"):
            # it's common to send an Object when we
            # by default only allow Players to subscribe.
            has_sub = self.subscriptions.has(subscriber.player)
        return has_sub


    def connect(self, subscriber):
        """
        Connect the user to this channel. This checks access.

        Args:
            subscriber (Player or Object): the entity to subscribe
                to this channel.

        Returns:
            success (bool): Whether or not the addition was
                successful.

        """
        # check access
        if not self.access(subscriber, 'listen'):
            return False
        # pre-join hook
        connect = self.pre_join_channel(subscriber)
        if not connect:
            return False
        # subscribe
        self.subscriptions.add(subscriber)
        # post-join hook
        self.post_join_channel(subscriber)
        return True

    def disconnect(self, subscriber):
        """
        Disconnect entity from this channel.

        Args:
            subscriber (Player of Object): the
                entity to disconnect.

        Returns:
            success (bool): Whether or not the removal was
                successful.

        """
        # pre-disconnect hook
        disconnect = self.pre_leave_channel(subscriber)
        if not disconnect:
            return False
        # disconnect
        self.subscriptions.remove(subscriber)
        # post-disconnect hook
        self.post_leave_channel(subscriber)
        return True

    def access(self, accessing_obj, access_type='listen', default=False, no_superuser_bypass=False):
        """
        Determines if another object has permission to access.

        Args:
            accessing_obj (Object): Object trying to access this one.
            access_type (str, optional): Type of access sought.
            default (bool, optional): What to return if no lock of access_type was found
            no_superuser_bypass (bool, optional): Turns off superuser
                lock bypass. Be careful with this one.

        Returns:
            return (bool): Result of lock check.

        """
        return self.locks.check(accessing_obj, access_type=access_type,
                                default=default, no_superuser_bypass=no_superuser_bypass)

    def delete(self):
        """
        Deletes channel while also cleaning up channelhandler.

        """
        self.attributes.clear()
        self.aliases.clear()
        super(DefaultChannel, self).delete()
        from evennia.comms.channelhandler import CHANNELHANDLER
        CHANNELHANDLER.update()

    def message_transform(self, msg, emit=False, prefix=True,
                          sender_strings=None, external=False):
        """
        Generates the formatted string sent to listeners on a channel.

        Args:
            msg (str): Message to send.
            emit (bool, optional): In emit mode the message is not associated
                with a specific sender name.
            prefix (bool, optional): Prefix `msg` with a text given by `self.channel_prefix`.
            sender_strings (list, optional): Used by bots etc, one string per external sender.
            external (bool, optional): If this is an external sender or not.

        """
        if sender_strings or external:
            body = self.format_external(msg, sender_strings, emit=emit)
        else:
            body = self.format_message(msg, emit=emit)
        if prefix:
            body = "%s%s" % (self.channel_prefix(msg, emit=emit), body)
        msg.message = body
        return msg

    def distribute_message(self, msgobj, online=False):
        """
        Method for grabbing all listeners that a message should be
        sent to on this channel, and sending them a message.

        Args:
            msgobj (Msg or TempMsg): Message to distribute.
            online (bool): Only send to receivers who are actually online
                (not currently used):

        Notes:
            This is also where logging happens, if enabled.

        """
        # get all players connected to this channel and send to them
        for entity in self.subscriptions.all():
            try:
                # note our addition of the from_channel keyword here. This could be checked
                # by a custom player.msg() to treat channel-receives differently.
                entity.msg(msgobj.message, from_obj=msgobj.senders, options={"from_channel":self.id})
            except AttributeError as e:
                logger.log_trace("%s\nCannot send msg to '%s'." % (e, entity))

        if msgobj.keep_log:
            # log to file
            logger.log_file(msgobj.message, self.attributes.get("log_file") or "channel_%s.log" % self.key)

    def msg(self, msgobj, header=None, senders=None, sender_strings=None,
            keep_log=None, online=False, emit=False, external=False):
        """
        Send the given message to all players connected to channel. Note that
        no permission-checking is done here; it is assumed to have been
        done before calling this method. The optional keywords are not used if
        persistent is False.

        Args:
            msgobj (Msg, TempMsg or str): If a Msg/TempMsg, the remaining
                keywords will be ignored (since the Msg/TempMsg object already
                has all the data). If a string, this will either be sent as-is
                (if persistent=False) or it will be used together with `header`
                and `senders` keywords to create a Msg instance on the fly.
            header (str, optional): A header for building the message.
            senders (Object, Player or list, optional): Optional if persistent=False, used
                to build senders for the message.
            sender_strings (list, optional): Name strings of senders. Used for external
                connections where the sender is not a player or object.
                When this is defined, external will be assumed.
            keep_log (bool or None, optional): This allows to temporarily change the logging status of
                this channel message. If `None`, the Channel's `keep_log` Attribute will
                be used. If `True` or `False`, that logging status will be used for this
                message only (note that for unlogged channels, a `True` value here will
                create a new log file only for this message).
            online (bool, optional) - If this is set true, only messages people who are
                online. Otherwise, messages all players connected. This can
                make things faster, but may not trigger listeners on players
                that are offline.
            emit (bool, optional) - Signals to the message formatter that this message is
                not to be directly associated with a name.
            external (bool, optional): Treat this message as being
                agnostic of its sender.

        Returns:
            success (bool): Returns `True` if message sending was
                successful, `False` otherwise.

        """
        senders = make_iter(senders) if senders else []
        if isinstance(msgobj, basestring):
            # given msgobj is a string - convert to msgobject (always TempMsg)
            msgobj = TempMsg(senders=senders, header=header, message=msgobj, channels=[self])
        # we store the logging setting for use in distribute_message()
        msgobj.keep_log = keep_log if keep_log is not None else self.db.keep_log

        # start the sending
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

        Args:
            message (str): Message to send.
            header (str, optional): Header of message to send.
            senders (Object or list, optional): Senders of message to send.

        """
        self.msg(message, senders=senders, header=header, keep_log=False)


    # hooks

    def channel_prefix(self, msg=None, emit=False):

        """
        Hook method. How the channel should prefix itself for users.

        Args:
            msg (str, optional): Prefix text
            emit (bool, optional): Switches to emit mode, which usually
                means to ignore any sender information. Not used by default.

        Returns:
            prefix (str): The created channel prefix.

        """
        return '[%s] ' % self.key

    def format_senders(self, senders=None):
        """
        Hook method. Function used to format a list of sender names.

        Args:
            senders (list): Sender object names.

        Returns:
            formatted_list (str): The list of names formatted appropriately.

        Notes:
            This function exists separately so that external sources
            can use it to format source names in the same manner as
            normal object/player names.

        """
        if not senders:
            return ''
        return ', '.join(senders)

    def pose_transform(self, msgobj, sender_string):
        """
        Hook method. Detects if the sender is posing, and modifies the
        message accordingly.

        Args:
            msgob (Msg or TempMsg): The message to analyze for a pose.
            sender_string (str): The name of the sender/poser.

        Returns:
            string (str): A message that combines the `sender_string`
                component with `msg` in different ways depending on if a
                pose was performed or not (this must be analyzed by the
                hook).

        """
        pose = False
        message = msgobj.message
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

    def format_external(self, msgobj, senders, emit=False):
        """
        Hook method. Used for formatting external messages. This is
        needed as a separate operation because the senders of external
        messages may not be in-game objects/players, and so cannot
        have things like custom user preferences.

        Args:
            msgobj (Msg or TempMsg): The message to send.
            senders (list): Strings, one per sender.
            emit (bool, optional): A sender-agnostic message or not.

        Returns:
            transformed (str): A formatted string.

        """
        if emit or not senders:
            return msgobj.message
        senders = ', '.join(senders)
        return self.pose_transform(msgobj, senders)

    def format_message(self, msgobj, emit=False):
        """
        Hook method. Formats a message body for display.

        Args:
            msgob (Msg or TempMsg): The message object to send.
            emit (bool, optional): The message is agnostic of senders.

        Returns:
            transformed (str): The formatted message.

        """
        # We don't want to count things like external sources as senders for
        # the purpose of constructing the message string.
        senders = [sender for sender in msgobj.senders if hasattr(sender, 'key')]
        if not senders:
            emit = True
        if emit:
            return msgobj.message
        else:
            senders = [sender.key for sender in msgobj.senders]
            senders = ', '.join(senders)
            return self.pose_transform(msgobj, senders)

    def pre_join_channel(self, joiner):
        """
        Hook method. Runs right before a channel is joined. If this
        returns a false value, channel joining is aborted.

        Args:
            joiner (object): The joining object.

        Returns:
            should_join (bool): If `False`, channel joining is aborted.

        """
        return True

    def post_join_channel(self, joiner):
        """
        Hook method. Runs right after an object or player joins a channel.

        Args:
            joiner (object): The joining object.

        """
        pass

    def pre_leave_channel(self, leaver):
        """
        Hook method. Runs right before a user leaves a channel. If this returns a false
        value, leaving the channel will be aborted.

        Args:
            joiner (object): The joining object.

        Returns:
            should_leave (bool): If `False`, channel parting is aborted.

        """
        return True

    def post_leave_channel(self, leaver):
        """
        Hook method. Runs right after an object or player leaves a channel.

        Args:
            joiner (object): The joining object.

        """
        pass

    def pre_send_message(self, msg):
        """
        Hook method.  Runs before a message is sent to the channel and
        should return the message object, after any transformations.
        If the message is to be discarded, return a false value.

        Args:
            msg (Msg or TempMsg): Message to send.

        Returns:
            result (Msg, TempMsg or bool): If False, abort send.

        """
        return msg

    def post_send_message(self, msg):
        """
        Hook method. Run after a message is sent to the channel.

        Args:
            msg (Msg or TempMsg): Message sent.

        """
        pass

    def at_init(self):
        """
        Hook method. This is always called whenever this channel is
        initiated -- that is, whenever it its typeclass is cached from
        memory. This happens on-demand first time the channel is used
        or activated in some way after being created but also after
        each server restart or reload.

        """
        pass
