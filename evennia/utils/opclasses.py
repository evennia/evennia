import datetime as _dt
from evennia.utils.ansi import ANSIString as _ANSI
from evennia.utils.validfuncs import _TZ_DICT
from evennia.utils.valid import VALID_HANDLER as _VAL


class _BaseOption(object):
    """
    Abstract Class to deal with encapsulating individual Options. An Option has a name/key, a description
    to display in relevant commands and menus, and a default value. It saves to the owner's Attributes using
    its Handler's save category.

    Designed to be extremely overloadable as some options can be cantankerous.

    Properties:
        expect_type (str): What users will see this as asking for. Example: Color or email.
        valid: Shortcut to the loaded VALID_HANDLER.
        valid_type (str): The key of the Validator this uses.
    """
    expect_type = ''
    valid = _VAL
    valid_type = ''

    def __str__(self):
        return self.key

    def __init__(self, handler, key, description, default, save_data=None):
        """

        Args:
            handler (OptionHandler): The OptionHandler that 'owns' this Option.
            key (str): The name this will be used for storage in a dictionary. Must be unique per
                OptionHandler.
            description (str): What this Option's text will show in commands and menus.
            default: A default value for this Option.
            save_data: Whatever was saved to Attributes. This differs by Option.
        """
        self.handler = handler
        self.key = key
        self.default_value = default
        self.description = description
        self.save_data = save_data

        # Value Storage contains None until the Option is loaded.
        self.value_storage = None

        # And it's not loaded until it's called upon to spit out its contents.
        self.loaded = False

    def load(self):
        """
        Takes the provided save data, validates it, and gets this Option ready to use.

        Returns:
            Boolean: Whether loading was successful.
        """
        if self.save_data is not None:
            try:
                self.value_storage = self.valid_save(self.save_data)
                self.loaded = True
                return True
            except Exception as e:
                print(e)  # need some kind of error message here!
        return False

    def customized(self):
        return self.value_storage != self.default_value

    def valid_save(self, save_data):
        """
        Perform sanity-checking on the save data. This isn't the same as Validators, as Validators deal with
        user input. save data might be a timedelta or a list or some other object. isinstance() is probably
        very useful here.

        Args:
            save_data: The data to check.

        Returns:
            Arbitrary: Whatever the Option needs to track, like a string or a datetime. Not the same as what
                users are SHOWN.
        """
        return save_data

    def clear(self):
        """
        Resets this Option to default settings.

        Returns:
            self. Why?
        """
        self.value_storage = None
        self.loaded = False
        return self

    @property
    def default(self):
        return self.default_value

    @property
    def value(self):
        if not self.loaded and self.save_data is not None:
            self.load()
        if self.loaded:
            return self.value_storage
        else:
            return self.default

    def validate(self, value, account):
        """
        Validate user input, which is presumed to be a string.

        Args:
            value (str): User input.
            account (AccountDB): The Account that is performing the validation. This is necessary because of
                other settings which may affect the check, such as an Account's timezone affecting how their
                datetime entries are processed.

        Returns:
            The results of a Validator call. Might be any kind of python object.
        """
        return self.do_validate(value, account)

    def do_validate(self, value, account):
        """
        Second layer of abstraction on validation due to design choices.

        Args:
            value:
            account:

        Returns:

        """
        return self.valid[self.valid_type](value, thing_name=self.key, account=account)

    def set(self, value, account):
        """
        Takes user input, presumed to be a string, and changes the value if it is a valid input.

        Args:
            value:
            account:

        Returns:

        """
        final_value = self.validate(value, account)
        self.value_storage = final_value
        self.loaded = True
        self.save()
        return self.display()

    def display(self):
        """
        Renders the Option's value as something pretty to look at.

        Returns:
            How the stored value should be projected to users. a raw timedelta is pretty ugly, y'know?
        """
        return self.value

    def export(self):
        """
        Serializes the save data for Attribute storage if it's something complicated.

        Returns:
            Whatever best handles the Attribute.
        """
        return self.value_storage

    def save(self):
        """
        Exports the current value to an Attribute.

        Returns:
            None
        """
        self.handler.obj.attributes.add(self.key, category=self.handler.save_category, value=self.export())


class Text(_BaseOption):
    expect_type = 'Text'
    valid_type = 'text'

    def do_validate(self, value, account):
        if not str(value):
            raise ValueError("Must enter some text!")
        return str(value)

    def valid_save(self, save_data):
        got_data = str(save_data)
        if not got_data:
            raise ValueError(f"{self.key} expected Text data, got '{save_data}'")
        return got_data


class Email(_BaseOption):
    expect_type = 'Email'
    valid_type = 'email'

    def valid_save(self, save_data):
        got_data = str(save_data)
        if not got_data:
            raise ValueError(f"{self.key} expected String data, got '{save_data}'")
        return got_data


class Boolean(_BaseOption):
    expect_type = 'Boolean'
    valid_type = 'boolean'

    def display(self):
        if self.value:
            return '1 - On/True'
        return '0 - Off/False'

    def export(self):
        return self.value

    def valid_save(self, save_data):
        if not isinstance(save_data, bool):
            raise ValueError(f"{self.key} expected Boolean, got '{save_data}'")
        return save_data


class Color(_BaseOption):
    expect_type = 'Color'
    valid_type = 'color'

    def display(self):
        return f'{self.value} - |{self.value}this|n'

    def valid_save(self, save_data):
        if not save_data or len(_ANSI(f'|{save_data}|n')) > 0:
            raise ValueError(f"{self.key} expected Color Code, got '{save_data}'")
        return save_data


class Timezone(_BaseOption):
    expect_type = 'Timezone'
    valid_type = 'timezone'

    @property
    def default(self):
        return _TZ_DICT[self.default_value]

    def valid_save(self, save_data):
        if save_data not in _TZ_DICT:
            raise ValueError(f"{self.key} expected Timezone Data, got '{save_data}'")
        return _TZ_DICT[save_data]

    def export(self):
        return str(self.value_storage)


class UnsignedInteger(_BaseOption):
    expect_type = 'Whole Number 0+'
    valid_type = 'unsigned_integer'

    def valid_save(self, save_data):
        if isinstance(save_data, int) and save_data >= 0:
            return save_data
        raise ValueError(f"{self.key} expected Whole Number 0+, got '{save_data}'")


class SignedInteger(_BaseOption):
    expect_type = 'Whole Number'
    valid_type = 'signed_integer'

    def valid_save(self, save_data):
        if isinstance(save_data, int):
            return save_data
        raise ValueError(f"{self.key} expected Whole Number, got '{save_data}'")


class PositiveInteger(_BaseOption):
    expect_type = 'Whole Number 1+'
    valid_type = 'positive_integer'

    def valid_save(self, save_data):
        if isinstance(save_data, int) and save_data > 0:
            return save_data
        raise ValueError(f"{self.key} expected Whole Number 1+, got '{save_data}'")


class Duration(_BaseOption):
    expect_type = 'Duration'
    valid_type = 'duration'

    def valid_save(self, save_data):
        if isinstance(save_data, int):
            return _dt.timedelta(0, save_data, 0, 0, 0, 0, 0)
        raise ValueError(f"{self.key} expected Timedelta in seconds, got '{save_data}'")

    def export(self):
        return self.value_storage.seconds


class Datetime(_BaseOption):
    expect_type = 'Datetime'
    valid_type = 'datetime'

    def valid_save(self, save_data):
        if isinstance(save_data, int):
            return _dt.datetime.utcfromtimestamp(save_data)
        raise ValueError(f"{self.key} expected UTC Datetime in EPOCH format, got '{save_data}'")

    def export(self):
        return int(self.value_storage.strftime('%s'))


class Future(Datetime):
    expect_type = 'Future Datetime'
    valid_type = 'future'


class Lock(Text):
    expect_type = 'Lock String'
    valid_type = 'lock'
