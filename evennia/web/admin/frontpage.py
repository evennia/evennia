"""
Admin views.

"""

from django.contrib.admin.sites import site
from evennia.accounts.models import AccountDB
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required


@staff_member_required
def evennia_admin(request):
    """
    Helpful Evennia-specific admin page.

    """
    return render(request, "admin/frontpage.html", {"accountdb": AccountDB})


def admin_wrapper(request):
    """
    Wrapper that allows us to properly use the base Django admin site, if needed.

    """
    return staff_member_required(site.index)(request)
