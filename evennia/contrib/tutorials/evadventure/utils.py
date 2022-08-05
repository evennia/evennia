"""
Various utilities.

"""

_OBJ_STATS = """
|c{key}|n
Value: ~|y{value}|n coins{carried}

{desc}

Slots: |w{size}|n, Used from: |w{use_slot_name}|n
Quality: |w{quality}|n, Uses: |wuses|n
Attacks using |w{attack_type_name}|n against |w{defense_type_name}|n
Damage roll: |w{damage_roll}|n""".strip()


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
        carried = f", Worn: [{carried.value}]" if carried else ""

    attack_type = getattr(obj, "attack_type", None)
    defense_type = getattr(obj, "attack_type", None)

    return _OBJ_STATS.format(
        key=obj.key,
        value=obj.value,
        carried=carried,
        desc=obj.db.desc,
        size=obj.size,
        use_slot_name=obj.inventory_use_slot.value,
        quality=getattr(obj, "quality", "N/A"),
        uses=getattr(obj, "uses", "N/A"),
        attack_type_name=attack_type.value if attack_type else "No attack",
        defense_type_name=defense_type.value if defense_type else "No defense",
        damage_roll=getattr(obj, "damage_roll", "None"),
    )
