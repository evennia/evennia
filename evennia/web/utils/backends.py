from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class CaseInsensitiveModelBackend(ModelBackend):
    """
    By default ModelBackend does case _sensitive_ username
    authentication, which isn't what is generally expected.  This
    backend supports case insensitive username authentication.

    """

    def authenticate(self, request, username=None, password=None, autologin=None):
        """
        Custom authenticate with bypass for auto-logins

        Args:
            request (Request): Request object.
            username (str, optional): Name of user to authenticate.
            password (str, optional): Password of user
            autologin (Account, optional): If given, assume this is
              an already authenticated account and bypass authentication.
        """
        if autologin:
            # Note: Setting .backend on account is critical in order to
            # be allowed to call django.auth.login(account) later. This
            # is necessary for the auto-login feature of the webclient,
            # but it's important to make sure Django doesn't change this
            # requirement or the name of the property down the line. /Griatch
            autologin.backend = "evennia.web.utils.backends.CaseInsensitiveModelBackend"
            return autologin
        else:
            # In this case .backend will be assigned automatically
            # somewhere along the way.
            Account = get_user_model()
            try:
                account = Account.objects.get(username__iexact=username)
                if account.check_password(password):
                    return account
                else:
                    return None
            except Account.DoesNotExist:
                return None
