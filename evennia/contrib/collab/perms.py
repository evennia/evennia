from django.core.serializers.json import json
from dateutil.parser import parse
from evennia.contrib.collab import collab_settings
from evennia.objects.objects import DefaultCharacter
from evennia.objects.models import ObjectDB
from evennia.accounts.accounts import DefaultAccount
from evennia.accounts.models import AccountDB
from evennia.utils.utils import inherits_from


class PermissionsError(Exception):
    """
    Used for cases when collaborative permissions checks aren't met.
    """
    pass


def owner_tag_key(owner):
    """
    Used for creating the string value lookup on object attributes to find out
    who created them quickly.
    """
    if inherits_from(owner, DefaultCharacter):
        cls = 'object'
    elif inherits_from(owner, DefaultAccount):
        cls = 'account'
    else:
        raise AssertionError("Owner is not an Object or account.")
    return json.dumps({'id': owner.id,
                       'date': str(owner.db_date_created),
                       'cls': cls}).lower()


def quota_queryset(account, typeclass):
    """
    We use the raw manager here with db_strval for quicker counting.
    """
    return ObjectDB.objects.get_by_tag(
        key=owner_tag_key(account), category='owner').filter(
            db_typeclass_path=typeclass)


def get_limit_for(account, collab_type):
    """
    Given a account and a key for CREATE_TYPES, determine if the account has
    already hit their quota for this object type.
    """
    if not collab_settings.COLLAB_QUOTAS_ENABLED:
        return float('inf')
    if account.locks.check_lockstring(
            account, collab_settings.COLLAB_QUOTA_BYPASS_LOCK):
        return float('inf')
    quota = getattr(account.admdb, 'quota_' + collab_type)
    if quota is not None:
        return quota
    return collab_settings.COLLAB_TYPES[collab_type]['quota']


def quota_check(account, collab_type):
    """
    Check to see if a account has any quota slots free for this collaborative
    type.
    """
    account = getattr(account, 'account', account)
    limit = get_limit_for(account, collab_type)
    if limit == float('inf'):
        return limit
    typeclass = collab_settings.COLLAB_TYPES[collab_type]['typeclass']
    current_object_count = quota_queryset(account, typeclass).count()
    if current_object_count >= limit:
        return 0
    return limit - current_object_count


def set_owner(subject, target):
    """
    Sets the owner for an object. The owner of an object has default
    permissions to perform several actions.

    Also sets a 'display owner', in the case that something is created while a
    character. This allows one to keep some obscurity between their character
    and account if needed.
    """
    account = getattr(subject, 'account', subject)
    target.tags.clear(category='owner')
    target.tags.clear(category='display_owner')
    target.tags.add(owner_tag_key(account), category='owner')
    target.tags.add(owner_tag_key(subject), category='display_owner')


def is_owner(subject, target, check_character=False):
    """
    Checks to see if the subject owns the target. If check_character is True,
    checks the display_owner when the distinction matters.
    """
    # Allow objects to act under the permissions of their owners.
    subject = get_owner(subject)
    if not subject:
        return False
    account = getattr(subject, 'account', subject)
    if subject == target:
        return True
    if account == getattr(target, 'account', None):
        return True
    if check_character:
        return target.tags.get(owner_tag_key(subject),
                               category='display_owner')
    return target.tags.get(owner_tag_key(account), category='owner')


def is_privileged(subject, target):
    """
    Check to see if the account has permissions that would override the normal
    permissions constraints, such as a wizard working with a normal account's
    object.
    """
    return target.locks.check_lockstring(
        subject, collab_settings.COLLAB_OVERRIDE_PERM_LOCK)


def collab_check(subject, target, locks=None, no_superuser_bypass=False):
    """
    Takes a subject, like a character or account, and sees if they should have
    access to a target. If they are the owner, then they do. Otherwise, checks
    all of the locks in a list of lock names, and if any of them or true,
    grants access, denying it otherwise.
    """
    locks = locks or []
    if is_owner(subject, target):
        return True
    if hasattr(target, 'check_protected'):
        protected = target.check_protected()
    else:
        protected = False
    if not protected and (not no_superuser_bypass and is_privileged(subject, target)):
        return True
    for lock in locks:
        if target.access(subject, lock):
            return True
    return False


def parse_owner(owner_tag):
    try:
        owner_info = json.loads(owner_tag)
    except ValueError:
        # Tag is corrupt. Return None.
        return None
    if owner_info['cls'] == 'account':
        cls = AccountDB
    elif owner_info['cls'] == 'object':
        cls = ObjectDB
    else:
        # Nonsense.
        return None
    db_date_created = parse(owner_info['date'])

    try:
        return cls.objects.get(id=owner_info['id'], db_date_created=db_date_created)
    except cls.DoesNotExist:
        return None


def get_owner(obj, account_check=False, display_only=False):
    """
    Grabs the owner tags of an object and displays either the display owner or
    true owner as specified. If both account_check and display_only are false,
    does whatever it can to find a responsible party. If display_only is True,
    only attempts to find who is the display owner of an object.

    If account_check is true, it skips checking for the display owner.

    accounts always own themselves. Character objects own themselves, but may
    have a account authority which owns them directly.
    """
    owner = None
    if inherits_from(obj, DefaultAccount):
        # accounts own themselves.
        return obj
    if not account_check:
        owner = obj.tags.get(category='display_owner')
        if owner:
            owner = parse_owner(owner)
            return owner
    if not owner and inherits_from(obj, DefaultCharacter) and not account_check:
        # Object is a character with no account. It owns itself.
        return obj
    if not owner and not display_only:
        owner = obj.tags.get(category='owner')
        if owner:
            owner = parse_owner(owner)
    return owner


def prefix_check(obj, attr_name, default_type='usr'):
    """
    Attempts to grab a handler from a prefixed attribute. For instance, if the
    attr_name was:

    'admh_test'

    The result would be:

    'test', obj.whattributes

    If the attribute name is something like:

    'test'

    And the object is not a collab typeclass, it would return:

    attr_name, obj.attributes

    ...But if it /is/ a collab typeclass, it will act as if the prefix is
    default_type, and thus parse to:

    'usr_test'

    ...if 'usr' is the default, and result in:

    'test', obj.usrattributes

    To refer to the normal .db attributes, one would use something like:

    '_test'

    And would get back:

    'test', obj.attributes
    """
    old_name = attr_name
    namer = attr_name.split('_', 1)
    if namer[0] in collab_settings.COLLAB_PROPTYPE_PERMS:
        attr_type = namer[0]
        attr_name = namer[1]
    else:
        attr_type = default_type
    try:
        handler = get_handler(obj, attr_type)
    except (AttributeError, TypeError):
        return old_name, obj.attributes
    return attr_name, handler


def get_handler(obj, key):
    if not key:
        return obj.attributes
    return getattr(obj, key + 'attributes')


def attr_check(account, target, access_type, attr_type=None):
    """
    Checks an attribute on a target, and sees if the account has access to
    it.

    attr_type can be either the name of the type or a handler.
    """
    if hasattr(attr_type, '_attrtype'):
        attr_type = attr_type._attrtype
    attr_type = attr_type or ''
    return target.locks.check_lockstring(
        account, collab_settings.COLLAB_PROPTYPE_PERMS[attr_type],
        access_type=access_type)
