"""
Error views.

"""

from django.shortcuts import render


def to_be_implemented(request):
    """
    A notice letting the user know that this particular feature hasn't been
    implemented yet.
    """

    pagevars = {"page_title": "To Be Implemented..."}

    return render(request, "tbi.html", pagevars)
