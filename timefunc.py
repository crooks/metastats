#!/usr/bin/python
#
# vim: tabstop=4 expandtab shiftwidth=4 autoindent
#
# timefunc.py - Time and date functions for stats generation
#
# Copyright (C) 2005 Steve Crook <steve@mixmin.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

import datetime
from mx import DateTime

def utcnow():
    utctime = datetime.datetime.utcnow()
    utcstamp = utctime.strftime("%Y-%m-%d %H:%M:%S")
    return utcstamp

# Create a timestamp for x hours ago
def hours_ago(past_hours):
    thentime = datetime.datetime.utcnow() - datetime.timedelta(hours=past_hours)
    timestamp = thentime.strftime("%Y-%m-%d %H:%M:%S")
    return timestamp

def hours_ahead(future_hours):
    thentime = datetime.datetime.utcnow() + datetime.timedelta(hours=future_hours)
    timestamp = thentime.strftime("%Y-%m-%d %H:%M:%S")
    return timestamp

# This function will convert minutes into hours and minutes
def hours_mins(mins):
    hours = int(mins / 60)
    minutes = int(mins % 60)
    return hours, minutes

# This function will convert an ARPA format timestamp into a standard one in
# the UTC timezone.
def arpa_check(datestr):
    try:
        generated = DateTime.ARPA.ParseDateTimeUTC(datestr)
    except:
        return 0
    stamp = generated.strftime("%Y-%m-%d %H:%M:%S")
    return stamp
