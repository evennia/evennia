import traceback
from logging import getLogger

import sys
from django.conf import settings
from evennia.contrib.collab.template.extensions import perm_bind, getter, setter, perm_check
from evennia.utils.ansi import raw
from jinja2 import BaseLoader

from jinja2 import DebugUndefined
from jinja2 import TemplateSyntaxError
from jinja2.exceptions import TemplatesNotFound
from jinja2.sandbox import SandboxedEnvironment


logger = getLogger(__name__)


class ExpressionLoader(BaseLoader):
    """
    Take a template's 'name' and evaluate it literally as the template.
    """
    def get_source(self, environment, template):
        return template, 'expression', None


class EvTemplateEnvironment(SandboxedEnvironment):
    def is_safe_attribute(self, obj, attr, value):
        if hasattr(obj, 'template_permitted') and attr in obj.template_permitted:
            return True
        return False

    def is_safe_callable(self, obj):
        return getattr(obj, 'evtemplate_safe', False)


ENV = None


def gen_env():
    global ENV
    ENV = EvTemplateEnvironment(
        autoescape=False, undefined=DebugUndefined, extensions=settings.COLLAB_TEMPLATE_EXTENSIONS,
        loader=ExpressionLoader(),
    )


def evtemplate(string, run_as=None, me=None, this=None, how=None, here=None, context=None, **kwargs):
    """
    Parses a Jinja2 template string in the sandboxed environment.

    run_as: The object the program should run as.
    me: The the one who is viewing the message.
    this: The relevant item that the message is being executed for
        (such as an object whose desc triggered this message)
    here: The location in which this message is being executed.
    how: A string that describes the cause for the rendering,
        like 'desc' or 'succ'. Optional but highly recommended.

    Jinja is not very consistent about its exception handling when it
    concerns with helping a developer figure out where an error is.

    There is probably a better way to handle the exceptions here, all the same.
    """
    if not ENV:
        gen_env()
    if not me:
        raise ValueError("You cannot render a template without an observer.")
    if not run_as:
        # If there is no one that the script should run as, it might mean that there's
        # no owner for the object. That can't be trusted, so just return the raw
        # template text, and log the issue.
        logger.info("Refused to render template without run_as set. Returning raw string.")
        return string
    if not here:
        here = me.location
    if not this:
        raise ValueError("Templates must have a 'this' to render for.")
    kwargs.update({
        'me': me,
        'run_as': run_as,
        'this': this,
        'here': here,
        'how': how,
        'perm_check': perm_check,
        'fetch': perm_bind(getter, run_as),
        'store': perm_bind(setter, run_as),
    })
    context = context or {}
    try:
        return ENV.from_string(string, globals=kwargs).render(**context)
    except TemplateSyntaxError as e:
        # Something was wrong with the source template string.
        if e.source:
            source_lines = [raw(u"{}:{}".format(i, line)) for i, line in enumerate(e.source.split('\n'), start=1)]
            source_lines[e.lineno - 1] = u"|r|h" + source_lines[e.lineno - 1] + u"|n"
            source_lines.append(str(e))
        else:
            source_lines = [u"Error on unknown line (possibly caused by an included template): {}".format(e)]

        return u'\n'.join(source_lines)
    except TemplatesNotFound:
        return u"Include error: Attempted to include a null value. Check to make sure your " \
               u"include statement contains a template string."
    except Exception as e:
        # Now we have the sort of exceptions Jinja is (especially) bad at handling.
        ex_type, ex, tb = sys.exc_info()
        tb = traceback.extract_tb(tb)
        if tb[-1][0] == '<template>':
            extra = u" on line {}".format(tb[-1][1])
        else:
            extra = u''
        return u"Error when executing template{}. {}: {}".format(extra, e.__class__.__name__, e)
