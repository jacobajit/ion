# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.shortcuts import render
from ..announcements.models import Announcement
from ..eighth.models import EighthBlock, EighthSignup, EighthSponsor, EighthScheduledActivity

logger = logging.getLogger(__name__)

def get_visible_announcements(user):
    """ Get a list of visible announcements for a given user (usually request.user).

        These visible announcements will be those that either have no groups assigned
        to them (and are therefore public) or those in which the user is a member.
    """
    announcements = Announcement.objects.order_by("-updated").all()
    user_announcements = []
    user_groups = user.groups.all()
    for announcement in announcements:
        ann_groups = announcement.groups.all()
        add = False
        for grp in ann_groups:
            if grp in user_groups:
                add = True
        if len(ann_groups) == 0:
            add = True

        if add:
            user_announcements.append(announcement)

    logger.debug("All announcements:")
    logger.debug(announcements)
    logger.debug("User announcements:")
    logger.debug(user_announcements)

    return user_announcements


def gen_schedule(user, num_blocks=6):
    """ Generate a list of information about a block and a student's current activity
        signup.
    """
    schedule = []

    block = EighthBlock.objects.get_first_upcoming_block()
    if block is None:
        schedule = None
    else:
        surrounding_blocks = [block] + list(block.next_blocks()[:num_blocks-1])
        signups = EighthSignup.objects.filter(user=user).select_related("scheduled_activity__block", "scheduled_activity__activity")
        block_signup_map = {s.scheduled_activity.block.id: s.scheduled_activity for s in signups}

        for b in surrounding_blocks:
            today = ((date.today() - b.date) == timedelta(0))
            info = {
                "id": b.id,
                "block_letter": b.block_letter,
                "current_signup": getattr(block_signup_map.get(b.id, {}), "activity", None),
                "current_signup_cancelled": getattr(block_signup_map.get(b.id, {}), "cancelled", False),
                "locked": b.locked,
                "date": b.date,
                "flags": ("locked" if b.locked else "open" + (" warning" if today else ""))
            }
            schedule.append(info)
        
    logger.debug(schedule)
    return schedule


def gen_sponsor_schedule(user, num_blocks=6):
    """ Return a list of :class:`EighthScheduledActivity`\s in which the given user
        is sponsoring.
    """

    sponsor = user.get_eighth_sponsor()
    overrid_acts = EighthScheduledActivity.objects.filter(sponsors=sponsor)
    def_acts = EighthScheduledActivity.objects.filter(activity__sponsors=sponsor)
    acts = list(overrid_acts) + list(def_acts)

    return acts[:num_blocks]

@login_required
def dashboard_view(request):
    """Process and show the dashboard."""

    if request.user.has_admin_permission("announcements") and "show_all" in request.GET:
        """ Show all announcements if user has admin permissions and
            the show_all GET argument is given. """
        announcements = Announcement.objects.order_by("-updated").all()
    else:
        """ Only show announcements for groups that the user is enrolled in. """
        announcements = get_visible_announcements(request.user)

    student = request.user.is_student
    eighth_sponsor = request.user.has_eighth_sponsor()

    
    if student:
        schedule = gen_schedule(request.user)
    else: schedule = None

    if eighth_sponsor:
        sponsor_schedule = gen_sponsor_schedule(request.user)
    else: sponsor_schedule = None

    context = {
        "announcements": announcements,
        "schedule": schedule,
        "sponsor_schedule": sponsor_schedule,
        "eighth_sponsor": eighth_sponsor
    }
    return render(request, "dashboard/dashboard.html", context)
