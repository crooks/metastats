#!/usr/bin/python
#
# vim: tabstop=4 expandtab shiftwidth=4 autoindent
#
# stats.py -- Harvest and analyse remailer statistics files
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

import logging
import db

from stats import gen_remailer_vitals

from timefunc import utcnow
from timefunc import hours_ago
from timefunc import hours_ahead

def failed(report_name):
    filename = '/home/crooks/testing/www/%s.html' % report_name
    htmlfile = open(filename,'w')

# Write standard html header section
    htmlfile.write('''
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">
<meta http-equiv="Content-Style-Type" content="text/css2" />
<meta name="keywords" content="Mixmaster,Remailer,Banana,Bananasplit">
<title>Bananasplit Website - Failing Remailers</title>
<link rel="StyleSheet" href="stats.css" type="text/css">
</head>

<body>
<h1>Failing Remailers</h1>
Remailer stats are normally biased away from the current day.  This is because
different latencies would skew results due to outstanding pings.  However, the
current day does provide a rapid insight into remailers that are currently
experiencing problems.<br>
<p>The following table lists remailers that are <u>currently</u> averaging less
than 50% return on pings. Please consider that this could be due to very high
latency rather than actual remailer failure.</p>
<p><i>Note: Bunker is not actually failing.  It's a Middleman remailer with no
current stats which means it cannot random hop pings back to the pinger.</i></P>
<table border="0" bgcolor="#000000">
<tr bgcolor="#F08080">
<th>Remailer Name</th><th>Ping Responses</th>
</tr>''')

    rotate_color = 0

    for name, addy in db.distinct_rem_names():
        remailer_vitals = gen_remailer_vitals(name, addy)
        logger.debug("Checking remailer %s %s", name, addy)
        addy_noat = addy.replace('@',".")
        full_name = "%s.%s" % (name, addy_noat)

        active_pings = db.remailer_active_pings(remailer_vitals)
        if len(active_pings) == 0:
            logger.info("We have no active pings for %s %s", name, addy)
            continue

        remailer_vitals['uptime'] = up_today(active_pings)

        if remailer_vitals['uptime'] < 5:
            logger.info("Remailer %s %s is failed.", name, addy)
            # Rotate background colours for rows
            if rotate_color:
                bgcolor = "#ADD8E6"
            else:
                bgcolor = "#E0FFFF"
            rotate_color = not rotate_color
            
            htmlfile.write('<tr bgcolor="%s"><th class="tableleft"><a href="%s.txt" title="%s">%s</a></th>' % (bgcolor, full_name, addy, name))
            htmlfile.write('<td>%d%%</td></tr>\n' % (remailer_vitals['uptime'] * 10))

        else:
            # Stats are greater than 50%, so delete any entries for this
            # remailer from the failed table.
            logger.debug("%s is healthy, deleting any DB entries it might have", name)

    htmlfile.write('</table>\n')

    htmlfile.write('<br>Last update: %s (UTC)<br>\n' % utcnow())
    htmlfile.write('<br><a href="index.html">Return to Index</a>')

    htmlfile.write('</body></html>')

# For a given remailer name, return the average uptime for today from up_hist.
# In up_hist, a '+' indicates a score of 10.
def up_today(entries):
    total = 0
    for line in entries:
        uptime = line[5]
        uptime_now = uptime[-1]
        if uptime_now == '+':
            score = 10
        elif uptime_now == '?':
            score = 0
        else:
            score = int(uptime_now)
        total += score
    return int(total / len(entries))

def init_logging():
    """Initialise logging.  This should be the first thing done so that all
    further operations are logged."""
    loglevels = {'debug': logging.DEBUG, 'info': logging.INFO,
                'warn': logging.WARN, 'error': logging.ERROR}
    level = loglevels['info']
    global logger
    logger = logging.getLogger('failed')
    hdlr = logging.FileHandler("/home/crooks/failed.log")
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(level)

# ----- Main Routine -----

init_logging()
logger.info("Processing started at %s", utcnow())
# Look for remailers in mlist2 that aren't in contacts. If there are any,
# insert them into contacts.
failed('failed')
logger.info("Processing finished at %s", utcnow())

