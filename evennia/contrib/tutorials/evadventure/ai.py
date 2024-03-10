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

mob.ai.set_state("patrol")

# tick the ai whenever needed
mob.ai.run()

```

"""

import random

from evennia.utils.logger import log_trace
from evennia.utils.utils import lazy_property

from .enums import Ability


class AIHandler:
    def __init__(self, obj):
        self.obj = obj
        self.ai_state = obj.attributes.get("ai_state", category="ai_state", default="idle")

    def set_state(self, state):
        self.ai_state = state
        self.obj.attributes.add("ai_state", state, category="ai_state")

    def get_state(self):
        return self.ai_state

    def get_targets(self):
        """
        Get a list of potential targets for the NPC to attack
        """
        return [obj for obj in self.obj.location.contents if hasattr(obj, "is_pc") and obj.is_pc]

    def get_traversable_exits(self, exclude_destination=None):
        return [
            exi
            for exi in self.obj.location.exits
            if exi.destination != exclude_destination and exi.access(self, "traverse")
        ]

    def random_probability(self, probabilities):
        """
        Given a dictionary of probabilities, return the key of the chosen probability.

        """
        r = random.random()
        # sort probabilities from higheest to lowest, making sure to normalize them 0..1
        prob_total = sum(probabilities.values())
        sorted_probs = sorted(
            ((key, prob / prob_total) for key, prob in probabilities.items()),
            key=lambda x: x[1],
            reverse=True,
        )
        total = 0
        for key, prob in sorted_probs:
            total += prob
            if r <= total:
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

    """

    # combat probabilities should add up to 1.0
    combat_probabilities = {
        "hold": 0.1,
        "attack": 0.9,
        "stunt": 0.0,
        "item": 0.0,
        "flee": 0.0,
    }

    @lazy_property
    def ai(self):
        return AIHandler(self)

    def ai_idle(self):
        pass

    def ai_attack(self):
        pass

    def ai_patrol(self):
        pass

    def ai_flee(self):
        pass


class IdleMobMixin(AIMixin):
    """
    A simple mob that understands AI commands, but does nothing.

    """

    def ai_idle(self):
        pass


class AggressiveMobMixin(AIMixin):
    """
    A simple aggressive mob that can roam, attack and flee.

    """

    combat_probabilities = {
        "hold": 0.0,
        "attack": 0.85,
        "stunt": 0.05,
        "item": 0.0,
        "flee": 0.05,
    }

    def ai_idle(self):
        """
        Do nothing, but switch to attack state if a target is found.

        """
        if self.ai.get_targets():
            self.ai.set_state("attack")

    def ai_attack(self):
        """
        Manage the attack/combat state of the mob.

        """
        if combathandler := self.nbd.combathandler:
            # already in combat
            allies, enemies = combathandler.get_sides(self)
            action = self.ai.random_probability(self.combat_probabilities)

            match action:
                case "hold":
                    combathandler.queue_action({"key": "hold"})
                case "attack":
                    combathandler.queue_action({"key": "attack", "target": random.choice(enemies)})
                case "stunt":
                    # choose a random ally to help
                    combathandler.queue_action(
                        {
                            "key": "stunt",
                            "recipient": random.choice(allies),
                            "advantage": True,
                            "stunt": Ability.STR,
                            "defense": Ability.DEX,
                        }
                    )
                case "item":
                    # use a random item on a random ally
                    target = random.choice(allies)
                    valid_items = [item for item in self.contents if item.at_pre_use(self, target)]
                    combathandler.queue_action(
                        {"key": "item", "item": random.choice(valid_items), "target": target}
                    )
                case "flee":
                    self.ai.set_state("flee")

        if not (targets := self.ai.get_targets()):
            self.ai.set_state("patrol")
        else:
            target = random.choice(targets)
            self.execute_cmd(f"attack {target.key}")

    def ai_patrol(self):
        """
        Patrol, moving randomly to a new room. If a target is found, switch to attack state.

        """
        if targets := self.ai.get_targets():
            self.ai.set_state("attack")
            self.execute_cmd(f"attack {random.choice(targets).key}")
        else:
            exits = self.ai.get_traversable_exits()
            if exits:
                exi = random.choice(exits)
                self.execute_cmd(f"{exi.key}")

    def ai_flee(self):
        """
        Flee from the current room, avoiding going back to the room from which we came. If no exits
        are found, switch to patrol state.

        """
        current_room = self.location
        past_room = self.attributes.get("past_room", category="ai_state", default=None)
        exits = self.ai.get_traversable_exits(exclude_destination=past_room)
        if exits:
            self.attributes.set("past_room", current_room, category="ai_state")
            exi = random.choice(exits)
            self.execute_cmd(f"{exi.key}")
        else:
            # if in a dead end, patrol will allow for backing out
            self.ai.set_state("patrol")
