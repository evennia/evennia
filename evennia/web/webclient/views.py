"""
This contains a simple view for rendering the webclient
page and serve it eventual static content.

"""

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.http import Http404
from django.shortcuts import render

from evennia.accounts.models import AccountDB
from evennia.utils import logger


def webclient(request):
    """
    Webclient page template loading.

    """
    # auto-login is now handled by evennia.web.utils.middleware

    # check if webclient should be enabled
    if not settings.WEBCLIENT_ENABLED:
        raise Http404

    # make sure to store the browser session's hash so the webclient can get to it!
    pagevars = {"browser_sessid": request.session.session_key}

    return render(request, "webclient.html", pagevars)
