"""
The report-management menu module.
"""

from django.conf import settings

from evennia.comms.models import Msg
from evennia.utils import logger
from evennia.utils.utils import crop, datetime_format, is_iter, iter_to_str

# the number of reports displayed on each page
_REPORTS_PER_PAGE = 10

_REPORT_STATUS_TAGS = ("closed", "in progress")
if hasattr(settings, "INGAME_REPORT_STATUS_TAGS"):
    if is_iter(settings.INGAME_REPORT_STATUS_TAGS):
        _REPORT_STATUS_TAGS = settings.INGAME_REPORT_STATUS_TAGS
    else:
        logger.log_warn(
            "The 'INGAME_REPORT_STATUS_TAGS' setting must be an iterable of strings; falling back to defaults."
        )


def menunode_list_reports(caller, raw_string, **kwargs):
    """Paginates and lists out reports for the provided hub"""
    hub = caller.ndb._evmenu.hub
    hub_name = " ".join(hub.key.split("_")).title()
    text = f"Managing {hub_name}"

    if not (report_list := getattr(caller.ndb._evmenu, "report_list", None)):
        report_list = Msg.objects.search_message(receiver=hub).order_by("db_date_created")
        caller.ndb._evmenu.report_list = report_list
    # allow the menu to filter print-outs by status
    if kwargs.get("status"):
        new_report_list = report_list.filter(db_tags__db_key=kwargs["status"])
        # we don't filter reports if there are no reports under that filter
        if not new_report_list:
            text = f"(No {kwargs['status']} reports)\n{text}"
        else:
            report_list = new_report_list
            text = f"Managing {kwargs['status']} {hub_name}"
    else:
        report_list = report_list.exclude(db_tags__db_key="closed")

    # filter by lock access
    report_list = [msg for msg in report_list if msg.access(caller, "read")]

    # this will catch both no reports filed and no permissions
    if not report_list:
        return "There is nothing there for you to manage.", {}

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
            "key": ("|uF|nilter by status", "filter", "status", "f"),
            "goto": "menunode_choose_filter",
        }
    )
    if start > 0:
        options.append(
            {
                "key": (f"|uP|nrevious {_REPORTS_PER_PAGE}", "previous", "prev", "p"),
                "goto": (
                    "menunode_list_reports",
                    {"page": max(start - _REPORTS_PER_PAGE, 0) // _REPORTS_PER_PAGE},
                ),
            }
        )
    if end < len(report_list):
        options.append(
            {
                "key": (f"|uN|next {_REPORTS_PER_PAGE}", "next", "n"),
                "goto": (
                    "menunode_list_reports",
                    {"page": (start + _REPORTS_PER_PAGE) // _REPORTS_PER_PAGE},
                ),
            }
        )
    return text, options


def menunode_choose_filter(caller, raw_string, **kwargs):
    """apply or clear a status filter to the main report view"""
    text = "View which reports?"
    # options for all the possible statuses
    options = [
        {"desc": status, "goto": ("menunode_list_reports", {"status": status})}
        for status in _REPORT_STATUS_TAGS
    ]
    # no filter
    options.append({"desc": "All open reports", "goto": "menunode_list_reports"})
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
    text = f"""\
{report.message}
{datetime_format(report.date_created)} by {iter_to_str(report.senders)}{' about '+iter_to_str(r.get_display_name(caller) for r in receivers) if receivers else ''}
{iter_to_str(report.tags.all())}"""

    options = []
    for tag in _REPORT_STATUS_TAGS:
        options.append(
            {
                "desc": f"{'Unmark' if tag in report.tags.all() else 'Mark' } as {tag}",
                "goto": (_report_toggle_tag, {"report": report, "tag": tag}),
            }
        )
    options.append({"desc": f"Manage another report", "goto": "menunode_list_reports"})
    return text, options
