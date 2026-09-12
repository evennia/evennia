"""
How sure discovery is, and why -- the confidence engine (Addendum B.28, B.33).

THREE WORDS, EACH WITH A RULE. B.28 defines them and this module is those
definitions made executable:

- **HIGH** -- a live character carries both a value and its ceiling, both are
  numbers, they are named as a pair, and the value was never above the ceiling.
- **MEDIUM** -- real but incomplete: a live number with no ceiling found, a pair
  found only by structure, a ceiling that was exceeded somewhere, a game object
  that might be a target, a command whose target semantics are unknown.
- **LOW** -- seen only in source, or its meaning is a guess. B.28: *low-confidence
  findings should not be selected by default*, so the report prints them
  commented out.

NEVER A NUMBER. "0.83" invites arithmetic on evidence that does not support it,
and nobody can say what the 0.03 is.

EVERY LEVEL CARRIES ITS REASONS. B.33: the developer must never be asked to
trust the scanner blindly. The reasons are what was found; the warnings are what
held the level down or what to check before pasting. A level with no reason
attached is a defect, and there is a test for it.

DETERMINISTIC. The same evidence gives the same level and the same words in the
same order, whatever order the scans ran in. A report that changes between two
runs on an unchanged game teaches a developer that it is noise.

"""

from dataclasses import replace

HIGH = "HIGH"
MEDIUM = "MEDIUM"
LOW = "LOW"

#: Most confident first, which is also the order the report lists them in.
LEVELS = (HIGH, MEDIUM, LOW)

#: What accepting a suggestion generates, per slot -- B.33's fifth question.
MAKES = {
    "resources": "a bar in the character panel",
    "resources:plain": "a number in the character panel (no ceiling, so no bar)",
    "effects": "an effect shown while this is true",
    "target": "the name shown for the current target",
    "actions": "an entry in the menu opened on something",
}

#: How many exceeded readings to name before summarising the rest.
MAX_NAMED_READINGS = 3


def lower(level):
    """
    One step less confident.

    Args:
        level (str): One of `LEVELS`.

    Returns:
        str: The next level down, or LOW.

    """
    index = LEVELS.index(level) if level in LEVELS else len(LEVELS) - 1
    return LEVELS[min(index + 1, len(LEVELS) - 1)]


def _origins(candidate):
    """
    The origin words present on a candidate.

    Args:
        candidate: A `Candidate`.

    Returns:
        set: Subset of `{"static", "typeclass", "runtime"}`.

    """
    return set(str(candidate.origin).replace(",", " ").split())


def _exceeded(candidate, partner):
    """
    Readings where the value was above the would-be ceiling.

    Args:
        candidate: The value.
        partner: The ceiling.

    Returns:
        list: `(character id, value, ceiling)`, in character order.

    """
    ceilings = dict(partner.observed)
    return sorted(
        (who, value, ceilings[who])
        for who, value in candidate.observed
        if who in ceilings and value > ceilings[who]
    )


def _written(origins):
    """
    Where, besides a live character, a candidate was seen.

    Args:
        origins (set): Origin words.

    Returns:
        list: Reasons naming the source and the typeclass, where they apply.

    """
    reasons = []
    if "static" in origins:
        reasons.append("also written in the game's source")
    if "typeclass" in origins:
        reasons.append("declared on the Character typeclass")
    return reasons


def _resource(candidate, partner):
    """
    The level and reasons for a number.

    Args:
        candidate: The candidate.
        partner: Its paired maximum, if any.

    Returns:
        tuple: `(level, reasons, warnings)`.

    """
    reasons, warnings = [], []
    live = "runtime" in _origins(candidate)

    if not (candidate.maximum and partner):
        reasons.append(
            "a number with no ceiling found, so it would show as a value rather than a bar"
        )
        return (MEDIUM if live else LOW), reasons, warnings

    partner_live = "runtime" in _origins(partner)
    if candidate.pairing == "structure":
        reasons.append(
            "paired by structure alone: %s extends the name %s and was never below it "
            "on the characters read" % (partner.name, candidate.name)
        )
    elif candidate.pairing == "stem":
        stem = candidate.leaf.rsplit("_", 1)[0]
        reasons.append(
            "%s and %s share the stem %s, and the second is named like a ceiling"
            % (candidate.name, partner.name, stem)
        )
        warnings.append(
            "a shared stem is weaker than one name extending the other -- check that "
            "both describe the same thing"
        )
    else:
        reasons.append(
            "%s and %s are named like a value and its ceiling" % (candidate.name, partner.name)
        )

    if live and partner_live:
        reasons.append("both are numbers on the characters read")

    over = _exceeded(candidate, partner)
    for who, value, ceiling in over[:MAX_NAMED_READINGS]:
        warnings.append(
            "%s was %s, above %s (%s), on #%s -- it may not be a ceiling"
            % (candidate.name, value, partner.name, ceiling, who)
        )
    if len(over) > MAX_NAMED_READINGS:
        warnings.append("and above it on %d more" % (len(over) - MAX_NAMED_READINGS))

    # Only one name directly extending the other can reach HIGH. A shared stem
    # and structure alone are real evidence, and weaker.
    if live and partner_live:
        level = HIGH if candidate.pairing == "name" and not over else MEDIUM
    elif live or partner_live:
        reasons.append("only one of the two was seen on a live character")
        level = MEDIUM
    else:
        level = LOW
    return level, reasons, warnings


def assess(candidate, partner=None, sampled=0, rivals=0):
    """
    Decide a candidate's confidence and say why.

    Args:
        candidate (Candidate): The candidate, with its evidence merged.
        partner (Candidate, optional): Its paired maximum.
        sampled (int, optional): How many characters were read.
        rivals (int, optional): For an object, how many *other* attributes also
            hold objects -- only one can be the target's name.

    Returns:
        Candidate: A copy with `confidence`, `reasons` and `warnings` set.

    """
    origins = _origins(candidate)
    live = "runtime" in origins
    warnings = list(candidate.warnings)
    slot = candidate.slot

    if slot == "resources":
        level, reasons, more = _resource(candidate, partner)
        warnings.extend(more)
    elif slot == "effects":
        # B.28 LOW: "semantic meaning uncertain". True/false is the shape of an
        # effect, and also of `is_builder` and `tutorial_done`.
        reasons = [
            "true or false, which is the shape of an effect that is on or off -- "
            "but nothing says what it means"
        ]
        level = LOW
    elif slot == "target":
        reasons = ["holds a game object, which is what a current target is"]
        if rivals:
            warnings.append(
                "%d other attribute%s also hold%s a game object, and only one can name "
                "the target" % (rivals, "" if rivals == 1 else "s", "s" if rivals == 1 else "")
            )
            level = LOW
        else:
            level = MEDIUM if live else LOW
    else:
        reasons = ["a %s value, which no Aetos slot displays as it is" % candidate.kind]
        level = LOW

    reasons.extend(_written(origins))
    if not live:
        reasons.append("not seen on a live character" if sampled else "no characters were read")

    if live and sampled > 1 and candidate.count == 1:
        warnings.append(
            "on only 1 of %d characters read -- possibly a leftover, or one "
            "character's experiment" % sampled
        )
        level = lower(level)

    # A merge that found the source and the live value disagreeing is not a
    # HIGH, whatever else is true: somebody is going to be surprised.
    if level == HIGH and candidate.warnings:
        level = MEDIUM

    return replace(
        candidate,
        confidence=level,
        reasons=tuple(dict.fromkeys(reasons)),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def makes(candidate):
    """
    What accepting a suggestion would put on screen.

    Args:
        candidate: A `Candidate` or `ActionCandidate`.

    Returns:
        str: One phrase.

    """
    slot = candidate.slot
    if slot == "resources" and not getattr(candidate, "maximum", None):
        return MAKES["resources:plain"]
    return MAKES.get(slot, "nothing -- it is listed for reference")
