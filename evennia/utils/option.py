from django.conf import settings
from evennia.utils.utils import string_partial_matching, callables_from_module


class OptionManager(object):
    """
    Loads and stores the final list of OPTION CLASSES.

    Can access these as properties or dictionary-contents.
    """
    def __init__(self):
        self.option_storage = {}
        for module in settings.OPTIONCLASS_MODULES:
            self.option_storage.update(callables_from_module(module))

    def __getitem__(self, item):
        return self.option_storage.get(item, None)

    def __getattr__(self, item):
        return self[item]


# Ensure that we have a Singleton that keeps all loaded Options.
OPTION_MANAGER = OptionManager()


class OptionHandler(object):
    """
    This is a generic Option handler meant for Typed Objects - anything that implements AttributeHandler.

    It uses a dictionary to store-and-cache frequently used settings such as colors for borders or an
    account's timezone.

    This is used for Account.options but it could be used by Scripts or Objects just as easily. All
    it needs to be provided is an options_dict.
    """

    def __init__(self, obj, options_dict=None, save_category=None):
        """
        Initialize an OptionHandler.

        Args:
            obj (TypedObject): The Typed Object this sits on. Obj MUST implement the Evennia AttributeHandler
                or this will barf.
            options_dict (dict): A dictionary of option keys, where the values are options. The format of those
                tuples is: ('key', "Description to show", 'option_type', <default value>)
            save_category (str): The Options data will be stored to this Attribute category on obj.
        """
        if not options_dict:
            options_dict = dict()
        self.options_dict = options_dict
        self.save_category = save_category
        self.obj = obj

        # This dictionary stores the in-memory Options by their key. Values are the Option objects.
        self.options = dict()

        # We use lazy-loading of each Option when it's called for, but it's good to have the save data
        # on hand.
        self.save_data = {s.key: s.value for s in obj.attributes.get(category=save_category,
                                                               return_list=True, return_obj=True) if s}

    def __getitem__(self, item):
        return self.get(item).value

    def get(self, item, return_obj=False):
        if item not in self.options_dict:
            raise KeyError("Option not found!")
        if item in self.options:
            op_found = self.options[item]
        else:
            op_found = self.load_option(item)
        if return_obj:
            return op_found
        return op_found.value

    def load_option(self, key):
        option_def = self.options_dict[key]
        save_data = self.save_data.get(key, None)
        self.obj.msg(save_data)
        loaded_option = OPTION_MANAGER[option_def[1]](self, key, option_def[0], option_def[2], save_data)
        self.options[key] = loaded_option
        return loaded_option

    def set(self, option, value, account):
        """
        Change an individual option.

        Args:
            option (str): The key of an option that can be changed. Allows partial matching.
            value (str): The value that should be checked, coerced, and stored.
            account (AccountDB): The Account performing the setting. Necessary due to other
                option lookups like timezone.

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
        return op.set(value, account)
