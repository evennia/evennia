from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

class CaseInsensitiveModelBackend(ModelBackend):
  """
  By default ModelBackend does case _sensitive_ username authentication, which isn't what is
  generally expected.  This backend supports case insensitive username authentication.
  """
  def authenticate(self, username=None, password=None):
    User = get_user_model()
    try:
      user = User.objects.get(username__iexact=username)
      if user.check_password(password):
        return user
      else:
        return None
    except User.DoesNotExist:
      return None
