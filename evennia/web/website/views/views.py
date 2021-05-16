"""
This file contains the generic, assorted views that don't fall under one of the other applications.
Views are django's way of processing e.g. html templates on the fly.

"""

from collections import OrderedDict

from django.contrib.admin.sites import site
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.db.models.functions import Lower
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, DetailView
from django.views.generic.base import RedirectView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from evennia import SESSION_HANDLER
from evennia.help.models import HelpEntry
from evennia.objects.models import ObjectDB
from evennia.accounts.models import AccountDB
from evennia.utils import class_from_module
from evennia.utils.logger import tail_log_file
from . import forms

from django.utils.text import slugify

#
# Channel views
#


#
# Help views
#


