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

import urllib2
import re
import sys

import config
import timefunc
from db import keyrings
from db import insert_key
from db import count_active_keys
from db import count_unique_keys
from db import remailer_keys

# Fetch stats url from a pinger
def url_fetch(url):
    pubring = urllib2.Request(url)
    failed = 0
    try:
        opener = urllib2.urlopen(pubring)
    except:
        failed = 1
    if failed:
        logger.info("Retrieval of %s failed", url)
        return 0
    else:
        try:
            content = opener.readlines()
            return content
        except:
            return 0

def pubring_process(ping_name, content):
    for line in content:
        is_pubring = pubring_re.match(line)
        if is_pubring:
            rem_name = is_pubring.group(1)
            rem_addy = is_pubring.group(2)
            rem_key = is_pubring.group(3)
            insert_key(ping_name, rem_name, rem_addy, rem_key)

def filenames(name, addy):
    noat = addy.replace('@',".")
    file = '%s/key.%s.%s.txt' % (config.reportdir, name, noat)
    url = 'key.%s.%s.txt' % (name, noat)
    return url, file

def write_remailer_stats(filename, name, addy):
    stats = open(filename, 'w')
    stats.write('Keystats for the %s Remailer (%s).\n\n' % (name, addy))
    for ping_name, key in remailer_keys(name, addy, ago, ahead):
        stats.write('%-20s %s\n' % (ping_name, key))
    stats.close()

def write_stats():
    indexname = "%s/%s" % (config.reportdir, config.keyindex)
    index = open(indexname, 'w')
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
<h1>Remailer Keystats Report</h1>
<p>This report provides stats on remailer keys held by each pinger.
In normal circumstances every pinger should provide a key, but exceptions
may occur if a pinger doesn't return a pubring.mix, or we haven't defined
what the url for the file is on a given pinger.  Unique Keys should be 1,
but during key expiration, some pingers will update before others, so 2 is
not exceptional.  Any more then 2 is plain wrong and demands investigation.</p>
<table border="0" bgcolor="#000000">
<tr bgcolor="#F08080"><th>Remailer</th><th>Address</th><th>Pingers Reporting</th>
<th>Pingers with Keys</th><th>Unique Keys</th></tr>\n''')
    colorflag = False
    for rem_name, rem_addy, count in count_active_keys(ago, ahead):
        url, filename = filenames(rem_name, rem_addy)
        # We need the Try/Except here as a return of None cannot be unpacked.
        # None occurs when no pingers have a valid return.  Eg. Dead remailer.
        try:
            count_keys,distinct_keys = count_unique_keys(rem_name, rem_addy, ago, ahead)
        except TypeError:
            count_keys = 0
            distinct_keys = 0
        write_remailer_stats(filename, rem_name, rem_addy)

        if colorflag: bgcolor = "#ADD8E6"
        else: bgcolor = "#E0FFFF"
        colorflag = not colorflag

        index.write('<tr bgcolor="%s"><th class="tableleft">' % (bgcolor,))
        if distinct_keys > 0:
            index.write('<a href="%s">%s</a>' % (url, rem_name))
        else:
            index.write('%s' % (rem_name,))
        index.write('</th><td>%s</td>' % (rem_addy,))
        index.write('<td>%s</td>' % (count,))
        index.write('<td>%s</td><td>%s</td>' % (count_keys, distinct_keys))
        index.write('</tr>\n')

    index.write('</table>\n</body>\n</html>\n')
    index.close()

def main():
    global pubring_re
    pubring_re = re.compile('([0-9a-z]{1,8})\s+(\S+@\S+)\s+([0-9a-z]+)\s')
    global now, ago, ahead
    now = timefunc.utcnow()
    ago = timefunc.hours_ago(config.active_age)
    ahead = timefunc.hours_ahead(config.active_future)

#    for url in keyrings():
#        ping_name = url[0]
#        pubring = url[1]
#        content = url_fetch(pubring)
#        pubring_process(ping_name, content)
    
    write_stats()


# Call main function.
if (__name__ == "__main__"):
    main()
