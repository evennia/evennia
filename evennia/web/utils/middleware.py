from django.contrib.auth import authenticate, login

from evennia.accounts.models import AccountDB
from evennia.utils import logger


class SharedLoginMiddleware(object):
    """
    Handle the shared login between website and webclient.

    """

    def __init__(self, get_response):
        # One-time configuration and initialization.
        self.get_response = get_response

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        # Synchronize credentials between webclient and website
        # Must be performed *before* rendering the view (issue #1723)
        self.make_shared_login(request)

        # Process view
        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        # Return processed view
        return response

    @classmethod
    def make_shared_login(cls, request):
        csession = request.session
        account = request.user
        website_uid = csession.get("website_authenticated_uid", None)
        webclient_uid = csession.get("webclient_authenticated_uid", None)

        if not csession.session_key:
            # this is necessary to build the sessid key
            csession.save()

        if account.is_authenticated:
            # Logged into website
            if website_uid is None:
                # fresh website login (just from login page)
                csession["website_authenticated_uid"] = account.id
            if webclient_uid is None:
                # auto-login web client
                csession["webclient_authenticated_uid"] = account.id

        elif webclient_uid:
            # Not logged into website, but logged into webclient
            if website_uid is None:
                csession["website_authenticated_uid"] = account.id
                account = AccountDB.objects.get(id=webclient_uid)
                try:
                    # calls our custom authenticate, in web/utils/backend.py
                    authenticate(autologin=account)
                    login(request, account)
                except AttributeError:
                    logger.log_trace()

        if csession.get("webclient_authenticated_uid", None):
            # set a nonce to prevent the webclient from erasing the webclient_authenticated_uid value
            csession["webclient_authenticated_nonce"] = (
                csession.get("webclient_authenticated_nonce", 0) + 1
            )
            # wrap around to prevent integer overflows
            if csession["webclient_authenticated_nonce"] > 32:
                csession["webclient_authenticated_nonce"] = 0
