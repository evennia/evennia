"""
Exceptions for the object application.
"""
from src.exceptions_generic import GenericException

class ObjectNotExist(GenericException):
    """
    Raised when an object is queried for but does not exist.
    """
    def __str__(self):
        return repr("No such object: %s" % self.value)
