"""
Channel

The channel class represents the out-of-character chat-room usable by
Accounts in-game. It is mostly overloaded to change its appearance, but
channels can be used to implement many different forms of message
distribution systems.

Note that sending data to channels are handled via the CMD_CHANNEL
syscommand (see evennia.syscmds). The sending should normally not need
to be modified.

"""

from evennia.comms.comms import DefaultChannel


class Channel(DefaultChannel):
    r"""
    This is the base class for all Channel Comms. Inherit from this to
    create different types of communication channels.

    Class-level variables:
    - `send_to_online_only` (bool, default True) - if set, will only try to
      send to subscribers that are actually active. This is a useful optimization.
    - `log_file` (str, default `"channel_{channelname}.log"`). This is the
      log file to which the channel history will be saved. The `{channelname}` tag
      will be replaced by the key of the Channel. If an Attribute 'log_file'
      is set, this will be used instead. If this is None and no Attribute is found,
      no history will be saved.
    - `channel_prefix_string` (str, default `"[{channelname} ]"`) - this is used
      as a simple template to get the channel prefix with `.channel_prefix()`. It is used
      in front of every channel message; use `{channelmessage}` token to insert the
      name of the current channel. Set to `None` if you want no prefix (or want to
      handle it in a hook during message generation instead.
    - `channel_msg_nick_pattern`(str, default `"{alias}\s*?|{alias}\s+?(?P<arg1>.+?)") -
      this is what used when a channel subscriber gets a channel nick assigned to this
      channel. The nickhandler uses the pattern to pick out this channel's name from user
      input. The `{alias}` token will get both the channel's key and any set/custom aliases
      per subscriber. You need to allow for an `<arg1>` regex group to catch any message
      that should be send to the  channel. You usually don't need to change this pattern
      unless you are changing channel command-style entirely.
    - `channel_msg_nick_replacement` (str, default `"channel {channelname} = $1"` - this
      is used by the nickhandler to generate a replacement string once the nickhandler (using
      the `channel_msg_nick_pattern`) identifies that the channel should be addressed
      to send a message to it. The `<arg1>` regex pattern match from `channel_msg_nick_pattern`
      will end up at the `$1` position in the replacement. Together, this allows you do e.g.
      'public Hello' and have that become a mapping to `channel public = Hello`. By default,
      the account-level `channel` command is used. If you were to rename that command you must
      tweak the output to something like `yourchannelcommandname {channelname} = $1`.

    * Properties:
        mutelist
        banlist
        wholist

    * Working methods:
        get_log_filename()
        set_log_filename(filename)
        has_connection(account) - check if the given account listens to this channel
        connect(account) - connect account to this channel
        disconnect(account) - disconnect account from channel
        access(access_obj, access_type='listen', default=False) - check the
                    access on this channel (default access_type is listen)
        create(key, creator=None, *args, **kwargs)
        delete() - delete this channel
        message_transform(msg, emit=False, prefix=True,
                          sender_strings=None, external=False) - called by
                          the comm system and triggers the hooks below
        msg(msgobj, header=None, senders=None, sender_strings=None,
            persistent=None, online=False, emit=False, external=False) - main
                send method, builds and sends a new message to channel.
        tempmsg(msg, header=None, senders=None) - wrapper for sending non-persistent
                messages.
        distribute_message(msg, online=False) - send a message to all
                connected accounts on channel, optionally sending only
                to accounts that are currently online (optimized for very large sends)
        mute(subscriber, **kwargs)
        unmute(subscriber, **kwargs)
        ban(target, **kwargs)
        unban(target, **kwargs)
        add_user_channel_alias(user, alias, **kwargs)
        remove_user_channel_alias(user, alias, **kwargs)


    Useful hooks:
        at_channel_creation() - called once, when the channel is created
        basetype_setup()
        at_init()
        at_first_save()
        channel_prefix() - how the channel should be
                  prefixed when returning to user. Returns a string
        format_senders(senders) - should return how to display multiple
                senders to a channel
        pose_transform(msg, sender_string) - should detect if the
                sender is posing, and if so, modify the string
        format_external(msg, senders, emit=False) - format messages sent
                from outside the game, like from IRC
        format_message(msg, emit=False) - format the message body before
                displaying it to the user. 'emit' generally means that the
                message should not be displayed with the sender's name.
        channel_prefix()

        pre_join_channel(joiner) - if returning False, abort join
        post_join_channel(joiner) - called right after successful join
        pre_leave_channel(leaver) - if returning False, abort leave
        post_leave_channel(leaver) - called right after successful leave
        at_pre_msg(message, **kwargs)
        at_post_msg(message, **kwargs)
        web_get_admin_url()
        web_get_create_url()
        web_get_detail_url()
        web_get_update_url()
        web_get_delete_url()

    """

    pass
