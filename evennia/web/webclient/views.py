
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
    # these can have 3 values:
    #   None - previously unused (auto-login)
    #   False - actively logged out (don't auto-login)
    #   <uid> - logged in User/Account id
    website_uid = csession.get("website_authenticated_uid", None)
    webclient_uid = csession.get("webclient_authenticated_uid", None)

    # check if user has authenticated to website
    if not csession.session_key:
        # this is necessary to build the sessid key
        csession.save()

    if webclient_uid:
        # The webclient has previously registered a login to this browser_session
        if not account.is_authenticated() and not website_uid:
            try:
                account = AccountDB.objects.get(id=webclient_uid)
            except AccountDB.DoesNotExist:
                # this can happen e.g. for guest accounts or deletions
                csession["website_authenticated_uid"] = False
                csession["webclient_authenticated_uid"] = False
                return
            try:
                # calls our custom authenticate in web/utils/backends.py
                account = authenticate(autologin=account)
                login(request, account)
                csession["website_authenticated_uid"] = webclient_uid
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
