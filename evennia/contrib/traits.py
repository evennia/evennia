"""
Traits

Whitenoise 2014, Ainneve contributors,
Griatch 2020


A `Trait` represents a modifiable property of (usually) a Character. They can
be used to represent everything from attributes (str, agi etc) to skills
(hunting, swords etc) or effects (poisoned, rested etc) and has extra
functionality beyond using plain Attributes for this.

Traits use Evennia Attributes under the hood, making them persistent (they survive
a server reload/reboot).

### Adding Traits to a typeclass

To access and manipulate tragts on an object, its Typeclass needs to have a
`TraitHandler` assigned it. Usually, the handler is made available as `.traits`
(in the same way as `.tags` or `.attributes`).

Here's an example for adding the TraitHandler to the base Object class:

    ```python
    # mygame/typeclasses/objects.py

    from evennia import DefaultObject
    from evennia.utils import lazy_property
    from evennia.contrib.traits import TraitHandler

    # ...

    class Object(DefaultObject):
        ...
        @lazy_property
        def traits(self):
            # this adds the handler as .traits
            return TraitHandler(self)

    ```

### Trait Configuration

A single Trait can be one of three basic types:

- `Static` - this means a base value and an optional modifier. A typical example would be
  something like a Strength stat or Skill value. That is, something that varies slowly or
  not at all.
- `Counter` - a Trait of this type has a base value and a current value that
  can vary inside a specified range. This could be used for skills that can only incrase
  to a max value.
- `Gauge` - Modified counter type modeling a refillable "gauge" that varies between "empty"
  and "full". The classic example is a Health stat.


    ```python
    obj.traits.add("hp", name="Health", type="static",
                   base=0, mod=0, min=None, max=None, extra={})
```

All traits have a read-only `actual` property that will report the trait's
actual value.

Example:

    ```python
    >>> hp = obj.traits.hp
    >>> hp.actual
    100
```

They also support storing arbitrary data via either dictionary key or
attribute syntax. Storage of arbitrary data in this way has the same
constraints as any nested collection type stored in a persistent Evennia
Attribute, so it is best to avoid attempting to store complex objects.

#### Static Trait Configuration

A static `Trait` stores a `base` value and a `mod` modifier value.
The trait's actual value is equal to `base`+`mod`.

Static traits can be used to model many different stats, such as
Strength, Character Level, or Defense Rating in many tabletop gaming
systems.

Constructor Args:
    name (str): name of the trait
    type (str): 'static' for static traits
    base (int, float): base value of the trait
    mod (int, optional): modifier value
    extra (dict, optional): keys of this dict are accessible on the
        `Trait` object as attributes or dict keys

Properties:
    actual (int, float): returns the value of `mod`+`base` properties
    extra (list[str]): list of keys stored in the extra data dict

Methods:
    reset_mod(): sets the value of the `mod` property to zero

Examples:

    '''python
    >>> char.traits.add("str", "Strength", base=5)
    >>> strength = char.traits.str
    >>> strength.actual
    5
    >>> strength.mod = 2            # add a bonus to strength
    >>> str(strength)
    'Strength               7 (+2)'
    >>> strength.reset_mod()        # clear bonuses
    >>> str(strength)
    'Strength               5 (+0)'
    >>> strength.newkey = 'newvalue'
    >>> strength.extra
    ['newkey']
    >>> strength
    Trait({'name': 'Strength', 'type': 'trait', 'base': 5, 'mod': 0,
    'min': None, 'max': None, 'extra': {'newkey': 'newvalue'}})
    ```

#### Counter Trait Configuration

Counter type `Trait` objects have a `base` value similar to static
traits, but adds a `current` value and a range along which it may
vary. Modifier values are applied to this `current` value instead
of `base` when determining the `actual` value. The `current` can
also be reset to its `base` value by calling the `reset_counter()`
method.

Counter style traits are best used to represent game traits such as
carrying weight, alignment points, a money system, or bonus/penalty
counters.

Constructor Args:
    (all keys listed above for 'static', plus:)
    min Optional(int, float, None): default None
        minimum allowable value for current; unbounded if None
    max Optional(int, float, None): default None
        maximum allowable value for current; unbounded if None

Properties:
    actual (int, float): returns the value of `mod`+`current` properties

Methods:
    reset_counter(): resets `current` equal to the value of `base`

Examples:

    ```python
    >>> char.traits.add("carry", "Carry Weight", base=0, min=0, max=10000)
    >>> carry = caller.traits.carry
    >>> str(carry)
    'Carry Weight           0 ( +0)'
    >>> carry.current -= 3           # try to go negative
    >>> carry                        # enforces zero minimum
    'Carry Weight           0 ( +0)'
    >>> carry.current += 15
    >>> carry
    'Carry Weight          15 ( +0)'
    >>> carry.mod = -5               # apply a modifier to reduce
    >>> carry                        # apparent weight
    'Carry Weight:         10 ( -5)'
    >>> carry.current = 10000        # set a semi-large value
    >>> carry                        # still have the modifier
    'Carry Weight        9995 ( -5)'
    >>> carry.reset()                # remove modifier
    >>> carry
    'Carry Weight        10000 ( +0)'
    >>> carry.reset_counter()
    >>> carry
    0
    ```

#### Gauge Trait Configuration

A "gauge" type `Trait` is a modified counter trait used to model a
gauge that can be emptied and refilled. The `base` property of a
gauge trait represents its "full" value. The `mod` property increases
or decreases that "full" value, rather than the `current`.

Gauge type traits are best used to represent traits such as health
points, stamina points, or magic points.

By default gauge type traits have a `min` of zero, and a `max` set
to the `base`+`mod` properties. A gauge will still work if its `max`
property is set to a value above its `base` or to None.

Constructor Args:
    (all keys listed above for 'static', plus:)
    min Optional(int, float, None): default 0
        minimum allowable value for current; unbounded if None
    max Optional(int, float, None, 'base'): default 'base'
        maximum allowable value for current; unbounded if None;
        if 'base', returns the value of `base`+`mod`.

Properties:
    actual (int, float): returns the value of the `current` property

Methods:
    fill_gauge(): adds the value of `base`+`mod` to `current`
    percent(): returns the ratio of actual value to max value as
        a percentage. if `max` is unbound, return the ratio of
        `current` to `base`+`mod` instead.

Examples:

    ```python
    >>> caller.traits.add("hp", "Health", base=10)
    >>> hp = caller.traits.hp
    >>> repr(hp)
    GaugeTrait({'name': 'HP', 'type': 'gauge', 'base': 10, 'mod': 0,
    'min': 0, 'max': 'base', 'current': 10, 'extra': {}})
    >>> str(hp)
    'HP:           10 /   10 ( +0)'
    >>> hp.current -= 6                    # take damage
    >>> str(hp)
    'HP:            4 /   10 ( +0)'
    >>> hp.current -= 6                    # take damage to below min
    >>> str(hp)
    'HP:            0 /   10 ( +0)'
    >>> hp.fill()                          # refill trait
    >>> str(hp)
    'HP:           10 /   10 ( +0)'
    >>> hp.current = 15                    # try to set above max
    >>> str(hp)                            # disallowed because max=='actual'
    'HP:           10 /   10 ( +0)'
    >>> hp.mod += 3                        # bonus on full trait
    >>> str(hp)                            # buffs flow to current
    'HP:           13 /   13 ( +3)'
    >>> hp.current -= 5
    >>> str(hp)
    'HP:            8 /   13 ( +3)'
    >>> hp.reset()                         # remove bonus on reduced trait
    >>> str(hp)                            # debuffs do not affect current
    'HP:            8 /   10 ( +0)'
            ```
"""

from django.conf import settings
from functools import total_ordering
from evennia.utils.dbserialize import _SaverDict
from evennia.utils import logger
from evennia.utils.utils import inherits_from, class_from_module


# This way the user can easily supply their own. Each
# class should have a class-property `trait_type` to
# identify the Trait class. The default ones are "static",
# "counter" and "gauge".

_TRAIT_CLASS_PATHS = [
    "evennia.contrib.traits.StaticTrait",
    "evennia.contrib.traits.CounterTrait",
    "evennia.contrib.traits.GaugeTrait",
]

if hasattr(settings, "TRAIT_CLASS_PATHS"):
    _TRAIT_CLASS_PATHS += settings.TRAIT_CLASS_PATHS

# delay trait-class import to avoid circular import
_TRAIT_CLASSES = None


def _delayed_import_trait_classes():
    """
    Import classes based on the given paths. Note that
    imports from settings are last in the list, so if they
    have the same trait_type set, they will replace the
    default.
    """
    global _TRAIT_CLASSES
    if _TRAIT_CLASSES is None:
        _TRAIT_CLASSES = {}
        for classpath in _TRAIT_CLASS_PATHS:
            try:
                cls = class_from_module(classpath)
            except ImportError:
                logger.log_trace(f"Could not import Trait from {classpath}.")
            else:
                if hasattr(cls, "trait_type"):
                    trait_type = cls.trait_type
                else:
                    trait_type = str(cls.__name___).lower()
                _TRAIT_CLASSES[trait_type] = cls


_GA = object.__getattribute__
_SA = object.__setattr__

# this is the default we offer in TraitHandler.add
DEFAULT_TRAIT_TYPE = "static"


class TraitException(Exception):
    """
    Base exception class raised by `Trait` objects.

    Args:
        msg (str): informative error message

    """

    def __init__(self, msg):
        self.msg = msg


class MandatoryTraitKey:
    """
    This represents a required key that must be
    supplied when a Trait is initialized. It's used
    by Trait classes when defining their required keys.
    """


class TraitHandler:
    """
    Factory class that instantiates Trait objects.

    """

    def __init__(self, obj, db_attribute_key="traits", db_attribute_category="traits"):
        """
        Initialize the handler and set up its internal Attribute-based storage.

        Args:
            obj (Object): Parent Object typeclass for this TraitHandler
            db_attribute_key (str): Name of the DB attribute for trait data storage

        """
        # load the available classes, if necessary
        _delayed_import_trait_classes()

        # Note that this retains the connection to the database, meaning every
        # update we do to .trait_data automatically syncs with database.
        self.trait_data = obj.attributes.get(db_attribute_key, category=db_attribute_category)
        if self.trait_data is None:
            # no existing storage; initialize it
            obj.attributes.add(db_attribute_key, {}, category=db_attribute_category)
            self.trait_data = {}
        self._cache = {}

    def __len__(self):
        """Return number of Traits registered with the handler"""
        return len(self.trait_data)

    def __setattr__(self, key, value):
        """Returns error message if trait objects are assigned directly."""
        if key in ("trait_data", "_cache"):
            _SA(self, key, value)
        else:
            raise TraitException(
                "Trait object not settable directly. Assign to one of "
                f"`{key}.base`, `{key}.mod`, or `{key}.current` instead."
            )

    def __setitem__(self, key, value):
        """Returns error message if trait objects are assigned directly."""
        return self.__setattr__(key, value)

    def __getattr__(self, key):
        """Returns Trait instances accessed as attributes."""
        return self.get(key)

    def __getitem__(self, key):
        """Returns `Trait` instances accessed as dict keys."""
        return self.get(key)

    def __repr__(self):
        return "TraitHandler ({num} Trait(s) stored): {keys}".format(
            num=len(self), keys=", ".join(self.all)
        )

    @property
    def all(self):
        """
        Get all trait keys in this handler.

        Returns:
            list: All Trait keys.

        """
        return list(self.trait_data.keys())

    def get(self, key):
        """
        Args:
            trait (str): key from the traits dict containing config data
                for the trait. "all" returns a list of all trait keys.

        Returns:
            (`Trait` or `None`): named Trait class or None if trait key
            is not found in traits collection.

        """
        trait = self._cache.get(key)
        if trait is None and key in self.trait_data:
            trait_type = self.trait_data[key]["trait_type"]
            try:
                trait_cls = _TRAIT_CLASSES[trait_type]
            except KeyError:
                raise TraitException("Trait class for {trait_type} could not be found.")
            trait = self._cache[key] = trait_cls(_GA(self, "trait_data")[key])
        return trait

    def add(self, key, name=None, trait_type=DEFAULT_TRAIT_TYPE, force=True, **trait_properties):
        """
        Create a new Trait and add it to the handler.

        Args:
            key (str): This is the name of the property that will be made
                available on this handler (example 'hp').
            name (str, optional): Name of the Trait, like "Health". If
                not given, will use `key` starting with a capital letter.
            trait_type (str, optional): One of 'static', 'counter' or 'gauge'.
            force_add (bool): If set, create a new Trait even if a Trait with
                the same `key` already exists.
            trait_properties (dict): These will all be use to initialize
                the new trait. See the `properties` class variable on each
                Trait class to see which are required.

        Raises:
            TraitException: If specifying invalid values for the given Trait,
                the `trait_type` is not recognized, or an existing trait
                already exists (and `force` is unset).

        """
        # from evennia import set_trace;set_trace()

        if key in self.trait_data:
            if force:
                self.remove(key)
            else:
                raise TraitException(f"Trait '{key}' already exists.")

        trait_class = _TRAIT_CLASSES.get(trait_type)
        if not trait_class:
            raise TraitException("Trait-type '{trait_type} is invalid.")

        trait_properties["name"] = key.title() if not name else name
        trait_properties["trait_type"] = trait_type

        # this will raise exception if input is insufficient
        trait_properties = trait_class.validate_input(trait_properties)

        print("trait_properties", trait_properties)

        self.trait_data[key] = trait_properties

    def remove(self, key):
        """
        Remove a Trait from the handler's parent object.

        Args:
            key (str): The name of the trait to remove.

        """
        if key not in self.trait_data:
            raise TraitException(f"Trait '{key}' not found.")

        if key in self._cache:
            del self._cache[key]
        del self.trait_data[key]

    def clear(self):
        """
        Remove all Traits from the handler's parent object.
        """
        for key in self.all:
            self.remove(key)


# Parent Trait class


class Trait:
    """Represents an object or Character trait.

    Note:
        See module docstring for configuration details.

    """
    # this is the name used to refer to this trait when adding
    # a new trait in the TraitHandler
    trait_type = "trait"

    # Keys required when creating a Trait of this type. This is a dict
    # of key: default. If a key must be given, use traits.TraitKeyRequired
    # as its value - this means the key must be explicitly set or
    # the trait will not be able to be created.
    # Apart from the keys given here, "name" and "trait_type" will also
    # always have to be a apart of the data.
    data_keys = {}

    # enable to set/retrieve other arbitrary properties on the Trait
    # and have them treated like data to store.
    allow_extra_properties = True

    def __init__(self, trait_data):
        """
        This both initializes and validates the Trait on creation. It must
        raise exception if validation fails. The TraitHandler will call this
        when the trait is furst added, to make sure it validates before
        storing.

        Args:
            trait_data (any): Any pickle-able values to store with this trait.
                This must contain any cls.data_keys that do not have a default
                value in cls.data_default_values. Any extra kwargs will be made
                available as extra properties on the Trait, assuming the class
                variable `allow_extra_properties` is set.

        Raises:
            TraitException: If input-validation failed.

        """
        self._data = self.__class__.validate_input(trait_data)

        if not isinstance(trait_data, _SaverDict):
            logger.log_warn(
                f"Non-persistent Trait data (type(trait_data)) "
                f"loaded for {type(self).__name__}."
            )

    @classmethod
    def validate_input(cls, trait_data):
        """
        Validate input

        """
        req = set(list(cls.data_keys.keys()) + ["name", "trait_type"])
        inp = set(trait_data.keys())
        unsets = req.difference(inp.intersection(req))
        unset_defaults = {key: cls.data_keys[key] for key in unsets}

        if MandatoryTraitKey in unset_defaults.values():
            # we have one or more unset keys that was mandatory
            unset_required = [key for key, value in unset_defaults.items()
                              if value == MandatoryTraitKey]
            raise TraitException(
                "Trait {} could not be created - misses required keys {}".format(
                    cls.trait_type, ", ".join(unset_required)
                )
            )
        # apply the default values
        trait_data.update(unset_defaults)

        if not cls.allow_extra_properties:
            # don't allow any extra properties - remove the extra data
            for key in inp.difference(req) not in ("name", "trait_type"):
                del trait_data[key]

        return trait_data

    # Grant access to properties on this Trait.

    def __getitem__(self, key):
        """Access extra parameters as dict keys."""
        try:
            return self.__getattr__(key)
        except AttributeError:
            raise KeyError(key)

    def __setitem__(self, key, value):
        """Set extra parameters as dict keys."""
        self.__setattr__(key, value)

    def __delitem__(self, key):
        """Delete extra parameters as dict keys."""
        self.__delattr__(key)

    def __getattr__(self, key):
        """Access extra parameters as attributes."""
        if key in ("data_keys", "data_default", "trait_type", "allow_extra_properties"):
            return _GA(self, key)
        try:
            return self._data[key]
        except KeyError:
            raise AttributeError(
                "{!r} {} ({}) has no attribute {!r}.".format(
                    self._data['name'],
                    type(self).__name__,
                    self.trait_type,
                    key)
            )

    def __setattr__(self, key, value):
        """Set extra parameters as attributes.

        Arbitrary attributes set on a Trait object will be
        stored in the 'extra' key of the `_data` attribute.

        This behavior is enabled by setting the instance
        variable `_locked` to True.

        """
        propobj = getattr(self.__class__, key, None)
        if isinstance(propobj, property):
            # we have a custom property named as this key, find and use its setter
            if propobj.fset:
                propobj.fset(self, value)
            return
        else:
            # this is some other value
            if key in ("_data", ):
                _SA(self, key, value)
                return
            if _GA(self, "allow_extra_properties"):
                _GA(self, "_data")[key] = value
                return
        raise AttributeError(f"Can't set attribute {key} on "
                             f"{self.trait_type} Trait.")

    def __delattr__(self, key):
        """Delete extra parameters as attributes."""
        if key not in _GA(self, properties) and key in self._data:
            del self._data[key]

    def __repr__(self):
        """Debug-friendly representation of this Trait."""
        return "{}({{{}}})".format(
            type(self).__name__,
            ", ".join(
                ["'{}': {!r}".format(k, self._data[k]) for k in self._keys if k in self._data]
            ),
        )

    def __str__(self):
        return f"<Trait {self.name}>"

    # access properties

    @property
    def name(self):
        """Display name for the trait."""
        return self._data["name"]

    key = name


@total_ordering
class NumericTrait(Trait):
    """
    Base trait for all Traits based on numbers. This implements
    number-comparisons, limits etc. It also features a "modifier" to the value,
    since this is a common use.

    """

    trait_type = "numeric"

    data_keys = {
        "base": 0
    }

    # Numeric operations

    def __eq__(self, other):
        """Support equality comparison between Traits or Trait and numeric.

        Note:
            This class uses the @functools.total_ordering() decorator to
            complete the rich comparison implementation, therefore only
            `__eq__` and `__lt__` are implemented.
        """
        if inherits_from(other, Trait):
            return self.actual == other.actual
        elif type(other) in (float, int):
            return self.actual == other
        else:
            return NotImplemented

    def __lt__(self, other):
        """Support less than comparison between `Trait`s or `Trait` and numeric."""
        if inherits_from(other, Trait):
            return self.actual < other.actual
        elif type(other) in (float, int):
            return self.actual < other
        else:
            return NotImplemented

    def __pos__(self):
        """Access `actual` property through unary `+` operator."""
        return self.actual

    def __add__(self, other):
        """Support addition between `Trait`s or `Trait` and numeric"""
        if inherits_from(other, Trait):
            return self.actual + other.actual
        elif type(other) in (float, int):
            return self.actual + other
        else:
            return NotImplemented

    def __sub__(self, other):
        """Support subtraction between `Trait`s or `Trait` and numeric"""
        if inherits_from(other, Trait):
            return self.actual - other.actual
        elif type(other) in (float, int):
            return self.actual - other
        else:
            return NotImplemented

    def __mul__(self, other):
        """Support multiplication between `Trait`s or `Trait` and numeric"""
        if inherits_from(other, Trait):
            return self.actual * other.actual
        elif type(other) in (float, int):
            return self.actual * other
        else:
            return NotImplemented

    def __floordiv__(self, other):
        """Support floor division between `Trait`s or `Trait` and numeric"""
        if inherits_from(other, Trait):
            return self.actual // other.actual
        elif type(other) in (float, int):
            return self.actual // other
        else:
            return NotImplemented

    # commutative property
    __radd__ = __add__
    __rmul__ = __mul__

    def __rsub__(self, other):
        """Support subtraction between `Trait`s or `Trait` and numeric"""
        if inherits_from(other, Trait):
            return other.actual - self.actual
        elif type(other) in (float, int):
            return other - self.actual
        else:
            return NotImplemented

    def __rfloordiv__(self, other):
        """Support floor division between `Trait`s or `Trait` and numeric"""
        if inherits_from(other, Trait):
            return other.actual // self.actual
        elif type(other) in (float, int):
            return other // self.actual
        else:
            return NotImplemented

    # Public members

    @property
    def actual(self):
        "The actual value of the trait"
        return self.base_mod_base()

    @property
    def base(self):
        """The trait's base value.

        Note:
            The setter for this property will enforce any range bounds set
            on this `Trait`.
        """
        return self._data["base"]


# Implementation of the respective Trait types


class StaticTrait(NumericTrait):
    """
    Static Trait. This has a modification value.

    """
    trait_type = "static"

    data_keys = {
        "base": 0,
        "mod": 0
    }

    def __str__(self):
        status = "{actual:11}".format(actual=self.actual)
        return "{name:12} {status} ({mod:+3})".format(name=self.name, status=status, mod=self.mod)

    # Helpers

    @property
    def mod(self):
        """The trait's modifier."""
        return self._data["mod"]

    @mod.setter
    def mod(self, amount):
        if type(amount) in (int, float):
            self._data["mod"] = amount

    @property
    def actual(self):
        "The actual value of the Trait"
        return self.base + self.mod


class CounterTrait(NumericTrait):
    """
    Counter Trait.

    This includes modifications and min/max limits as well as the notion of a
    current value.  The value can also be reset to the base value.

    """

    trait_type = "counter"

    data_keys = {
        "base": 0,
        "mod": 0,
        "current": 0,
        "min_value": None,
        "max_value": None,
    }

    # Helpers

    def _mod_base(self):
        """Calculate adding base and modifications"""
        return self._enforce_bounds(self.mod + self.base)

    def _mod_current(self):
        """Calculate the current value"""
        return self._enforce_bounds(self.mod + self.current)

    def _enforce_bounds(self, value):
        """Ensures that incoming value falls within trait's range."""
        if self.min is not None and value <= self.min:
            return self.min
        if self._data["max_value"] == "base" and value >= self.mod + self.base:
            return self.mod + self.base
        if self.max is not None and value >= self.max:
            return self.max
        return value

    # properties

    @property
    def actual(self):
        "The actual value of the Trait"
        return self._mod_current()

    @property
    def base(self):
        return self._data["base"]

    @base.setter
    def base(self, amount):
        if self._data.get("max_value", None) == "base":
            self._data["base"] = amount
        if type(amount) in (int, float):
            self._data["base"] = self._enforce_bounds(amount)

    @property
    def min(self):
        return self._data["min_value"]

    @min.setter
    def min(self, amount):
        if amount is None:
            self._data["min_value"] = amount
        elif type(amount) in (int, float):
            self._data["min_value"] = amount if amount < self.base else self.base

    @property
    def max(self):
        if self._data["max_value"] == "base":
            return self._mod_base()
        return self._data["max_value"]

    @max.setter
    def max(self, value):
        """The maximum value of the `Trait`.

        Note:
            This property may be set to the string literal 'base'.
            When set this way, the property returns the value of the
            `mod`+`base` properties.
        """
        if value == "base" or value is None:
            self._data["max_value"] = value
        elif type(value) in (int, float):
            self._data["max_value"] = value if value > self.base else self.base

    @property
    def current(self):
        """The `current` value of the `Trait`."""
        return self._data.get("current", self.base)

    @current.setter
    def current(self, value):
        if type(value) in (int, float):
            self._data["current"] = self._enforce_bounds(value)

    def reset_mod(self):
        """Clears any mod value to 0."""
        self.mod = 0

    def reset(self):
        """Resets `current` property equal to `base` value."""
        self.current = self.base

    def percent(self):
        """Returns the value formatted as a percentage."""
        if self.max:
            return "{:3.1f}%".format(self.current * 100.0 / self.max)
        elif self.base != 0:
            return "{:3.1f}%".format(self.current * 100.0 / self._mod_base())
        # if we get to this point, it's may be a divide by zero situation
        return "100.0%"


class GaugeTrait(CounterTrait):
    """
    Gauge Trait.

    This emulates a gauge-meter that can be reset.

    """

    trait_type = "gauge"

    # same as Counter, here for easy reference
    data_keys = {
        "base": 0,
        "mod": 0,
        "current": 0,
        "min_value": None,
        "max_value": None,
    }

    def __str__(self):
        status = "{actual:4} / {base:4}".format(actual=self.actual, base=self.base)
        return "{name:12} {status} ({mod:+3})".format(name=self.name, status=status, mod=self.mod)

    @property
    def actual(self):
        "The actual value of the trait"
        return self.current

    @property
    def mod(self):
        """The trait's modifier."""
        return self._data["mod"]

    @mod.setter
    def mod(self, amount):
        if type(amount) in (int, float):
            self._data["mod"] = amount
            delta = amount - self._data["mod"]
            if delta >= 0:
                # apply increases to current
                self.current = self._enforce_bounds(self.current + delta)
            else:
                # but not decreases, unless current goes out of range
                self.current = self._enforce_bounds(self.current)

    @property
    def current(self):
        """The `current` value of the `Trait`."""
        return self._data.get("current", self._mod_base())

    @current.setter
    def current(self, value):
        if type(value) in (int, float):
            self._data["current"] = self._enforce_bounds(value)

    def fill_gauge(self):
        """Adds the `mod`+`base` to the `current` value.

        Note:
            Will honor the upper bound if set.

        """
        self.current = self._enforce_bounds(self.current + self._mod_base())
