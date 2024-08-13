"""
Extended Room

Evennia Contribution - Griatch 2012, vincent-lg 2019, Griatch 2023

This is an extended Room typeclass for Evennia, supporting descriptions that vary
by season, time-of-day or arbitrary states (like burning). It has details, embedded
state tags, support for repeating random messages as well as a few extra commands.

- The room description can be set to change depending on the season or time of day.
- Parts of the room description can be set to change depending on arbitrary states (like burning).
- Details can be added to the room, which can be looked at like objects.
- Alternative text sections can be added to the room description, which will only show if
  the room is in a given state.
- Random messages can be set to repeat at a given rate.


Installation/testing:

Adding the `ExtendedRoomCmdset` to the default character cmdset will add all
new commands for use.

In more detail, in mygame/commands/default_cmdsets.py:

```
...
from evennia.contrib import extended_room   # <---

class CharacterCmdset(default_cmds.Character_CmdSet):
    ...
    def at_cmdset_creation(self):
        ...
        self.add(extended_room.ExtendedRoomCmdSet)  # <---

```

Then, reload to make the new commands available. Note that they only work
on rooms with the `ExtendedRoom` typeclass. Create new rooms with the correct
typeclass or use the `typeclass` command to swap existing rooms.

"""

import datetime
import random
import re
from collections import deque

from django.conf import settings
from django.db.models import Q

from evennia import (
    CmdSet,
    DefaultRoom,
    EvEditor,
    FuncParser,
    InterruptCommand,
    default_cmds,
    gametime,
    utils,
)
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.utils import list_to_string, repeat

# error return function, needed by Extended Look command
_AT_SEARCH_RESULT = utils.variable_from_module(*settings.SEARCH_AT_RESULT.rsplit(".", 1))


# funcparser callable for the ExtendedRoom


def func_state(roomstate, *args, looker=None, room=None, **kwargs):
    """
    Usage: $state(roomstate, text)

    Funcparser callable for ExtendedRoom. This is called by the FuncParser when it
    returns the description of the room. Use 'default' for a default text when no
    other states are set.

    Args:
        roomstate (str): A roomstate, like "morning", "raining". This is case insensitive.
        *args: All these will be combined into one string separated by commas.

    Keyword Args:
        looker (Object): The object looking at the room. Unused by default.
        room (ExtendedRoom): The room being looked at.

    Example:

        $state(morning, It is a beautiful morning!)

    Notes:
        We try to merge all args into one text, since this function doesn't require more than one
        argument. That way, one may be able to get away without using quotes.

    """
    roomstate = str(roomstate).lower()
    text = ", ".join(args)
    # make sure we have a room and a caller and not something parsed from the string
    if not (roomstate and looker and room) or isinstance(looker, str) or isinstance(room, str):
        return ""

    try:
        if roomstate in room.room_states or roomstate == room.get_time_of_day():
            return text
        if roomstate == "default" and not room.room_states:
            # return this if no roomstate is set
            return text
    except AttributeError:
        # maybe used on a non-ExtendedRoom?
        pass
    return ""


class ExtendedRoom(DefaultRoom):
    """
    An Extended Room

    Room states:
      A room state is set as a Tag with category "roomstate" and tagkey "on_fire" or "flooded"
      etc).

    Alternative descriptions:
    - Add an Attribute `desc_<roomstate>` to the room, where <roomstate> is the name of the
      roomstate to use this for, like `desc_on_fire` or `desc_flooded`. If not given, seasonal
      descriptions given in desc_spring/summer/autumn/winter will be used, and last the
      regular `desc` Attribute.

    Alternative text sections
    - Used to add alternative text sections to the room description. These are embedded in the
      description by adding `$state(roomstate, txt)`. They will show only if the room is in the
      given roomstate. These are managed via the add/remove/get_alt_text methods.

    Details:
    - This is set as an Attribute `details` (a dict) on the room, with the detail name as key.
      When looking at this room, the detail name can be used as a target to look at without having
      to add an actual database object for it. The `detail` command is used to add/remove details.

    Room messages
    - Set `room_message_rate > 0` and add a list of `room_messages`. These will be randomly
      echoed to the room at the given rate.

    """

    # fallback description if nothing else is set
    fallback_desc = "You see nothing special."

    # tag room_state category
    room_state_tag_category = "room_state"

    # time setup
    months_per_year = 12
    hours_per_day = 24

    # seasons per year, given as (start, end) boundaries, each a fraction of a year. These
    # will change the description. The last entry should wrap around to the first.
    seasons_per_year = {
        "spring": (3 / months_per_year, 6 / months_per_year),  # March - May
        "summer": (6 / months_per_year, 9 / months_per_year),  # June - August
        "autumn": (9 / months_per_year, 12 / months_per_year),  # September - November
        "winter": (12 / months_per_year, 3 / months_per_year),  # December - February
    }

    # time-dependent room descriptions (these must match the `seasons_per_year` above).
    desc_spring = AttributeProperty("", autocreate=False)
    desc_summer = AttributeProperty("", autocreate=False)
    desc_autumn = AttributeProperty("", autocreate=False)
    desc_winter = AttributeProperty("", autocreate=False)

    # time-dependent embedded descriptions, usable as $timeofday(morning, text)
    # (start, end) boundaries, each a fraction of a day. The last one should
    # end at 0 (not 24) to wrap around to midnight.
    times_of_day = {
        "night": (0, 6 / hours_per_day),  # midnight - 6AM
        "morning": (6 / hours_per_day, 12 / hours_per_day),  # 6AM - noon
        "afternoon": (12 / hours_per_day, 18 / hours_per_day),  # noon - 6PM
        "evening": (18 / hours_per_day, 0),  # 6PM - midnight
    }

    # normal vanilla description if no other `*_desc` matches or are set.
    desc = AttributeProperty("", autocreate=False)

    # look-targets without database objects
    details = AttributeProperty(dict, autocreate=False)

    # messages to send to the room
    room_message_rate = 0  # set >0s to enable
    room_messages = AttributeProperty(list, autocreate=False)

    # Broadcast message

    def _get_funcparser(self, looker):
        return FuncParser(
            {"state": func_state},
            looker=looker,
            room=self,
        )

    def _start_broadcast_repeat_task(self):
        if self.room_message_rate and self.room_messages and not self.ndb.broadcast_repeat_task:
            self.ndb.broadcast_repeat_task = repeat(
                self.room_message_rate, self.repeat_broadcast_msg_to_room, persistent=False
            )

    def at_init(self):
        """Evennia hook. Start up repeating function whenever object loads into memory."""
        self._start_broadcast_repeat_task()

    def start_repeat_broadcast_messages(self):
        """
        Start repeating the broadcast messages. Only needs to be called if adding messages
        and not having reloaded the server.

        """
        self._start_broadcast_repeat_task()

    def repeat_broadcast_message_to_room(self):
        """
        Send a message to the room at room_message_rate. By default
        we will randomize which one to send.

        """
        self.msg_contents(random.choice(self.room_messages))

    def get_time_of_day(self):
        """
        Get the current time of day.

        Override to customize.

        Returns:
            str: The time of day, such as 'morning', 'afternoon', 'evening' or 'night'.

        """
        timestamp = gametime.gametime(absolute=True)
        datestamp = datetime.datetime.fromtimestamp(timestamp)
        timeslot = float(datestamp.hour) / self.hours_per_day

        for time_of_day, (start, end) in self.times_of_day.items():
            if start < end and start <= timeslot < end:
                return time_of_day
        return time_of_day  # final back to the beginning

    def get_season(self):
        """
        Get the current season.

        Override to customize.

        Returns:
            str: The season, such as 'spring', 'summer', 'autumn' or 'winter'.

        """
        timestamp = gametime.gametime(absolute=True)
        datestamp = datetime.datetime.fromtimestamp(timestamp)
        timeslot = float(datestamp.month) / self.months_per_year

        for season_of_year, (start, end) in self.seasons_per_year.items():
            if start < end and start <= timeslot < end:
                return season_of_year
        return season_of_year  # final step is back to beginning

    # manipulate room states

    @property
    def room_states(self):
        """
        Get all room_states set on this room.

        """
        return list(sorted(self.tags.get(category=self.room_state_tag_category, return_list=True)))

    def add_room_state(self, *room_states):
        """
        Set a room-state or room-states to the room.

        Args:
            *room_state (str): A room state like 'on_fire' or 'flooded'. This will affect
                what `desc_*` and `roomstate_*` descriptions/inlines are used. You can add
                more than one at a time.

        Notes:
            You can also set time-based room_states this way, like 'morning' or 'spring'. This
            can be useful to force a particular description, but while this state is
            set this way, that state will be unaffected by the passage of time. Remove
            the state to let the current game time determine this type of states.

        """
        self.tags.batch_add(*((state, self.room_state_tag_category) for state in room_states))

    def remove_room_state(self, *room_states):
        """
        Remove a roomstate from the room.

        Args:
            *room_state (str): A roomstate like 'on_fire' or 'flooded'. If the
            room did not have this state, nothing happens.You can remove more than one at a time.

        """
        for room_state in room_states:
            self.tags.remove(room_state, category=self.room_state_tag_category)

    def clear_room_state(self):
        """
        Clear all room states.

        Note that fallback time-of-day and seasonal states are not affected by this, only
        custom states added with `.add_room_state()`.

        """
        self.tags.clear(category="room_state")

    # control the available room descriptions

    def add_desc(self, desc, room_state=None):
        """
        Add a custom description, matching a particular room state.

        Args:
            desc (str): The description to use when this roomstate is active.
            roomstate (str, None): The roomstate to match, like 'on_fire', 'flooded', or "spring".
                If `None`, set the default `desc` fallback.

        """
        if room_state is None:
            self.attributes.add("desc", desc)
        else:
            self.attributes.add(f"desc_{room_state}", desc)

    def remove_desc(self, room_state):
        """
        Remove a custom description.

        Args:
            room_state (str): The room-state description to remove.

        """
        self.attributes.remove(f"desc_{room_state}")

    def all_desc(self):
        """
        Get all available descriptions.

        Returns:
            dict: A mapping of roomstate to description. The `None` key indicates the
                base subscription (stored in the `desc` Attribute).

        """
        return {
            **{None: self.db.desc or ""},
            **{
                attr.key[5:]: attr.value
                for attr in self.db_attributes.filter(db_key__startswith="desc_").order_by("db_key")
            },
        }

    def get_stateful_desc(self):
        """
        Get the currently active room description based on the current roomstate.

        Returns:
            str: The current description.

        Note:
            Only one description can be active at a time. Priority order is as follows:

            Priority order is as follows:

                1. Room-states set by `add_roomstate()` that are not seasons.
                   If multiple room_states are set, the first one is used, sorted alphabetically.
                2. Seasons set by `add_room_state()`. This allows to 'pin' a season.
                3. Time-based seasons based on the current in-game time.
                4. None, if no seasons are defined in `.seasons_per_year`.

            If either of the above is found, but doesn't have a matching `desc_<roomstate>`
            description, we move on to the next priority. If no matches are found, the `desc`
            Attribute is used.

        """

        room_states = self.room_states
        seasons = self.seasons_per_year.keys()
        seasonal_room_states = []

        # get all available descriptions on this room
        # note: *_desc is the old form, we support it for legacy
        descriptions = dict(
            self.db_attributes.filter(
                Q(db_key__startswith="desc_") | Q(db_key__endswith="_desc")
            ).values_list("db_key", "db_value")
        )

        for roomstate in sorted(room_states):
            if roomstate not in seasons:
                # if we have a roomstate that is not a season, use it
                if desc := descriptions.get(f"desc_{roomstate}") or descriptions.get(
                    "{roomstate}_desc"
                ):
                    return desc
            else:
                seasonal_room_states.append(roomstate)

        if not seasons:
            # no seasons defined, so just return the default desc
            return self.attributes.get("desc")

        for seasonal_roomstate in seasonal_room_states:
            # explicit setting of season outside of automatic time keeping
            if desc := descriptions.get(f"desc_{seasonal_roomstate}"):
                return desc

        # no matching room_states, use time-based seasons. Also support legacy *_desc form
        season = self.get_season()
        if desc := descriptions.get(f"desc_{season}") or descriptions.get(f"{season}_desc"):
            return desc

        # fallback to normal desc Attribute
        return self.attributes.get("desc", self.fallback_desc)

    def replace_legacy_time_of_day_markup(self, desc):
        """
        Filter description by legacy markup like `<morning>...</morning>`. Filter
        out all such markings that does not match the current time. Supports
        'morning', 'afternoon', 'evening' and 'night'.

        Args:
            desc (str): The unmodified description.

        Returns:
            str: A possibly modified description.

        Notes:
            This is legacy. Use the $state markup for new rooms instead.

        """
        desc = desc or ""
        current_time_of_day = self.get_time_of_day()

        # regexes for in-desc replacements (gets cached)
        if not hasattr(self, "legacy_timeofday_regex_map"):
            timeslots = deque()
            for tod in self.times_of_day:
                timeslots.append(
                    (
                        tod,
                        re.compile(rf"<{tod}>(.*?)</{tod}>", re.IGNORECASE),
                    )
                )

            # map the regexes cyclically, so each one is first once
            self.legacy_timeofday_regex_map = {}
            for i in range(len(timeslots)):
                # mapping {"morning": [morning_regex, ...], ...}
                self.legacy_timeofday_regex_map[timeslots[0][0]] = [tup[1] for tup in timeslots]
                timeslots.rotate(-1)

        # do the replacement
        regextuple = self.legacy_timeofday_regex_map[current_time_of_day]
        for regex in regextuple:
            desc = regex.sub(r"\1" if regex == regextuple[0] else "", desc)
        return desc

    def get_display_desc(self, looker, **kwargs):
        """
        Evennia standard hook. Dynamically get the 'desc' component of the object description. This
        is called by the return_appearance method and in turn by the 'look' command.

        Args:
            looker (Object): Object doing the looking (unused by default).
            **kwargs: Arbitrary data for use when overriding.
        Returns:
            str: The desc display string.

        """
        # get the current description based on the roomstate
        desc = self.get_stateful_desc()
        # parse for legacy <morning>...</morning> markers
        desc = self.replace_legacy_time_of_day_markup(desc)
        # apply funcparser
        desc = self._get_funcparser(looker).parse(desc, **kwargs)
        return desc

    # manipulate details

    def add_detail(self, key, description):
        """
        This sets a new detail, using an Attribute "details".

        Args:
            detailkey (str): The detail identifier to add (for
                aliases you need to add multiple keys to the
                same description). Case-insensitive.
            description (str): The text to return when looking
                at the given detailkey. This can contain funcparser directives.

        """
        if not self.details:
            self.details = {}  # causes it to be created as real attribute
        self.details[key.lower()] = description

    set_detail = add_detail  # legacy name

    def remove_detail(self, key, *args):
        """
        Delete a detail.

        Args:
            key (str): the detail to remove (case-insensitive).
            *args: Unused (backwards compatibility)

        The description is only included for compliance but is completely
        ignored.  Note that this method doesn't raise any exception if
        the detail doesn't exist in this room.

        """
        self.details.pop(key.lower(), None)

    del_detail = remove_detail  # legacy alias

    def get_detail(self, key, looker=None):
        """
        This will attempt to match a "detail" to look for in the room.
        This will do a lower-case match followed by a startsby match. This
        is called by the new `look` Command.

        Args:
            key (str): A detail identifier.
            looker (Object, optional): The one looking.

        Returns:
            detail (str or None): A detail matching the given key, or `None` if
            it was not found.

        Notes:
            A detail is a way to offer more things to look at in a room
            without having to add new objects. For this to work, we
            require a custom `look` command that allows for `look <detail>`
            - the look command should defer to this method on
            the current location (if it exists) before giving up on
            finding the target.

        """
        key = key.lower()
        detail_keys = tuple(self.details.keys())

        detail = None
        if key in detail_keys:
            # exact match
            detail = self.details[key]
        else:
            # find closest match starting with key (shortest difference in length)
            lkey = len(key)
            startswith_matches = sorted(
                (
                    (detail_key, abs(lkey - len(detail_key)))
                    for detail_key in detail_keys
                    if detail_key.startswith(key)
                ),
                key=lambda tup: tup[1],
            )
            if startswith_matches:
                # use the matching startswith-detail with the shortest difference in length
                detail = self.details[startswith_matches[0][0]]

        if detail:
            detail = self._get_funcparser(looker).parse(detail)

        return detail

    return_detail = get_detail  # legacy name


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

    def look_detail(self):
        """
        Look for detail on room.
        """
        caller = self.caller
        if hasattr(self.caller.location, "get_detail"):
            detail = self.caller.location.get_detail(self.args, looker=self.caller)
            if detail:
                caller.location.msg_contents(
                    f"$You() $conj(look) closely at {self.args}.\n",
                    from_obj=caller,
                    exclude=caller,
                )
                caller.msg(detail)
                return True
        return False

    def func(self):
        """
        Handle the looking.
        """
        caller = self.caller
        if not self.args:
            target = caller.location
            if not target:
                caller.msg("You have no location to look at!")
                return
        else:
            # search, waiting to return errors so we can also check details
            target = caller.search(self.args, quiet=True)
            # if there's no target, check details
            if not target:
                # no target AND no detail means run the normal no-results message
                if not self.look_detail():
                    _AT_SEARCH_RESULT(target, caller, self.args, quiet=False)
                return
            # otherwise, run normal search result handling
            target = _AT_SEARCH_RESULT(target, caller, self.args, quiet=False)
            if not target:
                return
        desc = caller.at_look(target)
        # add the type=look to the outputfunc to make it
        # easy to separate this output in client.
        self.msg(text=(desc, {"type": "look"}), options=None)


# Custom build commands for setting seasonal descriptions
# and detailing extended rooms.


def _desc_load(caller):
    return caller.db.eveditor_target.db.desc or ""


def _desc_save(caller, buf):
    """
    Save line buffer to the desc prop. This should
    return True if successful and also report its status to the user.
    """
    roomstates = caller.db.eveditor_roomstates
    target = caller.db.eveditor_target

    if not roomstates or not hasattr(target, "add_desc"):
        # normal description
        target.db.desc = buf
    elif roomstates:
        for roomstate in roomstates:
            target.add_desc(buf, room_state=roomstate)
    else:
        target.db.desc = buf

    caller.msg("Saved.")
    return True


def _desc_quit(caller):
    caller.attributes.remove("eveditor_target")
    caller.msg("Exited editor.")


class CmdExtendedRoomDesc(default_cmds.CmdDesc):
    """
    describe an object or the current room.

    Usage:
      @desc[/switch] [<obj> =] <description>

    Switches:
      edit - Open up a line editor for more advanced editing.
      del - Delete the description of an object. If another state is given, its description
        will be deleted.
      spring||summer||autumn||winter - room description to use in respective in-game season
      <other> - room description to use with an arbitrary room state.

    Sets the description an object. If an object is not given,
    describe the current room, potentially showing any additional stateful descriptions. The room
    states only work with rooms.

    Examples:
        @desc/winter A cold winter scene.
        @desc/edit/summer
        @desc/burning This room is burning!
        @desc A normal room with no state.
        @desc/del/burning

    Rooms will automatically change season as the in-game time changes. You can
    set a specific room-state with the |wroomstate|n command.

    """

    key = "@desc"
    switch_options = None
    locks = "cmd:perm(desc) or perm(Builder)"
    help_category = "Building"

    def parse(self):
        super().parse()

        self.delete_mode = "del" in self.switches
        self.edit_mode = not self.delete_mode and "edit" in self.switches

        self.object_mode = "=" in self.args

        # all other switches are names of room-states
        self.roomstates = [state for state in self.switches if state not in ("edit", "del")]

    def edit_handler(self):
        if self.rhs:
            self.msg("|rYou may specify a value, or use the edit switch, but not both.|n")
            return
        if self.args:
            obj = self.caller.search(self.args)
        else:
            obj = self.caller.location or self.msg("|rYou can't describe oblivion.|n")
        if not obj:
            return

        if not (obj.access(self.caller, "control") or obj.access(self.caller, "edit")):
            self.caller.msg(f"You don't have permission to edit the description of {obj.key}.")
            return

        self.caller.db.eveditor_target = obj
        self.caller.db.eveditor_roomstates = self.roomstates
        # launch the editor
        EvEditor(
            self.caller,
            loadfunc=_desc_load,
            savefunc=_desc_save,
            quitfunc=_desc_quit,
            key="desc",
            persistent=True,
        )
        return

    def show_stateful_descriptions(self):
        location = self.caller.location
        room_states = location.room_states
        season = location.get_season()
        time_of_day = location.get_time_of_day()
        stateful_descs = location.all_desc()

        output = [
            f"Room {location.get_display_name(self.caller)} "
            f"Season: {season}. Time: {time_of_day}. "
            f"States: {', '.join(room_states) if room_states else 'None'}"
        ]
        other_active = False
        for state, desc in stateful_descs.items():
            if state is None:
                continue
            if state == season or state in room_states:
                output.append(f"Room state |w{state}|n |g(active)|n:\n{desc}")
                other_active = True
            else:
                output.append(f"Room state |w{state}|n:\n{desc}")

        active = " |g(active)|n" if not other_active else ""
        output.append(f"Room state |w(default)|n{active}:\n{location.db.desc}")

        sep = "\n" + "-" * 78 + "\n"
        self.caller.msg(sep.join(output))

    def func(self):
        caller = self.caller
        if not self.args and "edit" not in self.switches and "del" not in self.switches:
            if caller.location:
                # show stateful descs on the room
                self.show_stateful_descriptions()
                return
            else:
                caller.msg("You have no location to describe!")
                return

        if self.edit_mode:
            self.edit_handler()
            return

        if self.object_mode:
            # We are describing an object
            target = caller.search(self.lhs)
            if not target:
                return
            desc = self.rhs or ""
        else:
            # we are describing the current room
            target = caller.location or self.msg("|rYou don't have a location to describe.|n")
            if not target:
                return
            desc = self.args

        roomstates = self.roomstates
        if target.access(self.caller, "control") or target.access(self.caller, "edit"):
            if not roomstates or not hasattr(target, "add_desc"):
                # normal description
                target.db.desc = desc
            elif roomstates:
                for roomstate in roomstates:
                    if self.delete_mode:
                        target.remove_desc(roomstate)
                        caller.msg(f"The {roomstate}-description was deleted, if it existed.")
                    else:
                        target.add_desc(desc, room_state=roomstate)
                        caller.msg(
                            f"The {roomstate}-description was set on"
                            f" {target.get_display_name(caller)}."
                        )
            else:
                target.db.desc = desc
                caller.msg(f"The description was set on {target.get_display_name(caller)}.")
        else:
            caller.msg(
                "You don't have permission to edit the description "
                f"of {target.get_display_name(caller)}."
            )


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
                self.msg(
                    f"|rThe room {location.get_display_name(self.caller)} doesn't have any"
                    " details.|n"
                )
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

        method = "add_detail" if "del" not in self.switches else "remove_detail"
        if not hasattr(location, method):
            self.caller.msg("Details cannot be set on %s." % location)
            return
        for key in self.lhs.split(";"):
            # loop over all aliases, if any (if not, this will just be
            # the one key to loop over)
            getattr(location, method)(key, self.rhs)
        if "del" in self.switches:
            self.caller.msg(f"Deleted detail '{self.lhs}', if it existed.")
        else:
            self.caller.msg(f"Set detail '{self.lhs}': '{self.rhs}'")


class CmdExtendedRoomState(default_cmds.MuxCommand):
    """
    Toggle and view room state for the current room.

    Usage:
        @roomstate [<roomstate>]

    Examples:
        @roomstate spring
        @roomstate burning
        @roomstate burning      (a second time toggles it off)

    If the roomstate was already set, it will be disabled. Use
    without arguments to see the roomstates on the current room.

    """

    key = "@roomstate"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def parse(self):
        super().parse()
        self.room = self.caller.location
        if not self.room or not hasattr(self.room, "room_states"):
            self.caller.msg("You have no current location, or it doesn't support room states.")
            raise InterruptCommand()

        self.room_state = self.args.strip().lower()

    def func(self):
        caller = self.caller
        room = self.room
        room_state = self.room_state

        if room_state:
            # toggle room state
            if room_state in room.room_states:
                room.remove_room_state(room_state)
                caller.msg(f"Cleared room state '{room_state}' from this room.")
            else:
                room.add_room_state(room_state)
                caller.msg(f"Added room state '{room_state}' to this room.")
        else:
            # view room states
            room_states = list_to_string(
                [f"'{state}'" for state in room.room_states] if room.room_states else ("None",)
            )
            caller.msg(
                "Room states (not counting automatic time/season) on"
                f" {room.get_display_name(caller)}:\n {room_states}"
            )


class CmdExtendedRoomGameTime(default_cmds.MuxCommand):
    """
    Check the game time.

    Usage:
        time

    Shows the current in-game time and season.

    """

    key = "time"
    locks = "cmd:all()"
    help_category = "General"

    def parse(self):
        location = self.caller.location
        if (
            not location
            or not hasattr(location, "get_time_of_day")
            or not hasattr(location, "get_season")
        ):
            self.caller.msg("No location available - you are outside time.")
            raise InterruptCommand()
        self.location = location

    def func(self):
        location = self.location

        season = location.get_season()
        timeslot = location.get_time_of_day()

        prep = "an" if season == "autumn" else "a"
        self.caller.msg(f"It's {prep} {season} day, in the {timeslot}.")


# CmdSet for easily install all commands


class ExtendedRoomCmdSet(CmdSet):
    """
    Groups the extended-room commands.

    """

    def at_cmdset_creation(self):
        self.add(CmdExtendedRoomLook())
        self.add(CmdExtendedRoomDesc())
        self.add(CmdExtendedRoomDetail())
        self.add(CmdExtendedRoomState())
        self.add(CmdExtendedRoomGameTime())
