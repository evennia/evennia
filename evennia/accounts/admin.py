#
# This sets up how models are displayed
# in the web admin interface.
#
from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from evennia.accounts.models import AccountDB
from evennia.typeclasses.admin import AttributeInline, TagInline
from evennia.utils import create


# handle the custom User editor
class AccountDBChangeForm(UserChangeForm):
    """
    Modify the accountdb class.

    """

    class Meta(object):
        model = AccountDB
        fields = "__all__"

    username = forms.RegexField(
        label="Username",
        max_length=30,
        regex=r"^[\w. @+-]+$",
        widget=forms.TextInput(attrs={"size": "30"}),
        error_messages={
            "invalid": "This value may contain only letters, spaces, numbers "
            "and @/./+/-/_ characters."
        },
        help_text="30 characters or fewer. Letters, spaces, digits and " "@/./+/-/_ only.",
    )

    def clean_username(self):
        """
        Clean the username and check its existence.

        """
        username = self.cleaned_data["username"]
        if username.upper() == self.instance.username.upper():
            return username
        elif AccountDB.objects.filter(username__iexact=username):
            raise forms.ValidationError("An account with that name " "already exists.")
        return self.cleaned_data["username"]


class AccountDBCreationForm(UserCreationForm):
    """
    Create a new AccountDB instance.
    """

    class Meta(object):
        model = AccountDB
        fields = "__all__"

    username = forms.RegexField(
        label="Username",
        max_length=30,
        regex=r"^[\w. @+-]+$",
        widget=forms.TextInput(attrs={"size": "30"}),
        error_messages={
            "invalid": "This value may contain only letters, spaces, numbers "
            "and @/./+/-/_ characters."
        },
        help_text="30 characters or fewer. Letters, spaces, digits and " "@/./+/-/_ only.",
    )

    def clean_username(self):
        """
        Cleanup username.
        """
        username = self.cleaned_data["username"]
        if AccountDB.objects.filter(username__iexact=username):
            raise forms.ValidationError("An account with that name already " "exists.")
        return username


class AccountForm(forms.ModelForm):
    """
    Defines how to display Accounts

    """

    class Meta(object):
        model = AccountDB
        fields = "__all__"

    db_key = forms.RegexField(
        label="Username",
        initial="AccountDummy",
        max_length=30,
        regex=r"^[\w. @+-]+$",
        required=False,
        widget=forms.TextInput(attrs={"size": "30"}),
        error_messages={
            "invalid": "This value may contain only letters, spaces, numbers"
            " and @/./+/-/_ characters."
        },
        help_text="This should be the same as the connected Account's key "
        "name. 30 characters or fewer. Letters, spaces, digits and "
        "@/./+/-/_ only.",
    )

    db_typeclass_path = forms.CharField(
        label="Typeclass",
        initial=settings.BASE_ACCOUNT_TYPECLASS,
        widget=forms.TextInput(attrs={"size": "78"}),
        help_text="Required. Defines what 'type' of entity this is. This "
        "variable holds a Python path to a module with a valid "
        "Evennia Typeclass. Defaults to "
        "settings.BASE_ACCOUNT_TYPECLASS.",
    )

    db_permissions = forms.CharField(
        label="Permissions",
        initial=settings.PERMISSION_ACCOUNT_DEFAULT,
        required=False,
        widget=forms.TextInput(attrs={"size": "78"}),
        help_text="In-game permissions. A comma-separated list of text "
        "strings checked by certain locks. They are often used for "
        "hierarchies, such as letting an Account have permission "
        "'Admin', 'Builder' etc. An Account permission can be "
        "overloaded by the permissions of a controlled Character. "
        "Normal accounts use 'Accounts' by default.",
    )

    db_lock_storage = forms.CharField(
        label="Locks",
        widget=forms.Textarea(attrs={"cols": "100", "rows": "2"}),
        required=False,
        help_text="In-game lock definition string. If not given, defaults "
        "will be used. This string should be on the form "
        "<i>type:lockfunction(args);type2:lockfunction2(args);...",
    )
    db_cmdset_storage = forms.CharField(
        label="cmdset",
        initial=settings.CMDSET_ACCOUNT,
        widget=forms.TextInput(attrs={"size": "78"}),
        required=False,
        help_text="python path to account cmdset class (set in "
        "settings.CMDSET_ACCOUNT by default)",
    )


class AccountInline(admin.StackedInline):
    """
    Inline creation of Account

    """

    model = AccountDB
    template = "admin/accounts/stacked.html"
    form = AccountForm
    fieldsets = (
        (
            "In-game Permissions and Locks",
            {
                "fields": ("db_lock_storage",),
                # {'fields': ('db_permissions', 'db_lock_storage'),
                "description": "<i>These are permissions/locks for in-game use. "
                "They are unrelated to website access rights.</i>",
            },
        ),
        (
            "In-game Account data",
            {
                "fields": ("db_typeclass_path", "db_cmdset_storage"),
                "description": "<i>These fields define in-game-specific properties "
                "for the Account object in-game.</i>",
            },
        ),
    )

    extra = 1
    max_num = 1


class AccountTagInline(TagInline):
    """
    Inline Account Tags.

    """

    model = AccountDB.db_tags.through
    related_field = "accountdb"


class AccountAttributeInline(AttributeInline):
    """
    Inline Account Attributes.

    """

    model = AccountDB.db_attributes.through
    related_field = "accountdb"


class AccountDBAdmin(BaseUserAdmin):
    """
    This is the main creation screen for Users/accounts

    """

    list_display = ("username", "email", "is_staff", "is_superuser")
    form = AccountDBChangeForm
    add_form = AccountDBCreationForm
    inlines = [AccountTagInline, AccountAttributeInline]
    fieldsets = (
        (None, {"fields": ("username", "password", "email")}),
        (
            "Website profile",
            {
                "fields": ("first_name", "last_name"),
                "description": "<i>These are not used " "in the default system.</i>",
            },
        ),
        (
            "Website dates",
            {
                "fields": ("last_login", "date_joined"),
                "description": "<i>Relevant only to the website.</i>",
            },
        ),
        (
            "Website Permissions",
            {
                "fields": ("is_active", "is_staff", "is_superuser", "user_permissions", "groups"),
                "description": "<i>These are permissions/permission groups for "
                "accessing the admin site. They are unrelated to "
                "in-game access rights.</i>",
            },
        ),
        (
            "Game Options",
            {
                "fields": ("db_typeclass_path", "db_cmdset_storage", "db_lock_storage"),
                "description": "<i>These are attributes that are more relevant " "to gameplay.</i>",
            },
        ),
    )
    # ('Game Options', {'fields': (
    #     'db_typeclass_path', 'db_cmdset_storage',
    #     'db_permissions', 'db_lock_storage'),
    #     'description': '<i>These are attributes that are '
    #                    'more relevant to gameplay.</i>'}))

    add_fieldsets = (
        (
            None,
            {
                "fields": ("username", "password1", "password2", "email"),
                "description": "<i>These account details are shared by the admin "
                "system and the game.</i>",
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        """
        Custom save actions.

        Args:
            request (Request): Incoming request.
            obj (Object): Object to save.
            form (Form): Related form instance.
            change (bool): False if this is a new save and not an update.

        """
        obj.save()
        if not change:
            # calling hooks for new account
            obj.set_class_from_typeclass(typeclass_path=settings.BASE_ACCOUNT_TYPECLASS)
            obj.basetype_setup()
            obj.at_account_creation()

    def response_add(self, request, obj, post_url_continue=None):
        from django.http import HttpResponseRedirect
        from django.urls import reverse

        return HttpResponseRedirect(reverse("admin:accounts_accountdb_change", args=[obj.id]))


admin.site.register(AccountDB, AccountDBAdmin)
