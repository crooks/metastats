#!/usr/bin/python
#
# vim: tabstop=4 expandtab shiftwidth=4 autoindent
#
# timefunc.py - Time and date functions for stats generation
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

import config
from timefunc import utcnow
from db import distinct_rem_names
from db import chain_from_count2
from db import chain_to_count2
from db import active_pinger_names
from db import remailer_active_pings
from db import remailer_index_pings
from db import remailer_index_stats
from db import remailer_index_count

def bg_color(flag):
    """Return alternating background colours depending on the True/False
    nature of the flag passed."""
    if flag:
        bgcolor = "#ADD8E6"
    else:
        bgcolor = "#E0FFFF"
    return bgcolor

def gen_filename(name, addy):
    """Generate filenames and url names for the various hyperlinks."""
    noat = addy.replace('@',".")
    file = '%s/%s.%s.txt' % (config.reportdir, name, noat)
    file_chfr = '%s/chfr.%s.%s.txt' % (config.reportdir, name, noat)
    file_chto = '%s/chto.%s.%s.txt' % (config.reportdir, name, noat)
    url = '%s.%s.txt' % (name, noat)
    return file, file_chfr, file_chto, url

def keycheck(dictionary, key):
    """This function returns 0 if a dictionary doesn't have a valid key.
    Otherwise it returns the value of the key."""
    if dictionary.has_key(key):
        return dictionary[key]
    else:
        return 0

def index():
    """Generate an HTML index table referencing remailer name against pinger
    name.  The content of the table is remailer uptimes."""
    # Generate an index filename and open it.
    filename = "%s/index.html" % config.reportdir
    index = open(filename, 'w')
    # Write the standard HTML headers and the initial BODY parts.
    index.write('''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">
<meta http-equiv="Content-Style-Type" content="text/css2" />
<meta name="keywords" content="Mixmaster,Echolot,Remailer,Banana,Bananasplit">
<title>Bananasplit Website - Meta Statistics</title>
<link rel="StyleSheet" href="stats.css" type="text/css">
</head>
<body>
<table border="0" bgcolor="#000000">\n''')
    # For a pinger to be considered active, it must appear in tables mlist2
    # and pingers.  This basically means, don't create empty pinger columns
    # in the index file.
    active_pingers = active_pinger_names()
    index.write('<tr bgcolor="#F08080"><th></th><th>Chain From</th><th>Chain To</th>\n')
    # Write the pinger names as a header row.
    for pinger in active_pingers:
        index.write('<th><a href="%s">%s</a></th>\n' % (pinger[1], pinger[0]))
    # Add the final header row titles and close the row.
    index.write('<th>Average</th><th>StdDev</th><th>Count</th></tr>\n')
    # Set a flag for rotating backgroup colours
    color_flag = False
    # Define some time related variables
    now = utcnow()
    # Make a dictionary of how many chain from's for each remailer
    chfr_dict = chain_from_count2()
    chto_dict = chain_to_count2()
    for name, addy in distinct_rem_names():
        # We should have a key for every remailer, this is just a safeguard
        fr_count = keycheck(chfr_dict, name)
        to_count = keycheck(chto_dict, name)

        # First lets establish the bacground color for the row being processed
        color = bg_color(color_flag)
        color_flag = not color_flag
        file, chfr, chto, url = gen_filename(name, addy)
        # Generate the HTML for Table Row headers
        index.write('<tr bgcolor="%s"><th class="tableleft">\n' % (color,))
        # Generate the HTML for the Remailer Name column
        index.write('<a href="%s" title="%s">' % (url, addy))
        index.write('%s</a></th>\n' % (name,))
        # Generate the HTML for the Chain From column
        index.write('<td align="center">')
        index.write('<a href="chfr.%s" title="Broken Chains from %s">' % (url, addy))
        index.write('%s</a></td>\n' % (fr_count,))
        # Generate the HTML for the Chain To column
        index.write('<td align="center">')
        index.write('<a href="chto.%s" title="Broken Chains to %s">' % (url, addy))
        index.write('%s</a></td>\n' % (to_count,))
        uptimes = remailer_index_pings(name, addy)
        # Now we need a loop to parse each pinger column within the remailer
        # row
        for pinger in active_pingers:
            ping_name = pinger[0]
            title = "Remailer: %s Pinger: %s" % (name, ping_name)
            index.write('<td align="center" title="%s">' % title)
            if ping_name in uptimes:
                index.write('%3.1f</td>\n' % (uptimes[ping_name],))
            else:
                index.write('</td>\n')
        avg,stddev,count = remailer_index_stats(name, addy)
        # Average and StdDev can return 'None' if remailers have no current
        # data.  We have to catch this in order to present floats to the string
        # formatting line.
        if avg == None: avg = 0
        if stddev == None: stddev = 0
        # Write the average, stddev and count to the end of each index row.
        index.write('<td>%3.2f</td><td>%3.2f</td><td>%d</td>' % (avg, stddev, count))
    index.write('</tr>\n')

    # Add a row to the bottom of the table showing the count of remailer known
    # to each pinger.  We have to write a few empty cells to make things line
    # up because of the chain counts and totals columns.
    pinger_totals = remailer_index_count()
    index.write('<tr bgcolor="#F08080"><th class="tableleft">Count</th><td></td><td></td>\n')
    for pinger in active_pingers:
        ping_name = pinger[0]
        if pinger_totals.has_key(ping_name):
            index.write('<td title="%s">%s</td>\n' % (ping_name, pinger_totals[ping_name]))
        else:
            index.write('<td title="%s">0</td>\n' % (ping_name,))
    index.write('<td></td><td></td><td></td></tr>\n</table>\n')

    index.write('<br>Last update: %s (UTC)<br>\n' % utcnow())
    index.write('<br><a href="%s">Remailer Genealogy</a>' % config.gene_report_name)
    index.write('<br><a href="%s">Failing Remailers</a>' % config.failed_report_name)
    index.write('<br><a href="%s">Uptime Averages</a>' % config.uptime_report_name)
    index.write('<br><a href="%s">Keyring Stats</a>' % config.keyindex)
    # Write closing tags and close file
    index.write('</body></html>')
    index.close()

# Call main function.
if (__name__ == "__main__"):
    index()

