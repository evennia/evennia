import json
from collections import MutableMapping
from json import JSONEncoder

import time
from evennia.contrib.collab.perms import prefix_check, attr_check, collab_check
from evennia.contrib.gendersub import GENDER_PRONOUN_MAP, gender_sub
from evennia.typeclasses.models import TypedObject
from evennia.utils import inherits_from

from jinja2 import nodes
from jinja2.exceptions import SecurityError, TemplateSyntaxError
from jinja2.ext import Extension


def safe(func):
    """
    Decorator for functions so that they can be called by the sandboxed template system.
    """
    func.evtemplate_safe = True
    return func


class AttribJSONEncoder(JSONEncoder):
    """
    Decoder which can serialize references to TypeClassed objects.

    It's not actually used for storing any information, but is written in a practical
    fashion anyway.
    """
    def default(self, o):
        if isinstance(o, TypedObject):
            return {'##DBREF': [o.id, time.mktime(o.date_created.timetuple())]}
        return o


def get_gender_map(target):
    gender = target.usrattributes.get("gender", default="neutral").lower()
    gender_map = dict(GENDER_PRONOUN_MAP)
    custom_map = target.usrattributes.get("custom_gender_map", default=None)
    if inherits_from(custom_map, MutableMapping):
        gender_map.update(custom_map)
    gender = gender if gender in gender_map else 'neutral'
    return gender, gender_map


class PronounsExtension(Extension):
    """
    Adds pronoun substitutions.
    """
    tags = {'pro'}

    def parse(self, parser):
        # We get the line number so that we can give
        # that line number to the node we create by hand.
        lineno = next(parser.stream).lineno

        # now we parse a single expression that is used as the pronoun target.
        try:
            target = parser.parse_expression()
        except TemplateSyntaxError:
            target = nodes.Const(None)

        # now we parse the body of the cache block up to `endpro` and
        # drop the needle (which would always be `endpro` in that case)
        body = parser.parse_statements(['name:endpro'], drop_needle=True)
        ctx_ref = nodes.ContextReference()
        # now return a `CallBlock` node that calls our _pronoun_sub
        # helper method on this extension.
        block = nodes.CallBlock(self.call_method('pronoun_sub', args=[target, ctx_ref]), [], [], body)
        block.set_lineno(lineno)
        return block

    @safe
    def pronoun_sub(self, target, context, caller):
        if target is None:
            target = context['me']
        return gender_sub(target, caller())


def perm_bind(func, run_as):
    """
    To be used with the below get/set functions for getting/setting
    db attributes in a template.
    """
    @safe
    def wrapped(*args, **kwargs):
        return func(run_as, *args, **kwargs)
    return wrapped


def getter(run_as, target, prop_name):
    """
    Fetches the value of a property.
    """
    name, handler = prefix_check(target, prop_name)
    if attr_check(run_as, target, 'read', handler):
        result = handler.get(name)
        # Let's verify this object is primitive only all the way down,
        # and then make a different copy of it so that it is not saved
        # implicitly. Implicit saves could result in a security error
        # where a user who can read a mutable object could then change
        # it and affect something they should not have access to.
        try:
            result = json.dumps(result)
        except TypeError:
            raise SecurityError(
                "'{prop_name}' on {target} contains data which cannot be securely sandboxed.".format(
                    prop_name=prop_name, target=target)
            )
        return json.loads(result)
    raise SecurityError(
        "{run_as} does not have read access to property '{prop_name}' on {target}".format(
            run_as=run_as, prop_name=prop_name, target=target,
        )
    )


def setter(run_as, target, prop_name, prop_val):
    """
    Sets the value of a property.
    """
    name, handler = prefix_check(target, prop_name)
    if attr_check(run_as, target, 'write', handler):
        try:
            json.dumps(prop_val)
        except TypeError:
            raise SecurityError("{prop_val} contains data which cannot be securely sandboxed.".format(
                prop_val=repr(prop_val)
            ))
        handler.add(name, prop_val)
        return ''
    raise SecurityError(
        "{run_as} does not have write access to property '{prop_name}' on {target}".format(
            run_as=run_as, prop_name=prop_name, target=target,
        )
    )


perm_check = safe(collab_check)
