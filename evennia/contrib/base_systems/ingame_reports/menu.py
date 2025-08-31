"""
The report-management menu module.
"""

from django.conf import settings
from django.utils.translation import gettext as _

from evennia.comms.models import Msg
from evennia.utils import logger
from evennia.utils.utils import crop, datetime_format, is_iter, iter_to_str

# the number of reports displayed on each page
_REPORTS_PER_PAGE = 10

# the fallback standard tags
_REPORT_STATUS_TAGS = ("in progress", "rejected")
# the tag, used to mark a report as 'closed'
_REPORT_STATUS_CLOSED_TAG = _("closed")

if hasattr(settings, "INGAME_REPORT_STATUS_TAGS"):
    if is_iter(settings.INGAME_REPORT_STATUS_TAGS):
        _REPORT_STATUS_TAGS = settings.INGAME_REPORT_STATUS_TAGS
    else:
        logger.log_warn(
            "The 'INGAME_REPORT_STATUS_TAGS' setting must be an iterable of strings; falling back to defaults."
        )
# add the 'closed' tag to the tupel of tags
if _REPORT_STATUS_CLOSED_TAG not in _REPORT_STATUS_TAGS:
    _REPORT_STATUS_TAGS = _REPORT_STATUS_TAGS + (_REPORT_STATUS_CLOSED_TAG,)


def menunode_list_reports(caller, raw_string, **kwargs):
    """Paginates and lists out reports for the provided hub"""
    hub = caller.ndb._evmenu.hub
    hub_name = hub.key.split("_")[0].title() + " "
    hub_name += _("Reports")
    text = _("Managing {hub_name}").format(hub_name=hub_name)

    if not (report_list := getattr(caller.ndb._evmenu, "report_list", None)):
        report_list = Msg.objects.search_message(receiver=hub).order_by("db_date_created")
        caller.ndb._evmenu.report_list = report_list
    # allow the menu to filter print-outs by status
    status = kwargs.get("status")
    if status:
        new_report_list = report_list.filter(db_tags__db_key=kwargs["status"])
        # we don't filter reports if there are no reports under that filter
        if not new_report_list:
            text = _(
                "(No {status} reports)\n"
                "{text}"
            ).format(status=status, text=text)
        else:
            report_list = new_report_list
            text = _("Managing {status} {hub_name}").format(status=status, hub_name=hub_name)
    else:
        # use the 'closed' tag lowered, to be sure, the translation included no upper case chars
        report_list = report_list.exclude(db_tags__db_key=_REPORT_STATUS_CLOSED_TAG.lower())

    # filter by lock access
    report_list = [msg for msg in report_list if msg.access(caller, "read")]

    # this will catch both no reports filed and no permissions
    if not report_list:
        return _("No open {hub_name} at the moment.").format(hub_name=hub_name), {}

    page = kwargs.get("page", 0)
    start = page * _REPORTS_PER_PAGE
    end = start + _REPORTS_PER_PAGE
    report_slice = report_list[start:end]

    options = [
        {
            "desc": f"{datetime_format(report.date_created)} - {crop(report.message, 50)}",
            "goto": ("menunode_manage_report", {"report": report}),
        }
        for report in report_slice
    ]
    options.append(
        {
            "key": (_("|uF|nilter by status"), "filter", "status", "f"),
            "goto": "menunode_choose_filter",
        }
    )
    if start > 0:
        options.append(
            {
                "key": (
                    _("|uP|nrevious {_REPORTS_PER_PAGE}").format(_REPORTS_PER_PAGE, _REPORTS_PER_PAGE),
                    _("previous"),
                    _("prev"),
                    _("p")
                ),
                "goto": (
                    "menunode_list_reports",
                    {"page": max(start - _REPORTS_PER_PAGE, 0) // _REPORTS_PER_PAGE},
                ),
            }
        )
    if end < len(report_list):
        options.append(
            {
                "key": (
                    _("|uN|next {_REPORTS_PER_PAGE}").format(_REPORTS_PER_PAGE=_REPORTS_PER_PAGE),
                    _("next"),
                    _("n")
                ),
                "goto": (
                    "menunode_list_reports",
                    {"page": (start + _REPORTS_PER_PAGE) // _REPORTS_PER_PAGE},
                ),
            }
        )
    return text, options


def menunode_choose_filter(caller, raw_string, **kwargs):
    """apply or clear a status filter to the main report view"""
    text = _("View which reports?")
    # options for all the possible statuses
    options = [
        {"desc": status, "goto": ("menunode_list_reports", {"status": status})}
        for status in _REPORT_STATUS_TAGS
    ]
    # no filter
    options.append({"desc": _("All open reports"), "goto": "menunode_list_reports"})
    return text, options


def _report_toggle_tag(caller, raw_string, report, tag, **kwargs):
    """goto callable to toggle a status tag on or off"""
    if tag in report.tags.all():
        report.tags.remove(tag)
    else:
        report.tags.add(tag)
    return ("menunode_manage_report", {"report": report})


def menunode_manage_report(caller, raw_string, report, **kwargs):
    """
    Read out the full report text and targets, and allow for changing the report's status.
    """
    receivers = [r for r in report.receivers if r != caller.ndb._evmenu.hub]

    message = report.message
    timestamp = datetime_format(report.date_created)
    senders_str = iter_to_str(report.senders)
    tags_str = iter_to_str(report.tags.all())
    if receivers:
        receivers_str = iter_to_str(r.get_display_name(caller) for r in receivers)
        about_clause = _(" about {receivers}").format(receivers=receivers_str)
    else:
        about_clause = ""

    text = _(
        "{message}\n"
        "{timestamp} by {senders}{about_clause}\n"
        "{tags}"
    ).format(
        message=message,
        timestamp=timestamp,
        senders=senders_str,
        about_clause=about_clause,
        tags=tags_str
    )

    options = []
    for tag in _REPORT_STATUS_TAGS:
        if tag in report.tags.all():
            desc = _("Unmark as {tag}").format(tag=tag)
        else:
            desc = _("Mark as {tag}").format(tag=tag)
        options.append(
            {
                "desc": desc,
                "goto": (_report_toggle_tag, {"report": report, "tag": tag}),
            }
        )
    options.append({"desc": _("Manage another report"), "goto": "menunode_list_reports"})
    return text, options
