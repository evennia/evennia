"""
Currency Module
'Currency' classes represent monetary values on objects or characters.
They are instantiated by the 'CurrencyHandler' object, which is typically
set up as a property on the object or character's typeclass.

**Setup**
    To use currency on an object, add a function that passes the object
    itself into the constructor and returns a 'CurrencyHandler'. This 
    function should be decorated with the 'lazy_property' decorator.

    Example:
    ```python
        from evennia.utils import lazy_property
        from world.currency import CurrencyHandler

        Class Object(DefaultObject):
        ...
        @lazy_property
        def purse(self):
            return CurrencyHandler(self, db_attribute='purse')
    ```
**Currency Configuration**
    'Currency' objects can be configured with a name and a value (relative to other
    Currency). All currency objects have a settable 'amt' property that contains the 
    amount of that currency type.

    Example:
        ```python
        >>> gp = obj.currency.gp
        >>> gp.amt
        100
        ```

    Constructor Args:
        name(str): name of the currency type
        value(int, float): value based on other currency types in handler
        amt(int, float): amount of currency type held
    
    Methods:
        convert(Currency, Optional amount): Convert between Currency types.
        contents(): List all currencies that have amounts greater than zero
        
    Examples:
        ```python
        >>> purse.CC.convert(self.purse.SC,2)
        Converted 2 silver coin --> 20 copper coin
        >>> purse.CC.amt = 4    # Add 4 copper coins
        >>> str(purse.CC)
        '35 copper coins'
        >>> self.purse.contents
        20 copper coins, 2 silver coins
        >>> purse
        Currency({'CC': {'amt': 35, 'value': 10, 'name': 'copper coin'}, 
        'SC': {'amt': 19, 'value': 100, 'name': 'silver coin'}, 
        'GC': {'amt': 20, 'value': 1000, 'name': 'gold coin'}, 
        'BC': {'amt': 0, 'value': 1, 'name': 'brass coin'}})
"""
from evennia.utils.dbserialize import _SaverDict
from evennia.utils import logger, lazy_property
from functools import total_ordering

class CurrencyException(Exception):
    def __init__(self, msg):
        self.msg = msg

class CurrencyHandler(object):
    def __init__(self, obj, db_attribute='currency'):
        if not obj.attributes.has(db_attribute):
            obj.attributes.add(db_attribute, {})

        self.attr_dict = obj.attributes.get(db_attribute)
        self.cache = {}

    def __len__(self):
        # Return the number of values in 'attr_dict'.
        return len(self.attr_dict)

    def __setattr__(self, key, value):
        # Return an error message if attrib is assigned directly
        if key in ('attr_dict', 'cache'):
            super(CurrencyHandler, self).__setattr__(key, value)
        else:
            raise CurrencyException(
                "Currency object not settable. Assign one of " + 
                "the monetary conversion properties instead."
            )

    def __setitem__(self, key, value):
        # Returns error message if currency objects are assigned directly.
        return self.__setattr__(key, value)

    def __getattr__(self, currency):
        # Returns currency instances accessed as attributes.
        return self.get(currency)

    def __getitem__(self, currency):
        # Returns 'Currency' instances accessed as dict keys.
        return self.get(currency)

    def get(self, currency):
        """
        Args: 
            currency (str): key from the currency dict containing config data
            for the currency type. "all" returns a list of all currency keys
        Returns:
            ('Currency' or 'None'): named Currency class or None if currency key
            is not found in currency collection.
        """
        if currency not in self.cache:
            if currency not in self.attr_dict:
                return None
            data = self.attr_dict[currency]
            self.cache[currency] = Currency(data)
        return self.cache[currency]

    def add(self, key, name, value, amt):
        # Create a new Currency and add it to the handler.
        if key in self.attr_dict:
            raise CurrencyException("Currency '{}' already exists.".format(key))

        currency = dict(name=name,
                     value=value, 
                     amt=amt)

        self.attr_dict[key] = currency

    def remove(self, currency):
        # Remove a Currency type from the handler's parent object.
        if currency not in self.attr_dict:
            raise CurrencyException("Currency not found: {}".format(currency))

        if currency in self.cache:
            del self.cache[currency]
        del self.attr_dict[currency]

    def clear(self):
        # Remove all Currency from the handler's parent object.
        for currency in self.all:
            self.remove(currency)

    @property
    def all(self):
        # Return a list of all currency in this CurrencyHandler.
        return self.attr_dict.keys()

    @property
    def contents(self):
        # Return a formatted list of currency and amounts in this CurrencyHandler.
        liststr = ""
        for key in self.attr_dict.keys():
            cur = Currency(self.attr_dict[key])
            if cur.amt > 0:
                liststr += "{}, ".format(cur)
        if len(liststr.strip()) > 0: return liststr[:-2]
        else: return liststr.strip()

@total_ordering
class Currency(object):
    """
        Represents an object or Character currency.
        Note: 
            See module docstring for configuration details.
    """
    def __init__(self, data):
        if not 'name' in data:
            raise CurrencyException(
                "Required key not found in currency data: 'name'")
        if not 'value' in data:
            raise CurrencyException(
                "Required key not found in currency data: 'value'")
        self._value = data['value']
        if not 'amt' in data:
            data['amt'] = 0

        self._data = data
        self._keys = {'name', 'value', 'amt'}
        self._locked = True

        if not isinstance(data, _SaverDict):
            logger.log_warn(
                'Non-persistant {} class loaded.'.format(
                    type(self).__name__
                ))
    def __repr__(self):
        # Debug-friendly representation of this Currency.
        return "{}({{{}}})".format(
            type(self).__name__,
            ', '.join(["'{}': {!r}".format(k, self._data[k])
                for k in self._keys if k in self._data]))

    def __str__(self):
        # String returned from Currency
        if self._data['amt'] == 1: name = self.name
        else: name = "{}s".format(self.name)

        return "{amt} {name}".format(
            amt=self._data['amt'], name=name)

    def __unicode__(self):
        # User-friendly unicode representation of this Currency
        return unicode(str(self))

    # Numeric operations magic

    def __eq__(self, other):
        """
        Support equality comparison Currency or Currency and numeric
        Note:
            This class uses the @functools.total_ordering() decorator 
            to complete the rich comparison implementation, therefore
            only `__eq__` and `__lt__` are implemented.
        """
        if type(other) == Currency:
            return self.amt == other.amt
        elif type(other) in (float, int):
            return self.amt == other
        else:
            return NotImplemented

    def __lt__(self, other):
        # Supports less than comparison between Currencys or Currency and numeric
        if isinstance(other, Currency):
            return self.amt < other.amt
        elif type(other) in (float, int):
            return self.amt < other
        else:
            return NotImplemented

    def __pos__(self):
        # Access 'value' property through unary '+' operator
        return self.amt

    def __add__(self, other):
        # Support addition between Currencys or Currency and numeric
        if isinstance(other, Currency):
            return self.amt + other.amt
        elif type(other) in (float, int):
            return self.amt + other
        else:
            return NotImplemented

    def __sub__(self, other):
        # Support subtraction between Currency or Currency and numeric
        if isinstance(other, Currency):
            return self.amt - other.amt
        elif type(other) in (float, int):
            return self.amt - other
        else:
            return NotImplemented

    def __mul__(self, other):
        # Support multiplication between Currency or Currency and numeric
        if isinstance(other, Currency):
            return self.amt * other.amt
        elif type(other) in (float, int):
            return self.amt * other
        else:
            return NotImplemented

    def __floordiv__(self, other):
        # Support floor division between Currency or Currency and numeric
        if isinstance(other, Currency):
            return self.amt // other.amt
        elif type(other) in (float, int):
            return self.amt // other
        else:
            return NotImplemented

    # yay, commutative property!
    __radd__ = __add__
    __rmul__ = __mul__

    def __rsub__(self, other):
        # Support subtraction between Currency or Currency and numeric
        if isinstance(other, Currency):
            return other.amt - self.amt
        elif type(other) in (float, int):
            return other - self.amt
        else:
            return NotImplemented

    def __rfloordiv__(self, other):
        # Support floor division between Currency or Currency and numeric
        if isinstance(other, Currency):
            return other.amt // self.amt
        elif type(other) in (float, int):
            return other // self.amt
        else:
            return NotImplemented

    # Public members

    @property
    def name(self):
        # Display name for Currency
        return self._data['name']

    @property
    def value(self):
        # Display name for Currency
        return self._data['value']

    @property
    def amt(self):
        # Display name for Currency
        return self._data['amt']

    @amt.setter
    def amt(self, value):
        if type(value) in (int, float):
            if value >= 0: self._data['amt'] = value
            else: self._data['amt'] = 0

    # Public routines

    def convert(self, obj, amt=None):
        if isinstance(obj, Currency):
            if amt == None:
                # Convert the full amount
                amt_to_convert = obj.amt
            else:
                if type(amt) in (int, float):
                    if amt > obj.amt:
                        raise CurrencyException("There are not that many to convert")
                    if amt < 0:
                       raise CurrencyException("Cannot convert negative amounts")
                    else:
                        amt_to_convert = amt
                else: 
                    amt_to_convert = 0

            # Subtract converted amount
            obj.amt -= amt_to_convert      

            if obj.value > self.value:
                modifier = obj.value / self.value
                self.amt += amt_to_convert * modifier
                print "Converted {} {} --> {} {}".format(
                    amt_to_convert, obj.name, amt_to_convert * modifier, self.name)
            elif obj.value < self.value:
                modifier = self.value / obj.value
                self.amt += amt_to_convert / modifier
                print "Converted {} {} --> {} {}".format(
                    amt_to_convert, obj.name, amt_to_convert / modifier, self.name)                
            else:
                modifier = 1
                self.amt += amt_to_convert
                print "Converted {} {} --> {} {}".format(
                    amt_to_convert, obj.name, amt_to_convert, self.name)

        else:
            return NotImplemented
