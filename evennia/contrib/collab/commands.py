import evennia

from django.conf import settings
from evennia.commands.default.general import CmdGet, CmdDrop

from evennia.contrib.collab.perms import (
    quota_check, collab_check, PermissionsError, 
    is_owner, set_owner, attr_check, get_owner, prefix_check, get_handler)
from evennia.commands.cmdhandler import get_and_merge_cmdsets
from evennia.commands.default.muxcommand import MuxCommand
from evennia.commands.default.building import (
    CmdSetObjAlias, CmdListCmdSets, CmdName, CmdLock, CmdSetAttribute, CmdCpAttr, CmdMvAttr, CmdCopy
)
from evennia.contrib.collab.template.core import evtemplate
from evennia.utils import utils, lazy_property
from evennia.utils.ansi import ANSIString as A
from evennia.utils.eveditor import EvEditor
from evennia.utils.utils import inherits_from


# Reminder of some of the things in the default Build commands. Removing ones
# that don't matter or we've already implemented as we go.
# __all__ = (
#           "CmdTunnel",
#           "CmdTypeclass", "CmdWipe",
#           "CmdFind", "CmdTeleport",
#           "CmdScript", "CmdTag", "CmdSpawn")


def pre_collab(command, syntax_err, perm_err, locks=None, call_super=True, extra_check=None):
    """
    Used for commands that affect an object. Can optionally call the super if
    this is the only difference that needs to be handled.

    If extra_check is provided, will run that as a final check on the object before
    the super is called (if it is to be called)
    """
    if not command.lhs:
        command.msg("|r%s|n" % syntax_err)
        return False
    obj = command.caller.search(command.lhs)
    if not obj:
        return False
    if not collab_check(command.caller, obj, locks=locks):
        command.msg("|r%s|n" % perm_err)
        return False
    if extra_check:
        if not extra_check(obj):
            return False
    if call_super:
        super(command.__class__, command).func()
    return True


class BaseCreationCommand(MuxCommand):
    """
    Creates objects of different typeclasses as specified in the settings.
    """
    locks = "cmd:perm(create) or perm(Builder)"
    help_category = "Building"
    not_permitted = []

    def pre_load(self):
        """
        Used for typeclass-frontloaded commands like @dig.
        """

    def get_location(self):
        """
        Used to determine what object will be placed in the object's
        destination field upon creation.
        """
        if not self.caller.location:
            if hasattr(self.caller, 'account'):
                return self.caller
            else:
                raise ValueError(
                    "|rYou aren't anywhere. Where would you put it?|n")
        return self.caller.location

    def get_home(self):
        """
        Return the home for the new object.
        """
        return self.get_location()

    def get_destination(self):
        """
        Return the destination for the new object.
        """
        if not self.rhs:
            return None
        destination = self.caller.search(self.rhs)
        if not destination:
            raise ValueError
        return destination

    def get_key_and_aliases(self):
        """
        Return both the name for the object and any aliases it should have.
        """
        if not self.lhs:
            raise ValueError("|rYou must specify a name.|n")
        aliases = [A(name.strip()).clean() for name in self.lhs.split(';')]
        key = aliases.pop(0)
        return key, aliases

    def func(self):
        self.pre_load()
        try:
            self.create_type = self.switches[0]
        except IndexError:
            self.create_type = settings.COLLAB_DEFAULT_TYPE

        # This should only matter if pre_load is not used.
        if self.create_type in self.not_permitted:
            self.msg("|rType '%s' cannot be created with this"
                            " command.|n" % self.create_type)
            return
        lock = self.caller.locks.check_lockstring(
            self.caller,
            settings.COLLAB_TYPES[self.create_type]['create_lock'])
        if not lock:
            self.msg("|rYou don't have permission to create "
                            "objects of type '%s'.|n" % self.create_type)
            return
        if self.create_type not in settings.COLLAB_TYPES:
            self.msg("|rType '%s' is not recognized.|n"
                            % self.create_type)
            return
        self.account = getattr(self.caller, 'account', self.caller)
        if not quota_check(self.account, self.create_type):
            self.msg("|rYou have already met your quota for type '%s'.|n"
                     % self.create_type)
            return
        thing = self.create_object()
        if thing is None:
            return
        self.caller.db.last_created = thing
        self.post_creation(thing)
        self.success_message(thing)

    def success_message(self, thing):
        """
        This is liable to change depending on what we're actually creating to
        be more semantically useful.
        """
        self.msg("|gObject '%s' of type '%s' created with DBref #%s.|n" % (
            thing.name, self.create_type, thing.id))

    def post_creation(self, thing):
        """
        Perform any post-creation actions that should be done, like setting the
        owner.
        """
        set_owner(self.caller, thing)

    def perm_check(self, key, destination, location):
        """
        Verify that the user has permission to create an object with these
        parameters. Raise an exception if not.
        """
        if destination:
            if not collab_check(self.caller, destination, locks=['link_to']):
                raise PermissionsError(
                    "|rYou don't have permission to link to '%s'.|n"
                    % destination)
        if location:
            if not collab_check(self.caller, location, locks=['create_in']):
                raise PermissionsError(
                    "|rYou can't create something in '%s'.|n" % location.name)

    def create_object(self):
        """
        Perform the actual creation of the object, after some validation.
        """
        typeclass = settings.COLLAB_TYPES[self.create_type]['typeclass']
        try:
            key, aliases = self.get_key_and_aliases()
        except ValueError as err:
            self.msg(str(err))
            return
        try:
            destination = self.get_destination()
        except ValueError as err:
            self.msg(str(err))
            return
        try:
            location = self.get_location()
        except ValueError as err:
            self.msg(str(err))
            return
        try:
            self.perm_check(key, destination, location)
        except PermissionsError as err:
            self.msg(str(err))

        return evennia.create_object(key=key, aliases=aliases, location=location,
                                     destination=destination, typeclass=typeclass)


class CmdCreate(BaseCreationCommand):
    """
    Create an object.

    Usage:
        @create object name;object alias 1;alias2
    """
    key = '@create'

    @lazy_property
    def not_permitted(self):
        return [settings.COLLAB_EXIT_TYPE, settings.COLLAB_ROOM_TYPE]

    def get_location(self):
        if hasattr(self.caller, 'account'):
            return self.caller
        return super(CmdCreate, self).get_location()


class CmdDig(BaseCreationCommand):
    """
    Create a new room.

    Usage:
        @dig room name;room alias 1;room alias 2
    """
    key = '@dig'
    help_category = "Building"

    def get_location(self):
        return None

    def pre_load(self):
        self.switches.insert(0, settings.COLLAB_ROOM_TYPE)

    def success_message(self, thing):
        self.msg("|gRoom '%s' created with DBREF #%s. "
                 "Type @tel me=#%s to visit it."
                 % (thing.name, thing.id, thing.id))


class CmdOpen(BaseCreationCommand):
    """
    Create a new exit between the current room and a destination.

    Usage:
        @open Exit name;exit alias 1;exit=room
    """
    key = '@open'

    def get_location(self):
        return self.caller.location

    def pre_load(self):
        self.switches.insert(0, settings.COLLAB_EXIT_TYPE)


class CmdBuildNick(MuxCommand):
    """
    Sets a nick for the last object you created. Useful for when pasting
    several commands at once and the DBREF may change.

    Usage:
        @bn tmproom

    This will allow you to refer to the last object created as 'tmproom'. This
    might be appropriate if you used @dig.
    """
    key = '@buildnick'
    aliases = ['@bnick', '@bn']

    def func(self):
        if not self.caller.db.last_created:
            self.msg("|rCouldn't locate your last created object, or you have already assigned a nick to it.|n")
            return
        if not self.args:
            self.msg("|rUsage: @bn name|n")
        self.caller.nicks.add(self.args, "#%s" % self.caller.db.last_created.id,
                              category='object')
        self.msg("|gNick '|y%s|g' set for %s|n" % (self.args, self.caller.db.last_created))
        # Delete reference to object once a nick is established. Too likely otherwise that someone will
        # accidentally assign nicks to unintended objects.
        del self.caller.db.last_created


class CmdDestroy(MuxCommand):
    """
    Deletes an object from the game.

    Usage:
        @destroy thing
    """
    key = '@destroy'
    aliases = ['@rec', '@delete', '@recycle']
    locks = "cmd:perm(create) or perm(Builder)"

    def func(self):
        target = self.caller.search(self.args)
        if not target:
            return
        if not collab_check(self.caller, target, locks=['delete']):
            self.msg("|rYou don't have permission to destroy that.|n")
            return
        if self.caller == target:
            self.msg("|rSuicide is not the answer.|n")
            return
        owner = get_owner(target, account_check=True) == getattr(self.caller, 'account', self.caller)
        if not owner and 'force' not in self.switches:
            self.msg("|rYou don't own %s. If you really want to delete it, use the /force switch." % target)
            return
        name = target.name
        target_id = target.id
        target.delete()
        self.msg("|y%s(#%s) destroyed.|n" % (name, target_id))


class CmdChown(MuxCommand):
    """
    Take ownership of an object.

    Usage:
        @chown object

    Wizards may also chown objects to specific persons.

    Usage:
        @chown object=new owner
    """
    key = '@chown'

    def func(self):
        target = self.caller.search(self.lhs)
        if self.rhs:
            new_owner = self.caller.search(self.rhs)
            allowed_class = (
                inherits_from(new_owner,
                              settings.BASE_CHARACTER_TYPECLASS)
                or
                inherits_from(new_owner,
                              settings.BASE_account_TYPECLASS))
            if not allowed_class:
                self.msg("|rYou can't set '%s' as an owner.|n"
                         % new_owner.name)
                return
            if not collab_check(self.caller, new_owner, locks=['chown_to']):
                self.msg("|rYou don't have permission to give that person "
                         "possessions.|n")
                return
        if not target:
            return

        if is_owner(self.caller, target, check_character=True):
            self.msg("|rYou already own that.|n")
            return

        if not collab_check(self.caller, target, locks=['chown']):
            self.msg("|rYou don't have permission to change that object's "
                     "owner.|n")
            return

        set_owner(self.caller, target)
        self.msg("|gOwner for %s(#%s) set to %s(#%s).|n"
                 % (target.name, target.id, self.caller, self.caller.id))


class CmdLink(MuxCommand):
    """
    Set the destination of an object. Most useful for changing the place where
    exits will lead.

    Usage:
        @link exit=destination
    """
    key = '@link'

    def func(self):
        if not self.lhs:
            self.msg("|rUsage: @link thing=destination|n")
        source = self.caller.search(self.lhs)
        if not source:
            return
        if self.rhs:
            destination = self.caller.search(self.rhs)
            if not destination:
                return
        else:
            destination = None
        if not collab_check(self.caller, source, locks=['link']):
            self.msg("|rYou don't have permission to link to '%s'.|n" % source)
            return
        if destination and not collab_check(self.caller, destination,
                                            locks=['link_to']):
            self.msg("|rYou don't have permission to link to '%s'."
                     % destination.name)
            return
        source.destination = destination
        if destination is None:
            self.msg("|g'%s' unlinked." % source.name)
        else:
            self.msg("|g'%s' linked to '%s'."
                     % (source.name, destination.name))


class CmdSetHome(MuxCommand):
    """
    Set the home of an object.

    Usage:
        @home object=home
    """
    key = '@home'

    def func(self):
        if not self.rhs:
            self.msg("|rUsage: @home thing=home|n")
        obj = self.caller.search(self.lhs)
        if not obj:
            return
        if self.rhs:
            home = self.caller.search(self.rhs)
            if not home:
                return
        else:
            home = None
        if not collab_check(self.caller, obj, locks=['home']):
            self.msg("|rYou don't have permission to set the home for '%s'.|n"
                     % obj)
            return
        if home and not collab_check(self.caller, home, locks=['home_to']):
            self.msg("|rYou don't have permission to set home to '%s'."
                     % home.name)
            return
        obj.home = home
        if home is None:
            self.msg("|g'%s' home cleared. |yWarning, this object may get "
                     "lost if its container is destroyed.|n" % obj.name)
        else:
            self.msg("|g'%s' home set to '%s'."
                     % (obj.name, home.name))


class CmdDesc(MuxCommand):
    """
    Describe an object. To give an object a one-line description, use:

    @desc object=description

    To enter a line editor for a longer description, use:

    @desc/long object
    """
    key = '@desc'
    aliases = ['@describe']

    def func(self):
        if not ((self.lhs or self.rhs) or 'long' in self.switches):
            self.msg("|rUsage: @desc thing=Description|n")
        obj = self.caller.search(self.lhs)
        if not obj:
            return
        if not collab_check(self.caller, obj, locks=['desc']):
            self.msg("rYou don't have permission to describe this object.")
            return
        if self.rhs and 'long' in self.switches:
            self.msg("|rYou may specify a description, or use the long flag, "
                     "but not both.|n")
            return
        if self.rhs:
            obj.db.desc = self.rhs
            self.msg("|gDescription set.")
            return
        # Time to call in the line editor.

        # hook save/load functions
        def load():
            return obj.db.desc or ""

        def save():
            """
            Save line buffer to given attribute name. This should
            return True if successful and also report its status.
            """
            obj.db.desc = self.editor.buffer
            self.caller.msg("Saved.")
            return True

        self.editor = EvEditor(
            self.caller,
            loadfunc=load,
            savefunc=save,
            key="desc"
        )


class CmdCollabCpAttr(CmdCpAttr):
    __doc__ = CmdCpAttr.__doc__

    def check_from_attr(self, obj, attr, clear=False):
        attr_name, handler = prefix_check(obj, attr)
        if clear:
            access = 'write'
        else:
            access = 'read'
        if not attr_check(self.caller, obj, access, handler):
            if clear:
                action = 'clear'
            else:
                action = 'read from'
            self.msg("|rYou are not allowed to %s '%s' on '%s'.|n"
                     % (action, attr, obj))
            return False
        return True

    def check_to_attr(self, obj, attr):
        attr_name, handler = prefix_check(obj, attr)
        if not attr_check(self.caller, obj, 'write', handler):
            self.msg("|rYou are not allowed to write to '%s' on '%s'."
                     % (obj, attr))
            return False
        return True

    def check_has_attr(self, obj, attr):
        attr_name, handler = prefix_check(obj, attr)
        if not handler.has(attr_name):
            self.caller.msg(
                "%s doesn't have an attribute %s."
                % (obj.name, attr))
            return False
        return True

    def get_attr(self, obj, attr):
        """
        Hook for overriding on subclassed commands. Do any preprocessing
        required and get the attribute from the object.
        """
        attr_name, handler = prefix_check(obj, attr)
        return handler.get(attr_name)


class CmdExamine(MuxCommand):
    """
    Examine the technical details of an object. To learn the basics of an
    object's settings, use:

    examine obj

    To browse the attributes of an object, use:

    examine/db obj

    To see an object's non-persistant attributes (things that go away when
    the game restarts):

    examine/ndb obj

    To see detailed information about commands available to an object, run:

    examine/cmd obj
    """
    key = "@examine"
    aliases = ["@ex", "ex", "exam", "examine"]
    locks = "cmd:perm(examine) or perm(Builders)"
    help_category = "Building"

    account_mode = False

    def func(self):
        if not self.lhs:
            self.msg("|rUsage: ex obj[=attribute_dir]|n")
        obj = self.caller.search(self.lhs)
        if not obj:
            return
        if not self.rhs and not self.switches:
            self.overview(obj)
            self.obj = obj
            if hasattr(obj, "sessid") and obj.sessions.all():
                mergemode = "session"
            elif self.account_mode:
                mergemode = "account"
            else:
                mergemode = "object"
            get_and_merge_cmdsets(
                obj, self.session, self.account, obj, mergemode, self.raw).addCallback(
                    self.cmd_info)
            return

        if 'db' in self.switches:
            self.db_listing(obj)
            return

    def db_listing(self, obj):
        self.msg('-' * 79)
        self.msg('Attributes for %s:' % obj.name)
        for key in settings.COLLAB_PROPTYPE_PERMS.keys():
            try:
                 handler = get_handler(obj, key)
            except AttributeError:
                continue
            if not attr_check(self.caller, obj, 'read', handler):
                continue
            prefix = key + '_'
            attributes = []
            for attribute in handler.all():
                if attribute.strvalue:
                    attributes.append(
                        "%s%s [strvalue]: %s|n"
                        % (prefix, attribute.db_key, attribute.db_strvalue))
                else:
                    attributes.append(
                        "%s%s: %s|n"
                        % (prefix, attribute.db_key, attribute.value))
            attributes.sort()
            self.msg('\n'.join(attributes))
        self.msg('-' * 79)

    def namer(self, obj):
        if obj is None:
            return '|rNone|n'
        if collab_check(self.caller, obj):
            return "%s(#%s)" % (obj.name, obj.id)
        else:
            return obj.name

    def cmd_info(self, avail_cmdset):
        obj = self.obj
        if (len(obj.cmdset.all()) == 1 and obj.cmdset.current.key == "_EMPTY_CMDSET") or not avail_cmdset:
            self.msg("|wThere are no command sets on %s.|n" % obj.name)
            self.msg("-" * 78)
            return
        stored_cmdsets = obj.cmdset.all()
        stored_cmdsets.sort(key=lambda x: x.priority, reverse=True)
        stored_line = "{wStored Cmdset(s)|n:\n %s" % (
            "\n ".join(
                ("%s [%s] (%s, prio %s)" % (cmdset.path, cmdset.key,
                                            cmdset.mergetype, cmdset.priority)
            for cmdset in stored_cmdsets if cmdset.key != "_EMPTY_CMDSET")))

        # this gets all components of the currently merged set
        all_cmdsets = [(cmdset.key, cmdset) for cmdset in avail_cmdset.merged_from]
        # we always at least try to add account- and session sets since these are ignored
        # if we merge on the object level.
        if hasattr(obj, "account") and obj.account:
            all_cmdsets.extend([(cmdset.key, cmdset) for cmdset in obj.account.cmdset.all()])
            if obj.sessions.all():
                # if there are more sessions than one on objects it's because of multisession mode 3.
                # we only show the first session's cmdset here (it is -in principle- possible that
                # different sessions have different cmdsets but for admins who want such madness
                # it is better that they overload with their own CmdExamine to handle it).
                all_cmdsets.extend([(cmdset.key, cmdset) for cmdset in obj.account.sessions.all()[0].cmdset.all()])
        else:
            try:
                # we have to protect this since many objects don't have sessions.
                all_cmdsets.extend([(cmdset.key, cmdset) for cmdset in obj.get_session(obj.sessid.get()).cmdset.all()])
            except (TypeError, AttributeError):
                pass
        all_cmdsets = [cmdset for cmdset in dict(all_cmdsets).values()]
        all_cmdsets.sort(key=lambda x: x.priority, reverse=True)
        merged_line = "|wMerged Cmdset(s)|n:\n %s" % (
            ("\n ".join("%s [%s] (%s, prio %s)" % (cmdset.path, cmdset.key, cmdset.mergetype, cmdset.priority)
             for cmdset in all_cmdsets)))

        # list the commands available to this object
        avail_cmdset = sorted([cmd.key for cmd in avail_cmdset
                               if cmd.access(obj, "cmd")])

        cmdsetstr = utils.fill(", ".join(avail_cmdset), indent=2)
        commands_line = "|wCommands available to %s (result of Merged CmdSets)|n:\n %s" % (obj.key, cmdsetstr)
        separator = '-' * 78
        self.msg('\n'.join([stored_line, merged_line, commands_line,
                            separator]))

    def overview(self, obj):
        display_owner = get_owner(obj)
        if not collab_check(self.caller, obj, locks=['examine']):
            self.msg("Owner: %s" % display_owner)
            return
        true_owner = get_owner(obj, account_check=True)
        name = "|wName/Key: |c%s|n(#%s)" % (obj.name, obj.id)
        owner_string = '|wOwner: |n'
        if not (true_owner or display_owner):
            owner_string += 'This object is |rORPHANED|n'
        elif (true_owner == display_owner) or not display_owner:
            owner_string += '|c%s|n(#%s)[%s]' % (
                true_owner.name, true_owner.id,
                true_owner.__class__.__name__)
        elif display_owner and not true_owner:
            owner_string += '|c%s|n(#%s)[%s]' % (
                display_owner.name, display_owner.id,
                display_owner.__class__.__name__)
        else:
            owner_string += '|c%s|n(#%s)[%s] via |c%s|n(#%s)[%s]' % (
                true_owner.name, true_owner.id,
                true_owner.__class__.__name__, display_owner,
                display_owner.id, display_owner.__class__.__name__)
        typeclass = "|wTypeclass: %s (%s)" % (obj.typename,
                                              obj.typeclass_path)
        permissions = '|wPermissions:|n %s' % (
                      ', '.join(obj.permissions.all()) or '|rNone|n')
        lines = ["-" * 78, name, owner_string, typeclass, permissions]
        if getattr(obj, 'account', None):
            account_line = "|waccount:|n |c%s|n(#%s)" % (obj.account.name, obj.account.id)
            ppermissions_set = obj.account.permissions.all()
            if ppermissions_set:
                ppermissions = "|waccount Permisions:|n %s" % (
                    ', '.join(obj.account.permissions.all()))
            else:
                ppermissions = '|rNone|n'
            if obj.account.is_superuser:
                ppermissions += ' |g[Superuser]|n'
            if obj.account.db._quelled:
                ppermissions += ' |y(quelled)|n'
            lines.extend([account_line, ppermissions])
        sessions_line = "|wSessions: |n"
        if hasattr(obj, "sessions") and obj.sessions.all():
            sessions_line += (
                ", ".join(str(sess.sessid) for sess in obj.sessions.all()))
        else:
            sessions_line += 'No sessions attached.'
        location = "|wLocation: |n%s" % self.namer(obj.location)
        destination = "|wDestination: |n%s" % self.namer(obj.destination)
        home = "|wHome: |n%s" % self.namer(obj.home)
        scripts = "|wScripts|n: "
        if str(obj.scripts):
            scripts += '\n%s' % obj.scripts
        else:
            scripts += '|rNone|n'
        excluded = ['owner', 'display_owner']
        tags = "|wTags|n: %s" % (
            utils.fill(", ".join(
                "{}:{}".format(key, category) if category else key
                for key, category in obj.tags.all(return_key_and_category=True)
                if category not in excluded), indent=5)
            or '|rNone|n')

        lines.extend([sessions_line, location, destination, home,
                      scripts, tags])

        # add the contents
        exits = []
        pobjs = []
        things = []
        if hasattr(obj, "contents"):
            for content in obj.contents:
                if content.destination:
                    exits.append(content)
                elif content.account:
                    pobjs.append(content)
                else:
                    things.append(content)
            object_lists = [('Exits', exits), ('Characters', pobjs),
                            ('Contents', things)]
            for name, obj_list in object_lists:
                item_list = [self.namer(item) for item in obj_list]
                lines.append("{w%s: |n%s" % (
                    name, ', '.join(item_list) or '|rNone|n'))
        lines.append("-" * 78)
        self.msg('\n'.join(lines))


class CmdCollabSetAttribute(CmdSetAttribute):
    __doc__ = CmdSetAttribute.__doc__

    def check_obj(self, obj):
        if not collab_check(self.caller, obj, ['setattribute']):
            self.msg("|rYou do not have permission to set attributes on this "
                     "object.")
            return False
        return True

    def check_attr(self, obj, attr_name):
        attr_name, handler = prefix_check(obj, attr_name)
        if not attr_check(self.caller, obj, 'write', handler):
            self.msg("|rYou do not have permission to set '%s' "
                     "on this object.|n" % attr_name)
            return False
        return True

    def view_attr(self, obj, attr):
        """
        Look up the value of an attribute and return a string displaying it.
        """
        attr_name, handler = prefix_check(obj, attr)
        if handler.has(attr):
            return "\nAttribute %s/%s = %s" % (obj.name, attr,
                                               handler.get(attr_name))
        else:
            return "\n%s has no attribute '%s'." % (obj.name, attr)

    def rm_attr(self, obj, attr):
        """
        Remove an attribute from the object, and report back.
        """
        attr_name, handler = prefix_check(obj, attr)
        if handler.has(attr):
            val = handler.has(attr)
            handler.remove(attr)
            return "\nDeleted attribute '%s' (= %s) from %s." % (attr, val, obj.name)
        else:
            return "\n%s has no attribute '%s'." % (obj.name, attr)

    def set_attr(self, obj, attr, value):
        attr_name, handler = prefix_check(obj, attr)
        try:
            handler.add(attr_name, value)
            return "\nCreated attribute %s/%s = %s" % (obj.name, attr, value)
        except SyntaxError:
            # this means literal_eval tried to parse a faulty string
            return ("\n|rCritical Python syntax error in your value. Only "
                    "primitive Python structures are allowed.\nYou also "
                    "need to use correct Python syntax. Remember especially "
                    "to put quotes around all strings inside lists and "
                    "dicts.|n")


class CmdCollabSetObjAlias(CmdSetObjAlias):
    __doc__ = CmdSetObjAlias.__doc__

    def func(self):
        pre_collab(
            self, "Usage: @alias obj=alias",
            "You do not have permission to set an alias for this "
            "object", ['alias']
        )


class CmdCollabListCmdSets(CmdListCmdSets):
    __doc__ = CmdListCmdSets.__doc__

    def func(self):
        pre_collab(
            self, "Usage: @alias obj=alias",
            "You do not have permission to list that object's "
            "cmdsets.", ['listcmdsets']
        )


class CmdCollabName(CmdName):
    __doc__ = CmdName.__doc__

    def func(self):
        pre_collab(
            self, "Usage: @name <obj> = <newname>[;alias;alias;...]",
            "You do not have permission to name that.", ['name']
        )


class CmdCollabLock(CmdLock):
    __doc__ = CmdLock.__doc__

    def func(self):
        pre_collab(
            self, "@lock <object>[ = <lockstring>] or @lock[/switch] "
            "object/<access_type>",
            "You do not have permission to set locks on this object."
        )


class CmdCollabCopy(CmdCopy):
    __doc__ = CmdCopy.__doc__

    def check_target_location(self, target_location):
        if self.caller in target_location.contents:
            return True
        if target_location == self.caller:
            return True
        return collab_check(self.caller, target_location, locks=['create_in'])

    def quota_check(self, obj):
        """
        Make sure copying doesn't circumvent quota.
        """
        collab_type = settings.COLLAB_REVERSE_TYPES.get(obj.typeclass_path)
        if not collab_type:
            self.msg("|rThe type of this object is not registered, and thus cannot be copied.|n")
            return False

        if not quota_check(self.caller, collab_type):
            self.msg("|rYou have reached your quota for this item type.|n")
            return False
        return True

    def func(self):
        pre_collab(
            self,
            "@copy[/reset] <original obj> [= new_name][;alias;alias..][:new_location] [,new_name2 ...]",
            "You do not have permission to copy this object.",
            extra_check=self.quota_check
        )
        if not getattr(self, 'copied_obj', None):
            return
        set_owner(self.caller, self.copied_obj)
        self.caller.db.last_created = self.copied_obj


class CmdZone(MuxCommand):
    key = "@zone"

    def func(self):
        if not pre_collab(
            self, "Usage: @zone[/remove] obj=name",
            "You do not have permission to set the zone for this "
            "object", ['zone'], call_super=False,
        ):
            return
        obj = self.caller.search(self.lhs)
        if not self.rhs:
            self.msg("|rYou must provide a zone name.|")
            return
        func = 'add'
        if 'remove' in self.switches:
            func = 'remove'
        if inherits_from(obj, settings.BASE_EXIT_TYPECLASS):
            getattr(obj.tags, func)(self.rhs, category='zone_exit')
            self.reset_rooms()
        elif inherits_from(obj, settings.BASE_ROOM_TYPECLASS):
            getattr(obj.tags, func)(self.rhs, category='zone_room')
            obj.reset_zone_cmdset()
        elif inherits_from(obj, settings.BASE_SCRIPT_TYPECLASS):
            getattr(obj.tags, func)(self.rhs, category='zone_script')
        else:
            # Since these zones are used for large global state changes across several items,
            # better to have this fail if not unambiguous.
            self.msg("|r{obj} not compatible with zoning.|n")
            return
        if func == 'add':
            self.msg("|g{obj} added to {zone}.|n".format(obj=obj, zone=self.rhs))
        else:
            self.msg("|y{obj} removed from {zone}.|n".format(obj=obj, zone=self.rhs))

    def reset_rooms(self):
        """
        Find all tagged rooms, reset their zone command sets.

        This is constructed in such a manner to avoid loading things into
        memory when they don't need to be.
        """
        rooms = evennia.ObjectDB.objects.get_by_tag(
            key=self.rhs, category='zone_room', raw_queryset=True).values_list('id', flat=True)
        for room in rooms:
            room = evennia.ObjectDB.get_cached_instance(room)
            if room:
                room.reset_zone_cmdset()


class CmdCommandGet(CmdGet):
    __doc__ = CmdGet.__doc__

    def success_message(self, obj):
        if obj.usrdb.success:
            self.msg(evtemplate(unicode(obj.usrdb.success), me=self.caller, this=obj, run_as=obj.owner))
        else:
            self.msg("You pick up %s." % obj.name)
        if obj.usrdb.osuccess:
            result = evtemplate(
                unicode(obj.usrdb.osuccess), me=self.caller, this=obj, run_as=obj.owner
            )
            if result.startswith("'s"):
                prefix = self.caller.name
            else:
                prefix = "%s " % self.caller.name
            self.caller.location.msg_contents(
                prefix + result,
                exclude=self.caller
            )
        else:
            self.caller.location.msg_contents(
                "%s picks up %s." % (self.caller.name, obj.name),
                exclude=self.caller
            )

    def failure_message(self, obj):
        if obj.usrdb.failure:
            self.msg(evtemplate(unicode(obj.usrdb.failure), me=self.caller, this=obj, run_as=obj.owner))
        else:
            self.msg("You can't get yourself.")
        if obj.usrdb.ofailure:
            result = evtemplate(
                unicode(obj.usrdb.ofailure), me=self.caller, this=obj, run_as=obj.owner
            )
            if result.startswith("'s"):
                prefix = self.caller.name
            else:
                prefix = "%s " % self.caller.name
            self.caller.location.msg_contents(
                prefix + result,
                exclude=self.caller
            )


class CmdCollabDrop(CmdDrop):
    __doc__ = CmdDrop.__doc__

    def drop_message(self, obj):
        if obj.usrdb.drop:
            self.msg(evtemplate(unicode(obj.usrdb.drop), me=self.caller, this=obj, run_as=obj.owner))
        else:
            self.msg("You drop %s." % obj.name)
        if obj.usrdb.osuccess:
            result = evtemplate(
                unicode(obj.usrdb.odrop), me=self.caller, this=obj, run_as=obj.owner
            )
            if result.startswith("'s"):
                prefix = self.caller.name
            else:
                prefix = "%s " % self.caller.name
            self.caller.location.msg_contents(
                prefix + result,
                exclude=self.caller
            )
        else:
            self.caller.location.msg_contents(
                "%s picks up %s." % (self.caller.name, obj.name),
                exclude=self.caller
            )


class BaseMsgCommand(MuxCommand):
    """
    Base class for setting the exit messages, like @suc, @osuc, @fail, @ofail, etc.
    """
    key = 'N/A'

    def func(self):
        if not pre_collab(
                self, "Usage: @{} obj=message",
                "You do not have permission to set the {} for this "
                "object".format(self.key, self.key), ['zone'], call_super=False,
        ):
            return
        obj = self.caller.search(self.lhs)
        label = self.key.replace('@', '')
        if not self.rhs:
            obj.usrattributes.remove(label)
            self.msg("|yMessage removed.".format(self.key))
            return
        obj.usrattributes.add(label, self.rhs)
        self.msg("|gMessage set.")


class CmdSuccMsg(BaseMsgCommand):
    """
    @success object=message

    Sets the success message. This is shown when successfully taking an object
    or using an exit.
    """
    key = '@success'
    aliases = ['@succ', '@suc']


class CmdOSuccMsg(BaseMsgCommand):
    """
    @osuccess object=message

    Sets the osuccess message. This is shown to others in the room, prepended
    by the user's name, when successfully taking an object or using an exit.
    """
    key = '@osuccess'
    aliases = ['@osucc', '@osuc']


class CmdFailMsg(BaseMsgCommand):
    """
    @failure object=message

    Sets the failure message. This is shown when a user fails to pass a lock
    for taking an object or using an exit.
    """
    key = '@failure'
    aliases = ['@fail']


class CmdOFailMsg(BaseMsgCommand):
    """
    @ofailure object=message

    Sets the ofailure message. This is shown to others in the room, prepended by
    the user's name when they fail to pass a lock to take an object or
    use an exit.
    """
    key = '@ofailure'
    aliases = ['@ofail']


class CmdDropMsg(BaseMsgCommand):
    """
    @drop object=message

    Sets the drop message. This is shown when a user drops an object, or
    arrives in a new room.
    """
    key = '@drop'


class CmdODropMsg(BaseMsgCommand):
    """
    @odrop object=message

    Sets the odrop message. This is shown to others when a user drops an
    object, or when they arrive in a new room.
    """
    key = '@odrop'


build_commands = [
    CmdCreate, CmdLink, CmdSetHome, CmdChown, CmdDesc, CmdDestroy, CmdDig,
    CmdOpen, CmdBuildNick, CmdCollabSetObjAlias, CmdCollabListCmdSets,
    CmdCollabName, CmdCollabLock, CmdCollabSetAttribute, CmdMvAttr,
    CmdExamine, CmdCollabCopy, CmdZone, CmdSuccMsg, CmdOSuccMsg,
    CmdFailMsg, CmdOFailMsg, CmdDropMsg, CmdODropMsg,
]
