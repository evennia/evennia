from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm, UsernameField
from evennia.utils import class_from_module

class AccountCreationForm(UserCreationForm):
    
    class Meta:
        model = class_from_module(settings.BASE_ACCOUNT_TYPECLASS)
        fields = ("username", "email")
        field_classes = {'username': UsernameField}
    
    email = forms.EmailField(help_text="A valid email address. Optional; used for password resets.", required=False)