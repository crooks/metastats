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

import psycopg
import logging

from db import distinct_rem_names
from db import remailer_active_pings
from db import remailer_getop
from db import update_contacts
from db import mark_failed
from db import mark_recovered

from stats import gen_remailer_vitals

from timefunc import utcnow
from timefunc import hours_ago
from timefunc import hours_ahead

from reports import sendmail_failing
from reports import sendmail_failed
from reports import sendmail_update

def html(report_name):
    filename = '/home/stats/pyprod/www/%s.html' % report_name
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
    max_age = hours_ago(4)
    max_future = hours_ahead(8)

    for name, addy in distinct_rem_names():
        criteria = gen_remailer_vitals(name, addy, max_age, max_future)
        logger.debug("Checking remailer %s %s", name, addy)
        addy_noat = addy.replace('@',".")
        full_name = "%s.%s" % (name, addy_noat)

        active_pings = remailer_active_pings(criteria)
        if len(active_pings) == 0:
            logger.info("We have no active pings for %s %s", name, addy)
            continue

        criteria['uptime'] = up_today(active_pings)

        # If a remailers uptime is < 20%, then we mark it as failed and
        # record the time of failure in the genealogy table.  This has to
        # be a low percentage or bunker would be considered dead.
        if criteria['uptime'] < 2:
            mark_failed(name, addy, utcnow())

        if criteria['uptime'] < 5:
            logger.info("Remailer %s %s is failed.", name, addy)
            # Rotate background colours for rows
            if rotate_color:
                bgcolor = "#ADD8E6"
            else:
                bgcolor = "#E0FFFF"
            rotate_color = not rotate_color
            
            htmlfile.write('<tr bgcolor="%s"><th class="tableleft"><a href="%s.txt" title="%s">%s</a></th>' % (bgcolor, full_name, addy, name))
            htmlfile.write('<td>%d%%</td></tr>\n' % (criteria['uptime'] * 10))

            # Get the operator name and email address from the contacts DB.
            criteria['op_name'], criteria['op_addy'] = remailer_getop(name, addy)
            if criteria['op_name'] and criteria['op_addy']:
                opinfo = True
            else:
                opinfo = False

            # If the remailer has a previous last_uptime, it means it is already
            # treated as failed.  We will not need to insert it into 'failed',
            # it's already there.
            uptime, failed = failed_last_uptime(criteria)
            if uptime and failed:
                criteria['last_uptime'] = uptime
                criteria['fail_began'] = failed
                logger.info("%s was failed during previous run, then %s, now %s", name, criteria['last_uptime'], criteria['uptime'])
                # If the current stats are worse than the last ones, send an email
                if criteria['uptime'] < criteria['last_uptime']:
                    # Has the remailer drooped straight from healthy to zero?
                    if criteria['uptime'] == 0 and opinfo:
                        logger.info("%s has flat stats, sending failed email", name)
                        sendmail_failed(criteria)
                    # The remailer is unhealthy but not totally failed.
                    if criteria['uptime'] != 0 and opinfo:
                        logger.info("%s is dropping in stats, sending update email", name)
                        sendmail_update(criteria)
                # Current remailer uptime is the same as last_uptime
                if criteria['uptime'] == criteria['last_uptime']:
                    logger.info("%s remains unchanged at %d uptime", name, criteria['uptime'])
                # Uptime is now higher than last_uptime.  Things have improved.
                if criteria['uptime'] > criteria['last_uptime']:
                    logger.info("%s has risen in stats but still isn't healthy.", name)
                # Last thing within the "Already Failed" section, update the database
                # by replacing last_uptime with current stats.
                logger.debug("Updating DB for %s with new last_uptime of %d", criteria['uptime'])
                failed_update_uptime(criteria)

            # There is no recorded last_uptime for this remailer.  It's a
            # new failure.  Insert it into the failed table.
            else:
                logger.info("%s has no last_level, it's a new failure.", name)
                failed_insert(criteria)
                if criteria['uptime'] == 0 and opinfo:
                    logger.info("%s has dropped from healthy to flat stats.  Sending failed email.", name)
                    sendmail_failed(criteria)
                if criteria['uptime'] !=0 and opinfo:
                    logger.info("%s is a new failure, sending failing email.", name)
                    sendmail_failing(criteria)

        else:
            # Stats are greater than 50%, so delete any entries for this
            # remailer from the failed table.
            logger.debug("%s is healthy, deleting any DB entries it might have", name)
            failed_delete(criteria)
            mark_recovered(name, addy)

    htmlfile.write('</table>\n')

    htmlfile.write('<br>Last update: %s (UTC)<br>\n' % utcnow())
    htmlfile.write('<br><a href="index.html">Return to Index</a>')

    htmlfile.write('</body></html>')

def failed_last_uptime(criteria):
    curs.execute("""SELECT last_uptime, fail_began FROM failed WHERE
                    rem_name = %(rem_name)s AND
                    rem_addy = %(rem_addy)s""", criteria)
    result = curs.fetchone()
    if result:
        return result[0], result[1]
    else:
        return False, False

def failed_update_uptime(criteria):
    curs.execute("""UPDATE failed SET
                    last_uptime = %(uptime)i WHERE
                    rem_name = %(rem_name)s AND
                    rem_addy = %(rem_addy)s""", criteria)
    conn.commit()

def failed_insert(criteria):
    criteria['fail_began'] = utcnow()
    curs.execute("""INSERT INTO failed
                        (rem_name, rem_addy, last_uptime, fail_began)
                    VALUES (
                        %(rem_name)s,
                        %(rem_addy)s,
                        %(uptime)i,
                        %(fail_began)s)""", criteria)
    conn.commit()

# The following delete routine removes entries from the failed table when a
# remailer returns above 50% return on pings.  If a remailer dies forever, it
# will enter the failed table and then stay there forever.
# TODO: Do I want the behaviour described above?
def failed_delete(criteria):
    curs.execute("""DELETE FROM failed WHERE
                    rem_name = %(rem_name)s AND
                    rem_addy = %(rem_addy)s""", criteria)
    conn.commit()

def get_op_info(name, addy):
    op_info = remailer_getop(name, addy)
    if op_info[0] and op_info[1]:
        logger.debug("We have sufficient operator info to email the %s operator.", name)
        return op_info[0], op_info[1]
    else:
        logger.debug("Insufficient operator info to send email about %s.", name)
        return False, False

# For a given remailer name, return the average uptime for today from up_hist.
# In up_hist, a '+' indicates a score of 10.
def up_today(entries):
    total = 0
    for line in entries:
        uptime = line[4]
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
    hdlr = logging.FileHandler("/home/stats/pyprod/failed.log")
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(level)

# ----- Main Routine -----

DSN = 'dbname=remailers user=stats'

conn = psycopg.connect(DSN)
curs = conn.cursor()

init_logging()
logger.info("Processing started at %s", utcnow())
# Look for remailers in mlist2 that aren't in contacts. If there are any,
# insert them into contacts.
update_contacts()
html('failed')
logger.info("Processing finished at %s", utcnow())

