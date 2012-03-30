#
# This sets up how models are displayed
# in the web admin interface.
#

from django import forms
from django.conf import settings
from django.contrib import admin
from src.objects.models import ObjAttribute, ObjectDB, ObjectNick, Alias
from src.utils.utils import mod_import


class ObjAttributeInline(admin.TabularInline):
    model = ObjAttribute
    fields = ('db_key', 'db_value')
    extra = 0

class NickInline(admin.TabularInline):
    model = ObjectNick
    fields = ('db_nick', 'db_real', 'db_type')
    extra = 0

class AliasInline(admin.TabularInline):
    model = Alias
    fields = ("db_key",)
    extra = 0

class ObjectCreateForm(forms.ModelForm):
    "This form details the look of the fields"
    class Meta:
        model = ObjectDB
    db_key = forms.CharField(label="Name/Key",
                             widget=forms.TextInput(attrs={'size':'78'}),
                             help_text="Main identifier, like 'apple', 'strong guy', 'Elizabeth' etc. If creating a Character, check so the name is unique among characters!",)
    db_typeclass_path = forms.CharField(label="Typeclass",initial="Change to (for example) %s or %s." % (settings.BASE_OBJECT_TYPECLASS, settings.BASE_CHARACTER_TYPECLASS),
                                        widget=forms.TextInput(attrs={'size':'78'}),
                                        help_text="This defines what 'type' of entity this is. This variable holds a Python path to a module with a valid Evennia Typeclass. If you are creating a Character you should use the typeclass defined by settings.BASE_CHARACTER_TYPECLASS or one derived from that.")
    db_permissions = forms.CharField(label="Permissions",
                                     initial=settings.PERMISSION_PLAYER_DEFAULT,
                                     required=False,
                                     widget=forms.TextInput(attrs={'size':'78'}),
                                     help_text="a comma-separated list of text strings checked by certain locks. They are mainly of use for Character objects. Character permissions overload permissions defined on a controlling Player. Most objects normally don't have any permissions defined.")
    db_cmdset_storage = forms.CharField(label="CmdSet",
                                        initial=settings.CMDSET_DEFAULT,
                                        required=False,
                                        widget=forms.TextInput(attrs={'size':'78'}),
                                        help_text="Most non-character objects don't need a cmdset and can leave this field blank.")



class ObjectEditForm(ObjectCreateForm):
    "Form used for editing. Extends the create one with more fields"

    db_lock_storage = forms.CharField(label="Locks",
                                      required=False,
                                      widget=forms.Textarea(attrs={'cols':'100', 'rows':'2'}),
                                      help_text="In-game lock definition string. If not given, defaults will be used. This string should be on the form <i>type:lockfunction(args);type2:lockfunction2(args);...")


class ObjectDBAdmin(admin.ModelAdmin):

    list_display = ('id', 'db_key', 'db_location', 'db_player', 'db_typeclass_path')
    list_display_links = ('id', 'db_key')
    ordering = ['db_player', 'db_typeclass_path', 'id']
    search_fields = ['^db_key', 'db_typeclass_path']

    save_as = True
    save_on_top = True
    list_select_related = True
    list_filter = ('db_permissions', 'db_location', 'db_typeclass_path')

    # editing fields setup

    form = ObjectEditForm
    fieldsets = (
        (None, {
                'fields': (('db_key','db_typeclass_path'), ('db_permissions', 'db_lock_storage'),
                           ('db_location', 'db_home'), 'db_destination','db_cmdset_storage'
                           )}),
        )

    #deactivated temporarily, they cause empty objects to be created in admin
    inlines = [AliasInline]#, ObjAttributeInline]


    # Custom modification to give two different forms wether adding or not.

    add_form = ObjectCreateForm
    add_fieldsets = (
        (None, {
                'fields': (('db_key','db_typeclass_path'), 'db_permissions',
                           ('db_location', 'db_home'), 'db_destination','db_cmdset_storage'
                           )}),
        )
    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super(ObjectDBAdmin, self).get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        """
        Use special form during creation
        """
        defaults = {}
        if obj is None:
            defaults.update({
                    'form': self.add_form,
                    'fields': admin.util.flatten_fieldsets(self.add_fieldsets),
                    })
            defaults.update(kwargs)
        return super(ObjectDBAdmin, self).get_form(request, obj, **defaults)

    def save_model(self, request, obj, form, change):
        if not change:
            # adding a new object
            obj = obj.typeclass
            obj.basetype_setup()
            obj.basetype_posthook_setup()
            obj.at_object_creation()
        obj.at_init()


admin.site.register(ObjectDB, ObjectDBAdmin)
