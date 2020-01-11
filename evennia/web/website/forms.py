from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm, UsernameField
from django.forms import ModelForm
from django.utils.html import escape
from evennia.utils import class_from_module


class EvenniaForm(forms.Form):
    """
    This is a stock Django form, but modified so that all values provided
    through it are escaped (sanitized). Validation is performed by the fields
    you define in the form.

    This has little to do with Evennia itself and is more general web security-
    related.

    https://www.owasp.org/index.php/Input_Validation_Cheat_Sheet#Goals_of_Input_Validation

    """

    def clean(self):
        """
        Django hook. Performed on form submission.

        Returns:
            cleaned (dict): Dictionary of key:value pairs submitted on the form.

        """
        # Call parent function
        cleaned = super(EvenniaForm, self).clean()

        # Escape all values provided by user
        cleaned = {k: escape(v) for k, v in cleaned.items()}
        return cleaned


class AccountForm(UserCreationForm):
    """
    This is a generic Django form tailored to the Account model.

    In this incarnation it does not allow getting/setting of attributes, only
    core User model fields (username, email, password).

    """

    class Meta:
        """
        This is a Django construct that provides additional configuration to
        the form.

        """

        # The model/typeclass this form creates
        model = class_from_module(settings.BASE_ACCOUNT_TYPECLASS)

        # The fields to display on the form, in the given order
        fields = ("username", "email")

        # Any overrides of field classes
        field_classes = {"username": UsernameField}

    # Username is collected as part of the core UserCreationForm, so we just need
    # to add a field to (optionally) capture email.
    email = forms.EmailField(
        help_text="A valid email address. Optional; used for password resets.", required=False
    )


class ObjectForm(EvenniaForm, ModelForm):
    """
    This is a Django form for generic Evennia Objects that allows modification
    of attributes when called from a descendent of ObjectUpdate or ObjectCreate
    views.

    It defines no fields by default; you have to do that by extending this class
    and defining what fields you want to be recorded. See the CharacterForm for
    a simple example of how to do this.

    """

    class Meta:
        """
        This is a Django construct that provides additional configuration to
        the form.

        """

        # The model/typeclass this form creates
        model = class_from_module(settings.BASE_OBJECT_TYPECLASS)

        # The fields to display on the form, in the given order
        fields = ("db_key",)

        # This lets us rename ugly db-specific keys to something more human
        labels = {"db_key": "Name"}


class CharacterForm(ObjectForm):
    """
    This is a Django form for Evennia Character objects.

    Since Evennia characters only have one attribute by default, this form only
    defines a field for that single attribute. The names of fields you define should
    correspond to their names as stored in the dbhandler; you can display
    'prettier' versions of the fieldname on the form using the 'label' kwarg.

    The basic field types are CharFields and IntegerFields, which let you enter
    text and numbers respectively. IntegerFields have some neat validation tricks
    they can do, like mandating values fall within a certain range.

    For example, a complete "age" field (which stores its value to
    `character.db.age` might look like:

    age = forms.IntegerField(
        label="Your Age",
        min_value=18, max_value=9000,
        help_text="Years since your birth.")

    Default input fields are generic single-line text boxes. You can control what
    sort of input field users will see by specifying a "widget." An example of
    this is used for the 'desc' field to show a Textarea box instead of a Textbox.

    For help in building out your form, please see:
    https://docs.djangoproject.com/en/1.11/topics/forms/#building-a-form-in-django

    For more information on fields and their capabilities, see:
    https://docs.djangoproject.com/en/1.11/ref/forms/fields/

    For more on widgets, see:
    https://docs.djangoproject.com/en/1.11/ref/forms/widgets/

    """

    class Meta:
        """
        This is a Django construct that provides additional configuration to
        the form.

        """

        # Get the correct object model
        model = class_from_module(settings.BASE_CHARACTER_TYPECLASS)

        # Allow entry of the 'key' field
        fields = ("db_key",)

        # Rename 'key' to something more intelligible
        labels = {"db_key": "Name"}

    # Fields pertaining to configurable attributes on the Character object.
    desc = forms.CharField(
        label="Description",
        max_length=2048,
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="A brief description of your character.",
    )


class CharacterUpdateForm(CharacterForm):
    """
    This is a Django form for updating Evennia Character objects.

    By default it is the same as the CharacterForm, but if there are circumstances
    in which you don't want to let players edit all the same attributes they had
    access to during creation, you can redefine this form with those fields you do
    wish to allow.

    """

    pass
