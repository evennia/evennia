from evennia.utils.utils import string_partial_matching
from evennia.utils.containers import OPTION_CLASSES


class OptionHandler(object):
    """
    This is a generic Option handler meant for Typed Objects - anything that
    implements AttributeHandler. Retrieve options eithers as properties on
    this handler or by using the .get method.

    This is used for Account.options but it could be used by Scripts or Objects
    just as easily. All it needs to be provided is an options_dict.
    """

    def __init__(self, obj, options_dict=None, save_category=None):
        """
        Initialize an OptionHandler.

        Args:
            obj (TypedObject): The Typed Object this sits on. Obj MUST
                implement the Evennia AttributeHandler or this will barf.
            options_dict (dict): A dictionary of option keys, where the values
                are options. The format of those tuples is: ('key', "Description to
                show", 'option_type', <default value>)
            save_category (str): The Options data will be stored to this
                Attribute category on obj.

        """
        if not options_dict:
            options_dict = {}
        self.options_dict = options_dict
        self.save_category = save_category
        self.obj = obj

        # This dictionary stores the in-memory Options by their key. Values are the Option objects.
        self.options = {}

        # We use lazy-loading of each Option when it's called for, but it's
        # good to have the save data on hand.
        self.save_data = {s.key: s.value for s in obj.attributes.get(
            category=save_category, return_list=True, return_obj=True) if s}

    def __getattr__(self, key):
        return self.get(key).value

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
        if key in self.options:
            op_found = self.options[key]
        else:
            op_found = self._load_option(key)
        if return_obj:
            return op_found
        return op_found.value

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

    def _load_option(self, key):
        """
        Loads option on-demand if it has not been loaded yet.

        Args:
            key (str): The option being loaded.

        Returns:

        """
        desc, clsname, default_val = self.options_dict[key]
        save_data = self.save_data.get(key, None)
        self.obj.msg(save_data)
        loaded_option = OPTION_CLASSES.get(clsname)(self, key, desc, default_val, save_data)
        self.options[key] = loaded_option
        return loaded_option

    def set(self, option, value, **kwargs):
        """
        Change an individual option.

        Args:
            option (str): The key of an option that can be changed. Allows partial matching.
            value (str): The value that should be checked, coerced, and stored.
            kwargs (any, optional): These are passed into the Option's validation function,
                save function and display function and allows to customize either.

        Returns:
            New value
        """
        if not option:
            raise ValueError("Option field blank!")
        found = string_partial_matching(list(self.options_dict.keys()), option, ret_index=False)
        if not found:
            raise ValueError("Option not found!")
        if len(found) > 1:
            raise ValueError(f"That matched: {', '.join(found)}. Please be more specific.")
        found = found[0]
        op = self.get(found, return_obj=True)
        op.set(value, **kwargs)
        return op.display(**kwargs)
