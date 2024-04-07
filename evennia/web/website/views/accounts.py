"""
Views for managing accounts.

"""

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy

from evennia.utils import class_from_module
from evennia.web.website import forms

from .mixins import EvenniaCreateView, TypeclassMixin


class AccountMixin(TypeclassMixin):
    """
    This is used to grant abilities to classes it is added to.

    Any view class with this in its inheritance list will be modified to work
    with Account objects instead of generic Objects or otherwise.

    """

    # -- Django constructs --
    model = class_from_module(
        settings.BASE_ACCOUNT_TYPECLASS, fallback=settings.FALLBACK_ACCOUNT_TYPECLASS
    )
    form_class = forms.AccountForm


class AccountCreateView(AccountMixin, EvenniaCreateView):
    """
    Account creation view.

    """

    # -- Django constructs --
    template_name = "website/registration/register.html"
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        """
        Django hook, modified for Evennia.

        This hook is called after a valid form is submitted.

        When an account creation form is submitted and the data is deemed valid,
        proceeds with creating the Account object.

        """
        # Get values provided
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password1"]
        email = form.cleaned_data.get("email", "")

        # Create account. This also runs all validations on the username/password.
        account, errs = self.typeclass.create(username=username, password=password, email=email)

        if not account:
            # password validation happens earlier, only username checks appear here.
            form.add_error("username", ", ".join(errs))
            return self.form_invalid(form)
        else:
            # Inform user of success
            messages.success(
                self.request, f"Your account '{account.name}' was successfully created!"
            )
            return HttpResponseRedirect(self.success_url)
