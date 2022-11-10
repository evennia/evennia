#
# This sets up how models are displayed
# in the web admin interface.
#
from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.options import IS_POPUP_VAR
from django.contrib.admin.utils import unquote
from django.contrib.admin.widgets import FilteredSelectMultiple, ForeignKeyRawIdWidget
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.decorators import method_decorator
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.views.decorators.debug import sensitive_post_parameters

from evennia.accounts.models import AccountDB
from evennia.objects.models import ObjectDB
from evennia.utils import create

from . import utils as adminutils
from .attributes import AttributeInline
from .tags import TagInline

sensitive_post_parameters_m = method_decorator(sensitive_post_parameters())


# handle the custom User editor
class AccountChangeForm(UserChangeForm):
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

    db_typeclass_path = forms.ChoiceField(
        label="Typeclass",
        help_text="This is the Python-path to the class implementing the actual account functionality. "
        "You usually don't need to change this from the default.<BR>"
        "If your custom class is not found here, it may not be imported into Evennia yet.",
        choices=lambda: adminutils.get_and_load_typeclasses(parent=AccountDB),
    )

    db_lock_storage = forms.CharField(
        label="Locks",
        required=False,
        widget=forms.Textarea(attrs={"cols": "100", "rows": "2"}),
        help_text="Locks limit access to the entity. Written on form `type:lockdef;type:lockdef..."
        "<BR>(Permissions (used with the perm() lockfunc) are Tags with the 'permission' type)",
    )

    db_cmdset_storage = forms.CharField(
        label="CommandSet",
        initial=settings.CMDSET_ACCOUNT,
        widget=forms.TextInput(attrs={"size": "78"}),
        required=False,
    )

    is_superuser = forms.BooleanField(
        label="Superuser status",
        required=False,
        help_text="Superusers bypass all in-game locks and has all "
        "permissions without explicitly assigning them. Usually "
        "only one superuser (user #1) is needed and only a superuser "
        "can create another superuser.<BR>"
        "Only Superusers can change the user/group permissions below.",
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

    def __init__(self, *args, **kwargs):
        """
        Tweak some fields dynamically.

        """
        super().__init__(*args, **kwargs)

        # better help text for cmdset_storage
        account_cmdset = settings.CMDSET_ACCOUNT
        self.fields["db_cmdset_storage"].help_text = (
            "Path to Command-set path. Most non-character objects don't need a cmdset"
            " and can leave this field blank. Default cmdset-path<BR> for Accounts "
            f"is <strong>{account_cmdset}</strong> ."
        )


class AccountCreationForm(UserCreationForm):
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


class ObjectPuppetInline(admin.StackedInline):
    """
    Inline creation of puppet-Object in Account.

    """

    from .objects import ObjectCreateForm

    verbose_name = "Puppeted Object"
    model = ObjectDB
    view_on_site = False
    show_change_link = True
    # template = "admin/accounts/stacked.html"
    form = ObjectCreateForm
    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("db_key", "db_typeclass_path"),
                    ("db_location", "db_home", "db_destination"),
                    "db_cmdset_storage",
                    "db_lock_storage",
                ),
                "description": "Object currently puppeted by the account (note that this "
                "will go away if account logs out or unpuppets)",
            },
        ),
    )

    extra = 0
    readonly_fields = (
        "db_key",
        "db_typeclass_path",
        "db_destination",
        "db_location",
        "db_home",
        "db_account",
        "db_cmdset_storage",
        "db_lock_storage",
    )

    # disable adding/deleting this inline - read-only!
    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AccountDB)
class AccountAdmin(BaseUserAdmin):
    """
    This is the main creation screen for Users/accounts

    """

    list_display = (
        "id",
        "username",
        "is_staff",
        "is_superuser",
        "db_typeclass_path",
        "db_date_created",
    )
    list_display_links = ("id", "username")
    form = AccountChangeForm
    add_form = AccountCreationForm
    search_fields = ["=id", "^username", "db_typeclass_path"]
    ordering = ["-db_date_created", "id"]
    list_filter = ["is_superuser", "is_staff", "db_typeclass_path"]
    inlines = [AccountTagInline, AccountAttributeInline]
    readonly_fields = ["db_date_created", "serialized_string", "puppeted_objects"]
    view_on_site = False
    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("username", "db_typeclass_path"),
                    "password",
                    "email",
                    "db_date_created",
                    "db_lock_storage",
                    "db_cmdset_storage",
                    "puppeted_objects",
                    "serialized_string",
                )
            },
        ),
        (
            "Admin/Website properties",
            {
                "fields": (
                    ("first_name", "last_name"),
                    "last_login",
                    "date_joined",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "user_permissions",
                    "groups",
                ),
                "description": "<i>Used by the website/Django admin. "
                "Except for `superuser status`, the permissions are not used in-game.</i>",
            },
        ),
    )

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

    def serialized_string(self, obj):
        """
        Get the serialized version of the object.

        """
        from evennia.utils import dbserialize

        return str(dbserialize.pack_dbobj(obj))

    serialized_string.help_text = (
        "Copy & paste this string into an Attribute's `value` field to store this account there."
    )

    def puppeted_objects(self, obj):
        """
        Get any currently puppeted objects (read only list)

        """
        return mark_safe(
            ", ".join(
                '<a href="{url}">{name}</a>'.format(
                    url=reverse("admin:objects_objectdb_change", args=[obj.id]), name=obj.db_key
                )
                for obj in ObjectDB.objects.filter(db_account=obj)
            )
        )

    puppeted_objects.help_text = (
        "Objects currently puppeted by this Account. "
        "Link new ones from the `Objects` admin page.<BR>"
        "Note that these will disappear when a user unpuppets or goes offline - "
        "this is normal."
    )

    def get_form(self, request, obj=None, **kwargs):
        """
        Overrides help texts.

        """
        help_texts = kwargs.get("help_texts", {})
        help_texts["serialized_string"] = self.serialized_string.help_text
        help_texts["puppeted_objects"] = self.puppeted_objects.help_text
        kwargs["help_texts"] = help_texts

        # security disabling for non-superusers
        form = super().get_form(request, obj, **kwargs)
        disabled_fields = set()
        if not request.user.is_superuser:
            disabled_fields |= {"is_superuser", "user_permissions", "user_groups"}
        for field_name in disabled_fields:
            if field_name in form.base_fields:
                form.base_fields[field_name].disabled = True
        return form

    @sensitive_post_parameters_m
    def user_change_password(self, request, id, form_url=""):
        user = self.get_object(request, unquote(id))
        if not self.has_change_permission(request, user):
            raise PermissionDenied
        if user is None:
            raise Http404("%(name)s object with primary key %(key)r does not exist.") % {
                "name": self.model._meta.verbose_name,
                "key": escape(id),
            }
        if request.method == "POST":
            form = self.change_password_form(user, request.POST)
            if form.is_valid():
                form.save()
                change_message = self.construct_change_message(request, form, None)
                self.log_change(request, user, change_message)
                msg = "Password changed successfully."
                messages.success(request, msg)
                update_session_auth_hash(request, form.user)
                return HttpResponseRedirect(
                    reverse(
                        "%s:%s_%s_change"
                        % (
                            self.admin_site.name,
                            user._meta.app_label,
                            # the model_name is something we need to hardcode
                            # since our accountdb is a proxy:
                            "accountdb",
                        ),
                        args=(user.pk,),
                    )
                )
        else:
            form = self.change_password_form(user)

        fieldsets = [(None, {"fields": list(form.base_fields)})]
        adminForm = admin.helpers.AdminForm(form, fieldsets, {})

        context = {
            "title": "Change password: %s" % escape(user.get_username()),
            "adminForm": adminForm,
            "form_url": form_url,
            "form": form,
            "is_popup": (IS_POPUP_VAR in request.POST or IS_POPUP_VAR in request.GET),
            "add": True,
            "change": False,
            "has_delete_permission": False,
            "has_change_permission": True,
            "has_absolute_url": False,
            "opts": self.model._meta,
            "original": user,
            "save_as": False,
            "show_save": True,
            **self.admin_site.each_context(request),
        }

        request.current_app = self.admin_site.name

        return TemplateResponse(
            request,
            self.change_user_password_template or "admin/auth/user/change_password.html",
            context,
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
