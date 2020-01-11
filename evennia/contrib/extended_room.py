"""
Extended Room

Evennia Contribution - Griatch 2012, vincent-lg 2019

This is an extended Room typeclass for Evennia. It is supported
by an extended `Look` command and an extended `desc` command, also
in this module.


Features:

1) Time-changing description slots

This allows to change the full description text the room shows
depending on larger time variations. Four seasons (spring, summer,
autumn and winter) are used by default. The season is calculated
on-demand (no Script or timer needed) and updates the full text block.

There is also a general description which is used as fallback if
one or more of the seasonal descriptions are not set when their
time comes.

An updated `desc` command allows for setting seasonal descriptions.

The room uses the `evennia.utils.gametime.GameTime` global script. This is
started by default, but if you have deactivated it, you need to
supply your own time keeping mechanism.


2) In-description changing tags

Within each seasonal (or general) description text, you can also embed
time-of-day dependent sections. Text inside such a tag will only show
during that particular time of day. The tags looks like `<timeslot> ...
</timeslot>`. By default there are four timeslots per day - morning,
afternoon, evening and night.


3) Details

The Extended Room can be "detailed" with special keywords. This makes
use of a special `Look` command. Details are "virtual" targets to look
at, without there having to be a database object created for it. The
Details are simply stored in a dictionary on the room and if the look
command cannot find an object match for a `look <target>` command it
will also look through the available details at the current location
if applicable. The `@detail` command is used to change details.


4) Extra commands

  CmdExtendedRoomLook - look command supporting room details
  CmdExtendedRoomDesc - desc command allowing to add seasonal descs,
  CmdExtendedRoomDetail - command allowing to manipulate details in this room
                    as well as listing them
  CmdExtendedRoomGameTime - A simple `time` command, displaying the current
                    time and season.


Installation/testing:

Adding the `ExtendedRoomCmdset` to the default character cmdset will add all
new commands for use.

In more detail, in mygame/commands/default_cmdsets.py:

```
...
from evennia.contrib import extended_room   # <-new

class CharacterCmdset(default_cmds.Character_CmdSet):
    ...
    def at_cmdset_creation(self):
        ...
        self.add(extended_room.ExtendedRoomCmdSet)  # <-new

```

Then reload to make the bew commands available. Note that they only work
on rooms with the typeclass `ExtendedRoom`. Create new rooms with the right
typeclass or use the `typeclass` command to swap existing rooms.

"""


import datetime
import re
from django.conf import settings
from evennia import DefaultRoom
from evennia import gametime
from evennia import default_cmds
from evennia import utils
from evennia import CmdSet

# error return function, needed by Extended Look command
_AT_SEARCH_RESULT = utils.variable_from_module(*settings.SEARCH_AT_RESULT.rsplit(".", 1))

# regexes for in-desc replacements
RE_MORNING = re.compile(r"<morning>(.*?)</morning>", re.IGNORECASE)
RE_AFTERNOON = re.compile(r"<afternoon>(.*?)</afternoon>", re.IGNORECASE)
RE_EVENING = re.compile(r"<evening>(.*?)</evening>", re.IGNORECASE)
RE_NIGHT = re.compile(r"<night>(.*?)</night>", re.IGNORECASE)
# this map is just a faster way to select the right regexes (the first
# regex in each tuple will be parsed, the following will always be weeded out)
REGEXMAP = {
    "morning": (RE_MORNING, RE_AFTERNOON, RE_EVENING, RE_NIGHT),
    "afternoon": (RE_AFTERNOON, RE_MORNING, RE_EVENING, RE_NIGHT),
    "evening": (RE_EVENING, RE_MORNING, RE_AFTERNOON, RE_NIGHT),
    "night": (RE_NIGHT, RE_MORNING, RE_AFTERNOON, RE_EVENING),
}

# set up the seasons and time slots. This assumes gametime started at the
# beginning of the year (so month 1 is equivalent to January), and that
# one CAN divide the game's year into four seasons in the first place ...
MONTHS_PER_YEAR = 12
SEASONAL_BOUNDARIES = (3 / 12.0, 6 / 12.0, 9 / 12.0)
HOURS_PER_DAY = 24
DAY_BOUNDARIES = (0, 6 / 24.0, 12 / 24.0, 18 / 24.0)


# implements the Extended Room


class ExtendedRoom(DefaultRoom):
    """
    This room implements a more advanced `look` functionality depending on
    time. It also allows for "details", together with a slightly modified
    look command.
    """

    def at_object_creation(self):
        """Called when room is first created only."""
        self.db.spring_desc = ""
        self.db.summer_desc = ""
        self.db.autumn_desc = ""
        self.db.winter_desc = ""
        # the general desc is used as a fallback if a seasonal one is not set
        self.db.general_desc = ""
        # will be set dynamically. Can contain raw timeslot codes
        self.db.raw_desc = ""
        # this will be set dynamically at first look. Parsed for timeslot codes
        self.db.desc = ""
        # these will be filled later
        self.ndb.last_season = None
        self.ndb.last_timeslot = None
        # detail storage
        self.db.details = {}

    def get_time_and_season(self):
        """
        Calculate the current time and season ids.
        """
        # get the current time as parts of year and parts of day.
        # we assume a standard calendar here and use 24h format.
        timestamp = gametime.gametime(absolute=True)
        # note that fromtimestamp includes the effects of server time zone!
        datestamp = datetime.datetime.fromtimestamp(timestamp)
        season = float(datestamp.month) / MONTHS_PER_YEAR
        timeslot = float(datestamp.hour) / HOURS_PER_DAY

        # figure out which slots these represent
        if SEASONAL_BOUNDARIES[0] <= season < SEASONAL_BOUNDARIES[1]:
            curr_season = "spring"
        elif SEASONAL_BOUNDARIES[1] <= season < SEASONAL_BOUNDARIES[2]:
            curr_season = "summer"
        elif SEASONAL_BOUNDARIES[2] <= season < 1.0 + SEASONAL_BOUNDARIES[0]:
            curr_season = "autumn"
        else:
            curr_season = "winter"

        if DAY_BOUNDARIES[0] <= timeslot < DAY_BOUNDARIES[1]:
            curr_timeslot = "night"
        elif DAY_BOUNDARIES[1] <= timeslot < DAY_BOUNDARIES[2]:
            curr_timeslot = "morning"
        elif DAY_BOUNDARIES[2] <= timeslot < DAY_BOUNDARIES[3]:
            curr_timeslot = "afternoon"
        else:
            curr_timeslot = "evening"

        return curr_season, curr_timeslot

    def replace_timeslots(self, raw_desc, curr_time):
        """
        Filter so that only time markers `<timeslot>...</timeslot>` of
        the correct timeslot remains in the description.

        Args:
            raw_desc (str): The unmodified description.
            curr_time (str): A timeslot identifier.

        Returns:
            description (str): A possibly moified description.

        """
        if raw_desc:
            regextuple = REGEXMAP[curr_time]
            raw_desc = regextuple[0].sub(r"\1", raw_desc)
            raw_desc = regextuple[1].sub("", raw_desc)
            raw_desc = regextuple[2].sub("", raw_desc)
            return regextuple[3].sub("", raw_desc)
        return raw_desc

    def return_detail(self, key):
        """
        This will attempt to match a "detail" to look for in the room.

        Args:
            key (str): A detail identifier.

        Returns:
            detail (str or None): A detail matching the given key.

        Notes:
            A detail is a way to offer more things to look at in a room
            without having to add new objects. For this to work, we
            require a custom `look` command that allows for `look
            <detail>` - the look command should defer to this method on
            the current location (if it exists) before giving up on
            finding the target.

            Details are not season-sensitive, but are parsed for timeslot
            markers.
        """
        try:
            detail = self.db.details.get(key.lower(), None)
        except AttributeError:
            # this happens if no attribute details is set at all
            return None
        if detail:
            season, timeslot = self.get_time_and_season()
            detail = self.replace_timeslots(detail, timeslot)
            return detail
        return None

    def set_detail(self, detailkey, description):
        """
        This sets a new detail, using an Attribute "details".

        Args:
            detailkey (str): The detail identifier to add (for
                aliases you need to add multiple keys to the
                same description). Case-insensitive.
            description (str): The text to return when looking
                at the given detailkey.

        """
        if self.db.details:
            self.db.details[detailkey.lower()] = description
        else:
            self.db.details = {detailkey.lower(): description}

    def del_detail(self, detailkey, description):
        """
        Delete a detail.

        The description is ignored.

        Args:
            detailkey (str): the detail to remove (case-insensitive).
            description (str, ignored): the description.

        The description is only included for compliance but is completely
        ignored.  Note that this method doesn't raise any exception if
        the detail doesn't exist in this room.

        """
        if self.db.details and detailkey.lower() in self.db.details:
            del self.db.details[detailkey.lower()]

    def return_appearance(self, looker, **kwargs):
        """
        This is called when e.g. the look command wants to retrieve
        the description of this object.

        Args:
            looker (Object): The object looking at us.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            description (str): Our description.

        """
        # ensures that our description is current based on time/season
        self.update_current_description()
        # run the normal return_appearance method, now that desc is updated.
        return super(ExtendedRoom, self).return_appearance(looker, **kwargs)

    def update_current_description(self):
        """
        This will update the description of the room if the time or season
        has changed since last checked.
        """
        update = False
        # get current time and season
        curr_season, curr_timeslot = self.get_time_and_season()
        # compare with previously stored slots
        last_season = self.ndb.last_season
        last_timeslot = self.ndb.last_timeslot
        if curr_season != last_season:
            # season changed. Load new desc, or a fallback.
            new_raw_desc = self.attributes.get("%s_desc" % curr_season)
            if new_raw_desc:
                raw_desc = new_raw_desc
            else:
                # no seasonal desc set. Use fallback
                raw_desc = self.db.general_desc or self.db.desc
            self.db.raw_desc = raw_desc
            self.ndb.last_season = curr_season
            update = True
        if curr_timeslot != last_timeslot:
            # timeslot changed. Set update flag.
            self.ndb.last_timeslot = curr_timeslot
            update = True
        if update:
            # if anything changed we have to re-parse
            # the raw_desc for time markers
            # and re-save the description again.
            self.db.desc = self.replace_timeslots(self.db.raw_desc, curr_timeslot)


# Custom Look command supporting Room details. Add this to
# the Default cmdset to use.


class CmdExtendedRoomLook(default_cmds.CmdLook):
    """
    look

    Usage:
      look
      look <obj>
      look <room detail>
      look *<account>

    Observes your location, details at your location or objects in your vicinity.
    """

    def func(self):
        """
        Handle the looking - add fallback to details.
        """
        caller = self.caller
        args = self.args
        if args:
            looking_at_obj = caller.search(
                args,
                candidates=caller.location.contents + caller.contents,
                use_nicks=True,
                quiet=True,
            )
            if not looking_at_obj:
                # no object found. Check if there is a matching
                # detail at location.
                location = caller.location
                if (
                    location
                    and hasattr(location, "return_detail")
                    and callable(location.return_detail)
                ):
                    detail = location.return_detail(args)
                    if detail:
                        # we found a detail instead. Show that.
                        caller.msg(detail)
                        return
                # no detail found. Trigger delayed error messages
                _AT_SEARCH_RESULT(looking_at_obj, caller, args, quiet=False)
                return
            else:
                # we need to extract the match manually.
                looking_at_obj = utils.make_iter(looking_at_obj)[0]
        else:
            looking_at_obj = caller.location
            if not looking_at_obj:
                caller.msg("You have no location to look at!")
                return

        if not hasattr(looking_at_obj, "return_appearance"):
            # this is likely due to us having an account instead
            looking_at_obj = looking_at_obj.character
        if not looking_at_obj.access(caller, "view"):
            caller.msg("Could not find '%s'." % args)
            return
        # get object's appearance
        caller.msg(looking_at_obj.return_appearance(caller))
        # the object's at_desc() method.
        looking_at_obj.at_desc(looker=caller)


# Custom build commands for setting seasonal descriptions
# and detailing extended rooms.


class CmdExtendedRoomDesc(default_cmds.CmdDesc):
    """
    `desc` - describe an object or room.

    Usage:
      desc[/switch] [<obj> =] <description>

    Switches for `desc`:
      spring  - set description for <season> in current room.
      summer
      autumn
      winter

    Sets the "desc" attribute on an object. If an object is not given,
    describe the current room.

    You can also embed special time markers in your room description, like this:

        ```
        <night>In the darkness, the forest looks foreboding.</night>.
        ```

    Text marked this way will only display when the server is truly at the given
    timeslot. The available times are night, morning, afternoon and evening.

    Note that seasons and time-of-day slots only work on rooms in this
    version of the `desc` command.

    """

    aliases = ["describe"]
    switch_options = ()  # Inherits from default_cmds.CmdDesc, but unused here

    def reset_times(self, obj):
        """By deleteting the caches we force a re-load."""
        obj.ndb.last_season = None
        obj.ndb.last_timeslot = None

    def func(self):
        """Define extended command"""
        caller = self.caller
        location = caller.location
        if not self.args:
            if location:
                string = "|wDescriptions on %s|n:\n" % location.key
                string += " |wspring:|n %s\n" % location.db.spring_desc
                string += " |wsummer:|n %s\n" % location.db.summer_desc
                string += " |wautumn:|n %s\n" % location.db.autumn_desc
                string += " |wwinter:|n %s\n" % location.db.winter_desc
                string += " |wgeneral:|n %s" % location.db.general_desc
                caller.msg(string)
                return
        if self.switches and self.switches[0] in ("spring", "summer", "autumn", "winter"):
            # a seasonal switch was given
            if self.rhs:
                caller.msg("Seasonal descs only work with rooms, not objects.")
                return
            switch = self.switches[0]
            if not location:
                caller.msg("No location was found!")
                return
            if switch == "spring":
                location.db.spring_desc = self.args
            elif switch == "summer":
                location.db.summer_desc = self.args
            elif switch == "autumn":
                location.db.autumn_desc = self.args
            elif switch == "winter":
                location.db.winter_desc = self.args
            # clear flag to force an update
            self.reset_times(location)
            caller.msg("Seasonal description was set on %s." % location.key)
        else:
            # No seasonal desc set, maybe this is not an extended room
            if self.rhs:
                text = self.rhs
                obj = caller.search(self.lhs)
                if not obj:
                    return
            else:
                text = self.args
                obj = location
            obj.db.desc = text  # a compatibility fallback
            if obj.attributes.has("general_desc"):
                obj.db.general_desc = text
                self.reset_times(obj)
                caller.msg("General description was set on %s." % obj.key)
            else:
                # this is not an ExtendedRoom.
                caller.msg("The description was set on %s." % obj.key)


class CmdExtendedRoomDetail(default_cmds.MuxCommand):

    """
    sets a detail on a room

    Usage:
        @detail[/del] <key> [= <description>]
        @detail <key>;<alias>;... = description

    Example:
        @detail
        @detail walls = The walls are covered in ...
        @detail castle;ruin;tower = The distant ruin ...
        @detail/del wall
        @detail/del castle;ruin;tower

    This command allows to show the current room details if you enter it
    without any argument.  Otherwise, sets or deletes a detail on the current
    room, if this room supports details like an extended room. To add new
    detail, just use the @detail command, specifying the key, an equal sign
    and the description.  You can assign the same description to several
    details using the alias syntax (replace key by alias1;alias2;alias3;...).
    To remove one or several details, use the @detail/del switch.

    """

    key = "@detail"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        location = self.caller.location
        if not self.args:
            details = location.db.details
            if not details:
                self.msg("|rThe room {} doesn't have any detail set.|n".format(location))
            else:
                details = sorted(["|y{}|n: {}".format(key, desc) for key, desc in details.items()])
                self.msg("Details on Room:\n" + "\n".join(details))
            return

        if not self.rhs and "del" not in self.switches:
            detail = location.return_detail(self.lhs)
            if detail:
                self.msg("Detail '|y{}|n' on Room:\n{}".format(self.lhs, detail))
            else:
                self.msg("Detail '{}' not found.".format(self.lhs))
            return

        method = "set_detail" if "del" not in self.switches else "del_detail"
        if not hasattr(location, method):
            self.caller.msg("Details cannot be set on %s." % location)
            return
        for key in self.lhs.split(";"):
            # loop over all aliases, if any (if not, this will just be
            # the one key to loop over)
            getattr(location, method)(key, self.rhs)
        if "del" in self.switches:
            self.caller.msg("Detail %s deleted, if it existed." % self.lhs)
        else:
            self.caller.msg("Detail set '%s': '%s'" % (self.lhs, self.rhs))


# Simple command to view the current time and season


class CmdExtendedRoomGameTime(default_cmds.MuxCommand):
    """
    Check the game time

    Usage:
        time

    Shows the current in-game time and season.
    """

    key = "time"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        """Reads time info from current room"""
        location = self.caller.location
        if not location or not hasattr(location, "get_time_and_season"):
            self.caller.msg("No location available - you are outside time.")
        else:
            season, timeslot = location.get_time_and_season()
            prep = "a"
            if season == "autumn":
                prep = "an"
            self.caller.msg("It's %s %s day, in the %s." % (prep, season, timeslot))


# CmdSet for easily install all commands


class ExtendedRoomCmdSet(CmdSet):
    """
    Groups the extended-room commands.

    """

    def at_cmdset_creation(self):
        self.add(CmdExtendedRoomLook)
        self.add(CmdExtendedRoomDesc)
        self.add(CmdExtendedRoomDetail)
        self.add(CmdExtendedRoomGameTime)
