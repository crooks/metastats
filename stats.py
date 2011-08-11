#!/usr/bin/python
#
# vim: tabstop=4 expandtab shiftwidth=4 autoindent
#
# Copyright (C) 2011 Steve Crook <steve@mixmin.net>
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

# Note: Debian package python-egenix-mxdatetime is required.

from urllib2 import Request, urlopen, URLError
from mx import DateTime
import time
import re
from calendar import timegm

def geturl(url):
    user_agent =  'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
    headers = { 'User-Agent' : user_agent }
    req = Request(url, None, headers)
    try:
        f = urlopen(req)

        # Try and obtain the Content-Type of the URL
        info = f.info()
        if 'Content-Type' in info:
            ct = info['Content-Type']
        else:
            ct = None
    except URLError, e:
        if hasattr(e, 'reason'):
            logmes = "Could not fetch %s. Got: %s" % (url, e.reason)
            return 201, logmes, None
        elif hasattr(e, 'code'):
            logmes = "Could not fetch %s: %d error" % (url, e.code)
            return 201, logmes, None
    return 001, f.read(), ct

def arpa2utc(datestr):
    """Convert an ARPA formatted Date string to a standard UTC struct_time."""
    # Process the ARPA timestamp into an object
    ts = DateTime.ARPA.ParseDateTimeUTC(datestr)
    return ts.strftime("%Y-%m-%d %H:%M:%S")

def utc2epoch(datestr):
    """Convert a UTC struct_time to an Epoch."""
    # Make the string into a tuple
    tstup = time.strptime(datestr, '%Y-%m-%d %H:%M:%S')
    # Return the epoch of tstup (in UTC)
    return int(timegm(tstup))

def epoch2utc(epoch):
    """Convert an Epoch to a UTC struct_time."""
    tstup = time.gmtime(epoch)
    return time.strftime("%Y-%m-%d %H:%M:%S", tstup)

def time2int(timestr):
    """Convert a timestamp of 01:11 to 71 and return an integer."""
    elements = timestr.split(":", 1)
    # Cater for :11 meaning 0:11
    if not elements[0]:
        elements[0] = 0
    h = int(elements[0])
    m = int(elements[1])
    return h * 60 + m

def main():
    g1 = "(\S+)\s+"
    g2 = "([0-9A-H?]{12})\s+"
    g3 = "([0-9:]+)\s+"
    g4 = "(\S{12})\s+"
    g5 = "([0-9]{1,3}\.[0-9])%\s{2}"
    g6 = "([ D].{14})$"
    stat_re = re.compile(g1 + g2 + g3 + g4 + g5 + g6)
    valid_versions = [2]
    url = "http://pinger.banana.mixmin.net/mlist2.txt"
    rc, content, type = geturl(url)
    lines = content.split("\n")
    for line in lines:
        ll = line.lower()
        if ll.startswith("stats-version:"):
            version = float(ll.split(": ")[1])
            if version not in valid_versions:
                # Take some kind of action at this point
                print "Invalid Version"
            continue
        if ll.startswith("generated:"):
            generated = line.split(": ")[1]
            epoch = utc2epoch(arpa2utc(generated))
            continue
        stat_hit = stat_re.match(line)
        if stat_hit:
            print stat_hit.group(1)
            print stat_hit.group(2)
            print time2int(stat_hit.group(3))
            print stat_hit.group(4)
            print stat_hit.group(5)
            print stat_hit.group(6)

# Call main function.
if (__name__ == "__main__"):
    main()
