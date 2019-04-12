import datetime as _dt
from evennia import logger as _log
from evennia.utils.ansi import ANSIString as _ANSI
from evennia.utils.validfuncs import _TZ_DICT
from evennia.utils.containers import VALID_CONTAINER as _VAL


class BaseOption(object):
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
    validator_key = ''

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

    def display(self, **kwargs):
        """
        Renders the Option's value as something pretty to look at.

        Returns:
            How the stored value should be projected to users. a raw timedelta is pretty ugly, y'know?
        """
        return self.value

    def _load(self):
        """
        Takes the provided save data, validates it, and gets this Option ready to use.

        Returns:
            Boolean: Whether loading was successful.
        """
        if self.save_data is not None:
            try:
                self.value_storage = self.deserialize(self.save_data)
                self.loaded = True
                return True
            except Exception as e:
                _log.log_trace(e)
        return False

    def _save(self):
        """
        Exports the current value to an Attribute.

        Returns:
            None
        """
        self.handler.obj.attributes.add(self.key, category=self.handler.save_category, value=self.serialize())

    def deserialize(self, save_data):
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

    def serialize(self):
        """
        Serializes the save data for Attribute storage if it's something complicated.

        Returns:
            Whatever best handles the Attribute.
        """
        return self.value_storage

    @property
    def changed(self):
        return self.value_storage != self.default_value

    @property
    def default(self):
        return self.default_value

    @property
    def value(self):
        if not self.loaded and self.save_data is not None:
            self._load()
        if self.loaded:
            return self.value_storage
        else:
            return self.default

    @value.setter
    def value(self, value):
        """
        Takes user input, presumed to be a string, and changes the value if it is a valid input.

        Args:
            value:
            account:

        Returns:
            None
        """
        final_value = self.validate(value)
        self.value_storage = final_value
        self.loaded = True
        self._save()

    def validate(self, value):
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
        return _VAL[self.validator_key](value, thing_name=self.key)


class Text(BaseOption):
    validator_key = 'text'

    def deserialize(self, save_data):
        got_data = str(save_data)
        if not got_data:
            raise ValueError(f"{self.key} expected Text data, got '{save_data}'")
        return got_data


class Email(BaseOption):
    validator_key = 'email'

    def deserialize(self, save_data):
        got_data = str(save_data)
        if not got_data:
            raise ValueError(f"{self.key} expected String data, got '{save_data}'")
        return got_data


class Boolean(BaseOption):
    validator_key = 'boolean'

    def display(self, **kwargs):
        if self.value:
            return '1 - On/True'
        return '0 - Off/False'

    def serialize(self):
        return self.value

    def deserialize(self, save_data):
        if not isinstance(save_data, bool):
            raise ValueError(f"{self.key} expected Boolean, got '{save_data}'")
        return save_data


class Color(BaseOption):
    validator_key = 'color'

    def display(self, **kwargs):
        return f'{self.value} - |{self.value}this|n'

    def deserialize(self, save_data):
        if not save_data or len(_ANSI(f'|{save_data}|n')) > 0:
            raise ValueError(f"{self.key} expected Color Code, got '{save_data}'")
        return save_data


class Timezone(BaseOption):
    validator_key = 'timezone'

    @property
    def default(self):
        return _TZ_DICT[self.default_value]

    def deserialize(self, save_data):
        if save_data not in _TZ_DICT:
            raise ValueError(f"{self.key} expected Timezone Data, got '{save_data}'")
        return _TZ_DICT[save_data]

    def serialize(self):
        return str(self.value_storage)


class UnsignedInteger(BaseOption):
    validator_key = 'unsigned_integer'

    def deserialize(self, save_data):
        if isinstance(save_data, int) and save_data >= 0:
            return save_data
        raise ValueError(f"{self.key} expected Whole Number 0+, got '{save_data}'")


class SignedInteger(BaseOption):
    validator_key = 'signed_integer'

    def deserialize(self, save_data):
        if isinstance(save_data, int):
            return save_data
        raise ValueError(f"{self.key} expected Whole Number, got '{save_data}'")


class PositiveInteger(BaseOption):
    validator_key = 'positive_integer'

    def deserialize(self, save_data):
        if isinstance(save_data, int) and save_data > 0:
            return save_data
        raise ValueError(f"{self.key} expected Whole Number 1+, got '{save_data}'")


class Duration(BaseOption):
    validator_key = 'duration'

    def deserialize(self, save_data):
        if isinstance(save_data, int):
            return _dt.timedelta(0, save_data, 0, 0, 0, 0, 0)
        raise ValueError(f"{self.key} expected Timedelta in seconds, got '{save_data}'")

    def serialize(self):
        return self.value_storage.seconds


class Datetime(BaseOption):
    validator_key = 'datetime'

    def deserialize(self, save_data):
        if isinstance(save_data, int):
            return _dt.datetime.utcfromtimestamp(save_data)
        raise ValueError(f"{self.key} expected UTC Datetime in EPOCH format, got '{save_data}'")

    def serialize(self):
        return int(self.value_storage.strftime('%s'))


class Future(Datetime):
    validator_key = 'future'


class Lock(Text):
    validator_key = 'lock'
