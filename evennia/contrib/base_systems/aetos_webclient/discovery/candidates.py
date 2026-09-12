"""
The candidate data model.

A **candidate** is one answer to "here is something on your character that might
be worth putting on screen". It is not a binding and must never be mistaken for
one: a binding is a decision, and a candidate is evidence for a decision the
developer has not made yet.

WHAT A CANDIDATE HAS TO CARRY, and why each field is not optional:

- **The expression**, already in D1's grammar. A report that prints `hp` and
  leaves the developer to write `db.hp` has moved the error rather than removed
  it.
- **Where it was found.** `typeclasses/characters.py:42` or `on 4 of 4
  characters sampled`. A suggestion with no provenance cannot be checked, and
  the first thing anybody does with a generated settings block is check one line
  of it.
- **How it was found** -- static, typeclass or runtime. These have genuinely
  different reliability: a static hit is a line somebody wrote, a runtime hit is
  a value that exists right now and may be a leftover from a half-finished
  feature.
- **A partner, when one was found.** `db.hp` alone is a number. `db.hp` with
  `db.hp_max` is a health bar, which is what the developer actually wanted, and
  finding the pair is most of discovery's value.
- **Why it thinks so** (D3). Addendum B.33 makes explanation mandatory, so the
  confidence level travels with the reasons that produced it and the warnings
  that held it back. A level on its own is a number in disguise.

WHAT A CANDIDATE DOES NOT CARRY: a label the developer would want to read. The
scan knows the attribute is called `hp`; it does not know the game calls it
"Vitality". The report suggests `"label": "Hp"` and says plainly that the label
is the one field it has guessed.

"""

from dataclasses import dataclass, field, replace

from evennia.contrib.base_systems.aetos_webclient.discovery import confidence, redaction

#: How confident discovery is, in words rather than a number (Addendum B.28).
#:
#: D0 had two words, `likely` and `possible`. D3 adopts the addendum's three,
#: because B.28 attaches a rule to the bottom one -- low-confidence findings are
#: not selected by default -- and two levels cannot express "shown but not
#: selected". Still words: "0.7" for a runtime hit and "0.8" for a static one
#: implies the difference is 0.1 of something.
CONFIDENCE = confidence.LEVELS

#: What a value looks like, as far as the scan can tell. `unknown` is honest and
#: common: a static scan sees `self.db.hp = starting_hp` and cannot say what
#: `starting_hp` is. `object` is a game entity -- the shape of a current target.
KINDS = ("number", "text", "boolean", "object", "collection", "unknown")

#: Which `AETOS_BINDINGS` slot can use each kind.
#:
#: D0 put every candidate under `resources`. A text attribute there resolves to
#: no number, so the bar never draws -- a pasted setting that silently does
#: nothing. Text and collections have no slot that displays them as they are,
#: so they are mentioned in the report and never placed in the block.
SLOT_FOR_KIND = {"number": "resources", "boolean": "effects", "object": "target"}

#: Where a candidate came from, in the order the report names them.
ORIGINS = ("static", "typeclass", "runtime")

#: Attribute names that are never suggested.
#:
#: Evennia and common game code keep bookkeeping in attributes, and a report
#: that opens with `db.prelogout_location` buries the two lines the developer
#: wanted. Excluded from the *suggestion*, not from the scan -- `--all` still
#: shows them, because the exclusion list is a guess and the developer may be
#: looking for exactly one of these.
UNINTERESTING = frozenset(
    {
        # Evennia's own bookkeeping. These are on every character of every game,
        # so without this the first four lines of every report are identical and
        # tell the developer nothing about their own game.
        "prelogout_location",
        "last_puppet",
        "creator_id",
        "creator_ip",
        "_sessid",
        "_saved_contents",
        # Real object properties, but not attributes a binding reaches, and each
        # already has a place in the client that is not a resource bar.
        "desc",
        "aliases",
        "permissions",
        "locks",
        "cmdset",
        "tags",
        "home",
    }
)

#: Words that mark an attribute as the ceiling of another one.
#:
#: Addendum B.32 allows naming patterns as a heuristic. These are words for
#: "the most this can be", not names of resources: `hull_capacity` bounds
#: `hull_integrity` in a game this module has never heard of. Ordered so that
#: `maximum` is tried before `max`, or `hp_maximum` would be matched as `hp_max`
#: plus a stray `imum`.
CEILING_WORDS = ("maximum", "capacity", "limit", "total", "max", "cap")

#: How many characters must carry both values before structure alone pairs them.
#:
#: "Was never below it" on one reading is a coin that landed once. D3's first run
#: against the lab paired `poison` with `poison_left` -- rounds remaining, not a
#: ceiling -- from a single character.
MIN_STRUCTURAL_READINGS = 2

#: The part of D0's API that other code named. Kept as the forms it still pairs.
MAXIMUM_SUFFIXES = tuple("_%s" % word for word in CEILING_WORDS) + ("max",)


def _origin_parts(origin):
    """
    The origins named in an origin string.

    Args:
        origin (str): e.g. `"static and runtime"`.

    Returns:
        list: Known origins, in `ORIGINS` order.

    """
    words = str(origin).replace(",", " ").split()
    return [name for name in ORIGINS if name in words]


def _join(parts):
    """
    Origins as English: `static`, `static and runtime`, `a, b and c`.

    Args:
        parts (list): Origin names.

    Returns:
        str: The joined phrase.

    """
    if len(parts) <= 2:
        return " and ".join(parts)
    return "%s and %s" % (", ".join(parts[:-1]), parts[-1])


@dataclass(frozen=True)
class Candidate:
    """
    One attribute discovery thinks might be worth showing.

    Frozen, because a candidate is a record of what was observed. Anything that
    wants to change one is deriving a *new* observation, and `dataclasses.replace`
    makes that visible at the call site rather than letting a scan quietly edit
    another scan's findings.

    Attributes:
        expression (str): The binding expression, e.g. `db.hp` or `db.stats.hp`.
        name (str): The expression without `db.`, e.g. `hp` or `stats.hp`.
        origin (str): Which scans found it, e.g. `"static and runtime"`.
        evidence (str): Where it was found, in words a developer can go and check.
        kind (str): One of `KINDS`.
        maximum (str or None): A partner expression that looks like this one's
            ceiling, e.g. `db.hp_max`.
        confidence (str): One of `CONFIDENCE`. Set by `CandidateSet.assess`;
            scans do not decide it.
        pairing (str or None): `"name"`, `"stem"` or `"structure"` -- how the
            maximum was found, weakest last, because they deserve different trust.
        shown (str or None): A short, safe rendering of a live value.
        observed (tuple): `(character id, number)` for each numeric reading,
            so a ceiling can be checked against the value it claims to bound.
        count (int): How many characters carried it at runtime.
        reasons (tuple): Why it is at its confidence level.
        warnings (tuple): What held it back, or what a developer should check.

    """

    expression: str
    name: str
    origin: str
    evidence: str
    kind: str = "unknown"
    maximum: str = None
    confidence: str = confidence.LOW
    pairing: str = None
    shown: str = None
    observed: tuple = ()
    count: int = 0
    reasons: tuple = ()
    warnings: tuple = ()

    @property
    def leaf(self):
        """
        The last segment of the name.

        Returns:
            str: `hp` for both `hp` and `stats.hp`.

        """
        return self.name.rpartition(".")[2]

    @property
    def key(self):
        """
        The key this candidate is given in the generated settings block.

        Returns:
            str: The name with dots made underscores, so `stats.hp` and a
                top-level `hp` cannot collide.

        """
        return self.name.replace(".", "_")

    @property
    def interesting(self):
        """
        Whether this belongs in the default suggestion.

        Returns:
            bool: False for known bookkeeping and for names starting with an
                underscore, which is the convention for exactly that.

        """
        return not (self.leaf.startswith("_") or self.name in UNINTERESTING)

    @property
    def looks_like_a_resource(self):
        """
        Whether this is the shape of a thing that belongs on a bar.

        Returns:
            bool: True when there is a paired maximum, which is the only
                evidence strong enough to say so without guessing at the name.

        Notes:
            Deliberately not "is it called hp or health". A name list is a guess
            about somebody else's game, it is wrong in every language but
            English, and a game with `db.oxygen` and `db.oxygen_max` wants a bar
            just as much.

        """
        return bool(self.maximum)

    @property
    def slot(self):
        """
        The `AETOS_BINDINGS` slot this could go in.

        Returns:
            str or None: `None` when no slot displays this kind as it is.

        """
        return SLOT_FOR_KIND.get(self.kind)

    @property
    def seen_live(self):
        """
        Whether any character actually carried this.

        Returns:
            bool: True if the runtime scan found it.

        """
        return "runtime" in _origin_parts(self.origin)


#: The caveat a source-only action carries.
#:
#: Named rather than written twice, because the merge has to *recognise* it: a
#: command found in source and then found on a live character kept saying "not
#: seen in a live command set" beside the evidence that it was. A reason that
#: contradicts the evidence next to it costs the whole report its credibility.
SOURCE_ONLY_REASON = "not seen in a live command set"


@dataclass(frozen=True)
class ActionCandidate:
    """
    A game command that might belong in the menu opened on a target.

    Attributes:
        key (str): The command's key.
        command (str): What the action would send, e.g. `attack {target}`.
        evidence (str): Which command set and module it came from.
        confidence (str): One of `CONFIDENCE`.
        reasons (tuple): Why.
        warnings (tuple): What to check.

    """

    key: str
    command: str
    evidence: str
    confidence: str = confidence.LOW
    reasons: tuple = ()
    warnings: tuple = ()

    slot = "actions"


def _naming_forms(name):
    """
    The names a ceiling of `name` could have, most specific first.

    Args:
        name (str): A candidate name, possibly `parent.child`.

    Returns:
        list: Partner names in the same scope -- a dict's keys pair with keys
            in the same dict, never with a top-level attribute.

    """
    head, dot, leaf = name.rpartition(".")
    scope = head + dot
    forms = ["%s_%s" % (leaf, word) for word in CEILING_WORDS]
    forms.append("%smax" % leaf)
    forms.extend("%s_%s" % (word, leaf) for word in ("maximum", "max"))
    forms.append("max%s" % leaf)
    return [scope + form for form in forms]


def _stem_forms(name):
    """
    Ceilings that share a stem rather than extending the name.

    Args:
        name (str): e.g. `hull_integrity`.

    Returns:
        tuple: `(stem name, [partner names])` -- `hull`, `[hull_capacity, ...]`.
            Empty when the last segment is itself a ceiling word.

    """
    head, dot, leaf = name.rpartition(".")
    if "_" not in leaf:
        return None, []
    stem, last = leaf.rsplit("_", 1)
    if last in CEILING_WORDS:
        return None, []
    scope = head + dot
    return scope + stem, [scope + "%s_%s" % (stem, word) for word in CEILING_WORDS]


def _never_below(candidate, partner, minimum=1):
    """
    Whether a partner was at least the candidate's value everywhere both were.

    Args:
        candidate (Candidate): The value.
        partner (Candidate): The would-be ceiling.
        minimum (int, optional): How many shared readings are needed at all.

    Returns:
        bool: True if they were read together at least `minimum` times and the
            partner was never smaller.

    """
    ceilings = dict(partner.observed)
    shared = [(value, ceilings[who]) for who, value in candidate.observed if who in ceilings]
    return len(shared) >= minimum and all(value <= ceiling for value, ceiling in shared)


@dataclass
class CandidateSet:
    """
    Everything one run of discovery found, merged across every scan.

    Not a plain list, because merging is the part with a decision in it: the
    same attribute found statically and at runtime is *one* candidate with two
    pieces of evidence, not two rows that make the report look twice as
    productive as it was.

    Attributes:
        candidates (dict): Keyed by expression, so a merge is a lookup.
        actions (dict): Action candidates, keyed by command key.
        withheld (set): Names refused because they look like credentials.

    """

    candidates: dict = field(default_factory=dict)
    actions: dict = field(default_factory=dict)
    withheld: set = field(default_factory=set)

    def add(self, candidate):
        """
        Record a candidate, merging it with any existing one.

        Args:
            candidate (Candidate): The observation to record.

        Returns:
            Candidate or None: The stored candidate, which may be a merge, or
                None if it was withheld.

        Notes:
            **A credential is refused here, whichever scan offered it**, so a
            future scan cannot forget to (B.46). The runtime scan also refuses
            before reading the value; this is the second lock, not the only one.

            The merge keeps the *stronger* claim on every field. A static scan
            that saw `self.db.hp = 100` knows the kind is a number; a runtime
            scan that read `None` off a fresh character does not. Taking the
            last write would make the result depend on scan order. Where both
            know and disagree, the live value wins -- it is what a binding will
            actually read -- and the disagreement becomes a warning.

        """
        if redaction.is_sensitive_expression(candidate.expression):
            self.withheld.add(candidate.name)
            return None

        existing = self.candidates.get(candidate.expression)
        if existing is None:
            self.candidates[candidate.expression] = candidate
            return candidate

        warnings = list(existing.warnings) + list(candidate.warnings)
        kind = existing.kind if existing.kind != "unknown" else candidate.kind
        if "unknown" not in (existing.kind, candidate.kind) and existing.kind != candidate.kind:
            live, written = (candidate, existing) if candidate.seen_live else (existing, candidate)
            kind = live.kind
            warnings.append(
                "the source makes this %s but the live value is %s -- a binding reads "
                "the live value" % (written.kind, live.kind)
            )

        merged = replace(
            existing,
            origin=_join(_origin_parts("%s %s" % (existing.origin, candidate.origin))),
            evidence="%s; %s" % (existing.evidence, candidate.evidence),
            kind=kind,
            maximum=existing.maximum or candidate.maximum,
            pairing=existing.pairing or candidate.pairing,
            shown=existing.shown or candidate.shown,
            observed=existing.observed + candidate.observed,
            count=max(existing.count, candidate.count),
            warnings=tuple(dict.fromkeys(warnings)),
        )
        self.candidates[candidate.expression] = merged
        return merged

    def add_action(self, action):
        """
        Record an action candidate, keeping the stronger evidence.

        Args:
            action (ActionCandidate): The command found.

        Notes:
            A command found in a live command set and the same command found in
            source are one action with two pieces of evidence. The *stronger*
            claim wins whichever arrived first: a class in a file says the
            command exists, and a loaded command set says a character actually
            has it. Taking the first would make the result depend on scan order.

        """
        existing = self.actions.get(action.key)
        if existing is None:
            self.actions[action.key] = action
            return

        rank = {level: index for index, level in enumerate(CONFIDENCE)}
        stronger, weaker = (
            (action, existing)
            if rank.get(action.confidence, 9) < rank.get(existing.confidence, 9)
            else (existing, action)
        )
        # Whichever half came from source carried "not seen in a live command
        # set". If the other half *is* the live command set, that is no longer
        # true and must not travel with the merge.
        reasons = [
            reason
            for reason in dict.fromkeys(stronger.reasons + weaker.reasons)
            if reason != SOURCE_ONLY_REASON
        ]
        self.actions[action.key] = replace(
            stronger,
            evidence="%s; %s" % (stronger.evidence, weaker.evidence),
            reasons=tuple(reasons),
            warnings=tuple(dict.fromkeys(stronger.warnings + weaker.warnings)),
        )

    def _pairable(self, candidate):
        """
        Whether a candidate could be a value or a ceiling at all.

        Args:
            candidate (Candidate): The candidate.

        Returns:
            bool: True for numbers, and for `unknown` -- a static scan often
                cannot tell, and refusing those would refuse most source pairs.

        """
        return candidate.kind in ("number", "unknown")

    def _attach(self, candidate, partner, how):
        """
        Record that `partner` is `candidate`'s ceiling.

        Args:
            candidate (Candidate): The value.
            partner (Candidate): The ceiling.
            how (str): `"name"` or `"structure"`.

        """
        self.candidates[candidate.expression] = replace(
            candidate, maximum=partner.expression, pairing=how
        )

    def pair_maximums(self):
        """
        Attach each candidate's ceiling, where one is present.

        Returns:
            int: How many pairs were made.

        Notes:
            Run after every scan rather than during one, because the pair can be
            split between them -- `hp` written in the typeclass and `hp_max`
            set from a command is an ordinary way for a game to end up.

            Three passes, weakest last, and **a ceiling is claimed once**:

            1. **The name extends into a ceiling word** -- `hp` / `hp_max`,
               `oxygen` / `oxygen_capacity`, `hp` / `max_hp`.
            2. **A shared stem with a ceiling word** -- `hull_integrity` /
               `hull_capacity` -- only when the stem is not itself an attribute.
               Otherwise `hp_regen` would claim `hp_max` from `hp`. Weaker than
               (1), and marked `stem`: in the lab, `target_hp` / `target_max`
               pair this way and are the *target's* health, not the player's.
            3. **Structure alone** -- one name extends the other and was never
               below it on any character read. This is what pairs a game written
               in a language with no ceiling word in the list, and it is marked
               as such so the confidence engine trusts it less. Two possible
               partners is no partner: guessing between them is a coin toss.

            The maximum itself stays in the set. It is a real attribute and a
            developer may want it shown on its own; the report is what decides
            not to list it twice.

        """
        by_name = {candidate.name: candidate for candidate in self.candidates.values()}
        claimed = set()
        paired = 0

        def free(name):
            """
            The candidate called `name`, if it could still be somebody's ceiling.

            Args:
                name (str): A candidate name.

            Returns:
                Candidate or None: None if absent, already claimed, or not a
                    number-shaped value.

            """
            partner = by_name.get(name)
            if partner is None or name in claimed or not self._pairable(partner):
                return None
            return partner

        values = [
            candidate
            for name, candidate in sorted(by_name.items())
            if self._pairable(candidate) and not candidate.maximum
        ]

        # 1. The name extends into a ceiling word.
        for candidate in values:
            if candidate.name in claimed:
                continue
            for form in _naming_forms(candidate.name):
                partner = free(form)
                if partner is not None and partner.name != candidate.name:
                    self._attach(candidate, partner, "name")
                    claimed.add(partner.name)
                    paired += 1
                    break

        # 2. A stem shared with a ceiling word.
        for candidate in values:
            if self.candidates[candidate.expression].maximum or candidate.name in claimed:
                continue
            stem, forms = _stem_forms(candidate.name)
            if stem is None or stem in by_name:
                continue
            for form in forms:
                partner = free(form)
                if partner is not None:
                    self._attach(candidate, partner, "stem")
                    claimed.add(partner.name)
                    paired += 1
                    break

        # 3. Structure alone.
        for candidate in values:
            if self.candidates[candidate.expression].maximum or candidate.name in claimed:
                continue
            if candidate.kind != "number" or len(candidate.observed) < MIN_STRUCTURAL_READINGS:
                continue
            options = [
                partner
                for name, partner in sorted(by_name.items())
                if name.startswith(candidate.name + "_")
                and name not in claimed
                and partner.kind == "number"
                and _never_below(candidate, partner, MIN_STRUCTURAL_READINGS)
            ]
            if len(options) == 1:
                self._attach(candidate, options[0], "structure")
                claimed.add(options[0].name)
                paired += 1

        return paired

    def assess(self, sampled=0):
        """
        Give every candidate its confidence level and the reasons for it.

        Args:
            sampled (int, optional): How many characters the runtime scan read.

        Notes:
            Separate from the scans, so that the level is decided once, from
            everything, by one set of rules -- rather than each scan guessing
            and a merge picking the more optimistic guess.

        """
        objects = [
            candidate
            for candidate in self.candidates.values()
            if candidate.kind == "object" and candidate.interesting
        ]
        texts = {c.name for c in self.candidates.values() if c.kind == "text"}
        for expression, candidate in list(self.candidates.items()):
            assessed = confidence.assess(
                candidate,
                partner=self.candidates.get(candidate.maximum),
                sampled=sampled,
                rivals=len(objects) - 1 if candidate.kind == "object" else 0,
            )
            # `target_name` beside `target_hp` / `target_max` is D2's documented
            # shape for the target slot: an entity named by one attribute and
            # measured by others. Discovery cannot know whose health it is, so it
            # says what it sees rather than moving the entry.
            if candidate.pairing == "stem":
                stem = candidate.name.rsplit("_", 1)[0]
                if "%s_name" % stem in texts:
                    assessed = replace(
                        assessed,
                        warnings=assessed.warnings
                        + (
                            "db.%s_name names something with the same stem -- if these "
                            "measure that rather than the character, they belong in the "
                            "target slot instead" % stem,
                        ),
                    )
            self.candidates[expression] = assessed

    def suggestions(self, include_all=False):
        """
        The candidates worth putting in a report, in a stable order.

        Args:
            include_all (bool, optional): Include bookkeeping attributes that
                are normally filtered out.

        Returns:
            list: Candidates, paired ones first, then alphabetically.

        Notes:
            A candidate that is another one's maximum is not listed on its own
            when its partner is listed, or every health bar appears in the
            report twice and the developer deletes one at random.

        """
        chosen = [
            candidate
            for candidate in self.candidates.values()
            if include_all or candidate.interesting
        ]
        ceilings = {candidate.maximum for candidate in chosen if candidate.maximum}
        chosen = [c for c in chosen if c.expression not in ceilings]
        return sorted(chosen, key=lambda c: (not c.looks_like_a_resource, c.name))

    def by_slot(self, slot, include_all=False):
        """
        The suggestions that belong in one `AETOS_BINDINGS` slot.

        Args:
            slot (str): One of `schema.BINDING_SLOTS`.
            include_all (bool, optional): As for `suggestions`.

        Returns:
            list: Candidates (or action candidates), most confident first.

        """
        rank = {level: index for index, level in enumerate(CONFIDENCE)}
        if slot == "actions":
            chosen = list(self.actions.values())
            return sorted(chosen, key=lambda a: (rank.get(a.confidence, 9), a.key))
        chosen = [c for c in self.suggestions(include_all) if c.slot == slot]
        return sorted(chosen, key=lambda c: (rank.get(c.confidence, 9), c.name))

    def unslotted(self, include_all=False):
        """
        Suggestions that no slot can display as they are.

        Args:
            include_all (bool, optional): As for `suggestions`.

        Returns:
            list: Text and collection candidates, alphabetically.

        """
        return sorted(
            (c for c in self.suggestions(include_all) if c.slot is None),
            key=lambda c: c.name,
        )

    def __len__(self):
        """
        How many distinct candidates were found.

        Returns:
            int: The count after merging, so an attribute both scans saw counts
                once.

        """
        return len(self.candidates)
