"""
The guided walkthrough: review, test, accept, generate (Addendum B.35-B.40).

WHY A WIZARD AT ALL, when `evennia aetos discover` already prints a block a
developer can paste. Because pasting is where the mistakes happen and nothing
catches them: a binding that resolves to `None` looks exactly like a binding
that is right until a browser is open and a bar is missing. The wizard's whole
reason to exist is the **test** step -- it reads the expression off a real
character, shows the number, and only then offers to accept it.

ONE QUESTION AT A TIME, AND EVERY ANSWER REVERSIBLE. Nothing is written until
the end, quitting writes nothing at all, and what is written goes to
`aetos-discovery/` where nothing imports it. A developer who does not like the
result deletes a directory.

NO `input()` AND NO `print()` HERE. The wizard is handed an `ask` and a `say`,
which the management command wires to the terminal and the tests wire to a
script. That is not only for testing: a prompt loop that owns its own I/O cannot
be driven by anything else, and this one should be usable from a future
`evennia aetos apply` or a test harness without being rewritten.

WHAT IT WILL NOT DO. It does not edit `settings.py`, it does not write into the
game's source, and it never accepts a candidate whose test failed without the
developer saying so in as many words.

"""

from evennia.contrib.base_systems.aetos_webclient.bindings import schema
from evennia.contrib.base_systems.aetos_webclient.discovery import confidence, report

#: What the developer may answer when offered a candidate.
CHOICES = "yenq?"

#: Fields the developer may edit, per slot.
EDITABLE = {
    "resources": ("label", "value", "maximum"),
    "effects": ("label", "value"),
    "target": ("label", "value"),
    "actions": ("label", "command"),
}


class Quit(Exception):
    """The developer asked to stop. Nothing is written."""


class Wizard:
    """
    One guided pass over what discovery found.

    Attributes:
        accepted (dict): Slot -> {key -> entry}, ready to generate.
        accepted_lines (list): Human-readable record for the report.
        ignored_lines (list): The same, for what was passed over.

    """

    def __init__(self, found, context=None, character=None, ask=None, say=None, resolver=None):
        """
        Build a wizard.

        Args:
            found (CandidateSet): What the scans found, assessed.
            context (dict, optional): What was read, for the summary.
            character (Object, optional): The character to test bindings
                against. Without one, nothing can be tested and the wizard says
                so rather than pretending.
            ask (callable, optional): `ask(prompt)` -> the developer's answer.
            say (callable, optional): `say(text)` -> shows a line.
            resolver (AetosBindingResolver, optional): Used for the test step.

        """
        self.found = found
        self.context = context or {}
        self.character = character
        self._ask = ask or (lambda prompt: "")
        self._say = say or (lambda text: None)
        self.accepted = {}
        self.accepted_lines = []
        self.ignored_lines = []
        self.provider_findings = []

        if resolver is None:
            from evennia.contrib.base_systems.aetos_webclient.bindings.resolver import (
                AetosBindingResolver,
            )

            resolver = AetosBindingResolver()
        self.resolver = resolver

    # ------------------------------------------------------------------ input

    def ask(self, prompt, allowed=None):
        """
        Ask the developer something, refusing an answer that is not offered.

        Args:
            prompt (str): The question.
            allowed (str, optional): Permitted first letters, lower case.

        Returns:
            str: The answer, lower-cased and stripped when `allowed` is given.

        Raises:
            Quit: On `q`, or when input ends. **End of input is a quit, not a
                default.** A wizard that took EOF as "yes" would accept
                everything when run without a terminal.

        """
        try:
            answer = self._ask(prompt)
        except (EOFError, KeyboardInterrupt):
            raise Quit("input ended")
        if answer is None:
            raise Quit("input ended")
        if allowed is None:
            return answer.strip()
        answer = answer.strip().lower()[:1]
        while answer not in allowed:
            self.say("Please answer one of: %s" % ", ".join(allowed.upper()))
            try:
                answer = (self._ask(prompt) or "").strip().lower()[:1]
            except (EOFError, KeyboardInterrupt):
                raise Quit("input ended")
        if answer == "q":
            raise Quit("the developer stopped")
        return answer

    def say(self, text=""):
        """
        Show a line.

        Args:
            text (str, optional): What to show.

        """
        self._say(text)

    # ------------------------------------------------------------------ steps

    def run(self):
        """
        Walk every candidate, then report what was decided.

        Returns:
            dict: `accepted`, `accepted_lines`, `ignored_lines`,
                `provider_findings`, and `quit` -- True when the developer
                stopped early, in which case nothing should be written.

        """
        stopped = False
        try:
            self._introduce()
            for slot in schema.BINDING_SLOTS:
                for candidate in self.found.by_slot(slot):
                    self._offer(slot, candidate)
            self._offer_provider()
        except Quit as reason:
            stopped = True
            self.say("")
            self.say("Stopped (%s). Nothing has been written." % reason)

        return {
            "accepted": self.accepted,
            "accepted_lines": self.accepted_lines,
            "ignored_lines": self.ignored_lines,
            "provider_findings": self.provider_findings,
            "quit": stopped,
        }

    def _introduce(self):
        """Say what is about to happen, and what cannot happen."""
        self.say("Aetos setup")
        self.say("===========")
        self.say("")
        if self.context.get("characters"):
            self.say("Reading: %s" % ", ".join(self.context["characters"]))
        self.say(
            "Nothing is changed for you. At the end this writes to aetos-discovery/, "
            "which nothing imports."
        )
        if self.character is None:
            self.say(
                "No character was selected, so bindings cannot be tested against live "
                "values. Run this again with --character once somebody has played."
            )
        self.say("")

    def _offer(self, slot, candidate):
        """
        Present one candidate and act on the answer.

        Args:
            slot (str): The binding slot.
            candidate: A `Candidate` or `ActionCandidate`.

        """
        entry = self._entry_for(slot, candidate)
        while True:
            self._present(slot, candidate, entry)
            answer = self.ask(
                "Use this integration?  [Y]es [E]dit [N]o [?]explain [Q]uit ", CHOICES
            )
            if answer == "?":
                self._explain(slot, candidate)
                continue
            if answer == "e":
                entry = self._edit(slot, entry)
                continue
            if answer == "n":
                self.ignored_lines.append("%s %s" % (slot, self._name_of(slot, entry)))
                self.say("Ignored.")
                self.say("")
                return
            if self._accept(slot, entry):
                return

    def _entry_for(self, slot, candidate):
        """
        The settings entry a candidate would produce, before any editing.

        Args:
            slot (str): The binding slot.
            candidate: The candidate.

        Returns:
            dict: `key` plus the fields for that slot.

        """
        key, fields = report.entry_for(slot, candidate)
        entry = {"key": key}
        entry.update(dict(fields or []))
        return entry

    def _name_of(self, slot, entry):
        """
        How an entry is named in the record.

        Args:
            slot (str): The binding slot.
            entry (dict): The entry.

        Returns:
            str: e.g. `health (db.health)`.

        """
        subject = entry.get("value") or entry.get("command") or ""
        return "%s (%s)" % (entry["key"], subject)

    def _present(self, slot, candidate, entry):
        """
        Show a candidate the way B.35 lays one out.

        Args:
            slot (str): The binding slot.
            candidate: The candidate.
            entry (dict): The entry as it currently stands.

        """
        heading = "Possible %s found" % slot.rstrip("s")
        self.say(heading)
        self.say("-" * len(heading))
        self.say("Suggested name:  %s" % entry.get("label", ""))
        for field in ("value", "maximum", "command"):
            if entry.get(field):
                self.say("%-16s %s" % (field.capitalize() + ":", entry[field]))
        tested = self._test(entry)
        if tested:
            self.say("Test values:     %s" % tested)
        self.say("")
        self.say("Evidence:")
        for reason in candidate.reasons or ("(none recorded)",):
            self.say("  - %s" % reason)
        for warning in candidate.warnings:
            self.say("  ! %s" % warning)
        self.say("")
        self.say("Confidence: %s" % candidate.confidence)
        self.say("")

    def _test(self, entry):
        """
        Read the entry's expressions off the selected character.

        Args:
            entry (dict): The entry.

        Returns:
            str or None: e.g. `82 / 100`, `nothing -- db.hp is not set on #12`,
                or None when there is nothing to test.

        Notes:
            This is the step the wizard exists for (B.40). A binding that
            resolves to nothing looks exactly like a correct one until a browser
            is open, and the developer is the wrong person to find that out
            last.

        """
        if self.character is None or not entry.get("value"):
            return None
        readings = []
        for field in ("value", "maximum"):
            expression = entry.get(field)
            if not expression:
                continue
            value = self.resolver.resolve(self.character, expression)
            readings.append(
                "%s" % value if value is not None else "nothing (%s is not set)" % expression
            )
        return " / ".join(readings)

    def _resolves(self, entry):
        """
        Whether the entry's main value reads as something.

        Args:
            entry (dict): The entry.

        Returns:
            bool or None: None when it could not be tested at all.

        """
        if self.character is None or not entry.get("value"):
            return None
        return self.resolver.resolve(self.character, entry["value"]) is not None

    def _explain(self, slot, candidate):
        """
        Answer "why are you showing me this" in full (B.33).

        Args:
            slot (str): The binding slot.
            candidate: The candidate.

        """
        self.say("")
        self.say("Found:    %s" % candidate.evidence)
        self.say("Level:    %s -- %s" % (candidate.confidence, self._level_means(candidate)))
        self.say("Accepting it generates: %s" % confidence.makes(candidate))
        self.say(
            "A binding names where a value is stored. Aetos reads it directly and never "
            "calls anything, so a computed value needs a provider class instead."
        )
        self.say("")

    def _level_means(self, candidate):
        """
        One sentence on what a confidence level is claiming.

        Args:
            candidate: The candidate.

        Returns:
            str: The meaning of its level.

        """
        return {
            confidence.HIGH: "a live character has this, and its ceiling, and both are numbers",
            confidence.MEDIUM: "real, but something about it is incomplete or uncertain",
            confidence.LOW: "seen, but not enough to suggest on its own",
        }.get(candidate.confidence, "")

    def _edit(self, slot, entry):
        """
        Let the developer change the entry without editing Python (B.38).

        Args:
            slot (str): The binding slot.
            entry (dict): The entry as it stands.

        Returns:
            dict: The edited entry.

        """
        edited = dict(entry)
        for field in EDITABLE.get(slot, ("label",)):
            current = edited.get(field, "")
            answer = self.ask("%s [%s]: " % (field, current))
            if not answer:
                continue
            if field in schema.EXPRESSION_FIELDS and not schema.is_valid_expression(answer):
                self.say("  That %s" % schema.explain_expression(answer))
                self.say("  Keeping %r." % current)
                continue
            edited[field] = answer
        self.say("")
        return edited

    def _accept(self, slot, entry):
        """
        Record an acceptance, after the test has had its say.

        Args:
            slot (str): The binding slot.
            entry (dict): The entry.

        Returns:
            bool: True when it was accepted, False to ask again.

        """
        resolves = self._resolves(entry)
        if resolves is False:
            self.say(
                "That does not read as anything on the character tested. Pasted as it "
                "is, the panel would stay empty."
            )
            answer = self.ask("Accept it anyway?  [Y]es [N]o [Q]uit ", "ynq")
            if answer != "y":
                return False

        key = entry.pop("key")
        self.accepted.setdefault(slot, {})[key] = {
            field: value for field, value in entry.items() if value
        }
        entry["key"] = key
        self.accepted_lines.append(
            "%s %s%s"
            % (slot, self._name_of(slot, entry), "" if resolves is not False else " (test failed)")
        )
        self.say("Accepted.")
        self.say("")
        return True

    def _offer_provider(self):
        """
        Offer starter provider code, when a provider is the honest answer.

        Notes:
            Only asked when something was actually found that a binding cannot
            express -- a handler, or a categorised attribute. Offering a
            skeleton to a game that does not need one is an invitation to paste
            an empty provider and wonder why nothing appears.

        """
        findings = [
            problem for problem in self.context.get("problems", []) if "AETOS_PROVIDERS" in problem
        ]
        if not findings:
            return
        self.say("Some values here cannot be reached by a binding:")
        for finding in findings:
            self.say("  - %s" % finding)
        self.say("")
        answer = self.ask("Write starter provider code for these?  [Y]es [N]o [Q]uit ", "ynq")
        if answer == "y":
            self.provider_findings = findings
            self.say("It will be written as starter code, for you to finish.")
        self.say("")
