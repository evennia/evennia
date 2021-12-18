"""
Module containing the CallbackHandler for individual objects.
"""

from collections import namedtuple


class CallbackHandler(object):

    """
    The callback handler for a specific object.

    The script that contains all callbacks will be reached through this
    handler.  This handler is therefore a shortcut to be used by
    developers.  This handler (accessible through `obj.callbacks`) is a
    shortcut to manipulating callbacks within this object, getting,
    adding, editing, deleting and calling them.

    """

    script = None

    def __init__(self, obj):
        self.obj = obj

    def all(self):
        """
        Return all callbacks linked to this object.

        Returns:
            All callbacks in a dictionary callback_name: callback}.  The callback
            is returned as a namedtuple to simplify manipulation.

        """
        callbacks = {}
        handler = type(self).script
        if handler:
            dicts = handler.get_callbacks(self.obj)
            for callback_name, in_list in dicts.items():
                new_list = []
                for callback in in_list:
                    callback = self.format_callback(callback)
                    new_list.append(callback)

                if new_list:
                    callbacks[callback_name] = new_list

        return callbacks

    def get(self, callback_name):
        """
        Return the callbacks associated with this name.

        Args:
            callback_name (str): the name of the callback.

        Returns:
            A list of callbacks associated with this object and of this name.

        Note:
            This method returns a list of callback objects (namedtuple
            representations).  If the callback name cannot be found in the
            object's callbacks, return an empty list.

        """
        return self.all().get(callback_name, [])

    def get_variable(self, variable_name):
        """
        Return the variable value or None.

        Args:
            variable_name (str): the name of the variable.

        Returns:
            Either the variable's value or None.

        """
        handler = type(self).script
        if handler:
            return handler.get_variable(variable_name)

        return None

    def add(self, callback_name, code, author=None, valid=False, parameters=""):
        """
        Add a new callback for this object.

        Args:
            callback_name (str): the name of the callback to add.
            code (str): the Python code associated with this callback.
            author (Character or Account, optional): the author of the callback.
            valid (bool, optional): should the callback be connected?
            parameters (str, optional): optional parameters.

        Returns:
            The callback definition that was added or None.

        """
        handler = type(self).script
        if handler:
            return self.format_callback(
                handler.add_callback(
                    self.obj, callback_name, code, author=author, valid=valid, parameters=parameters
                )
            )

    def edit(self, callback_name, number, code, author=None, valid=False):
        """
        Edit an existing callback bound to this object.

        Args:
            callback_name (str): the name of the callback to edit.
            number (int): the callback number to be changed.
            code (str): the Python code associated with this callback.
            author (Character or Account, optional): the author of the callback.
            valid (bool, optional): should the callback be connected?

        Returns:
            The callback definition that was edited or None.

        Raises:
            RuntimeError if the callback is locked.

        """
        handler = type(self).script
        if handler:
            return self.format_callback(
                handler.edit_callback(
                    self.obj, callback_name, number, code, author=author, valid=valid
                )
            )

    def remove(self, callback_name, number):
        """
        Delete the specified callback bound to this object.

        Args:
            callback_name (str): the name of the callback to delete.
            number (int): the number of the callback to delete.

        Raises:
            RuntimeError if the callback is locked.

        """
        handler = type(self).script
        if handler:
            handler.del_callback(self.obj, callback_name, number)

    def call(self, callback_name, *args, **kwargs):
        """
        Call the specified callback(s) bound to this object.

        Args:
            callback_name (str): the callback name to call.
            *args: additional variables for this callback.

        Keyword Args:
            number (int, optional): call just a specific callback.
            parameters (str, optional): call a callback with parameters.
            locals (dict, optional): a locals replacement.

        Returns:
            True to report the callback was called without interruption,
            False otherwise.  If the callbackHandler isn't found, return
            None.

        """
        handler = type(self).script
        if handler:
            return handler.call(self.obj, callback_name, *args, **kwargs)

        return None

    @staticmethod
    def format_callback(callback):
        """
        Return the callback namedtuple to represent the specified callback.

        Args:
            callback (dict): the callback definition.

        The callback given in argument should be a dictionary containing
        the expected fields for a callback (code, author, valid...).

        """
        if "obj" not in callback:
            callback["obj"] = None
        if "name" not in callback:
            callback["name"] = "unknown"
        if "number" not in callback:
            callback["number"] = -1
        if "code" not in callback:
            callback["code"] = ""
        if "author" not in callback:
            callback["author"] = None
        if "valid" not in callback:
            callback["valid"] = False
        if "parameters" not in callback:
            callback["parameters"] = ""
        if "created_on" not in callback:
            callback["created_on"] = None
        if "updated_by" not in callback:
            callback["updated_by"] = None
        if "updated_on" not in callback:
            callback["updated_on"] = None

        return Callback(**callback)


Callback = namedtuple(
    "Callback",
    (
        "obj",
        "name",
        "number",
        "code",
        "author",
        "valid",
        "parameters",
        "created_on",
        "updated_by",
        "updated_on",
    ),
)
