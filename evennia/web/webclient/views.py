
"""
This contains a simple view for rendering the webclient
page and serve it eventual static content.

"""
from __future__ import print_function
from django.shortcuts import render
from django.contrib.auth import login, authenticate

from evennia.accounts.models import AccountDB
from evennia.utils import logger


def _shared_login(request):
    """
    Handle the shared login between website and webclient.

    """
    csession = request.session
    account = request.user
    sesslogin = csession.get("logged_in", None)

    # check if user has authenticated to website
    if csession.session_key is None:
        # this is necessary to build the sessid key
        csession.save()
    elif account.is_authenticated():
        if not sesslogin:
            # User has already authenticated to website
            csession["logged_in"] = account.id
    elif sesslogin:
        # The webclient has previously registered a login to this browser_session
        account = AccountDB.objects.get(id=sesslogin)
        try:
            # calls our custom authenticate in web/utils/backends.py
            account = authenticate(autologin=account)
            login(request, account)
        except AttributeError:
            logger.log_trace()


def webclient(request):
    """
    Webclient page template loading.

    """
    # handle webclient-website shared login
    _shared_login(request)

    # make sure to store the browser session's hash so the webclient can get to it!
    pagevars = {'browser_sessid': request.session.session_key}

    return render(request, 'webclient.html', pagevars)
