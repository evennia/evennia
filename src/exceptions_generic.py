"""
This module contains exceptions used throughout the server
"""
class GenericException(Exception):
    """
    The custom exception class from which all other exceptions are derived.
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
