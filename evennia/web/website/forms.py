from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm, UsernameField
from django.forms import ModelForm
from django.utils.html import escape
from evennia.utils import class_from_module

class EvenniaForm(forms.Form):
    
    def clean(self):
        cleaned = super(EvenniaForm, self).clean()
        
        # Escape all values provided by user
        cleaned = {k:escape(v) for k,v in cleaned.items()}
        return cleaned

class AccountForm(EvenniaForm, UserCreationForm):
    
    class Meta:
        model = class_from_module(settings.BASE_ACCOUNT_TYPECLASS)
        fields = ("username", "email")
        field_classes = {'username': UsernameField}
    
    email = forms.EmailField(help_text="A valid email address. Optional; used for password resets.", required=False)
    
class ObjectForm(EvenniaForm, ModelForm):
    
    class Meta:
        model = class_from_module(settings.BASE_OBJECT_TYPECLASS)
        fields = ("db_key",)
        labels = {
            'db_key': 'Name',
        }
    
class CharacterForm(ObjectForm):
    
    class Meta:
        # Get the correct object model
        model = class_from_module(settings.BASE_CHARACTER_TYPECLASS)
        # Allow entry of the 'key' field
        fields = ("db_key",)
        # Rename 'key' to something more intelligible
        labels = {
            'db_key': 'Name',
        }
        
    # Fields pertaining to user-configurable attributes on the Character object.
    desc = forms.CharField(label='Description', widget=forms.Textarea(attrs={'rows': 3}), max_length=2048, required=False)
    
class CharacterUpdateForm(CharacterForm):
    """
    Provides a form that only allows updating of db attributes, not model
    attributes.
    
    """
    pass