"""
The main index page, including the game stats

"""

from django.conf import settings
from django.views.generic import TemplateView

from evennia import SESSION_HANDLER
from evennia.accounts.models import AccountDB
from evennia.objects.models import ObjectDB
from evennia.utils import class_from_module


def _gamestats():
    """
    Generate a the gamestat context for the main index page
    """
    # Some misc. configurable stuff.
    # TODO: Move this to either SQL or settings.py based configuration.
    fpage_account_limit = 4

    # A QuerySet of the most recently connected accounts.
    recent_users = AccountDB.objects.get_recently_connected_accounts()
    nplyrs_conn_recent = len(recent_users) or "none"
    nplyrs = AccountDB.objects.num_total_accounts() or "none"
    nplyrs_reg_recent = len(AccountDB.objects.get_recently_created_accounts()) or "none"
    nsess = SESSION_HANDLER.account_count()
    # nsess = len(AccountDB.objects.get_connected_accounts()) or "no one"

    nobjs = ObjectDB.objects.count()
    nobjs = nobjs or 1  # fix zero-div error with empty database
    Character = class_from_module(
        settings.BASE_CHARACTER_TYPECLASS, fallback=settings.FALLBACK_CHARACTER_TYPECLASS
    )
    nchars = Character.objects.all_family().count()
    Room = class_from_module(
        settings.BASE_ROOM_TYPECLASS, fallback=settings.FALLBACK_ROOM_TYPECLASS
    )
    nrooms = Room.objects.all_family().count()
    Exit = class_from_module(
        settings.BASE_EXIT_TYPECLASS, fallback=settings.FALLBACK_EXIT_TYPECLASS
    )
    nexits = Exit.objects.all_family().count()
    nothers = nobjs - nchars - nrooms - nexits

    pagevars = {
        "page_title": "Front Page",
        "accounts_connected_recent": recent_users[:fpage_account_limit],
        "num_accounts_connected": nsess or "no one",
        "num_accounts_registered": nplyrs or "no",
        "num_accounts_connected_recent": nplyrs_conn_recent or "no",
        "num_accounts_registered_recent": nplyrs_reg_recent or "no one",
        "num_rooms": nrooms or "none",
        "num_exits": nexits or "no",
        "num_objects": nobjs or "none",
        "num_characters": nchars or "no",
        "num_others": nothers or "no",
    }
    return pagevars


class EvenniaIndexView(TemplateView):
    """
    This is a basic example of a Django class-based view, which are functionally
    very similar to Evennia Commands but differ in structure. Commands are used
    to interface with users using a terminal client. Views are used to interface
    with users using a web browser.

    To use a class-based view, you need to have written a template in HTML, and
    then you write a view like this to tell Django what values to display on it.

    While there are simpler ways of writing views using plain functions (and
    Evennia currently contains a few examples of them), just like Commands,
    writing views as classes provides you with more flexibility-- you can extend
    classes and change things to suit your needs rather than having to copy and
    paste entire code blocks over and over. Django also comes with many default
    views for displaying things, all of them implemented as classes.

    This particular example displays the index page.

    """

    # Tell the view what HTML template to use for the page
    template_name = "website/index.html"

    # This method tells the view what data should be displayed on the template.
    def get_context_data(self, **kwargs):
        """
        This is a common Django method. Think of this as the website
        equivalent of the Evennia Command.func() method.

        If you just want to display a static page with no customization, you
        don't need to define this method-- just create a view, define
        template_name and you're done.

        The only catch here is that if you extend or overwrite this method,
        you'll always want to make sure you call the parent method to get a
        context object. It's just a dict, but it comes prepopulated with all
        sorts of background data intended for display on the page.

        You can do whatever you want to it, but it must be returned at the end
        of this method.

        Keyword Args:
            any (any): Passed through.

        Returns:
            context (dict): Dictionary of data you want to display on the page.

        """
        # Always call the base implementation first to get a context object
        context = super().get_context_data(**kwargs)

        # Add game statistics and other pagevars
        context.update(_gamestats())

        return context
