from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

class CaseInsensitiveModelBackend(ModelBackend):
  """
  By default ModelBackend does case _sensitive_ username
  authentication, which isn't what is generally expected.  This
  backend supports case insensitive username authentication.

  """
  def authenticate(self, username=None, password=None, autologin=None):
      """
      Custom authenticate with bypass for auto-logins

      Args:
          username (str, optional): Name of user to authenticate.
          password (str, optional): Password of user
          autologin (Player, optional): If given, assume this is
            an already authenticated player and bypass authentication.
      """
      if autologin:
          # Note: Setting .backend on player is critical in order to
          # be allowed to call django.auth.login(player) later. This
          # is necessary for the auto-login feature of the webclient,
          # but it's important to make sure Django doesn't change this
          # requirement or the name of the property down the line. /Griatch
          autologin.backend = "evennia.web.utils.backends.CaseInsensitiveModelBackend"
          return autologin
      else:
          # In this case .backend will be assigned automatically
          # somewhere along the way.
          Player = get_user_model()
          try:
            player = Player.objects.get(username__iexact=username)
            if player.check_password(password):
              return player
            else:
              return None
          except Player.DoesNotExist:
            return None
