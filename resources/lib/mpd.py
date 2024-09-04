#!/usr/bin/env python
# encoding: utf-8
#
# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import unicode_literals, absolute_import, division

import xml.dom.minidom as minidom
import datetime
import re

def parse_duration(duration_str):
    # Regular expression to parse ISO 8601 duration format (e.g., PT1H2M3S)
    pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?')
    match = pattern.match(duration_str)
    if not match:
        return 0

    hours, minutes, seconds = match.groups()
    hours = int(hours) if hours else 0
    minutes = int(minutes) if minutes else 0
    seconds = float(seconds) if seconds else 0

    return datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)

def find_unprotected_periods(doc):
    unprotected_periods = []
    protected_periods = []

    periods = doc.getElementsByTagNameNS("urn:mpeg:dash:schema:mpd:2011", "Period")
    for period in periods:
        content_protection = period.getElementsByTagNameNS("urn:mpeg:dash:schema:mpd:2011", "ContentProtection")
        if not content_protection:
            unprotected_periods.append(period)
        else:
            protected_periods.append(period)

    return unprotected_periods, protected_periods

def format_start_time(timedelta_obj):
    total_seconds = timedelta_obj.total_seconds()
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    # Format seconds to 6 decimal places
    return "PT{}M{:.6f}S".format(minutes, seconds)

def set_period_start_times(periods):
    current_time = datetime.timedelta()
    for period in periods:
        start_time = format_start_time(current_time)
        period.setAttribute("start", start_time)

        duration_str = period.getAttribute("duration")
        if duration_str:
            duration = parse_duration(duration_str)
            current_time += duration
        else:
            # If no duration is provided, assume a default duration (e.g., 0 seconds)
            duration = datetime.timedelta(seconds=0)
            current_time += duration

def move_unprotected_periods(content):
    doc = minidom.parseString(content)

    # Find unprotected and protected periods
    unprotected_periods, protected_periods = find_unprotected_periods(doc)

    if not unprotected_periods:
         return content

    # Remove all periods
    mpd = doc.getElementsByTagNameNS("urn:mpeg:dash:schema:mpd:2011", "MPD")[0]
    periods = doc.getElementsByTagNameNS("urn:mpeg:dash:schema:mpd:2011", "Period")
    for period in periods:
        mpd.removeChild(period)

    # Insert unprotected periods at the beginning
    all_periods = unprotected_periods + protected_periods
    for period in all_periods:
        mpd.appendChild(period)

    # Set the start times for all periods
    set_period_start_times(all_periods)

    return doc.toprettyxml()

def get_content_start(content):
    doc = minidom.parseString(content)
    periods = doc.getElementsByTagNameNS("urn:mpeg:dash:schema:mpd:2011", "Period")

    for period in periods:
        content_protection = period.getElementsByTagNameNS("urn:mpeg:dash:schema:mpd:2011", "ContentProtection")
        if content_protection:
            start = period.getAttribute("start")
            if start:
                return parse_duration(start).total_seconds()

    return 0
