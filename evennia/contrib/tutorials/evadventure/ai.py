"""
NPC AI module for EvAdventure (WIP)

This implements a simple state machine for NPCs to follow.

The AIHandler class is stored on the NPC object and is queried by the game loop to determine what
the NPC does next. This leads to the calling of one of the relevant state methods on the NPC, which
is where the actual logic for the NPC's behaviour is implemented. Each state is responsible for
switching to the next state when the conditions are met.

The AIMixin class is a mixin that can be added to any object that needs AI. It provides the `.ai`
reference to the AIHandler and a few basic `ai_*` methods for basic AI behaviour.


Example usage:

```python
from evennia import create_object
from .npc import EvadventureNPC
from .ai import AIMixin

class MyMob(AIMixin, EvadventureNPC):
    pass

mob = create_object(MyMob, key="Goblin", location=room)

mob.ai.set_state("roam")

# tick the ai whenever needed
mob.ai.run()

```

"""

import random

from evennia.utils.logger import log_trace
from evennia.utils.utils import lazy_property

from .enums import Ability
from .utils import random_probability


class AIHandler:

    attribute_name = "ai_state"
    attribute_category = "ai_state"

    def __init__(self, obj):
        self.obj = obj
        self.ai_state = obj.attributes.get(
            self.attribute_name, category=self.attribute_category, default="idle"
        )

    def set_state(self, state):
        self.ai_state = state
        self.obj.attributes.add(self.attribute_name, state, category=self.attribute_category)

    def get_state(self):
        return self.ai_state

    def get_targets(self):
        """
        Get a list of potential targets for the NPC to combat.

        """
        return [obj for obj in self.obj.location.contents if hasattr(obj, "is_pc") and obj.is_pc]

    def get_traversable_exits(self, exclude_destination=None):
        """
        Get a list of exits that the NPC can traverse. Optionally exclude a destination.

        Args:
            exclude_destination (Object, optional): Exclude exits with this destination.

        """
        return [
            exi
            for exi in self.obj.location.exits
            if exi.destination != exclude_destination and exi.access(self, "traverse")
        ]

    def random_probability(self, probabilities):
        """
        Given a dictionary of probabilities, return the key of the chosen probability.

        Args:
            probabilities (dict): A dictionary of probabilities, where the key is the action and the
                value is the probability of that action.

        """
        # sort probabilities from higheest to lowest, making sure to normalize them 0..1
        prob_total = sum(probabilities.values())
        sorted_probs = sorted(
            ((key, prob / prob_total) for key, prob in probabilities.items()),
            key=lambda x: x[1],
            reverse=True,
        )

        rand = random.random()
        total = 0
        for key, prob in sorted_probs:
            total += prob
            if rand <= total:
                return key

    def run(self):
        try:
            state = self.get_state()
            getattr(self.obj, f"ai_{state}")()
        except Exception:
            log_trace(f"AI error in {self.obj.name} (running state: {state})")


class AIMixin:
    """
    Mixin for adding AI to an Object. This is a simple state machine. Just add more `ai_*` methods
    to the object to make it do more things.

    In the tutorial, the handler is added directly to the Mob class, to avoid going into the details
    of multiple inheritance. In a real game, you would probably want to use a mixin like this.

    """

    @lazy_property
    def ai(self):
        return AIHandler(self)
