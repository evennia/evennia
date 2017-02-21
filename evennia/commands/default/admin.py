"""

Admin commands

"""

import time
import re
from django.conf import settings
from evennia.server.sessionhandler import SESSIONS
from evennia.server.models import ServerConfig
from evennia.utils import evtable, search, class_from_module

COMMAND_DEFAULT_CLASS = class_from_module(settings.COMMAND_DEFAULT_CLASS)

PERMISSION_HIERARCHY = [p.lower() for p in settings.PERMISSION_HIERARCHY]

# limit members for API inclusion
__all__ = ("CmdBoot", "CmdBan", "CmdUnban", "CmdDelPlayer",
           "CmdEmit", "CmdNewPassword", "CmdPerm", "CmdWall")


class CmdBoot(COMMAND_DEFAULT_CLASS):
    """
    kick a player from the server.

    Usage
      @boot[/switches] <player obj> [: reason]

    Switches:
      quiet - Silently boot without informing player
      sid - boot by session id instead of name or dbref

    Boot a player object from the server. If a reason is
    supplied it will be echoed to the user unless /quiet is set.
    """

    key = "@boot"
    locks = "cmd:perm(boot) or perm(Wizards)"
    help_category = "Admin"

    def func(self):
        """Implementing the function"""
        caller = self.caller
        args = self.args

        if not args:
            caller.msg("Usage: @boot[/switches] <player> [:reason]")
            return

        if ':' in args:
            args, reason = [a.strip() for a in args.split(':', 1)]
        else:
            args, reason = args, ""

        boot_list = []

        if 'sid' in self.switches:
            # Boot a particular session id.
            sessions = SESSIONS.get_sessions(True)
            for sess in sessions:
                # Find the session with the matching session id.
                if sess.sessid == int(args):
                    boot_list.append(sess)
                    break
        else:
            # Boot by player object
            pobj = search.player_search(args)
            if not pobj:
                caller.msg("Player %s was not found." % args)
                return
            pobj = pobj[0]
            if not pobj.access(caller, 'boot'):
                string = "You don't have the permission to boot %s." % (pobj.key, )
                caller.msg(string)
                return
            # we have a bootable object with a connected user
            matches = SESSIONS.sessions_from_player(pobj)
            for match in matches:
                boot_list.append(match)

        if not boot_list:
            caller.msg("No matching sessions found. The Player does not seem to be online.")
            return

        # Carry out the booting of the sessions in the boot list.

        feedback = None
        if 'quiet' not in self.switches:
            feedback = "You have been disconnected by %s.\n" % caller.name
            if reason:
                feedback += "\nReason given: %s" % reason

        for session in boot_list:
            session.msg(feedback)
            session.player.disconnect_session_from_player(session)


# regex matching IP addresses with wildcards, eg. 233.122.4.*
IPREGEX = re.compile(r"[0-9*]{1,3}\.[0-9*]{1,3}\.[0-9*]{1,3}\.[0-9*]{1,3}")


def list_bans(banlist):
    """
    Helper function to display a list of active bans. Input argument
    is the banlist read into the two commands @ban and @unban below.
    """
    if not banlist:
        return "No active bans were found."

    table = evtable.EvTable("|wid", "|wname/ip", "|wdate", "|wreason")
    for inum, ban in enumerate(banlist):
        table.add_row(str(inum + 1),
                      ban[0] and ban[0] or ban[1],
                      ban[3], ban[4])
    return "|wActive bans:|n\n%s" % table


class CmdBan(COMMAND_DEFAULT_CLASS):
    """
    ban a player from the server

    Usage:
      @ban [<name or ip> [: reason]]

    Without any arguments, shows numbered list of active bans.

    This command bans a user from accessing the game. Supply an optional
    reason to be able to later remember why the ban was put in place.

    It is often preferable to ban a player from the server than to
    delete a player with @delplayer. If banned by name, that player
    account can no longer be logged into.

    IP (Internet Protocol) address banning allows blocking all access
    from a specific address or subnet. Use an asterisk (*) as a
    wildcard.

    Examples:
      @ban thomas             - ban account 'thomas'
      @ban/ip 134.233.2.111   - ban specific ip address
      @ban/ip 134.233.2.*     - ban all in a subnet
      @ban/ip 134.233.*.*     - even wider ban

    A single IP filter can be easy to circumvent by changing computers
    or requesting a new IP address. Setting a wide IP block filter with
    wildcards might be tempting, but remember that it may also
    accidentally block innocent users connecting from the same country
    or region.

    """
    key = "@ban"
    aliases = ["@bans"]
    locks = "cmd:perm(ban) or perm(Immortals)"
    help_category = "Admin"

    def func(self):
        """
        Bans are stored in a serverconf db object as a list of
        dictionaries:
          [ (name, ip, ipregex, date, reason),
            (name, ip, ipregex, date, reason),...  ]
        where name and ip are set by the user and are shown in
        lists. ipregex is a converted form of ip where the * is
        replaced by an appropriate regex pattern for fast
        matching. date is the time stamp the ban was instigated and
        'reason' is any optional info given to the command. Unset
        values in each tuple is set to the empty string.
        """
        banlist = ServerConfig.objects.conf('server_bans')
        if not banlist:
            banlist = []

        if not self.args or (self.switches
                             and not any(switch in ('ip', 'name')
                                         for switch in self.switches)):
            self.caller.msg(list_bans(banlist))
            return

        now = time.ctime()
        reason = ""
        if ':' in self.args:
            ban, reason = self.args.rsplit(':', 1)
        else:
            ban = self.args
        ban = ban.lower()
        ipban = IPREGEX.findall(ban)
        if not ipban:
            # store as name
            typ = "Name"
            bantup = (ban, "", "", now, reason)
        else:
            # an ip address.
            typ = "IP"
            ban = ipban[0]
            # replace * with regex form and compile it
            ipregex = ban.replace('.', '\.')
            ipregex = ipregex.replace('*', '[0-9]{1,3}')
            ipregex = re.compile(r"%s" % ipregex)
            bantup = ("", ban, ipregex, now, reason)
        # save updated banlist
        banlist.append(bantup)
        ServerConfig.objects.conf('server_bans', banlist)
        self.caller.msg("%s-Ban |w%s|n was added." % (typ, ban))


class CmdUnban(COMMAND_DEFAULT_CLASS):
    """
    remove a ban from a player

    Usage:
      @unban <banid>

    This will clear a player name/ip ban previously set with the @ban
    command.  Use this command without an argument to view a numbered
    list of bans. Use the numbers in this list to select which one to
    unban.

    """
    key = "@unban"
    locks = "cmd:perm(unban) or perm(Immortals)"
    help_category = "Admin"

    def func(self):
        """Implement unbanning"""

        banlist = ServerConfig.objects.conf('server_bans')

        if not self.args:
            self.caller.msg(list_bans(banlist))
            return

        try:
            num = int(self.args)
        except Exception:
            self.caller.msg("You must supply a valid ban id to clear.")
            return

        if not banlist:
            self.caller.msg("There are no bans to clear.")
        elif not (0 < num < len(banlist) + 1):
            self.caller.msg("Ban id |w%s|x was not found." % self.args)
        else:
            # all is ok, clear ban
            ban = banlist[num - 1]
            del banlist[num - 1]
            ServerConfig.objects.conf('server_bans', banlist)
            self.caller.msg("Cleared ban %s: %s" %
                            (num, " ".join([s for s in ban[:2]])))


class CmdDelPlayer(COMMAND_DEFAULT_CLASS):
    """
    delete a player from the server

    Usage:
      @delplayer[/switch] <name> [: reason]

    Switch:
      delobj - also delete the player's currently
               assigned in-game object.

    Completely deletes a user from the server database,
    making their nick and e-mail again available.
    """

    key = "@delplayer"
    locks = "cmd:perm(delplayer) or perm(Immortals)"
    help_category = "Admin"

    def func(self):
        """Implements the command."""

        caller = self.caller
        args = self.args

        if hasattr(caller, 'player'):
            caller = caller.player

        if not args:
            self.msg("Usage: @delplayer <player/user name or #id> [: reason]")
            return

        reason = ""
        if ':' in args:
            args, reason = [arg.strip() for arg in args.split(':', 1)]

        # We use player_search since we want to be sure to find also players
        # that lack characters.
        players = search.player_search(args)

        if not players:
            self.msg('Could not find a player by that name.')
            return

        if len(players) > 1:
            string = "There were multiple matches:\n"
            string += "\n".join(" %s %s" % (player.id, player.key) for player in players)
            self.msg(string)
            return

        # one single match

        player = players.pop()

        if not player.access(caller, 'delete'):
            string = "You don't have the permissions to delete that player."
            self.msg(string)
            return

        uname = player.username
        # boot the player then delete
        self.msg("Informing and disconnecting player ...")
        string = "\nYour account '%s' is being *permanently* deleted.\n" % uname
        if reason:
            string += " Reason given:\n  '%s'" % reason
        player.msg(string)
        player.delete()
        self.msg("Player %s was successfully deleted." % uname)


class CmdEmit(COMMAND_DEFAULT_CLASS):
    """
    admin command for emitting message to multiple objects

    Usage:
      @emit[/switches] [<obj>, <obj>, ... =] <message>
      @remit           [<obj>, <obj>, ... =] <message>
      @pemit           [<obj>, <obj>, ... =] <message>

    Switches:
      room : limit emits to rooms only (default)
      players : limit emits to players only
      contents : send to the contents of matched objects too

    Emits a message to the selected objects or to
    your immediate surroundings. If the object is a room,
    send to its contents. @remit and @pemit are just
    limited forms of @emit, for sending to rooms and
    to players respectively.
    """
    key = "@emit"
    aliases = ["@pemit", "@remit"]
    locks = "cmd:perm(emit) or perm(Builders)"
    help_category = "Admin"

    def func(self):
        """Implement the command"""

        caller = self.caller
        args = self.args

        if not args:
            string = "Usage: "
            string += "\n@emit[/switches] [<obj>, <obj>, ... =] <message>"
            string += "\n@remit           [<obj>, <obj>, ... =] <message>"
            string += "\n@pemit           [<obj>, <obj>, ... =] <message>"
            caller.msg(string)
            return

        rooms_only = 'rooms' in self.switches
        players_only = 'players' in self.switches
        send_to_contents = 'contents' in self.switches

        # we check which command was used to force the switches
        if self.cmdstring == '@remit':
            rooms_only = True
            send_to_contents = True
        elif self.cmdstring == '@pemit':
            players_only = True

        if not self.rhs:
            message = self.args
            objnames = [caller.location.key]
        else:
            message = self.rhs
            objnames = self.lhslist

        # send to all objects
        for objname in objnames:
            obj = caller.search(objname, global_search=True)
            if not obj:
                return
            if rooms_only and obj.location is not None:
                caller.msg("%s is not a room. Ignored." % objname)
                continue
            if players_only and not obj.has_player:
                caller.msg("%s has no active player. Ignored." % objname)
                continue
            if obj.access(caller, 'tell'):
                obj.msg(message)
                if send_to_contents and hasattr(obj, "msg_contents"):
                    obj.msg_contents(message)
                    caller.msg("Emitted to %s and contents:\n%s" % (objname, message))
                else:
                    caller.msg("Emitted to %s:\n%s" % (objname, message))
            else:
                caller.msg("You are not allowed to emit to %s." % objname)


class CmdNewPassword(COMMAND_DEFAULT_CLASS):
    """
    change the password of a player

    Usage:
      @userpassword <user obj> = <new password>

    Set a player's password.
    """

    key = "@userpassword"
    locks = "cmd:perm(newpassword) or perm(Wizards)"
    help_category = "Admin"

    def func(self):
        """Implement the function."""

        caller = self.caller

        if not self.rhs:
            self.msg("Usage: @userpassword <user obj> = <new password>")
            return

        # the player search also matches 'me' etc.
        player = caller.search_player(self.lhs)
        if not player:
            return
        player.set_password(self.rhs)
        player.save()
        self.msg("%s - new password set to '%s'." % (player.name, self.rhs))
        if player.character != caller:
            player.msg("%s has changed your password to '%s'." % (caller.name,
                                                                  self.rhs))


class CmdPerm(COMMAND_DEFAULT_CLASS):
    """
    set the permissions of a player/object

    Usage:
      @perm[/switch] <object> [= <permission>[,<permission>,...]]
      @perm[/switch] *<player> [= <permission>[,<permission>,...]]

    Switches:
      del : delete the given permission from <object> or <player>.
      player : set permission on a player (same as adding * to name)

    This command sets/clears individual permission strings on an object
    or player. If no permission is given, list all permissions on <object>.
    """
    key = "@perm"
    aliases = "@setperm"
    locks = "cmd:perm(perm) or perm(Immortals)"
    help_category = "Admin"

    def func(self):
        """Implement function"""

        caller = self.caller
        switches = self.switches
        lhs, rhs = self.lhs, self.rhs

        if not self.args:
            string = "Usage: @perm[/switch] object [ = permission, permission, ...]"
            caller.msg(string)
            return

        playermode = 'player' in self.switches or lhs.startswith('*')
        lhs = lhs.lstrip("*")

        if playermode:
            obj = caller.search_player(lhs)
        else:
            obj = caller.search(lhs, global_search=True)
        if not obj:
            return

        if not rhs:
            if not obj.access(caller, 'examine'):
                caller.msg("You are not allowed to examine this object.")
                return

            string = "Permissions on |w%s|n: " % obj.key
            if not obj.permissions.all():
                string += "<None>"
            else:
                string += ", ".join(obj.permissions.all())
                if (hasattr(obj, 'player') and
                    hasattr(obj.player, 'is_superuser') and
                        obj.player.is_superuser):
                    string += "\n(... but this object is currently controlled by a SUPERUSER! "
                    string += "All access checks are passed automatically.)"
            caller.msg(string)
            return

        # we supplied an argument on the form obj = perm
        locktype = "edit" if playermode else "control"
        if not obj.access(caller, locktype):
            caller.msg("You are not allowed to edit this %s's permissions."
                       % ("player" if playermode else "object"))
            return

        caller_result = []
        target_result = []
        if 'del' in switches:
            # delete the given permission(s) from object.
            for perm in self.rhslist:
                obj.permissions.remove(perm)
                if obj.permissions.get(perm):
                    caller_result.append("\nPermissions %s could not be removed from %s." % (perm, obj.name))
                else:
                    caller_result.append("\nPermission %s removed from %s (if they existed)." % (perm, obj.name))
                    target_result.append("\n%s revokes the permission(s) %s from you." % (caller.name, perm))
        else:
            # add a new permission
            permissions = obj.permissions.all()

            for perm in self.rhslist:

                # don't allow to set a permission higher in the hierarchy than
                # the one the caller has (to prevent self-escalation)
                if (perm.lower() in PERMISSION_HIERARCHY and not
                        obj.locks.check_lockstring(caller, "dummy:perm(%s)" % perm)):
                    caller.msg("You cannot assign a permission higher than the one you have yourself.")
                    return

                if perm in permissions:
                    caller_result.append("\nPermission '%s' is already defined on %s." % (rhs, obj.name))
                else:
                    obj.permissions.add(perm)
                    plystring = "the Player" if playermode else "the Object/Character"
                    caller_result.append("\nPermission '%s' given to %s (%s)." % (rhs, obj.name, plystring))
                    target_result.append("\n%s gives you (%s, %s) the permission '%s'."
                                         % (caller.name, obj.name, plystring, rhs))
        caller.msg("".join(caller_result).strip())
        if target_result:
            obj.msg("".join(target_result).strip())


class CmdWall(COMMAND_DEFAULT_CLASS):
    """
    make an announcement to all

    Usage:
      @wall <message>

    Announces a message to all connected players.
    """
    key = "@wall"
    locks = "cmd:perm(wall) or perm(Wizards)"
    help_category = "Admin"

    def func(self):
        """Implements command"""
        if not self.args:
            self.caller.msg("Usage: @wall <message>")
            return
        message = "%s shouts \"%s\"" % (self.caller.name, self.args)
        self.msg("Announcing to all connected players ...")
        SESSIONS.announce_all(message)
