"""
Legacy Comms-commands

Griatch 2021

In Evennia 1.0, the old Channel commands (originally inspired by MUX) were
replaced by the single `channel` command that performs all these function.
That command is still required to talk on channels. This contrib (extracted
from Evennia 0.9.5) reuses the channel-management of the base Channel command
but breaks out its functionality into separate Commands with MUX-familiar names.

- `allcom` - `channel/all` and `channel`
- `addcom` - `channel/alias`, `channel/sub` and `channel/unmute`
- `delcom` - `channel/unalias`, `alias/unsub` and `channel/mute`
- `cboot` - `channel/boot` (`channel/ban` and `/unban` not supported)
- `cwho` - `channel/who`
- `ccreate` - `channel/create`
- `cdestroy` - `channel/destroy`
- `clock` - `channel/lock`
- `cdesc` - `channel/desc`

Installation:

- Import the `CmdSetLegacyComms` cmdset from this module into `mygame/commands/default_cmdsets.py`
- Add it to the CharacterCmdSet's `at_cmdset_creation` method.
- Reload the server.

Example:

```python
# in mygame/commands/default_cmdsets.py

# ..
from evennia.contrib.base_systems.mux_comms_cmds import CmdSetLegacyComms   # <----

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # ...
    def at_cmdset_creation(self):
        # ...
        self.add(CmdSetLegacyComms)   # <----
```

"""
from django.conf import settings

from evennia.commands.cmdset import CmdSet
from evennia.commands.default.comms import CmdChannel
from evennia.utils import logger

CHANNEL_DEFAULT_TYPECLASS = settings.BASE_CHANNEL_TYPECLASS


class CmdAddCom(CmdChannel):
    """
    Add a channel alias and/or subscribe to a channel

    Usage:
       addcom [alias=] <channel>

    Joins a given channel. If alias is given, this will allow you to
    refer to the channel by this alias rather than the full channel
    name. Subsequent calls of this command can be used to add multiple
    aliases to an already joined channel.
    """

    key = "addcom"
    aliases = ["aliaschan", "chanalias"]
    help_category = "Comms"
    locks = "cmd:not pperm(channel_banned)"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    account_caller = True

    def func(self):
        """Implement the command"""

        caller = self.caller
        args = self.args

        if not args:
            self.msg("Usage: addcom [alias =] channelname.")
            return

        if self.rhs:
            # rhs holds the channelname
            channelname = self.rhs
            alias = self.lhs
        else:
            channelname = self.args
            alias = None

        channel = self.search_channel(channelname)
        if not channel:
            return

        string = ""
        if not channel.has_connection(caller):
            # we want to connect as well.
            success, err = self.sub_to_channel(channel)
            if success:
                # if this would have returned True, the account is connected
                self.msg(f"You now listen to the channel {channel.key}")
            else:
                self.msg(f"{channel.key}: You are not allowed to join this channel.")
                return

        if channel.unmute(caller):
            self.msg(f"You unmute channel {channel.key}.")
        else:
            self.msg(f"You are already connected to channel {channel.key}.")

        if alias:
            # create a nick and add it to the caller.
            self.add_alias(channel, alias)
            self.msg(f" You can now refer to the channel {channel} with the alias '{alias}'.")
        else:
            string += " No alias added."
            self.msg(string)


class CmdDelCom(CmdChannel):
    """
    remove a channel alias and/or unsubscribe from channel

    Usage:
       delcom <alias or channel>
       delcom/all <channel>

    If the full channel name is given, unsubscribe from the
    channel. If an alias is given, remove the alias but don't
    unsubscribe. If the 'all' switch is used, remove all aliases
    for that channel.
    """

    key = "delcom"
    aliases = ["delaliaschan", "delchanalias"]
    help_category = "Comms"
    locks = "cmd:not perm(channel_banned)"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    account_caller = True

    def func(self):
        """Implementing the command."""

        caller = self.caller

        if not self.args:
            self.msg("Usage: delcom <alias or channel>")
            return
        ostring = self.args.lower().strip()

        channel = self.search_channel(ostring)
        if not channel:
            return

        if not channel.has_connection(caller):
            self.msg("You are not listening to that channel.")
            return

        if ostring == channel.key.lower():
            # an exact channel name - unsubscribe
            delnicks = "all" in self.switches
            # find all nicks linked to this channel and delete them
            if delnicks:
                aliases = self.get_channel_aliases(channel)
                for alias in aliases:
                    self.remove_alias(alias)
            success, err = self.unsub_from_channel(channel)
            if success:
                wipednicks = " Eventual aliases were removed." if delnicks else ""
                self.msg(f"You stop listening to channel '{channel.key}'.{wipednicks}")
            else:
                self.msg(err)
            return
        else:
            # we are removing a channel nick
            self.remove_alias(ostring)
            self.msg(f"Any alias '{ostring}' for channel {channel.key} was cleared.")


class CmdAllCom(CmdChannel):
    """
    perform admin operations on all channels

    Usage:
      allcom [on | off | who | destroy]

    Allows the user to universally turn off or on all channels they are on, as
    well as perform a 'who' for all channels they are on. Destroy deletes all
    channels that you control.

    Without argument, works like comlist.
    """

    key = "allcom"
    aliases = []  # important to not inherit parent's aliases
    locks = "cmd: not pperm(channel_banned)"
    help_category = "Comms"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    account_caller = True

    def func(self):
        """Runs the function"""

        caller = self.caller
        args = self.args
        if not args:
            subscribed, available = self.list_channels()
            self.msg("\n|wAvailable channels:\n{table}")
            return
            return

        if args == "on":
            # get names of all channels available to listen to
            # and activate them all
            channels = [
                chan
                for chan in CHANNEL_DEFAULT_TYPECLASS.objects.get_all_channels()
                if chan.access(caller, "listen")
            ]
            for channel in channels:
                self.execute_cmd("addcom %s" % channel.key)
        elif args == "off":
            # get names all subscribed channels and disconnect from them all
            channels = CHANNEL_DEFAULT_TYPECLASS.objects.get_subscriptions(caller)
            for channel in channels:
                self.execute_cmd("delcom %s" % channel.key)
        elif args == "destroy":
            # destroy all channels you control
            channels = [
                chan
                for chan in CHANNEL_DEFAULT_TYPECLASS.objects.get_all_channels()
                if chan.access(caller, "control")
            ]
            for channel in channels:
                self.execute_cmd("cdestroy %s" % channel.key)
        elif args == "who":
            # run a who, listing the subscribers on visible channels.
            string = "\n|CChannel subscriptions|n"
            channels = [
                chan
                for chan in CHANNEL_DEFAULT_TYPECLASS.objects.get_all_channels()
                if chan.access(caller, "listen")
            ]
            if not channels:
                string += "No channels."
            for channel in channels:
                string += "\n|w%s:|n\n %s" % (channel.key, channel.wholist)
            self.msg(string.strip())
        else:
            # wrong input
            self.msg("Usage: allcom on | off | who | clear")


class CmdCdestroy(CmdChannel):
    """
    destroy a channel you created

    Usage:
      cdestroy <channel>

    Destroys a channel that you control.
    """

    key = "cdestroy"
    aliases = []
    help_category = "Comms"
    locks = "cmd: not pperm(channel_banned)"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    account_caller = True

    def func(self):
        """Destroy objects cleanly."""

        caller = self.caller

        if not self.args:
            self.msg("Usage: cdestroy <channelname>")
            return

        channel = self.search_channel(self.args)

        if not channel:
            self.msg("Could not find channel %s." % self.args)
            return
        if not channel.access(caller, "control"):
            self.msg("You are not allowed to do that.")
            return
        channel_key = channel.key
        message = f"{channel.key} is being destroyed. Make sure to change your aliases."
        self.destroy_channel(channel, message)
        self.msg("Channel '%s' was destroyed." % channel_key)
        logger.log_sec(
            "Channel Deleted: %s (Caller: %s, IP: %s)."
            % (channel_key, caller, self.session.address)
        )


class CmdCBoot(CmdChannel):
    """
    kick an account from a channel you control

    Usage:
       cboot[/quiet] <channel> = <account> [:reason]

    Switch:
       quiet - don't notify the channel

    Kicks an account or object from a channel you control.

    """

    key = "cboot"
    aliases = []
    switch_options = ("quiet",)
    locks = "cmd: not pperm(channel_banned)"
    help_category = "Comms"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    account_caller = True

    def func(self):
        """implement the function"""

        if not self.args or not self.rhs:
            string = "Usage: cboot[/quiet] <channel> = <account> [:reason]"
            self.msg(string)
            return

        channel = self.search_channel(self.lhs)
        if not channel:
            return

        reason = ""
        if ":" in self.rhs:
            target, reason = self.rhs.rsplit(":", 1)
            is_account = target.strip().startswith("*")
            searchstring = target.lstrip("*")
        else:
            is_account = target.strip().startswith("*")
            searchstring = self.rhs.lstrip("*")

        target = self.caller.search(searchstring, account=is_account)
        if not target:
            return
        if reason:
            reason = " (reason: %s)" % reason
        if not channel.access(self.caller, "control"):
            string = "You don't control this channel."
            self.msg(string)
            return

        success, err = self.boot_user(target, quiet="quiet" in self.switches)
        if success:
            self.msg(f"Booted {target.key} from {channel.key}")
            logger.log_sec(
                "Channel Boot: %s (Channel: %s, Reason: %s, Caller: %s, IP: %s)."
                % (self.caller, channel, reason, self.caller, self.session.address)
            )
        else:
            self.msg(err)


class CmdCWho(CmdChannel):
    """
    show who is listening to a channel

    Usage:
      cwho <channel>

    List who is connected to a given channel you have access to.
    """

    key = "cwho"
    aliases = []
    locks = "cmd: not pperm(channel_banned)"
    help_category = "Comms"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    account_caller = True

    def func(self):
        """implement function"""

        if not self.args:
            string = "Usage: cwho <channel>"
            self.msg(string)
            return

        channel = self.search_channel(self.lhs)
        if not channel:
            return
        if not channel.access(self.caller, "listen"):
            string = "You can't access this channel."
            self.msg(string)
            return
        string = "\n|CChannel subscriptions|n"
        string += "\n|w%s:|n\n  %s" % (channel.key, channel.wholist)
        self.msg(string.strip())


class CmdChannelCreate(CmdChannel):
    """
    create a new channel

    Usage:
     ccreate <new channel>[;alias;alias...] = description

    Creates a new channel owned by you.
    """

    key = "ccreate"
    aliases = "channelcreate"
    locks = "cmd:not pperm(channel_banned) and pperm(Player)"
    help_category = "Comms"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    account_caller = True

    def func(self):
        """Implement the command"""

        if not self.args:
            self.msg("Usage ccreate <channelname>[;alias;alias..] = description")
            return

        description = ""

        if self.rhs:
            description = self.rhs
        lhs = self.lhs
        channame = lhs
        aliases = None
        if ";" in lhs:
            channame, aliases = lhs.split(";", 1)
            aliases = [alias.strip().lower() for alias in aliases.split(";")]

        new_chan, err = self.create_channel(channame, description, aliases=aliases)
        if new_chan:
            self.msg(f"Created channel {new_chan.key} and connected to it.")
        else:
            self.msg(err)


class CmdClock(CmdChannel):
    """
    change channel locks of a channel you control

    Usage:
      clock <channel> [= <lockstring>]

    Changes the lock access restrictions of a channel. If no
    lockstring was given, view the current lock definitions.
    """

    key = "clock"
    aliases = ["clock"]
    locks = "cmd:not pperm(channel_banned) and perm(Admin)"
    help_category = "Comms"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    account_caller = True

    def func(self):
        """run the function"""

        if not self.args:
            string = "Usage: clock channel [= lockstring]"
            self.msg(string)
            return

        channel = self.search_channel(self.lhs)
        if not channel:
            return

        if not self.rhs:
            # no =, so just view the current locks
            self.msg(f"Current locks on {channel.key}\n{channel.locks}")
            return
        # we want to add/change a lock.
        if not channel.access(self.caller, "control"):
            string = "You don't control this channel."
            self.msg(string)
            return
        # Try to add the lock
        success, err = self.set_lock(channel, self.rhs)
        if success:
            self.msg(f"Lock(s) applied. Current locks on {channel.key}:\n{channel.locks}")
        else:
            self.msg(err)


class CmdCdesc(CmdChannel):
    """
    describe a channel you control

    Usage:
      cdesc <channel> = <description>

    Changes the description of the channel as shown in
    channel lists.

    """

    key = "cdesc"
    aliases = []
    locks = "cmd:not pperm(channel_banned)"
    help_category = "Comms"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    account_caller = True

    def func(self):
        """Implement command"""

        caller = self.caller

        if not self.rhs:
            self.msg("Usage: cdesc <channel> = <description>")
            return
        channel = self.search_channel(self.lhs)
        if not channel:
            return
        # check permissions
        if not channel.access(caller, "control"):
            self.msg("You cannot admin this channel.")
            return
        self.set_desc(channel, self.rhs)
        self.msg(f"Description of channel '{channel.key}' set to '{self.rhs}'.")


class CmdSetLegacyComms(CmdSet):
    def at_cmdset_createion(self):
        self.add(CmdAddCom())
        self.add(CmdAllCom())
        self.add(CmdDelCom())
        self.add(CmdCdestroy())
        self.add(CmdCBoot())
        self.add(CmdCWho())
        self.add(CmdChannelCreate())
        self.add(CmdClock())
        self.add(CmdCdesc())
