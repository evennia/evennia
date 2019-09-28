"""
Base objects for the Evscaperoom contrib.


The object class itself provide the actions possible to use on that object.
This makes these objects suitable for use with multi-inheritance. For example,
to make an object both possible to smell and eat or drink, find the appropriate
parents in this module and make an object like this:

class Apple(Edible, Smellable):

    def at_drink(self, caller):
        # ...

    def at_smell(self, caller):
        # ...

Various object parents could be more complex, so read the class for more info.

Available parents:

- EvscapeRoomObject - parent class for all Evscaperoom entities (also the room itself)
- Feelable
- Listenable
- Smellable
- Rotatable
- Openable
- Readable
- IndexReadable  (like a lexicon you have to give a search term in)
- Movable
- Edible
- Drinkable
- Usable
- Insertable  (can be inserted into a target)
- Combinable  (combines with another object to create a new one)
- Mixable     (used for mixing potions into it)
- HasButtons  (an object with buttons on it)
- CodeInput   (code locks)
- Sittable    (can be sat on)
- Liable      (can be lied down on)
- Kneeable    (can be kneed down on)
- Climbable   (can be climbed on)
- Positionable (supports sit/lie/knee/climb at once)

"""
import re
import inspect
from evennia import DefaultObject
from evennia.utils.utils import list_to_string, wrap
from .utils import create_evscaperoom_object
from .utils import parse_for_perspectives, parse_for_things


class EvscaperoomObject(DefaultObject):
    """
    Default object base for all objects related to the contrib.

    """

    # these will be automatically filtered out by self.parse for
    # focus-commands using arguments like (`combine [with] object`)
    # override this per-class as necessary.
    action_prepositions = ("in", "with", "on", "into", "to")

    # this mapping allows for prettier descriptions of our current
    # position
    position_prep_map = {"sit": "sitting", "kneel": "kneeling", "lie": "lying", "climb": "standing"}

    def at_object_creation(self):
        """
        Called once when object is first created.

        """
        # state flags (setup/reset for each state).
        self.db.tagcategory = None
        self.db.flags = {}

        self.db.desc = "Nothing of interest."

        self.db.positions = {}

    _tagcategory = None

    @property
    def tagcategory(self):
        if not self._tagcategory:
            self._tagcategory = (
                self.location.db.tagcategory if self.location else self.db.tagcategory
            )
        return self._tagcategory

    @property
    def room(self):
        return self.location or self

    @property
    def roomstate(self):
        return self.room.statehandler.current_state

    def next_state(self, statename=None):
        """
        Helper to have the object switch the room to next state

        Args:
            statename (str, optional): If given, move to this
                state next. Otherwise use the default next-state
                of the current state.

        """
        self.room.statehandler.next_state(next_state=statename)

    def set_flag(self, flagname):
        "Set flag on object"
        self.db.flags[flagname] = True

    def unset_flag(self, flagname):
        "Unset flag on object"
        if flagname in self.db.flags:
            del self.db.flags[flagname]

    def check_flag(self, flagname):
        "Check if flag is set on this object"
        return self.db.flags.get(flagname, False)

    def set_character_flag(self, char, flagname, value=True):
        "Set flag on character"
        flags = char.attributes.get(flagname, category=self.tagcategory, default={})
        flags[flagname] = value
        char.attributes.add(flagname, flags, category=self.tagcategory)

    def unset_character_flag(self, char, flagname):
        "Set flag on character"
        flags = char.attributes.get(flagname, category=self.tagcategory, default={})
        if flagname in flags:
            flags.pop(flagname, None)
            char.attributes.add(flagname, flags, category=self.tagcategory)

    def check_character_flag(self, char, flagname):
        "Check if flag is set on character"
        flags = char.attributes.get(flagname, category=self.tagcategory, default={})
        return flags.get(flagname, False)

    def msg_room(self, caller, string, skip_caller=False):
        """
        Message everyone in the room with a message that is parsed for
        ~first/third person grammar, as well as for *thing markers.

        Args:
            caller (Object or None): Sender of the message. If None, there
                is no sender.
            string (str): Message to parse and send to the room.
            skip_caller (bool): Send to everyone except caller.

        Notes:
            Messages sent by this method will be tagged with a type of
            'your_action' and `others_action`. This is an experiment for
            allowing users of e.g. the webclient to redirect messages to
            differnt windows.

        """
        you = caller.key if caller else "they"
        first_person, third_person = parse_for_perspectives(string, you=you)
        for char in self.room.get_all_characters():
            options = char.attributes.get("options", category=self.room.tagcategory, default={})
            style = options.get("things_style", 2)
            if char == caller:
                if not skip_caller:
                    txt = parse_for_things(first_person, things_style=style)
                    char.msg((txt, {"type": "your_action"}))
            else:
                txt = parse_for_things(third_person, things_style=style)
                char.msg((txt, {"type": "others_action"}))

    def msg_char(self, caller, string, client_type="your_action"):
        """
        Send message only to caller (not to the room at large)

        """
        # we must clean away markers
        first_person, _ = parse_for_perspectives(string)
        options = caller.attributes.get("options", category=self.room.tagcategory, default={})
        style = options.get("things_style", 2)
        txt = parse_for_things(first_person, things_style=style)
        caller.msg((txt, {"type": client_type}))

    def msg_system(self, message, target=None, borders=True):
        """
        Send a 'system message' by using the State.msg function.
        """
        self.room.state.msg(message, target=target, borders=borders)

    def get_position(self, caller):
        """
        Get position of caller on this object (like lying, sitting, kneeling,
        standing). See the Positionable child class.

        Args:
            caller (Object): The one position we seek.

        Returns:
            obj, pos (Object, str): The object we have a position relative to,
                as well as the name of that position (lying, sitting, kneeling,
                standing).  If these are None, it means we are standing on the
                floor.

        """
        pos = caller.attributes.get("position", category=self.tagcategory)
        if pos:
            obj, old_position = pos
            return obj, old_position
        return None, None

    def set_position(self, caller, new_position):
        """
        Set position of caller (like lying, sitting, kneeling, standing)
        on this object. See Positionable child class.

        Args:
            caller (Object): The one positioning themselves on this object.
            new_position (str, None): One of "lie", "kneel", "sit" or "stand".
                If `None`, remove position (character stands normally on the
                floor).

        """
        if new_position is None:
            # reset position
            caller.attributes.remove("position", category=self.tagcategory)
            if caller in self.db.positions:
                del self.db.positions[caller]
        else:
            # set a new position on this object
            position = (self, new_position)
            caller.attributes.add("position", position, category=self.tagcategory)
            self.db.positions[caller] = new_position

    def at_focus(self, caller):
        """
        Called when somone is focusing on this object.

        Args:
            caller (Character): The one doing the focusing.

        """
        self.msg_char(caller, caller.at_look(self), client_type="look")

    def at_unfocus(self, caller):
        """
        Called when focus leaves this object. Note that more than one caller
        may be focusing on the object at the same time, so we should not change
        the state of the object itself here!

        Args:
            caller (Character): The one doing the unfocusing.

        """
        pass

    def at_speech(self, speaker, action):
        """
        We don't use the default at_say hook since we handle the send logic in
        the command. This is only meant to trigger eventual game-events when
        speaking to an object or the room.

        Args:
            speaker (Character): The one speaking.
            action (str): One of 'say', 'whisper' or 'shout'

        """
        pass

    def parse(self, args):
        """
        Simple parser of focus arguments starting with a preposition,
        like 'combine with <object>' <- we want to strip out the preposition
        here.

        """
        args = re.sub(
            r"|".join(r"^{}\s".format(prep) for prep in self.action_prepositions), "", args
        )
        return args

    def get_cmd_signatures(self):
        """
        This allows the object to return more detailed call signs
        for each of their at_focus_* methods. This is useful for
        things like detailed arguments (only 'move' but 'move left/right')

        Returns:
            callsigns (list, None): List of strings to inject into the
                available action list produced by `self.get_help`. If `None`,
                automatically find actions based on the method names.
            custom_helpstr (str): This should be the help text for
                the command with a marker `{callsigns}` for where to
                inject the list of callsigns.

        """
        command_signatures = []
        helpstr = ""
        methods = inspect.getmembers(self, predicate=inspect.ismethod)
        for name, method in methods:
            if name.startswith("at_focus_"):
                command_signatures.append(name[9:])
        command_signatures = sorted(command_signatures)

        if len(command_signatures) == 1:
            helpstr = f"It looks like {self.key} may be " "suitable to {callsigns}."
        else:
            helpstr = (
                f"At first glance, it looks like {self.key} might be " "suitable to {callsigns}."
            )
        return command_signatures, helpstr

    def get_short_desc(self, full_desc):
        """
        Extract the first sentence from the desc and use as the short desc.

        """
        mat = re.match(r"(^.*?[.?!])", full_desc.strip(), re.M + re.U + re.I + re.S)
        if mat:
            return mat.group(0).strip()
        return full_desc

    def get_help(self, caller):
        """
        Get help about this object. By default we return a
        listing of all actions you can do on this object.

        """
        # custom-created signatures. We don't sort these
        command_signatures, helpstr = self.get_cmd_signatures()

        callsigns = list_to_string(["*" + sig for sig in command_signatures], endsep="or")

        # parse for *thing markers (use these as items)
        options = caller.attributes.get("options", category=self.room.tagcategory, default={})
        style = options.get("things_style", 2)

        helpstr = helpstr.format(callsigns=callsigns)
        helpstr = parse_for_things(helpstr, style, clr="|w")
        return wrap(helpstr, width=80)

    # Evennia hooks

    def return_appearance(self, looker, **kwargs):
        """ Could be modified per state. We generally don't worry about the
        contents of the object by default.

        """
        # accept a custom desc
        desc = kwargs.get("desc", self.db.desc)

        if kwargs.get("unfocused", False):
            # use the shorter description
            focused = ""
            desc = self.get_short_desc(desc)
            helptxt = ""
        else:
            focused = " |g(examining |G- use '|gex|G' again to look away. See also '|ghelp|G')|n"
            helptxt = kwargs.get("helptxt", f"\n\n({self.get_help(looker)})")

        obj, pos = self.get_position(looker)
        pos = (
            f" |w({self.position_prep_map[pos]} on " f"{obj.get_display_name(looker)})"
            if obj
            else ""
        )

        return f" ~~ |y{self.get_display_name(looker)}|n{focused}{pos}|n ~~\n\n{desc}{helptxt}"


class Feelable(EvscaperoomObject):
    """
    Any object that you can feel the surface of.

    """

    def at_focus_feel(self, caller, **kwargs):
        self.msg_char(caller, f"You feel *{self.key}.")


class Listenable(EvscaperoomObject):
    """
    Any object one can listen to.

    """

    def at_focus_listen(self, caller, **kwargs):
        self.msg_char(caller, f"You listen to *{self.key}")


class Smellable(EvscaperoomObject):
    """
    Any object you can smell.

    """

    def at_focus_smell(self, caller, **kwargs):
        self.msg_char(caller, f"You smell *{self.key}.")


class Rotatable(EvscaperoomObject):
    """
    Any object that you can lift up and look at from different angles

    """

    rotate_flag = "rotatable"
    start_rotatable = True

    def at_object_creation(self):
        super().at_object_creation()

        if self.start_rotatable:
            self.set_flag("rotatable")

    def at_focus_rotate(self, caller, **kwargs):

        if self.check_flag("rotatable"):
            self.at_rotate(caller)
        else:
            self.at_cannot_rotate(caller)

    at_focus_turn = at_focus_rotate

    def at_rotate(self, caller):
        self.msg_char(caller, f"You turn *{self.key} around.")

    def at_cannot_rotate(self, caller):
        self.msg_char(caller, f"You cannot rotate this.")


class Openable(EvscaperoomObject):
    """
    Any object that you can open/close. It's lockable with
    a flag.

    """

    # this flag must be set for item to open. None for unlocked.
    unlock_flag = "unlocked"
    open_flag = "open"
    # start this item in the opened/unlocked state
    start_open = False

    def at_object_creation(self):
        super().at_object_creation()
        if self.start_open:
            self.set_flag(self.unlock_flag)
            self.set_flag(self.open_flag)

    def at_focus_open(self, caller, **kwargs):
        if self.check_flag(self.open_flag):
            self.at_already_open(caller)
        elif self.unlock_flag is None or self.check_flag(self.unlock_flag):
            self.set_flag(self.open_flag)
            self.at_open(caller)
        else:
            self.at_locked(caller)

    def at_focus_close(self, caller, **kwargs):
        if not self.check_flag(self.open_flag):
            self.at_already_closed(caller)
        else:
            self.unset_flag(self.open_flag)
            self.at_close(caller)

    def at_open(self, caller):
        self.msg_char(caller, f"You open *{self.key}")

    def at_already_open(self, caller):
        self.msg_char(caller, f"{self.key.capitalize()} is already open.")

    def at_locked(self, caller):
        self.msg_char(caller, f"{self.key.capitalize()} won't open.")

    def at_close(self, caller):
        self.msg_char(caller, f"You close *{self.key}.")

    def at_already_closed(self, caller):
        self.msg_char(caller, f"{self.key.capitalize()} is already closed.")


class Readable(EvscaperoomObject):
    """
    Any object that you can read from. This is controlled
    from a flag.

    """

    # this must be set to be able to read. None to
    # always be able to read.

    read_flag = "readable"
    start_readable = True

    def at_object_creation(self):
        super().at_object_creation()
        if self.start_readable:
            self.set_flag(self.read_flag)

    def at_focus_read(self, caller, **kwargs):

        if self.read_flag is None or self.check_flag(self.read_flag):
            self.at_read(caller)
        else:
            self.at_cannot_read(caller)

    def at_read(self, caller, *args, **kwargs):
        self.msg_char(caller, f"You read from *{self.key}.")

    def at_cannot_read(self, caller, *args, **kwargs):
        self.msg_char(caller, "You cannot understand a thing!")


class IndexReadable(Readable):
    """
    Any object for which you need to specify a key/index to get a given result
    back. For example a lexicon or book where you enter a topic or a page
    number to see what's to be read on that page.
    """

    # keys should be lower-key
    index = {"page1": "This is page1", "page2": "This is page2", "page two": "page2"}  # alias

    def at_focus_read(self, caller, **kwargs):

        topic = kwargs.get("args").strip().lower()

        entry = self.index.get(topic, None)

        if entry is None or not self.check_flag(self.read_flag):
            self.at_cannot_read(caller, topic)
        else:
            if entry in self.index:
                # an alias-reroute
                entry = self.index[entry]
            self.at_read(caller, topic, entry)

    def get_cmd_signatures(self):
        txt = (
            f"You don't have the time to read this from beginning to end. "
            "Use *read <topic> to look up something in particular."
        )
        return [], txt

    def at_cannot_read(self, caller, topic, *args, **kwargs):
        self.msg_char(caller, f"Cannot find an entry on '{topic}'.")

    def at_read(self, caller, topic, entry, *args, **kwargs):
        self.msg_char(caller, f"You read about '{topic}':\n{entry.strip()}")


class Movable(EvscaperoomObject):
    """
    Any object that can be moved from one place to another
    or in one direction or another.

    Once moved to a given position, the object's state will
    change.

    """

    # these are the possible locations (or directions) to move to
    # name: callable
    move_positions = {"left": "at_left", "right": "at_right"}
    start_position = "left"

    def at_object_creation(self):
        super().at_object_creation()
        self.db.position = self.start_position

    def get_cmd_signatures(self):
        txt = "Looks like you can {callsigns}."
        return ["move", "push", "shove left/right"], txt

    def at_focus_move(self, caller, **kwargs):
        pos = self.parse(kwargs["args"])
        callfunc_name = self.move_positions.get(pos)

        if callfunc_name:
            if self.db.position == pos:
                self.at_already_moved(caller, pos)
            else:
                self.db.position = pos
                getattr(self, callfunc_name)(caller)
        else:
            self.at_cannot_move(caller)

    at_focus_shove = at_focus_move
    at_focus_push = at_focus_move

    def at_cannot_move(self, caller):
        self.msg_char(caller, "That does not work.")

    def at_already_moved(self, caller, position):
        self.msg_char(caller, f"You already moved *{self.key} to the {position}.")

    def at_left(self, caller):
        self.msg_char(caller, f"You move *{self.key} left")

    def at_right(self, caller):
        self.msg_char(caller, f"You move *{self.key} right")


class BaseConsumable(EvscaperoomObject):
    """
    Any object that is consumable in some way. This acts as an
    abstract parent.

    This sets a flag that
    is unique for each person consuming, allowing it to e.g. only
    be consumed once (don't support multi-uses here, that's left for
    a custom object if needed).

    """

    consume_flag = "consume"
    # may only consume once
    one_consume_only = True

    def handle_consume(self, caller, action, **kwargs):
        """
        Wrap this by the at_focus method
        """
        if self.one_consume_only and self.has_consumed(caller):
            self.at_already_consumed(caller, action)
        else:
            self.has_consumed(caller, True)
            self.at_consume(caller, action)

    def has_consumed(self, caller, setflag=False):
        "Check if caller already consumed at least once"
        flag = f"{self.consume_flag}#{caller.id}"
        if setflag:
            self.set_flag(flag)
        else:
            return self.check_flag(flag)

    def at_consume(self, caller, action):
        if hasattr(self, f"at_{action}"):
            getattr(self, f"at_{action}")(caller)
        else:
            self.msg_char(caller, f"You {action} *{self.key}.")

    def at_already_consumed(self, caller, action):
        self.msg_char(caller, f"You can't {action} any more.")


class Edible(BaseConsumable):
    """
    Any object specifically possible to eat.

    """

    consume_flag = "eat"

    def at_focus_eat(self, caller, **kwargs):
        super().handle_consume(caller, "eat", **kwargs)


class Drinkable(BaseConsumable):
    """
    Any object specifically possible to drink.

    """

    consume_flag = "drink"

    def at_focus_drink(self, caller, **kwargs):
        super().handle_consume(caller, "drink", **kwargs)

    def at_focus_sip(self, caller, **kwargs):
        super().handle_consume(caller, "sip", **kwargs)

    def at_consume(self, caller, action):
        self.msg_char(caller, f"You {action} from *{self.key}.")

    def at_already_consumed(self, caller, action):
        self.msg_char(caller, f"You can't drink any more.")


class BaseApplicable(EvscaperoomObject):
    """
    Any object that can be applied/inserted/used on another object in some way.
    This acts an an abstract base class.

    """

    # the target object this is to be used with must
    # have this flag. It'll likely be unique to this
    # object combination.
    target_flag = "applicable"

    def handle_apply(self, caller, action, **kwargs):
        """
        Wrap this with the at_focus methods in the child classes

        """
        args = self.parse(kwargs["args"])
        if not args:
            self.msg_char(caller, "You need to specify a target.")
            return
        obj = caller.search(args)
        if not obj:
            return
        try:
            can_apply = obj.check_flag(self.target_flag)
        except AttributeError:
            can_apply = False
        if can_apply:
            self.at_apply(caller, action, obj)
        else:
            self.at_cannot_apply(caller, action, obj)

    def at_apply(self, caller, action, obj):
        self.msg_char(caller, f"You {action} *{self.key} to {obj.key}.")

    def at_cannot_apply(self, caller, action, obj):
        self.msg_char(caller, f"You cannot {action} *{self.key} to {obj.key}.")


class Usable(BaseApplicable):
    """
    Any object that can be used with another object.

    """

    target_flag = "usable"

    def at_focus_use(self, caller, **kwargs):
        super().handle_apply(caller, "use", **kwargs)

    def at_apply(self, caller, action, obj):
        self.msg_char(caller, f"You {action} *{self.key} with {obj.key}")

    def at_cannot_apply(self, caller, action, obj):
        self.msg_char(caller, f"You cannot {action} *{self.key} with {obj.key}.")


class Insertable(BaseApplicable):
    """
    Any object that can be inserted into another object.

    This would cover a key, for example.

    """

    # this would likely be a custom name
    target_flag = "insertable"

    def at_focus_insert(self, caller, **kwargs):
        super().handle_apply(caller, "insert", **kwargs)

    def at_apply(self, caller, action, obj):
        self.msg_char(caller, f"You {action} *{self.key} in {obj.key}.")

    def get_cmd_signatures(self):
        txt = "You can use this object to {callsigns}"
        return ["insert in <object>"], txt

    def at_cannot_apply(self, caller, action, obj):
        self.msg_char(caller, f"You cannot {action} *{self.key} in {obj.key}.")


class Combinable(BaseApplicable):
    """
    Any object that combines with another object to create
    a new one.

    """

    # the other object must have this flag to be able to be combined
    # (this is likely unique for a given combination)
    target_flag = "combinable"
    # create-dict to pass into the create_object for the
    # new "combined" object.
    new_create_dict = {
        "typeclass": "evscaperoom.objects.Combinable",
        "key": "sword",
        "aliases": ["combined"],
    }
    # if set, destroy the two components used to make the new one
    destroy_components = True

    def at_focus_combine(self, caller, **kwargs):
        super().at_focus_apply(caller, **kwargs)

    def get_cmd_signatures(self):
        txt = "It looks like this should work: {callsigns}"
        return ["combine <object>"], txt

    def at_cannot_apply(self, caller, action, obj):
        self.msg_char(caller, f"You cannot {action} *{self.key} with {obj.key}.")

    def at_apply(self, caller, action, other_obj):
        create_dict = self.new_create_dict
        if "location" not in create_dict:
            create_dict["location"] = self.location
        new_obj = create_evscaperoom_object(**create_dict)
        if new_obj and self.destroy_components:
            self.msg_char(
                caller, f"You combine *{self.key} with {other_obj.key} to make {new_obj.key}!"
            )
            other_obj.delete()
            self.delete()


class Mixable(EvscaperoomObject):
    """
    Any object into which you can mix ingredients (such as when
    mixing a potion). This offers no actions on its own, instead
    the ingredients should be 'used' with this object in order
    mix, calling at_mix when they do.
    """

    # ingredients can check for this before they allow to mix at all
    mixer_flag = "mixer"
    # ingredients must have these flags and this order
    ingredient_recipe = ["ingredient1", "ingredient2", "ingredient3"]

    def at_object_creation(self):
        super().at_object_creation()
        self.set_flag(self.mixer_flag)
        # this holds the ingredients as they are added
        self.db.ingredients = []

    def check_mixture(self):
        "check so mixture is correct, returning True/False."
        ingredients = list(self.db.ingredients)
        for iflag, flag in enumerate(self.ingredient_recipe):
            try:
                if not ingredients[iflag].check_flag(flag):
                    return False
            except (IndexError, AttributeError):
                return False
        # we only get here if all ingredients have the right flags in the right
        # order
        return True

    def handle_mix(self, caller, ingredient, **kwargs):
        """
        Add ingredient object to mixture.

        Called by the mixing ingredient. We assume the ingredient has already
        checked to make sure they allow themselves to be mixed into an object
        with this mixer_flag.

        """
        self.db.ingredients.append(ingredient)
        # normal mix
        self.at_mix(caller, ingredient, **kwargs)

        if len(self.db.ingredients) >= len(self.ingredient_recipe):
            # we have enough, check if it matches recipe

            if self.check_mixture():
                self.at_mix_success(caller, ingredient, **kwargs)
            else:
                self.room.log(
                    f"{self.name} mix failure: Tried {' + '.join([ing.key for ing in self.db.ingredients if ing])}"
                )
                self.db.ingredients = []
                self.at_mix_failure(caller, ingredient, **kwargs)

    def at_mix(self, caller, ingredient, **kwargs):
        self.msg_room(caller, f"~You ~mix {ingredient.key} into *{self.key}.")

    def at_mix_failure(self, caller, ingredient, **kwargs):
        self.msg_room(caller, f"This mix doesn't work. ~You ~clean and start over.")

    def at_mix_success(self, caller, ingredient, **kwargs):
        self.msg_room(caller, f"~You successfully ~complete the mix!")


class HasButtons(EvscaperoomObject):
    """
    Any object with buttons to push/press

    """

    # mapping keys/aliases to calling method
    buttons = {
        "green button": "at_green_button",
        "green": "at_green_button",
        "red button": "at_red_button",
        "red": "at_red_button",
    }

    def get_cmd_signatures(self):
        helptxt = (
            "It looks like you should be able to operate "
            f"*{self.key} by means of "
            "{callsigns}."
        )
        return ["push", "press red/green button"], helptxt

    def at_focus_press(self, caller, **kwargs):
        arg = self.parse(kwargs["args"])
        callfunc_name = self.buttons.get(arg)
        if callfunc_name:
            getattr(self, callfunc_name)(caller)
        else:
            self.at_nomatch(caller)

    at_focus_push = at_focus_press

    def at_nomatch(self, caller):
        self.msg_char(caller, "That does not seem right.")

    def at_green_button(self, caller):
        self.msg_char(caller, "You press the green button.")

    def at_red_button(self, caller):
        self.msg_char(caller, "You press the red button.")


class CodeInput(EvscaperoomObject):
    """
    Any object where you can enter a code of some sort
    to have an effect happen.

    """

    # the code of this
    code = "PASSWORD"
    code_hint = "eight letters A-Z"
    case_insensitive = True
    # code locked no matter what is input
    infinitely_locked = False

    def at_focus_code(self, caller, **kwargs):

        args = self.parse(kwargs["args"].strip())

        if not args:
            self.at_no_code(caller)
            return
        if self.infinitely_locked:
            code_correct = False
        elif self.case_insensitive:
            code_correct = args.upper() == self.code.upper()
        else:
            code_correct = args == self.code

        if code_correct:
            self.at_code_correct(caller, args)
        else:
            self.at_code_incorrect(caller, args)

    def get_cmd_signatures(self):
        helptxt = "Looks like you need to use {callsigns}."
        return ["code <code>"], helptxt

    def at_no_code(self, caller):
        self.msg_char(caller, f"Looks like you need to enter |w{self.code_hint}|n.")

    def at_code_correct(self, caller, code_tried):
        self.msg_char(caller, "That's the right code!")

    def at_code_incorrect(self, caller, code_tried):
        self.msg_char(caller, f"That's not the right code (need {self.code_hint}).")


class BasePositionable(EvscaperoomObject):
    """
    Any object a character can be positioned on. This is meant as an
    abstract parent.

    This is a little special since a char can only have one position at a
    time and must therefore be aware of the other 'positional' actions
    any object may support (otherwise you may end up sitting/standing/etc on
    more than one object at once!)

    We set a Attribute (obj, position) on the caller to indicate that
    they have a position on an object. This is necessary so as to not have
    the caller sit on more than one sittable object at a time, for example. The
    'positions' Attribute on this object holds a mapping of who is sitting
    lying etc on this object.  We don't add a limit to how many chars could
    have a position on an object - it's not realistic, but this goes with the
    philosophy that one character should not be able to block others if they go
    inactive etc.

    This state is also tied to the general 'stand' command, which should return
    the player to the normal standing state regardless of if they focus on this
    object or not.

    """

    def at_object_creation(self):
        super().at_object_creation()
        # mapping {object: position}.
        self.db.positions = {}

    def handle_position(self, caller, new_pos, **kwargs):
        """
        Wrap this with the at_focus_ method of the child class.

        """
        old_obj, old_pos = self.get_position(caller)
        if old_obj:
            if old_obj is self:
                if old_pos == new_pos:
                    self.at_again_position(caller, new_pos)
                else:
                    self.set_position(caller, new_pos)
                    self.at_position(caller, new_pos)
            else:
                self.at_cannot_position(caller, new_pos, old_obj, old_pos)
        else:
            self.set_position(caller, new_pos)
            self.at_position(caller, new_pos)

    def at_cannot_position(self, caller, position, old_obj, old_pos):
        self.msg_char(
            caller,
            f"You can't; you are currently {self.position_prep_map[old_pos]} on *{old_obj.key} "
            "(better |wstand|n first).",
        )

    def at_again_position(self, caller, position):
        self.msg_char(
            caller, f"But you are already {self.position_prep_map[position]} on *{self.key}?"
        )

    def at_position(self, caller, position):
        self.msg_room(caller, f"~You ~{position} on *{self.key}.")


class Sittable(BasePositionable):
    """
    Any object you can sit on.

    """

    def at_focus_sit(self, caller, **kwargs):
        super().handle_position(caller, "sit", **kwargs)


class Liable(BasePositionable):
    """
    Any object you can lie down on.

    """

    def at_focus_lie(self, caller, **kwargs):
        super().handle_position(caller, "lie", **kwargs)


class Kneelable(BasePositionable):
    """
    Any object you can kneel on.

    """

    def at_focus_kneel(self, caller, **kwargs):
        super().handle_position(caller, "kneel", **kwargs)


class Climbable(BasePositionable):
    """
    Any object you can climb up to stand on. We name this
    'climb' so as to not collide with the general 'stand'
    command, which resets your position.

    """

    def at_focus_climb(self, caller, **kwargs):
        super().handle_position(caller, "climb", **kwargs)


class Positionable(Sittable, Liable, Kneelable, Climbable):
    """
    An object on which you can position yourself in one of the
    supported ways (sit, lie, kneel or climb)

    """

    def get_cmd_signatures(self):
        txt = "It looks like you can {callsigns} on it."
        return ["sit", "lie", "kneel", "climb"], txt
