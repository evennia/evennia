"""
Contains all the validation functions.

All validation functions must have a checker (probably a session) and entry arg.

They can employ more paramters at your leisure.


"""

import datetime as _dt
import re as _re

import pytz as _pytz
from django.utils.translation import gettext as _

from evennia.utils.ansi import strip_ansi
from evennia.utils.utils import string_partial_matching as _partial
from evennia.utils.utils import validate_email_address

_TZ_DICT = {str(tz): _pytz.timezone(tz) for tz in _pytz.common_timezones}


def text(entry, option_key="Text", **kwargs):
    try:
        return str(entry)
    except Exception as err:
        raise ValueError(_("Input could not be converted to text ({err})").format(err=err))


def color(entry, option_key="Color", **kwargs):
    """
    The color should be just a color character, so 'r' if red color is desired.

    """
    if not entry:
        raise ValueError(_("Nothing entered for a {option_key}!").format(option_key=option_key))
    test_str = strip_ansi(f"|{entry}|n")
    if test_str:
        raise ValueError(
            _("'{entry}' is not a valid {option_key}.").format(entry=entry, option_key=option_key)
        )
    return entry


def datetime(entry, option_key="Datetime", account=None, from_tz=None, **kwargs):
    """
    Process a datetime string in standard forms while accounting for the
    inputer's timezone. Always returns a result in UTC.

    Args:
        entry (str): A date string from a user.
        option_key (str): Name to display this datetime as.
        account (AccountDB): The Account performing this lookup. Unless `from_tz` is provided,
            the account's timezone option will be used.
        from_tz (pytz.timezone): An instance of a pytz timezone object from the
            user. If not provided, tries to use the timezone option of `account`.
            If neither one is provided, defaults to UTC.
    Returns:
        datetime in UTC.
    Raises:
        ValueError: If encountering a malformed timezone, date string or other format error.

    """
    if not entry:
        raise ValueError(_("No {option_key} entered!").format(option_key=option_key))
    if not from_tz:
        from_tz = _pytz.UTC
        if account:
            acct_tz = account.options.get("timezone", "UTC")
            try:
                from_tz = _pytz.timezone(acct_tz)
            except Exception as err:
                raise ValueError(
                    _("Timezone string '{acct_tz}' is not a valid timezone ({err})").format(
                        acct_tz=acct_tz, err=err
                    )
                )
        else:
            from_tz = _pytz.UTC

    utc = _pytz.UTC
    now = _dt.datetime.utcnow().replace(tzinfo=utc)
    cur_year = now.strftime("%Y")
    split_time = entry.split(" ")
    if len(split_time) == 3:
        entry = f"{split_time[0]} {split_time[1]} {split_time[2]} {cur_year}"
    elif len(split_time) == 4:
        entry = f"{split_time[0]} {split_time[1]} {split_time[2]} {split_time[3]}"
    else:
        raise ValueError(
            _("{option_key} must be entered in a 24-hour format such as: {timeformat}").format(
                option_key=option_key, timeformat=now.strftime("%b %d %H:%M")
            )
        )
    try:
        local = _dt.datetime.strptime(entry, "%b %d %H:%M %Y")
    except ValueError:
        raise ValueError(
            _("{option_key} must be entered in a 24-hour format such as: {timeformat}").format(
                option_key=option_key, timeformat=now.strftime("%b %d %H:%M")
            )
        )
    local_tz = from_tz.localize(local)
    return local_tz.astimezone(utc)


def duration(entry, option_key="Duration", **kwargs):
    """
    Take a string and derive a datetime timedelta from it.

    Args:
        entry (string): This is a string from user-input. The intended format is, for example:
            "5d 2w 90s" for 'five days, two weeks, and ninety seconds.' Invalid sections are
            ignored.
        option_key (str): Name to display this query as.

    Returns:
        timedelta

    """
    time_string = entry.lower().split(" ")
    seconds = 0
    minutes = 0
    hours = 0
    days = 0
    weeks = 0

    for interval in time_string:
        if _re.match(r"^[\d]+s$", interval):
            seconds += int(interval.rstrip("s"))
        elif _re.match(r"^[\d]+m$", interval):
            minutes += int(interval.rstrip("m"))
        elif _re.match(r"^[\d]+h$", interval):
            hours += int(interval.rstrip("h"))
        elif _re.match(r"^[\d]+d$", interval):
            days += int(interval.rstrip("d"))
        elif _re.match(r"^[\d]+w$", interval):
            weeks += int(interval.rstrip("w"))
        elif _re.match(r"^[\d]+y$", interval):
            days += int(interval.rstrip("y")) * 365
        else:
            raise ValueError(
                _("Could not convert section '{interval}' to a {option_key}.").format(
                    interval=interval, option_key=option_key
                )
            )

    return _dt.timedelta(days, seconds, 0, 0, minutes, hours, weeks)


def future(entry, option_key="Future Datetime", from_tz=None, **kwargs):
    time = datetime(entry, option_key, from_tz=from_tz)
    if time < _dt.datetime.utcnow().replace(tzinfo=_dt.timezone.utc):
        raise ValueError(
            _("That {option_key} is in the past! Must give a Future datetime!").format(
                option_key=option_key
            )
        )
    return time


def signed_integer(entry, option_key="Signed Integer", **kwargs):
    if not entry:
        raise ValueError(
            _("Must enter a whole number for {option_key}!").format(option_key=option_key)
        )
    try:
        num = int(entry)
    except ValueError:
        raise ValueError(
            _("Could not convert '{entry}' to a whole " "number for {option_key}!").format(
                entry=entry, option_key=option_key
            )
        )
    return num


def positive_integer(entry, option_key="Positive Integer", **kwargs):
    num = signed_integer(entry, option_key)
    if not num >= 1:
        raise ValueError(
            _("Must enter a whole number greater than 0 for {option_key}!").format(
                option_key=option_key
            )
        )
    return num


def unsigned_integer(entry, option_key="Unsigned Integer", **kwargs):
    num = signed_integer(entry, option_key)
    if not num >= 0:
        raise ValueError(
            _("{option_key} must be a whole number greater than " "or equal to 0!").format(
                option_key=option_key
            )
        )
    return num


def boolean(entry, option_key="True/False", **kwargs):
    """
    Simplest check in computer logic, right? This will take user input to flick the switch on or off

    Args:
        entry (str): A value such as True, On, Enabled, Disabled, False, 0, or 1.
        option_key (str): What kind of Boolean we are setting. What Option is this for?

    Returns:
        Boolean

    """
    error = _("Must enter a true/false input for {option_key}. Accepts {alternatives}.").format(
        option_key=option_key, alternatives="0/1, True/False, On/Off, Yes/No, Enabled/Disabled"
    )
    if not isinstance(entry, str):
        raise ValueError(error)
    entry = entry.upper()
    if entry in ("1", "TRUE", "ON", "ENABLED", "ENABLE", "YES"):
        return True
    if entry in ("0", "FALSE", "OFF", "DISABLED", "DISABLE", "NO"):
        return False
    raise ValueError(error)


def timezone(entry, option_key="Timezone", **kwargs):
    """
    Takes user input as string, and partial matches a Timezone.

    Args:
        entry (str): The name of the Timezone.
        option_key (str): What this Timezone is used for.

    Returns:
        A PYTZ timezone.

    """
    if not entry:
        raise ValueError(_("No {option_key} entered!").format(option_key=option_key))
    found = _partial(list(_TZ_DICT.keys()), entry, ret_index=False)
    if len(found) > 1:
        raise ValueError(
            _("That matched: {matches}. Please be more specific!").format(
                matches=", ".join(str(t) for t in found)
            )
        )
    if found:
        return _TZ_DICT[found[0]]
    raise ValueError(
        _("Could not find timezone '{entry}' for {option_key}!").format(
            entry=entry, option_key=option_key
        )
    )


def email(entry, option_key="Email Address", **kwargs):
    if not entry:
        raise ValueError(_("Email address field empty!"))
    valid = validate_email_address(entry)
    if not valid:
        raise ValueError(_("That isn't a valid {option_key}!").format(option_key=option_key))
    return entry


def lock(entry, option_key="locks", access_options=None, **kwargs):
    entry = entry.strip()
    if not entry:
        raise ValueError(_("No {option_key} entered to set!").format(option_key=option_key))
    for locksetting in entry.split(";"):
        access_type, lockfunc = locksetting.split(":", 1)
        if not access_type:
            raise ValueError(_("Must enter an access type!"))
        if access_options:
            if access_type not in access_options:
                raise ValueError(
                    _("Access type must be one of: {alternatives}").format(
                        alternatives=", ".join(access_options)
                    )
                )
        if not lockfunc:
            raise ValueError(_("Lock func not entered."))
    return entry
