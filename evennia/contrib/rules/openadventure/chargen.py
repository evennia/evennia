"""
This is a convenient module for use by chargen implementations. It gives access
to ready-made calculations (using the various rule systems) to get options and
evaluate results during the character generation process.

"""
from dataclasses import dataclass
from evennia.utils.utils import callables_from_module, inherits_from


@dataclass
class ChargenChoice:
    """
    This temporarily stores the choices done during chargen. It could be
    saved to an Attribute if persistence is required.

    """
    rulename = ""
    data = {}


class ChargenStep:
    """
    This represents the steps of a character generation. It assumes this is a
    sequential process (if chargen allows jumping that's fine too, one could
    just have a menu that points to each step).

    """
    step_name = ""
    prev_step = None
    next_step = None

    def get_help(self, *args, **kwargs):
        """
        This returns help text for this choice.

        """
        return self.__doc__.strip()

    def options(self, *args, **kwargs):
        """
        This presents the choices allowed by this step.

        Returns:
            list: A list of all applicable choices, usually as rule-classes.

        """

    def validate_input(self, inp, *args, **kwargs):
        """
        This can be used to validate free-form inputs from the user.

        Args:
            inp (str): Input from the user.
        Returns:
            bool: If input was valid or not.

        """

    def user_choice(self, *args, **kwargs):
        """
        This should be called with the user's choice. This must already be
        determined to be a valid choice at this point.

        Args:
            *args, **kwargs: Input on any form.

        Returns:
            CharacterStore: Storing the current, valid choice.

        """


class ArchetypeChoice(ChargenStep):
    """
    Choose one archetype and record all of its characteristics–or–choose two
    archetypes, halve all the characteristic's numbers, then combine their
    values.

    """
    step_name = "Choose an Archetype"
    prev_step = None
    next_step = "Choose a Race"

    def get_help(self, *args, **kwargs):
        return self.__doc__.strip()

    def options(self, *args, **kwargs):
        """
        Returns a list of Archetypes. Each Archetype class has a `.modifiers`
        dict on it with values keyed to enums for the bonuses/drawbacks of that
        archetype. The archetype's name is the class name, retrieved with `.__name__`.

        """
        from . import archetypes
        return callables_from_module(archetypes)

    def user_choice(self, choice1, choice2=None, **kwargs):
        """
        We allow one or two choices - they must be passed into this method
        together.

        Args:
            choice1 (Archetype): The first archetype choice.
            choice2 (Archetype, optional): Second choice (for dual archetype choice)

        Returns:
            ChargenStore: Holds rule_name and data; data has an additional 'name' field
                to identify the archetype (which may be a merger of two names).

        """
        data1 = choice1.modifiers
        if choice2:
            # dual-archetype - add with choice1 values and half, rounding down
            data2 = choice2.modifiers
            data = {}
            for key, value1 in data1.items():
                value2 = data2.get(key, 0)
                data[key] = int((value1 + value2) / 2)
            # add values from choice2 that was not yet covered
            data.update({key: int(value2 / 2) for key, value in data2.items() if key not in data})
            # create a new name for the dual-archetype by combining the names alphabetically
            data['name'] = "-".join(sorted((choice1.__name__, choice2.__name__)))
        else:
            data = data1
            data['name'] = choice1.__name__

        return ChargenChoice(rulename="archetype", data=data)


class RaceChoice(ChargenStep):
    """
    Choose a race/creature type that best suits this character.

    """
    step_name = "Choose a Race"
    prev_step = "Choose an Archetype"
    next_step = "Choose a race Focus"


    def options(self, *args, **kwargs):
        """
        Returns a list of races. Each Race class has the following properties:
        ::
            size = enum for small, average, large
            bodytype = enum for slim, average, stocky
            modifiers = dict of enums and bonuses/drawbacks
            foci = list of which Focus may be chosen for this race
            feats = list of which Feats may be chosen for this race

        """
        from . import races
        all_ = callables_from_module(races)
        return [race for race in all_ if inherits_from(race, race.Race)]

    def user_choice(self, choice, *args, **kwargs):
        """
        The choice should be a distinct race.

        Args:
            choice (Race): The chosen race.

        Returns:
            ChargenChoice: This will have the Race class as .data.

        """
        return ChargenChoice(rulename="race", data=choice)


class FocusChoice(ChargenStep):
    """
    Each race has three 'subtypes' or Foci available to them. This represents
    natural strengths of that race that come across more or less in different
    individuals. Each Character may pick one race-Focus to emphasize.

    """
    def options(self, race, *args, **kwargs):
        """
        To know which focus to offer, the chosen Race must be passed.

        Args:
            race (Race): The race chosen on the previous step.

        """
        return list(race.foci)

    def user_choice(self, choice, *args, **kwargs):
        """

        """



