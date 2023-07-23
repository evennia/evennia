"""
NPC AI module for EvAdventure (WIP)

This implements a state machine for the NPCs, where it uses inputs from the game to determine what
to do next. The AI works on the concept of being 'ticks', at which point, the AI will decide to move
between different 'states', performing different 'actions' within each state until changing to
another state. The odds of changing between states and performing actions are weighted, allowing for
an AI agent to be more or less likely to perform certain actions.

The state machine is fed a dictionary of states and their transitions, and a dictionary of available
actions to choose between.
::

    {
        "states": {
            "state1": {"action1": odds, "action2": odds, ...},
            "state2": {"action1": odds, "action2": odds, ...}, ...
        }
        "transition": {
            "state1": {"state2": "odds, "state3": odds, ...},
            "state2": {"state1": "odds, "state3": odds, ...}, ...
        }
    }

The NPC class needs to look like this:
::

    class NPC(DefaultCharacter):

        # ...

        @lazy_property
        def ai(self):
            return AIHandler(self)

        def ai_roam(self, action):
            # perform the action within the current state ai.state

        def ai_hunt(self, action):
            # etc

"""

import random

from evennia.utils import logger
from evennia.utils.dbserialize import deserialize

# Some example AI structures

EMOTIONAL_AI = {
    # Non-combat AI that has different moods for conversations
    "states": {
        "neutral": {"talk_neutral": 0.9, "change_state": 0.1},
        "happy": {"talk_happy": 0.9, "change_state": 0.1},
        "sad": {"talk_sad": 0.9, "change_state": 0.1},
        "angry": {"talk_angry": 0.9, "change_state": 0.1},
    }
}

STATIC_AI = {
    # AI that just hangs around until attacked
    "states": {
        "idle": {"do_nothing": 1.0},
        "combat": {"attack": 0.9, "stunt": 0.1},
    }
}

ROAM_AI = {
    # AI that roams around randomly, now and then stopping.
    "states": {
        "idle": {"do_nothing": 0.9, "change_state": 0.1},
        "roam": {
            "move_north": 0.1,
            "move_south": 0.1,
            "move_east": 0.1,
            "move_west": 0.1,
            "wait": 0.4,
            "change_state": 0.2,
        },
        "combat": {"attack": 0.9, "stunt": 0.05, "flee": 0.05},
    },
    "transitions": {
        "idle": {"roam": 0.5, "idle": 0.5},
        "roam": {"idle": 0.1, "roam": 0.9},
    },
}

HUNTER_AI = {
    "states": {
        "hunt_roam": {
            "move_north": 0.2,
            "move_south": 0.2,
            "move_east": 0.2,
            "move_west": 0.2,
        },
        "hunt_track": {
            "track_and_move": 0.9,
            "change_state": 0.1,
        },
        "combat": {"attack": 0.8, "stunt": 0.1, "other": 0.1},
    },
    "transitions": {
        # add a chance of the hunter losing its trail
        "hunt_track": {"hunt_roam": 1.0},
    },
}


class AIHandler:
    """
    AIHandler class. This should be placed on the NPC object, and will handle the state machine,
    including transitions and actions.

    Add to typeclass with @lazyproperty:

        class NPC(DefaultCharacter):
            # ...

            @lazyproperty
            def ai(self):
                return AIHandler(self)

    """

    def __init__(self, obj):
        self.obj = obj

    def __str__(self):
        return f"AIHandler for {self.obj}. Current state: {self.state}"

    @staticmethod
    def _normalize_odds(odds):
        """
        Normalize odds to 1.0.

        Args:
            odds (list): List of odds to normalize.
        Returns:
            list: Normalized list of odds.

        """
        return [float(i) / sum(odds) for i in odds]

    @staticmethod
    def _weighted_choice(choices, odds):
        """
        Choose a random element from a list of choices, with odds.

        Args:
            choices (list): List of choices to choose from. Unordered.
            odds (list): List of odds to choose from, matching the choices list. This
                can be a list of integers or floats, indicating priority. Have odds sum
                up to 100 or 1.0 to properly represent predictable odds.
        Returns:
            object: Randomly chosen element from choices.

        """
        return random.choices(choices, odds)[0]

    @staticmethod
    def _weighted_choice_dict(choices):
        """
        Choose a random element from a dictionary of choices, with odds.

        Args:
            choices (dict): Dictionary of choices to choose from, with odds as values.
        Returns:
            object: Randomly chosen element from choices.

        """
        return AIHandler._weighted_choice(list(choices.keys()), list(choices.values()))

    @staticmethod
    def _validate_ai_dict(aidict):
        """
        Validate and normalize an AI dictionary.

        Args:
            aidict (dict): AI dictionary to normalize.
        Returns:
            dict: Normalized AI dictionary.

        """
        if "states" not in aidict:
            raise ValueError("AI dictionary must contain a 'states' key.")

        if "transitions" not in aidict:
            aidict["transitions"] = {}

        # if we have no transitions, make sure we have a transition for each state set to 0
        for state in aidict["states"]:
            if state not in aidict["transitions"]:
                aidict["transitions"][state] = {}
            for state2 in aidict["states"]:
                if state2 not in aidict["transitions"][state]:
                    aidict["transitions"][state][state2] = 0.0

        # normalize odds
        for state, actions in aidict["states"].items():
            aidict["states"][state] = AIHandler._normalize_odds(list(actions.values()))
        for state, transitions in aidict["transitions"].items():
            aidict["transitions"][state] = AIHandler._normalize_odds(list(transitions.values()))

        return aidict

    @property
    def state(self):
        """
        Return the current state of the AI.

        Returns:
            str: Current state of the AI.

        """
        return self.obj.attributes.get("ai_state", category="ai", default="idle")

    @state.setter
    def state(self, value):
        """
        Set the current state of the AI. This allows to force a state change, e.g. when starting
        combat.

        Args:
            value (str): New state of the AI.

        """
        return self.obj.attributes.add("ai_state", category="ai")

    @property
    def states(self):
        """
        Return the states dictionary for the AI.

        Returns:
            dict: States dictionary for the AI.

        """
        return self.obj.attributes.get("ai_states", category="ai", default={"idle": {}})

    @states.setter
    def states(self, value):
        """
        Set the states dictionary for the AI.

        Args:
            value (dict): New states dictionary for the AI.

        """
        return self.obj.attributes.add("ai_states", value, category="ai")

    @property
    def transitions(self):
        """
        Return the transitions dictionary for the AI.

        Returns:
            dict: Transitions dictionary for the AI.

        """
        return self.obj.attributes.get("ai_transitions", category="ai", default={"idle": []})

    @transitions.setter
    def transitions(self, value):
        """
        Set the transitions dictionary for the AI.

        Args:
            value (dict): New transitions dictionary for the AI. This will be automatically
            normalized.

        """
        for state in value.keys():
            value[state] = dict(
                zip(value[state].keys(), self._normalize_odds(value[state].values()))
            )
        return self.obj.attributes.add("ai_transitions", value, category="ai")

    def add_aidict(self, aidict):
        """
        Add an AI dictionary to the AI handler.

        Args:
            aidict (dict): AI dictionary to add.

        """
        aidict = self._validate_ai_dict(aidict)
        self.states = aidict["states"]
        self.transitions = aidict["transitions"]

    def adjust_transition_probability(self, state_start, state_end, odds):
        """
        Adjust the transition probability between two states.

        Args:
            state_start (str): State to start from.
            state_end (str): State to end at.
            odds (int): New odds for the transition.

        Note:
            This will normalize the odds across the other transitions from the starting state.

        """
        transitions = deserialize(self.transitions)
        transitions[state_start][state_end] = odds
        transitions[state_start] = dict(
            zip(
                transitions[state_start].keys(),
                self._normalize_odds(transitions[state_start].values()),
            )
        )
        self.transitions = transitions

    def get_next_state(self):
        """
        Get the next state for the AI.

        Returns:
            str: Next state for the AI.

        """
        return self._weighted_choice_dict(self.transitions[self.state])

    def get_next_action(self):
        """
        Get the next action for the AI within the current state.

        Returns:
            str: Next action for the AI.

        """
        return self._weighted_choice_dict(self.states[self.state])

    def execute_ai(self):
        """
        Execute the next ai action in the current state.

        This assumes that each available state exists as a method on the object, named
        ai_<state_name>, taking an optional argument of the next action to perform. The method
        will itself update the state or transition weights through this handler.

        Some states have in-built state transitions, via the special "change_state" action.

        """
        next_action = self.get_next_action()
        statechange = 0
        while next_action == "change_state":
            self.state = self.get_next_state()
            next_action = self.get_next_action()
            if statechange > 5:
                logger.log_err(f"AIHandler: {self.obj} got stuck in a state-change loop.")
                return

        # perform the action
        getattr(self.obj, f"ai_{self.state}")(next_action)
