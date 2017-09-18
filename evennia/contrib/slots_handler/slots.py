"""
Slots Handler

This class is designed to sit on typeclassed objects and allow for other
objects to be attached to configurable slots on the handler-endowed object.

Built by DamnedScholar (https://github.com/damnedscholar)
"""


from collections import OrderedDict
import evennia
from evennia.objects.objects import DefaultObject
from evennia.utils.dbserialize import _SaverDict, _SaverList, _SaverSet


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

    def __defrag_nums(self, cats):
        "Worker function to consolidate filled numbered slots."
        if not isinstance(cats, list):
            cats = [cats]

        arrays = self.all(obj=True)
        arrays = [a for a in arrays if a.key in cats]

        for a in arrays:
            slots = a.value
            out = {k: v for k, v in slots.items() if isinstance(k, str)}
            numbered = [(k, v) for k, v in slots.items() if isinstance(k, int)]
            keys = [n[0] for n in numbered]
            values = [n[1] for n in numbered]
            d = len(values) - 1
            empty = [values.pop(0) for i in range(0, d) if values[0] == ""]
            numbered = zip(keys, values + empty)
            out.update(numbered)
            self.obj.attributes.add(a.key, out, category="slots")

    # Public methods
    def all(self, obj=False):
        """
        Args:
            obj (bool): Whether or not to return the attribute objects.
                (Default: False)

        Returns:
            slots (dict): A dict of all slots.
        """
        d = self.obj.attributes.get(category="slots", return_obj=True)

        if not d:
            return {}
        elif not isinstance(d, list):
            d = [d]

        if obj:
            # Return attribute objects if requested.
            return d
        else:
            # Return a dict detached from the database.
            r = {s.key: s.value for s in d}
            return r

    def add(self, slots):
        """
        Create arrays of slots, or add additional slots to existing arrays.

        Args:
            slots (dict): A dict of slots to add. Since you can't add empty
                categories, it would be pointless to pass a list to this
                function, and so it doesn't accept lists for input.

        Returns:
            slots (dict): A dict of slots that have been successfully added.
        """

        if not isinstance(slots, (dict, _SaverDict)):
            raise Exception("You have to declare slots in the form "
                            "`{key: [values]}`.")

        arrays = {a.key: a for a in self.obj.slots.all(obj=True)}
        modified = {}
        for name in slots:
            existing = arrays.get(name, False)
            # Add all string values to the slot list.
            to_add = [k for k in slots[name] if isinstance(k, str)]
            # Iterate through numerical values in the input and store the sum.
            requirement = [n for n in slots[name] if isinstance(n, int)] + [0]
            requirement = sum(requirement)
            highest = 0
            if existing:
                array = existing.value
                numbered = [k for k in array if isinstance(k, int)] + [0]
                highest = sorted(numbered)[-1]
            for i in range(highest, highest + requirement):
                to_add.append(i+1)
            to_add = {slot: "" for slot in to_add}

            if not existing:
                self.obj.attributes.add(name, to_add, category="slots")
                new = self.obj.attributes.get(name, category="slots")
                modified.update(new)
            else:
                array.update(to_add)
                modified.update(array)

        return modified

    def delete(self, slots):
        """
        This will delete slots from an existing array.
        WARNING: If you have anything attached in slots when they are removed,
        the slots' contents will also be removed. This function will return a
        dict of any removed slots and their contents, so it can act as a pop(),
        but if you don't catch that data, it WILL be lost.

        Args:
            slots (list or dict): Slot categories or individual slots to
                delete.

        Returns:
            slots (dict): A dict of slots that have been successfully deleted
                and their contents.
        """

        if not isinstance(slots, (dict, _SaverDict, list, _SaverList)):
            raise Exception("You have to declare slots in the form "
                            "`{key: [values]}`, or categories in the form "
                            "`[values]`.")

        arrays = {a.key: a for a in self.obj.slots.all(obj=True)}
        deleted = {}
        for name in slots:
            existing = arrays.get(name, False)
            del_temp = {}
            if not existing:
                # If the named array isn't there, skip to the next one.
                break
            array = existing.value

            if isinstance(slots, (list, _SaverList)):
                # If the input is a list, it is interpreted as a list of
                # category names and all slots are deleted.
                deleted.update({name: array})
                self.obj.attributes.delete(name, category="slots")
            elif isinstance(slots, (dict, _SaverDict)):
                # If the input is a dict, only the specific slots indicated
                # will be deleted.
                self.__defrag_nums(existing.key)  # Just in case.
                named = {k: v for k, v in array.items()
                         if isinstance(k, str)}
                numbered = {k: v for k, v in array.items()
                            if isinstance(k, int)}
                to_del = [s for s in slots[name] if isinstance(s, str)]
                highest = sorted(numbered.keys() + [0])[-1]
                del_num = sum([n for n in slots[name] if isinstance(n, int)])
                to_del = to_del + [i for i
                                   in range(highest, highest - del_num, -1)]

                del_temp = {d: array.pop(d) for d in to_del}
                deleted.update({name: del_temp})

        return deleted

    def attach(self, target, slots=None):
        """
        Attempt to attach the target in all slots it consumes. Optionally, the
        target's slots may be overridden.

        Args:
            target (object): The object to be attached.
            slots (list or dict, optional): If slot instructions are given,
                this will completely override any slots on the object.

        Returns:
            slots (dict): A dict of slots that `target` has attached to.
        """

        if not slots:
            slots = target.db.slots
            if not slots:
                slots = target.ndb.slots
                if not slots:
                    try:
                        slots = target.slots
                    except AttributeError:
                        raise Exception("No slots detected.")

        modified = {}

        if not isinstance(slots, (dict, _SaverDict, list, _SaverList)):
            raise Exception("You have to declare slots in the form "
                            "`{key: [values]}`, or categories in the form "
                            "`[values]`.")

        arrays = {a.key: a for a in self.obj.slots.all(obj=True)}
        for name in slots:
            array = arrays.get(name, False)
            if not array:
                raise Exception("You need to add slots before you can "
                                "attach things to them.")
            else:
                array = array.value

            new = {}

            if isinstance(slots, (dict, _SaverDict)):
                # Get the number of open slots, then count to see if there are
                # enough for the attachment.
                numbered = [n for n in array.keys()
                            if isinstance(n, int) and not array[n]]
                requirement = [n for n in slots[name] if isinstance(n, int)]
                requirement = sum(requirement + [0])
                if len(numbered) < requirement:
                    raise Exception("You're running out of numbered "
                                    "slots. You need to add or free up slots "
                                    "before you can attach this.")

                if numbered:
                    new.update({numbered[i]: target
                                for i in range(0, requirement)})

                # Get the list of open named slots and check to see if all of
                # the requested slots are members of them.
                named = [n for n in array.keys()
                         if isinstance(n, str) and not array[n]]
                requirement = [n for n in slots[name] if isinstance(n, str)]
                if requirement and not set(requirement).issubset(named):
                    raise Exception("You're running out of named slots. "
                                    "You need to add or free up slots before "
                                    "you can attach this.")

                if named:
                    new.update({req: target
                                for req in requirement})

            elif isinstance(slots, (list, _SaverList)):
                for slot, contents in array.items():
                    if contents == "":
                        new.update({slot: target})

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

        Args:
            target (object or `None`): The object being dropped.
            slots (dict or list, optional): Slot categories or individual slots
                to drop from.

        Returns:
            slots (dict): A dict of slots that have been emptied.
        """

        arrays = self.obj.slots.all()
        if not slots:
            slots = arrays.keys()

        if not isinstance(slots, (dict, _SaverDict, list, _SaverList)):
            raise Exception("You have to declare slots in the form "
                            "`{key: [values]}`, or categories in the form "
                            "`[values]`.")

        modified = {}

        # If no slots are declared, the object should be dropped from all slots
        # without regard for which slots the object thinks that it should be
        # occupying.
        if not arrays:
            raise Exception("You don't seem to have any slots to use.")
        if not slots:
            slots = [cat for cat in arrays.keys()]

        for name in slots:
            new = {}
            mod = {}
            array = arrays[name]

            if isinstance(slots, (list, _SaverList)):
                # If the input is a list, it is interpreted as a list of
                # category names and all slots are emptied of the target.
                for slot, contents in array.items():
                    if (target and contents is target) or not target:
                        new.update({slot: ''})
                        mod.update({slot: contents})
            elif isinstance(slots, (dict, _SaverDict)):
                # If the input is a dict, only named slots will be emptied.
                # Numbered slots should be specified as a single number.
                i = 0
                numbered = [k for k in slots[name] if isinstance(k, int)]
                numbered = [i + 1 for k in numbered for i in range(i, k)]
                named = [k for k in slots[name] if isinstance(k, str)]
                for slot in named:
                    if (target and array[slot] is target) or not target:
                        new.update({slot: ''})
                        mod.update({slot: array[slot]})
                for i in range(0, len(numbered)):
                    for check in array:
                        if isinstance(check, int) and array[check] is target:
                            new.update({check: ''})
                            mod.update({check: array[check]})

            else:
                raise Exception("The slots requested are not in an "
                                "appropriate type (a list of attribute names, "
                                "or a dict of category and slot names).")

            arrays[name].update(new)
            modified.update({name: mod})

        self.__defrag_nums(modified.keys())
        return {k: v for k, v in modified.items() if v}

    def replace(self, target, slots=None):
        """
        Works exactly like `.slots.attach`, but first invokes `.slots.drop` on
        all requested slots.

        Args:
            target (object): The object to be attached.
            slots (list or dict, optional): If slot instructions are given,
                this will completely override any slots on the object.

        Returns:
            results (tuple): The results of both commands are returned as a
                tuple in the form `(drop, attach)`.
        """

        if not slots:
            slots = target.db.slots
            if not slots:
                slots = target.ndb.slots
                if not slots:
                    try:
                        slots = target.slots
                    except AttributeError:
                        raise Exception("You have to either have slots on "
                                        "the target or declare them in the "
                                        "method call.")

        drop = self.obj.slots.drop(None, slots)
        attach = self.obj.slots.attach(target, slots)

        return (drop, attach)

    def where(self, target):
        """
        Returns:
            slots (dict): Slots where `target` is attached.
        """

        arrays = self.obj.slots.all()
        # Filter out all empty entries.
        r = {name: [s for s, c in slots.items() if c is target]
             for name, slots in arrays.items()}
        r = {name: contents for name, contents in r.items() if contents}

        return r


class SlottedObject(DefaultObject):
    """
    This is a demo object for SlotsHandler, which can be used as a parent or
    a mixin.
    """

    @lazy_property
    def slots(self):
        return SlotsHandler(self)


class SlottableObject(DefaultObject):
    """
    This is a demo object for SlotsHandler.
    """

    def at_object_creation(self):
        "Called at object creation."
        self.db.slots = {"addons": ["left"]}
