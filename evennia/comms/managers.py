"""
These managers define helper methods for accessing the database from
Comm system components.

"""


from django.db.models import Q
from evennia.typeclasses.managers import TypedObjectManager, TypeclassManager
from evennia.utils import logger

_GA = object.__getattribute__
_AccountDB = None
_ObjectDB = None
_ChannelDB = None
_SESSIONS = None

# error class


class CommError(Exception):
    """
    Raised by comm system, to allow feedback to player when caught.
    """

    pass


#
# helper functions
#


def dbref(inp, reqhash=True):
    """
    Valid forms of dbref (database reference number) are either a
    string '#N' or an integer N.

    Args:
        inp (int or str): A possible dbref to check syntactically.
        reqhash (bool): Require an initial hash `#` to accept.

    Returns:
        is_dbref (int or None): The dbref integer part if a valid
            dbref, otherwise `None`.

    """
    if reqhash and not (isinstance(inp, str) and inp.startswith("#")):
        return None
    if isinstance(inp, str):
        inp = inp.lstrip("#")
    try:
        if int(inp) < 0:
            return None
    except Exception:
        return None
    return inp


def identify_object(inp):
    """
    Helper function. Identifies if an object is an account or an object;
    return its database model

    Args:
        inp (any): Entity to be idtified.

    Returns:
        identified (tuple): This is a tuple with (`inp`, identifier)
            where `identifier` is one of "account", "object", "channel",
            "string", "dbref" or None.

    """
    if hasattr(inp, "__dbclass__"):
        clsname = inp.__dbclass__.__name__
        if clsname == "AccountDB":
            return inp, "account"
        elif clsname == "ObjectDB":
            return inp, "object"
        elif clsname == "ChannelDB":
            return inp, "channel"
    if isinstance(inp, str):
        return inp, "string"
    elif dbref(inp):
        return dbref(inp), "dbref"
    else:
        return inp, None


def to_object(inp, objtype="account"):
    """
    Locates the object related to the given accountname or channel key.
    If input was already the correct object, return it.

    Args:
        inp (any): The input object/string
        objtype (str): Either 'account' or 'channel'.

    Returns:
        obj (object): The correct object related to `inp`.

    """
    obj, typ = identify_object(inp)
    if typ == objtype:
        return obj
    if objtype == "account":
        if typ == "object":
            return obj.account
        if typ == "string":
            return _AccountDB.objects.get(user_username__iexact=obj)
        if typ == "dbref":
            return _AccountDB.objects.get(id=obj)
        logger.log_err("%s %s %s %s %s" % (objtype, inp, obj, typ, type(inp)))
        raise CommError()
    elif objtype == "object":
        if typ == "account":
            return obj.obj
        if typ == "string":
            return _ObjectDB.objects.get(db_key__iexact=obj)
        if typ == "dbref":
            return _ObjectDB.objects.get(id=obj)
        logger.log_err("%s %s %s %s %s" % (objtype, inp, obj, typ, type(inp)))
        raise CommError()
    elif objtype == "channel":
        if typ == "string":
            return _ChannelDB.objects.get(db_key__iexact=obj)
        if typ == "dbref":
            return _ChannelDB.objects.get(id=obj)
        logger.log_err("%s %s %s %s %s" % (objtype, inp, obj, typ, type(inp)))
        raise CommError()
    # an unknown
    return None


#
# Msg manager
#


class MsgManager(TypedObjectManager):
    """
    This MsgManager implements methods for searching and manipulating
    Messages directly from the database.

    These methods will all return database objects (or QuerySets)
    directly.

    A Message represents one unit of communication, be it over a
    Channel or via some form of in-game mail system. Like an e-mail,
    it always has a sender and can have any number of receivers (some
    of which may be Channels).

    """

    def identify_object(self, inp):
        """
        Wrapper to identify_object if accessing via the manager directly.

        Args:
            inp (any): Entity to be idtified.

        Returns:
            identified (tuple): This is a tuple with (`inp`, identifier)
                where `identifier` is one of "account", "object", "channel",
                "string", "dbref" or None.

        """
        return identify_object(inp)

    def get_message_by_id(self, idnum):
        """
        Retrieve message by its id.

        Args:
            idnum (int or str): The dbref to retrieve.

        Returns:
            message (Msg): The message.

        """
        try:
            return self.get(id=self.dbref(idnum, reqhash=False))
        except Exception:
            return None

    def get_messages_by_sender(self, sender, exclude_channel_messages=False):
        """
        Get all messages sent by one entity - this could be either a
        account or an object

        Args:
            sender (Account or Object): The sender of the message.
            exclude_channel_messages (bool, optional): Only return messages
                not aimed at a channel (that is, private tells for example)

        Returns:
            messages (list): List of matching messages

        Raises:
            CommError: For incorrect sender types.

        """
        obj, typ = identify_object(sender)
        if exclude_channel_messages:
            # explicitly exclude channel recipients
            if typ == "account":
                return list(
                    self.filter(db_sender_accounts=obj, db_receivers_channels__isnull=True).exclude(
                        db_hide_from_accounts=obj
                    )
                )
            elif typ == "object":
                return list(
                    self.filter(db_sender_objects=obj, db_receivers_channels__isnull=True).exclude(
                        db_hide_from_objects=obj
                    )
                )
            else:
                raise CommError
        else:
            # get everything, channel or not
            if typ == "account":
                return list(self.filter(db_sender_accounts=obj).exclude(db_hide_from_accounts=obj))
            elif typ == "object":
                return list(self.filter(db_sender_objects=obj).exclude(db_hide_from_objects=obj))
            else:
                raise CommError

    def get_messages_by_receiver(self, recipient):
        """
        Get all messages sent to one given recipient.

        Args:
            recipient (Object, Account or Channel): The recipient of the messages to search for.

        Returns:
            messages (list): Matching messages.

        Raises:
            CommError: If the `recipient` is not of a valid type.

        """
        obj, typ = identify_object(recipient)
        if typ == "account":
            return list(self.filter(db_receivers_accounts=obj).exclude(db_hide_from_accounts=obj))
        elif typ == "object":
            return list(self.filter(db_receivers_objects=obj).exclude(db_hide_from_objects=obj))
        elif typ == "channel":
            return list(self.filter(db_receivers_channels=obj).exclude(db_hide_from_channels=obj))
        else:
            raise CommError

    def get_messages_by_channel(self, channel):
        """
        Get all persistent messages sent to one channel.

        Args:
            channel (Channel): The channel to find messages for.

        Returns:
            messages (list): Persistent Msg objects saved for this channel.

        """
        return self.filter(db_receivers_channels=channel).exclude(db_hide_from_channels=channel)

    def search_message(self, sender=None, receiver=None, freetext=None, dbref=None):
        """
        Search the message database for particular messages. At least
        one of the arguments must be given to do a search.

        Args:
            sender (Object or Account, optional): Get messages sent by a particular account or object
            receiver (Object, Account or Channel, optional): Get messages
                received by a certain account,object or channel
            freetext (str): Search for a text string in a message.  NOTE:
                This can potentially be slow, so make sure to supply one of
                the other arguments to limit the search.
            dbref (int): The exact database id of the message. This will override
                    all other search criteria since it's unique and
                    always gives only one match.

        Returns:
            messages (list or Msg): A list of message matches or a single match if `dbref` was given.

        """
        # unique msg id
        if dbref:
            msg = self.objects.filter(id=dbref)
            if msg:
                return msg[0]

        # We use Q objects to gradually build up the query - this way we only
        # need to do one database lookup at the end rather than gradually
        # refining with multiple filter:s. Django Note: Q objects can be
        # combined with & and | (=AND,OR). ~ negates the queryset

        # filter by sender
        sender, styp = identify_object(sender)
        if styp == "account":
            sender_restrict = Q(db_sender_accounts=sender) & ~Q(db_hide_from_accounts=sender)
        elif styp == "object":
            sender_restrict = Q(db_sender_objects=sender) & ~Q(db_hide_from_objects=sender)
        else:
            sender_restrict = Q()
        # filter by receiver
        receiver, rtyp = identify_object(receiver)
        if rtyp == "account":
            receiver_restrict = Q(db_receivers_accounts=receiver) & ~Q(
                db_hide_from_accounts=receiver
            )
        elif rtyp == "object":
            receiver_restrict = Q(db_receivers_objects=receiver) & ~Q(db_hide_from_objects=receiver)
        elif rtyp == "channel":
            receiver_restrict = Q(db_receivers_channels=receiver) & ~Q(
                db_hide_from_channels=receiver
            )
        else:
            receiver_restrict = Q()
        # filter by full text
        if freetext:
            fulltext_restrict = Q(db_header__icontains=freetext) | Q(db_message__icontains=freetext)
        else:
            fulltext_restrict = Q()
        # execute the query
        return list(self.filter(sender_restrict & receiver_restrict & fulltext_restrict))

    # back-compatibility alias
    message_search = search_message


#
# Channel manager
#


class ChannelDBManager(TypedObjectManager):
    """
    This ChannelManager implements methods for searching and
    manipulating Channels directly from the database.

    These methods will all return database objects (or QuerySets)
    directly.

    A Channel is an in-game venue for communication. It's essentially
    representation of a re-sender: Users sends Messages to the
    Channel, and the Channel re-sends those messages to all users
    subscribed to the Channel.

    """

    def get_all_channels(self):
        """
        Get all channels.

        Returns:
            channels (list): All channels in game.

        """
        return self.all()

    def get_channel(self, channelkey):
        """
        Return the channel object if given its key.
        Also searches its aliases.

        Args:
            channelkey (str): Channel key to search for.

        Returns:
            channel (Channel or None): A channel match.

        """
        dbref = self.dbref(channelkey)
        if dbref:
            try:
                return self.get(id=dbref)
            except self.model.DoesNotExist:
                pass
        results = self.filter(
            Q(db_key__iexact=channelkey)
            | Q(db_tags__db_tagtype__iexact="alias", db_tags__db_key__iexact=channelkey)
        ).distinct()
        return results[0] if results else None

    def get_subscriptions(self, subscriber):
        """
        Return all channels a given entity is subscribed to.

        Args:
            subscriber (Object or Account): The one subscribing.

        Returns:
            subscriptions (list): Channel subscribed to.

        """
        clsname = subscriber.__dbclass__.__name__
        if clsname == "AccountDB":
            return subscriber.account_subscription_set.all()
        if clsname == "ObjectDB":
            return subscriber.object_subscription_set.all()
        return []

    def search_channel(self, ostring, exact=True):
        """
        Search the channel database for a particular channel.

        Args:
            ostring (str): The key or database id of the channel.
            exact (bool, optional): Require an exact (but not
                case sensitive) match.

        """
        dbref = self.dbref(ostring)
        if dbref:
            try:
                return self.get(id=dbref)
            except self.model.DoesNotExist:
                pass
        if exact:
            channels = self.filter(
                Q(db_key__iexact=ostring)
                | Q(db_tags__db_tagtype__iexact="alias", db_tags__db_key__iexact=ostring)
            ).distinct()
        else:
            channels = self.filter(
                Q(db_key__icontains=ostring)
                | Q(db_tags__db_tagtype__iexact="alias", db_tags__db_key__icontains=ostring)
            ).distinct()
        return channels

    # back-compatibility alias
    channel_search = search_channel


class ChannelManager(ChannelDBManager, TypeclassManager):
    """
    Wrapper to group the typeclass manager to a consistent name.
    """

    pass
