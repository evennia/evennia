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
            trait = self._cache[key] = trait_cls(self.trait_data[key])
        return trait

    def add(
        self,
        key,
        name=None,
        trait_type=DEFAULT_TRAIT_TYPE,
        base=0,
        modifier=0,
        min_value=None,
        max_value=None,
        force=False,
        **extra_properties,
    ):
        """
        Create a new Trait and add it to the handler.

        Args:
            key (str): This is the name of the property that will be made
                available on this handler (example 'hp').
            name (str, optional): This is a longer name used in Trait
                string representation (example 'Health'). If not given, this
                will be set the same as `key`, starting with a capital letter.
            trait_type (str, optional): One of 'static', 'counter' or 'gauge'.
            base (int or float, optional): The base value, or 'full' value in the case
                of a gauge.
            modifier (int, optional): A modifier affecting the current or base value.
            min_value (int or float, optional): The minimum allowed value.
            max_value (int or float, optional): The maximum allowed value.
            force (bool, optional): Always add, replacing any existing trait.
            **extra_properties (any): All other kwargs will be made available as key:value
                properties on the handler. These must all be possible to store
                in an Attribute.

        Raises:
            TraitException: If specifying invalid values or an existing trait
                already exists (and `force` is unset).

        """
        # from evennia import set_trace;set_trace()

        if key in self.trait_data:
            if force:
                self.remove(key)
            else:
                raise TraitException(f"Trait '{key}' already exists.")

        if trait_type not in _TRAIT_CLASSES:
            raise TraitException("Trait-type '{trait_type} is invalid.")

        trait_kwargs = dict(
            name=name if name is not None else key.title(),
            trait_type=trait_type,
            base=base,
            modifier=modifier,
            min_value=min_value,
            max_value=max_value,
            extra_properties=extra_properties,
        )

        self.trait_data[key] = trait_kwargs

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


@total_ordering
class Trait:
    """Represents an object or Character trait.

    Note:
        See module docstring for configuration details.
    """

    _keys = (
        "name",
        "trait_type",
        "base",
        "modifier",
        "current",
        "min_value",
        "max_value",
        "extra_properties",
    )

    def __init__(self, trait_data):
        """
        Initialize a Trait with stored data.

        Args:
            trait_data (_SaverDict or dict): This will be a _SaverDict if
                passed from the TraitHandler, which means this will automatically
                save itself the database when updating

        """

        self._type = trait_data["trait_type"]
        self._data = trait_data
        self._locked = True

        if not isinstance(trait_data, _SaverDict):
            logger.log_warn(
                f"Non-persistent Trait data (type(trait_data)) "
                f"loaded for {type(self).__name__}."
            )

    # Private helper members

    def _enforce_bounds(self, value):
        """Ensures that incoming value falls within trait's range."""
        if self._type in RANGE_TRAITS:
            if self.min is not None and value <= self.min:
                return self.min
            if self._data["max"] == "base" and value >= self.mod + self.base:
                return self.mod + self.base
            if self.max is not None and value >= self.max:
                return self.max
        return value

    def _mod_base(self):
        return self._enforce_bounds(self.mod + self.base)

    def _mod_current(self):
        return self._enforce_bounds(self.mod + self.current)

    def __repr__(self):
        """Debug-friendly representation of this Trait."""
        return "{}({{{}}})".format(
            type(self).__name__,
            ", ".join(
                ["'{}': {!r}".format(k, self._data[k]) for k in self._keys if k in self._data]
            ),
        )

    def __str__(self):
        status = "{actual:11}".format(actual=self.actual)
        return "{name:12} {status} ({mod:+3})".format(name=self.name, status=status, mod=self.mod)

    # Extra Properties - allow access to properties on Trait

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
        try:
            return self._data["extra_properties"][key]
        except KeyError:
            raise AttributeError(
                "{} '{}' has no attribute {!r}".format(type(self).__name__, self.name, key)
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
            if propobj.fset is None:
                raise AttributeError(f"Can't set attribute {key}.")
            propobj.fset(self, value)
        else:
            if self.__dict__.get("_locked", False) and key not in ("_keys",):
                _GA(self, "_data")["extra_properties"][key] = value
            else:
                _SA(self, key, value)

    def __delattr__(self, key):
        """Delete extra parameters as attributes."""
        if key in self._data["extra_properties"]:
            del self._data["extra_properties"][key]

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
    def name(self):
        """Display name for the trait."""
        return self._data["name"]

    key = name

    @property
    def actual(self):
        "The actual value of the trait"
        return self._mod_base()

    @property
    def base(self):
        """The trait's base value.

        Note:
            The setter for this property will enforce any range bounds set
            on this `Trait`.
        """
        return self._data["base"]

    @base.setter
    def base(self, amount):
        if self._data.get("max", None) == "base":
            self._data["base"] = amount
        if type(amount) in (int, float):
            self._data["base"] = self._enforce_bounds(amount)

    @property
    def mod(self):
        """The trait's modifier."""
        return self._data["modifier"]

    @mod.setter
    def mod(self, amount):
        if type(amount) in (int, float):
            self._data["modifier"] = amount

    @property
    def min(self):
        return self._data["min_value"]

    @min.setter
    def min(self, value):
        self._data["min_value"] = value

    @property
    def max(self):
        return self._data["max_value"]

    @max.setter
    def max(self, value):
        self._data["max_value"] = value

    @property
    def current(self):
        """The `current` value of the `Trait`."""
        return self._data.get("current", self.base)

    @current.setter
    def current(self, value):
        self._data["current"] = value

    @property
    def extra(self):
        """Returns a list containing available extra data keys."""
        return self._data["extra"].keys()

    def reset_mod(self):
        """Clears any mod value to 0."""
        self.mod = 0

    def reset(self):
        """Resets `current` property equal to `base` value."""
        self.current = self.base

    def percent(self):
        """Returns the value formatted as a percentage."""
        return "100.0%"


# Implementation of the respective Trait types


class StaticTrait(Trait):
    """
    Static Trait.

    """

    trait_type = "static"

    @property
    def min(self):
        raise TraitException(f"Static Trait {self.key} has no minimum value.")

    @min.setter
    def min(self):
        raise TraitException(f"Cannot set minimum value for static Trait {self.key}.")

    @property
    def max(self):
        raise TraitException("Static Trait {self.key} has no maximum value.")

    @max.setter
    def max(self):
        raise TraitException("Cannot set maximum value for static Trait {self.key}.")

    @property
    def current(self):
        """The `current` value of the `Trait`. This is the same as base for a Static Trait."""
        return self.base

    @current.setter
    def current(self, value):
        """Current == base for Static Traits."""
        self.base = self.current = value

    def reset(self):
        raise TraitException(f"Cannot reset static Trait {self.key}.")


class CounterTrait(Trait):
    """
    Counter Trait.

    """

    trait_type = "counter"

    @property
    def actual(self):
        "The actual value of the Trait"
        return self._mod_current()

    @property
    def min(self):
        """The lower bound of the range."""
        return super().min

    @min.setter
    def min(self, amount):
        if amount is None:
            self._data["min"] = amount
        elif type(amount) in (int, float):
            self._data["min"] = amount if amount < self.base else self.base

    @property
    def max(self):
        if self._data["max_value"] == "base":
            return self._mod_base()
        return super().max

    @max.setter
    def max(self):
        """The maximum value of the `Trait`.

        Note:
            This property may be set to the string literal 'base'.
            When set this way, the property returns the value of the
            `mod`+`base` properties.
        """
        if self._data["max_value"] == "base":
            return self._mod_base()
        return super().max

    @max.setter
    def max(self, value):
        if value == "base" or value is None:
            self._data["max_value"] = value
        elif type(value) in (int, float):
            self._data["max_value"] = value if value > self.base else self.base

    @property
    def current(self):
        """The `current` value of the `Trait`."""
        return super().current

    @current.setter
    def current(self, value):
        if type(value) in (int, float):
            self._data["current"] = self._enforce_bounds(value)
        else:
            raise AttributeError("'current' property is read-only on static 'Trait'.")

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

    """

    trait_type = "gauge"

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
        return super().mod

    @mod.setter
    def mod(self, amount):
        if type(amount) in (int, float):
            self._data["modifier"] = amount
            delta = amount - self._data["modifier"]
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
        super().current = value

    def fill_gauge(self):
        """Adds the `mod`+`base` to the `current` value.

        Note:
            Will honor the upper bound if set.

        """
        self.current = self._enforce_bounds(self.current + self._mod_base())
