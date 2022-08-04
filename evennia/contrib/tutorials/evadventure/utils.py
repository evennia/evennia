"""
Various utilities.

"""

_OBJ_STATS = """
|c{key}|n  Value: approx. |y{value}|n coins {carried}

{desc}

Slots: |w{size}|n Used from: |w{use_slot_name}|n
Quality: |w{quality}|n Uses: |wuses|n
Attacks using: |w{attack_type_name}|n against |w{defense_type_value}|n
Damage roll: |w{damage_roll}""".strip()


def get_obj_stats(obj, owner=None):
    """
    Get a string of stats about the object.

    Args:
        obj (EvAdventureObject): The object to get stats for.
        owner (EvAdventureCharacter, optional): If given, it allows us to
            also get information about if the item is currently worn/wielded.

    Returns:
        str: A stat string to show about the object.

    """
    carried = ""
    if owner:
        objmap = dict(owner.equipment.all())
        carried = objmap.get(obj)
        carried = f"Worn: [{carried.value}]" if carried else ""

    return _OBJ_STATS.format(
        key=obj.key,
        value=obj.value,
        carried=carried,
        desc=obj.db.desc,
        size=obj.size,
        use_slot=obj.use_slot.value,
        quality=obj.quality,
        uses=obj.uses,
        attack_type=obj.attack_type.value,
        defense_type=obj.defense_type.value,
        damage_roll=obj.damage_roll,
    )
