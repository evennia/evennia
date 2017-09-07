class SlotsHandler:
    """
    Handler for the slots system. This handler is designed to be attached to
    objects with a particular @lazy-property name, so it will be referred to as
    `.slots`, though individual games can set that however they like.

    Place on character or other typeclassed object:
    ```
    @lazy_property
    def slots(self):
        return SlotsHandler(self)
    ```

    The purpose of this handler is to sit on a "holder" typeclassed object and
    manage slots for "held" objects. The first thing that should happen is
    using `self.slots.add()` on the holder object to identify the available
    options. `.slots.delete()` can be used to delete or pop old slots.

    By default, a held object can have slots stored on it (the handler will
    check `.db.slots`, `.ndb.slots`, and `.slots` in that order), and
    `self.slots.attach()` will attempt to attach it on all of those slots (it
    should fail if it can't attach on every slot). `self.slots.drop()` will
    remove the target from any of the slots given it. Both of these methods
    have the option to be given a custom `slots` argument, which will override
    the slots on the held object.

    Using the custom `slots` in `attach()` and `drop()` provides some
    customization facility in that you can store *any* object in a slot, not
    just an object that has been set up for it.
    """

    def __init__(self, obj):
        self.obj = obj
        self._objid = obj.id

    def is_name_valid(self, test):
        "Internal function to check if the name is right."
        try:
            exec(test + " = 1")
        except SyntaxError:
            raise ValueError("You have to limit slot category names to "
                             "characters that are valid in variable names.")

    def all(self):
        "Return a dict of all slots."
        d = self.obj.attributes.get(category="slots", return_obj=True)

        r = [(s.key, s.value) for s in d]

        return dict(r)

    def add(self, name, num=0, *slots):
        """
        Create an array of slots, or add additional slots to an existing array.

        Args:
            name: The name of the array.
            *slots: A set of lists, strings, and/or tuples defining slot names.
            num: Any unnamed slots.
        """

        self.is_name_valid(name)
        existing = self.obj.attributes.get(name, category="slots")
        self.obj.msg("Existing attribute {}: {}".format(name, repr(existing)))
        slot_list = []
        for arg in slots:
            if isinstance(arg, list):
                slot_list += arg
            elif isinstance(arg, str):
                slot_list.append(arg)
            elif isinstance(arg, tuple):
                slot_list.append(list(arg))
            else:
                raise ValueError("Only lists, strings, and tuples accepted.")
        # To find where the numbers should start, iterate through numerical
        # keys and store the highest value.
        highest = 0
        if existing:
            for slot in existing.keys():
                if isinstance(slot, int) and slot > highest:
                    highest = slot
        for i in range(highest, highest + num):
            slot_list.append(i+1)
        slots = {slot: "" for slot in slot_list}

        if not existing:
            new = self.obj.attributes.add(name, slots, category="slots")

            return True
        else:
            existing.update(slots)
            return True

    def delete(self, name, num=0, *slots):
        """
        This will delete slots from an existing array.
        WARNING: If you have anything attached in slots when they are removed,
        the slots' contents will also be removed. This function will return a
        dict of any removed slots and their contents, so it can act as a pop(),
        but if you don't catch that data, it WILL be lost.
        """

        self.is_name_valid(name)
        existing = self.obj.attributes.get(name, category="slots")
        if not existing: # If the named array isn't there, don't bother.
            return False
        slot_list = []
        if not num and not slots:
            self.obj.attributes.remove(name)
        for arg in slots:
            if isinstance(arg, list):
                slot_list += arg
            elif isinstance(arg, str):
                slot_list.append(arg)
            elif isinstance(arg, tuple):
                slot_list.append(list(arg))
            else:
                raise ValueError
        # To find where the numbers should start, iterate through numerical
        # keys and store the highest value.
        highest = 0
        if existing:
            for key in existing.keys():
                if isinstance(key, int) and key > highest:
                    highest = key
        for i in range(highest, highest - num, -1):
            slot_list.append(i)

        deleted = {}

        for slot in slot_list:
            deleted.update({slot: existing.pop(slot)})

        return deleted

    def attach(self, target, slots=None):
        "Attempt to attach the target in all slots it consumes. Optionally, the target's slots may be overridden."

        if not slots:
            slots = target.db.slots
            if not slots:
                slots = target.ndb.slots
                if not slots:
                    try:
                        slots = target.slots
                    except AttributeError:
                        return StatMsg(False, "No slots detected.")

        modified = {}

        if not isinstance(slots, (dict, _SaverDict)):
            return StatMsg(False, "You have to declare slots in the form "
                           "`{key: [values]}`.")

        for name in slots:
            array = self.obj.attributes.get(name, category="slots")
            if not array:
                return StatMsg(False, "You need to add slots before you can "
                               "attach anything.")

            new = {}

            # Get the number of open slots, then count to see if there are
            # enough for the attachment.
            numbered = [n for n in array.keys()
                        if isinstance(n, int) and not array[n]]
            requirement = [n for n in slots[name] if isinstance(n, int)] + [0]
            requirement = sum(requirement)
            if len(numbered) < requirement:
                return StatMsg(False, "You're running out of numbered slots. "
                               "You need to add or free up slots before you "
                               "can attach this.")

            if numbered:
                new.update({numbered[i]: target
                            for i in range(0, requirement)})

            # Get the list of open named slots and check to see if all of the
            # requested slots are members of them.
            named = [n for n in array.keys()
                     if isinstance(n, str) and not array[n]]
            requirement = [n for n in slots[name] if isinstance(n, str)]
            if requirement and not set(requirement).issubset(named):
                return StatMsg(False, "You're running out of named slots. "
                               "You need to add or free up slots before you "
                               "can attach this.")

            if named:
                new.update({req: target
                            for req in requirement})

            array.update(new)
            modified.update({name: new})

        return modified

    def drop(self, target, slots=None):
        """
        Attempt to drop the target from all slots it occupies, or the slots
        provided. This function is messy in that it doesn't care if the
        slots exist or not, it just tries to drop everything it is given. This
        function will return a dict of any emptied slots, so it can act as a
        pop(), but if you don't catch that data, it WILL be lost.
        """
        if slots and not isinstance(slots, dict):
            return StatMsg(False, "You have to declare slots in the form "
                           "`{key: [values]}`.")

        modified = {}
        arrays = self.obj.attributes.get(category="slots", return_obj=True)
        if not isinstance(arrays, list):
            arrays = [arrays]

        # If no slots are declared, the object should be dropped from all slots
        # without regard for which slots the object thinks that it should be
        # occupying.
        if not arrays:
            return StatMsg(False, "You don't seem to have any slots to use.")
        if not slots:
            slots = [array.key for array in arrays]

        # At this point, the attribute objects only get in the way, so we
        # extract the values.
        arrays = {array.key: array.value for array in arrays}

        for name in slots:
            new = {}
            mod = []

            if isinstance(slots, (list, tuple, set)):
                # If the input is not a dict, it is interpreted as a list of
                # category names and all slots are emptied of the target.
                for slot, contents in arrays[name].items():
                    if contents is target:
                        new.update({slot: ''})
                        mod.append(slot)
            elif isinstance(slots, dict):
                # If the input is a dict, only named slots will be emptied.
                # Numbered slots should be specified as a single number.
                i = 0
                numbered = [k for k in slots[name] if isinstance(k, int)]
                numbered = [i + 1 for k in numbered for i in range(i, k)]
                named = [k for k in slots[name] if isinstance(k, str)]
                for slot in named:
                    if arrays[name][slot] is target:
                        new.update({slot: ''})
                        mod.append(slot)
                for i in range(0, len(numbered)):
                    for check in arrays[name]:
                        if isinstance(check, int) and arrays[name][check] is target:
                            new.update({check: ''})
                            mod.append(check)

            else:
                return StatMsg(False, "The slots requested are not in an "
                               "appropriate type (a list, tuple, or set "
                               "of attribute names, or a dict of category "
                               "and slot names).")

            comp = len(mod)
            # mod = [s for s in mod if not isinstance(s, int)]
            # mod[0:0] = [comp - len(mod) if comp - len(mod) > 0]

            arrays[name].update(new)
            modified.update({name: mod})

        return {k: v for k, v in modified.items() if v}

    def where(self, target):
        "Return a dict of slots representing where target is attached."

        arrays = self.obj.attributes.get(category="slots", return_obj=True)
        if not isinstance(arrays, list):
            arrays = [arrays]
        arrays = {array.key: array.value for array in arrays}

        # Filter out all empty entries.
        r = {name: [s for s, c in slots.items() if c is target]
             for name, slots in arrays.items()}
        r = {name: contents for name, contents in r.items() if contents}

        return r
