#
#  Copyright (c) 2009-2010 Gintautas Miliauskas
#
#   Permission is hereby granted, free of charge, to any person
#   obtaining a copy of this software and associated documentation
#   files (the "Software"), to deal in the Software without
#   restriction, including without limitation the rights to use,
#   copy, modify, merge, publish, distribute, sublicense, and/or sell
#   copies of the Software, and to permit persons to whom the
#   Software is furnished to do so, subject to the following
#   conditions:
#
#   The above copyright notice and this permission notice shall be
#   included in all copies or substantial portions of the Software.
#
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#   EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#   OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#   NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#   HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#   WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#   FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#   OTHER DEALINGS IN THE SOFTWARE.

"""
Pickle field implementation for Django.

Modified for Evennia by Griatch and the Evennia community.

"""
from ast import literal_eval
from datetime import datetime

from copy import deepcopy
from base64 import b64encode, b64decode
from zlib import compress, decompress

# import six # this is actually a pypy component, not in default syslib
from django.core.exceptions import ValidationError
from django.db import models

from django.forms.fields import CharField
from django.forms.widgets import Textarea

from pickle import loads, dumps
from django.utils.encoding import force_text


DEFAULT_PROTOCOL = 4


class PickledObject(str):
    """
    A subclass of string so it can be told whether a string is a pickled
    object or not (if the object is an instance of this class then it must
    [well, should] be a pickled one).

    Only really useful for passing pre-encoded values to ``default``
    with ``dbsafe_encode``, not that doing so is necessary. If you
    remove PickledObject and its references, you won't be able to pass
    in pre-encoded values anymore, but you can always just pass in the
    python objects themselves.
    """


class _ObjectWrapper(object):
    """
    A class used to wrap object that have properties that may clash with the
    ORM internals.

    For example, objects with the `prepare_database_save` property such as
    `django.db.Model` subclasses won't work under certain conditions and the
    same apply for trying to retrieve any `callable` object.
    """

    __slots__ = ("_obj",)

    def __init__(self, obj):
        self._obj = obj


def wrap_conflictual_object(obj):
    if hasattr(obj, "prepare_database_save") or callable(obj):
        obj = _ObjectWrapper(obj)
    return obj


def dbsafe_encode(value, compress_object=False, pickle_protocol=DEFAULT_PROTOCOL):
    # We use deepcopy() here to avoid a problem with cPickle, where dumps
    # can generate different character streams for same lookup value if
    # they are referenced differently.
    # The reason this is important is because we do all of our lookups as
    # simple string matches, thus the character streams must be the same
    # for the lookups to work properly. See tests.py for more information.
    value = dumps(deepcopy(value), protocol=pickle_protocol)
    if compress_object:
        value = compress(value)
    value = b64encode(value).decode()  # decode bytes to str
    return PickledObject(value)


def dbsafe_decode(value, compress_object=False):
    value = value.encode()  # encode str to bytes
    value = b64decode(value)
    if compress_object:
        value = decompress(value)
    return loads(value)


class PickledWidget(Textarea):
    """
    This is responsible for outputting HTML representing a given field.
    """

    def render(self, name, value, attrs=None, renderer=None):
        """Display of the PickledField in django admin"""

        repr_value = repr(value)

        # analyze represented value to see how big the field should be
        if attrs is not None:
            attrs["name"] = name
        else:
            attrs = {"name": name}
        attrs["cols"] = 30
        # adapt number of rows to number of lines in string
        rows = 1
        if isinstance(value, str) and "\n" in repr_value:
            rows = max(1, len(value.split("\n")))
        attrs["rows"] = rows
        attrs = self.build_attrs(attrs)

        try:
            # necessary to convert it back after repr(), otherwise validation errors will mutate it
            value = literal_eval(repr_value)
        except ValueError:
            pass
        return super().render(name, value, attrs=attrs, renderer=renderer)

    def value_from_datadict(self, data, files, name):
        dat = data.get(name)
        # import evennia;evennia.set_trace()
        return dat


class PickledFormField(CharField):
    """
    This represents one input field for the form.

    """

    widget = PickledWidget
    default_error_messages = dict(CharField.default_error_messages)
    default_error_messages["invalid"] = (
        "This is not a Python Literal. You can store things like strings, "
        "integers, or floats, but you must do it by typing them as you would "
        "type them in the Python Interpreter. For instance, strings must be "
        "surrounded by quote marks. We have converted it to a string for your "
        "convenience. If it is acceptable, please hit save again."
    )

    def __init__(self, *args, **kwargs):
        # This needs to fall through to literal_eval.
        kwargs["required"] = False
        super().__init__(*args, **kwargs)

    def clean(self, value):
        value = super().clean(value)

        # handle empty input
        try:
            if not value.strip():
                # Field was left blank. Make this None.
                value = "None"
        except AttributeError:
            pass

        # parse raw Python
        try:
            return literal_eval(value)
        except (ValueError, SyntaxError):
            pass

        # fall through to parsing the repr() of the data
        try:
            value = repr(value)
            return literal_eval(value)
        except (ValueError, SyntaxError):
            raise ValidationError(self.error_messages["invalid"])


class PickledObjectField(models.Field):
    """
    A field that will accept *any* python object and store it in the
    database. PickledObjectField will optionally compress its values if
    declared with the keyword argument ``compress=True``.

    Does not actually encode and compress ``None`` objects (although you
    can still do lookups using None). This way, it is still possible to
    use the ``isnull`` lookup type correctly.
    """

    def __init__(self, *args, **kwargs):
        self.compress = kwargs.pop("compress", False)
        self.protocol = kwargs.pop("protocol", DEFAULT_PROTOCOL)
        super().__init__(*args, **kwargs)

    def get_default(self):
        """
        Returns the default value for this field.

        The default implementation on models.Field calls force_text
        on the default, which means you can't set arbitrary Python
        objects as the default. To fix this, we just return the value
        without calling force_text on it. Note that if you set a
        callable as a default, the field will still call it. It will
        *not* try to pickle and encode it.

        """
        if self.has_default():
            if callable(self.default):
                return self.default()
            return self.default
        # If the field doesn't have a default, then we punt to models.Field.
        return super().get_default()

    def from_db_value(self, value, *args):
        """
        B64decode and unpickle the object, optionally decompressing it.

        If an error is raised in de-pickling and we're sure the value is
        a definite pickle, the error is allowed to propagate. If we
        aren't sure if the value is a pickle or not, then we catch the
        error and return the original value instead.

        """
        if value is not None:
            try:
                value = dbsafe_decode(value, self.compress)
            except Exception:
                # If the value is a definite pickle; and an error is raised in
                # de-pickling it should be allowed to propogate.
                if isinstance(value, PickledObject):
                    raise
            else:
                if isinstance(value, _ObjectWrapper):
                    return value._obj
        return value

    def formfield(self, **kwargs):
        return PickledFormField(**kwargs)

    def pre_save(self, model_instance, add):
        value = super().pre_save(model_instance, add)
        return wrap_conflictual_object(value)

    def get_db_prep_value(self, value, connection=None, prepared=False):
        """
        Pickle and b64encode the object, optionally compressing it.

        The pickling protocol is specified explicitly (by default 2),
        rather than as -1 or HIGHEST_PROTOCOL, because we don't want the
        protocol to change over time. If it did, ``exact`` and ``in``
        lookups would likely fail, since pickle would now be generating
        a different string.

        """
        if value is not None and not isinstance(value, PickledObject):
            # We call force_text here explicitly, so that the encoded string
            # isn't rejected by the postgresql_psycopg2 backend. Alternatively,
            # we could have just registered PickledObject with the psycopg
            # marshaller (telling it to store it like it would a string), but
            # since both of these methods result in the same value being stored,
            # doing things this way is much easier.
            value = force_text(dbsafe_encode(value, self.compress, self.protocol))
        return value

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_value(value)

    def get_internal_type(self):
        return "TextField"

    def get_db_prep_lookup(self, lookup_type, value, connection=None, prepared=False):
        if lookup_type not in ["exact", "in", "isnull"]:
            raise TypeError("Lookup type %s is not supported." % lookup_type)
        # The Field model already calls get_db_prep_value before doing the
        # actual lookup, so all we need to do is limit the lookup types.
        return super().get_db_prep_lookup(
            lookup_type, value, connection=connection, prepared=prepared
        )
