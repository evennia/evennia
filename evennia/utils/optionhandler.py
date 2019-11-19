from evennia.utils.utils import string_partial_matching
from evennia.utils.containers import OPTION_CLASSES

_GA = object.__getattribute__
_SA = object.__setattr__


class InMemorySaveHandler(object):
    """
    Fallback SaveHandler, implementing a minimum of the required save mechanism
    and storing data in memory.

    """

    def __init__(self):
        self.storage = {}

    def add(self, key, value=None, **kwargs):
        self.storage[key] = value

    def get(self, key, default=None, **kwargs):
        return self.storage.get(key, default)


class OptionHandler(object):
    """
    This is a generic Option handler. It is commonly used
    implements AttributeHandler. Retrieve options eithers as properties on
    this handler or by using the .get method.

    This is used for Account.options but it could be used by Scripts or Objects
    just as easily. All it needs to be provided is an options_dict.

    """

    def __init__(
        self,
        obj,
        options_dict=None,
        savefunc=None,
        loadfunc=None,
        save_kwargs=None,
        load_kwargs=None,
    ):
        """
        Initialize an OptionHandler.

        Args:
            obj (object): The object this handler sits on. This is usually a TypedObject.
            options_dict (dict): A dictionary of option keys, where the values
                are options. The format of those tuples is: ('key', "Description to
                show", 'option_type', <default value>)
            savefunc (callable): A callable for all options to call when saving itself.
                It will be called as `savefunc(key, value, **save_kwargs)`. A common one
                to pass would be AttributeHandler.add.
            loadfunc (callable): A callable for all options to call when loading data into
                itself. It will be called as `loadfunc(key, default=default, **load_kwargs)`. 
                A common one to pass would be AttributeHandler.get.
            save_kwargs (any): Optional extra kwargs to pass into `savefunc` above.
            load_kwargs (any): Optional extra kwargs to pass into `loadfunc` above.
        Notes:
            Both loadfunc and savefunc must be specified. If only one is given, the other
            will be ignored and in-memory storage will be used.

        """
        self.obj = obj
        self.options_dict = {} if options_dict is None else options_dict

        if not savefunc and loadfunc:
            self._in_memory_handler = InMemorySaveHandler()
            savefunc = InMemorySaveHandler.add
            loadfunc = InMemorySaveHandler.get
        self.savefunc = savefunc
        self.loadfunc = loadfunc
        self.save_kwargs = {} if save_kwargs is None else save_kwargs
        self.load_kwargs = {} if load_kwargs is None else load_kwargs

        # This dictionary stores the in-memory Options objects by their key for
        # quick lookup.
        self.options = {}

    def __getattr__(self, key):
        """
        Allow for obj.options.key

        """
        return self.get(key)

    def __setattr__(self, key, value):
        """
        Allow for obj.options.key = value

        But we must be careful to avoid infinite loops!

        """
        try:
            if key in _GA(self, "options_dict"):
                _GA(self, "set")(key, value)
        except AttributeError:
            pass
        _SA(self, key, value)

    def _load_option(self, key):
        """
        Loads option on-demand if it has not been loaded yet.

        Args:
            key (str): The option being loaded.

        Returns:

        """
        desc, clsname, default_val = self.options_dict[key]
        loaded_option = OPTION_CLASSES.get(clsname)(self, key, desc, default_val)
        # store the value for future easy access
        self.options[key] = loaded_option
        return loaded_option

    def get(self, key, return_obj=False):
        """
        Retrieves an Option stored in the handler. Will load it if it doesn't exist.

        Args:
            key (str): The option key to retrieve.
            return_obj (bool, optional): If True, returns the actual option
                object instead of its value.
        Returns:
            option_value (any or Option): An option value  the Option itself.
        Raises:
            KeyError: If option is not defined.

        """
        if key not in self.options_dict:
            raise KeyError("Option not found!")
        op_found = self.options.get(key) or self._load_option(key)
        return op_found if return_obj else op_found.value

    def set(self, key, value, **kwargs):
        """
        Change an individual option.

        Args:
            key (str): The key of an option that can be changed. Allows partial matching.
            value (str): The value that should be checked, coerced, and stored.:
            kwargs (any, optional): These are passed into the Option's validation function,
                save function and display function and allows to customize either.

        Returns:
            value (any): Value stored in option, after validation.

        """
        if not key:
            raise ValueError("Option field blank!")
        match = string_partial_matching(list(self.options_dict.keys()), key, ret_index=False)
        if not match:
            raise ValueError("Option not found!")
        if len(match) > 1:
            raise ValueError(f"Multiple matches: {', '.join(match)}. Please be more specific.")
        match = match[0]
        op = self.get(match, return_obj=True)
        op.set(value, **kwargs)
        return op.value

    def all(self, return_objs=False):
        """
        Get all options defined on this handler.

        Args:
            return_objs (bool, optional): Return the actual Option objects rather
                than their values.
        Returns:
            all_options (dict): All options on this handler, either `{key: value}`
                or `{key: <Option>}` if `return_objs` is `True`.

        """
        return [self.get(key, return_obj=return_objs) for key in self.options_dict]
