"""
Currency Module
'Currency' classes represent monetary values on objects or characters.
They are instantiated by the 'CurrencyHandler' object, which is typically
set up as a property on the object or character's typeclass.

**Setup**

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

    You can now add properies in order to represent
    cooper coins (CC) and silver coins (SC). Each property
    is a Python dict object, that contains a value (used
    for conversions between currencies), a name (for display),
    and an amount.

    ```python
    currency = {
        'CC': {'value': 10, 'name': 'copper coin', 'amount': 0},
        'SC': {'value': 100, 'name': 'silver coin', 'amount': 0}
        }
    ```

**Currency Configuration**

    When called, the CurrencyHandler returns a standard Python object of type
    Currency. Properties on the Currency object can then be referenced for
    calculating amounts and doing conversions. Currency objects can be
    configured with a name and a value (relative to other Currency).

    Example:

        Let's get the amount of copper coins (CC) on our test object:

        ```python
        >>> cc = obj.currency.CC
        >>> cc.amount
        100
        ```

    Constructor Args:
        name(str): name of the currency type
        value(int, float): value based on other currency types in handler
        amount(int, float): amount of currency type held
    
    Methods:
        convert(Currency, Optional amount): Convert between Currency types.
        to_string(): List all currencies that have amounts greater than zero
        total(): Returns a total in lowest currency
        
    Examples:

        Let's convert some of the silver coins (SC) on our test
        object into copper coins (CC).

        ```python
        >>> obj.purse.CC.convert(self.purse.SC,2)
        Converted 2 silver coin --> 20 copper coin
        ```

        We can also do add more copper coins (CC).

        ```python
        >>> obj.purse.CC.amount = 4    # Add 4 copper coins
        >>> str(obj.purse.CC)
        '35 copper coins'
        ```

        Finally, let's look at the current state of the Currency
        object's properties, to verify they reflects our changes.

        ```python
        >>> self.purse.to_string
        20 copper coins, 2 silver coins
        >>> obj.db.purse
        Currency({'CC': {'amount': 35, 'value': 10, 'name': 'copper coin'},
        'SC': {'amount': 19, 'value': 100, 'name': 'silver coin'}})
        ```
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

    def add(self, key, name, value, amount):
        """
        Create a new Currency dict and add it to the CurrencyHandler.

        Args:
            key (str): key that will be representing currency dict
            name (str): a pretty text representation of the dict used
                for print exports.
            value (int): value of one unit of currency, relative to other
                currency dicts in the handler.

                Example:

                    currency.add('CC', 'copper coin', 10, 1)
                    currency.add('SC', 'silver coin', 100, 1)
                    currency.add('BC', 'brass coin', 1, 1)

                    One silver coin will convert to 10 copper coins (10 to 1)
                    or 100 brass coins (100 to 1).

            amount (int): value that represents how many units of a given
            currency there are in the handler.
        """
        if key in self.attr_dict:
            raise CurrencyException("Currency '{}' already exists.".format(key))

        currency = dict(name=name,
                        value=value,
                        amount=amount)

        self.attr_dict[key] = currency

    def remove(self, currency):
        """
        Remove a Currency type from the handler's parent object.

        Args:
            currency (dict): remove selected dict object from CurrencyHandler
        """
        if currency not in self.attr_dict:
            raise CurrencyException("Currency not found: {}".format(currency))

        if currency in self.cache:
            del self.cache[currency]
        del self.attr_dict[currency]

    def clear(self):
        """
        Remove all Currency dicts from the handler's parent object.
        """
        # Remove all Currency from the handler's parent object.
        for currency in self.all:
            self.remove(currency)

    @property
    def all(self):
        """
        Return a list of all currency dicts in CurrencyHandler.
        """
        return self.attr_dict.keys()

    @property
    def to_string(self):
        """
        Return a formatted list of currency and amounts in this CurrencyHandler.
        """
        liststr = ""
        for key in self.attr_dict.keys():
            cur = Currency(self.attr_dict[key])
            if cur.amount > 0:
                liststr += "{}, ".format(cur)
        if len(liststr.strip()) > 0:
            return liststr[:-2]
        else:
            return liststr.strip()

    @property
    def total(self):
        """
        Calculates the effective value for each Currency dict contained in the
        CurrencyHandler based on the amount * value attributes in each dict and
        then returns a formatted list of currency and amounts in CurrencyHandler
        """
        total = 0
        in_currency = None
        for key in self.attr_dict.keys():
            cur = Currency(self.attr_dict[key])
            if cur.amount > 0:
                # Add currency to the total
                total += cur.amount * cur.value
            if in_currency is None:
                # Use the first currency we find
                in_currency = cur
            elif cur.value < in_currency.value:
                # We want the lowest currency value
                in_currency = cur

        # Now we want to return what we have collected
        if in_currency is None:
            return {'total': 0, 'name': ''}
        else:
            return {'total': total, 'name': in_currency.name}

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
        if not 'amount' in data:
            data['amount'] = 0

        self._data = data
        self._keys = {'name', 'value', 'amount'}
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
        if self._data['amount'] == 1:
            name = self.name
        else:
            name = "{}s".format(self.name)

        return "{amount} {name}".format(
            amount=self._data['amount'], name=name)

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
            return self.amount == other.amount
        elif type(other) in (float, int):
            return self.amount == other
        else:
            return NotImplemented

    def __lt__(self, other):
        # Supports less than comparison between Currencys or Currency and numeric
        if isinstance(other, Currency):
            return self.amount < other.amount
        elif type(other) in (float, int):
            return self.amount < other
        else:
            return NotImplemented

    def __pos__(self):
        # Access 'value' property through unary '+' operator
        return self.amount

    def __add__(self, other):
        # Support addition between Currencys or Currency and numeric
        if isinstance(other, Currency):
            return self.amount + other.amount
        elif type(other) in (float, int):
            return self.amount + other
        else:
            return NotImplemented

    def __sub__(self, other):
        # Support subtraction between Currency or Currency and numeric
        if isinstance(other, Currency):
            return self.amount - other.amount
        elif type(other) in (float, int):
            return self.amount - other
        else:
            return NotImplemented

    def __mul__(self, other):
        # Support multiplication between Currency or Currency and numeric
        if isinstance(other, Currency):
            return self.amount * other.amount
        elif type(other) in (float, int):
            return self.amount * other
        else:
            return NotImplemented

    def __floordiv__(self, other):
        # Support floor division between Currency or Currency and numeric
        if isinstance(other, Currency):
            return self.amount // other.amount
        elif type(other) in (float, int):
            return self.amount // other
        else:
            return NotImplemented

    # yay, commutative property!
    __radd__ = __add__
    __rmul__ = __mul__

    def __rsub__(self, other):
        # Support subtraction between Currency or Currency and numeric
        if isinstance(other, Currency):
            return other.amount - self.amount
        elif type(other) in (float, int):
            return other - self.amount
        else:
            return NotImplemented

    def __rfloordiv__(self, other):
        # Support floor division between Currency or Currency and numeric
        if isinstance(other, Currency):
            return other.amount // self.amount
        elif type(other) in (float, int):
            return other // self.amount
        else:
            return NotImplemented

    # Public members

    @property
    def name(self):
        """
        Display name attribute for Currency dict
        """
        return self._data['name']

    @property
    def value(self):
        """
        Display value attribute for Currency dict
        """
        return self._data['value']

    @property
    def amount(self):
        """
        Display amount attribute for Currency dict
        """
        return self._data['amount']

    @amount.setter
    def amount(self, value):
        if type(value) in (int, float):
            if value >= 0:
                self._data['amount'] = value
            else:
                self._data['amount'] = 0

    # Public routines

    def convert(self, obj, amount=None):
        """
        Use to convert Currency from one defined type, into another
        based on their defined values in the CurrencyHandler.

        Args:
            obj (dict): selected dict object from CurrencyHandler
            amount (int): integer value amount to convert from
                selected type to current type. If no amount is specified,
                the entire amount in dict will be converted.
        """
        if isinstance(obj, Currency):
            if not amount:
                # Convert the full amount
                amount_to_convert = obj.amount
            else:
                if type(amount) in (int, float):
                    if amount > obj.amount:
                        raise CurrencyException("There are not that many to convert")
                    if amount < 0:
                       raise CurrencyException("Cannot convert negative amounts")
                    else:
                        amount_to_convert = amount
                else:
                    amount_to_convert = 0

            # Subtract converted amount
            obj.amount -= amount_to_convert

            if obj.value > self.value:
                modifier = obj.value / self.value
                self.amount += amount_to_convert * modifier
            elif obj.value < self.value:
                modifier = self.value / obj.value
                self.amount += amount_to_convert / modifier
            else:
                modifier = 1
                self.amount += amount_to_convert

        else:
            return NotImplemented
