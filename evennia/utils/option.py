from evennia.utils.utils import string_partial_matching


class OptionHandler(object):
    """
    This is a generic Option handler meant for Typed Objects - anything that implements AttributeHandler.

    It uses a dictionary to store-and-cache frequently used settings such as colors for borders or an
    account's timezone.
    """

    def __init__(self, obj, options_dict=None, save_category=None):
        if not options_dict:
            options_dict = dict()
        self.options_dict = options_dict
        self.save_category = save_category
        self.obj = obj
        self.options = dict()

    def __getitem__(self, item):
        if item not in self.options_dict:
            raise KeyError("Option not found!")
        if item in self.options:
            return self.options[item]
        import evennia
        option_def = self.options_dict[item]
        save_data = self.obj.attributes.get(item, category=self.save_category)
        if not save_data:
            return evennia.VALID_HANDLER[option_def[1]](option_def[2])
        self.options[item] = save_data
        return save_data

    def get(self, item):
        return self[item]

    def set(self, option, value):
        """
        Change an individual option.

        Args:
            option (str): The key of an option that can be changed. Allows partial matching.
            value (str): The value that should be checked, coerced, and stored.

        Returns:
            New value
        """
        import evennia
        if not option:
            raise ValueError("Option field blank!")
        found = string_partial_matching(list(self.options_dict.keys()), option, ret_index=False)
        if not found:
            raise ValueError("Option not found!")
        if len(found) > 1:
            raise ValueError(f"That matched: {', '.join(found)}. Please be more specific.")
        found = found[0]
        option_def = self.options_dict[found]
        if not value:
            raise ValueError("Value field blank!")
        new_value = evennia.VALID_HANDLER[option_def[1]](value, thing_name=found)
        self.obj.attributes.add(found, category=self.save_category, value=new_value)
        self.options[found] = new_value
        return new_value
