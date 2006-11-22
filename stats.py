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

import config
import datetime
import psycopg2
import socket
import urllib2
import logging
import re
import sys

import db
from timefunc import utcnow
from timefunc import hours_ago
from timefunc import hours_ahead
from timefunc import arpa_check
#from configobj import ConfigObj
#from validate import Validator

DSN = 'dbname=metastats user=crooks'

# --- Configuration ends here -----

def init_logging():
    """Initialise logging.  This should be the first thing done so that all
    further operations are logged."""
    loglevels = {'debug': logging.DEBUG, 'info': logging.INFO,
                'warn': logging.WARN, 'error': logging.ERROR}
    level = loglevels['debug']
    global logger
    logger = logging.getLogger('stats')
    #TODO Following should be defined in a config file
    hdlr = logging.FileHandler("/home/crooks/metalog")
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(level)

# Fetch stats url from a pinger
def url_fetch(url):
    if url.endswith(".htm") or url.endswith(".html"):
        logger.warn("%s is probably html, not text.  Trying anyway", url)
    else:
        logger.debug("Attempting to retreive %s", url)
    pingurl = urllib2.Request(url)
    failed = 0
    try:
        opener = urllib2.urlopen(pingurl)
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

# Do some string to integer conversion
def numeric(seq):
    seq = seq.strip() # Get rid of spaces
    if numeric_re.match(seq): # Regex to check for digits 0-9
        seq = int(seq)
        return seq
    return 0

# Process each line of a pinger url and write results to database
def url_process(pinger_name,pinger):
    genstamp = 0 # Timestamp extracted from URL
    address_hash = {}  # Key: Remailer Name, Content: Remailer Address
    stats_hash = {} # Key: Remailer Name, Content: Stats line

# The following sections assume the required elements of the stats url are in
# the correct sequence:
# Generated Timestamp, Stats lines, Address lines
# Two hashes are used to store stats and address details, both keyed by
# remailer name.
    for row in pinger:
        if row.startswith('Generated: ') and not genstamp:
            gentime = row.split('ted: ')
            genstamp = arpa_check(gentime[1])
            logger.debug("Found timestamp %s on stats from %s", genstamp, pinger_name)
            continue

        is_stat = stat_re.match(row)
        if is_stat:
            rem_name = is_stat.group(1)
            if stats_hash.has_key(rem_name):
                logger.warn("Pinger %s reports multiple entries for %s", pinger_name, rem_name)
            else:
                stats_hash[rem_name] = is_stat.group(2)
                logger.debug("Processing entry for remailer %s in %s stats", rem_name, pinger_name)
            continue

        is_addy = addy_re.match(row)
        if is_addy:
            rem_name = is_addy.group(1)
            if address_hash.has_key(rem_name):
                logger.warn("The address %s appears to be duplicated in %s stats", address_hash[rem_name], pinger_name)
            else:
                address_hash[rem_name] = is_addy.group(2)
                logger.debug("Found email address of %s for %s in %s stats", address_hash[rem_name], rem_name, pinger_name)

# Now we have populated the stats and address hashes, we need to work through
# each stats entry and extract the components for writing to the database.
    for remailer in stats_hash:
        line = stats_hash[remailer]
        if address_hash.has_key(remailer):
            if len(line) == 59 or len(line) == 60:
                try:
                    lat_hist = line[0:13]
                    lat_hour = numeric(line[14:16]) * 60
                    lat_min = numeric(line[17:20])
                    lat_time = int(lat_hour + lat_min)
                    up_hist = line[22:34]
                    up_dec = numeric(line[36:39]) * 10
                    up_frac = numeric(line[40:41])
                    up_time = int(up_dec + up_frac)
                    options = line[44:59]
                except:
                    logger.warn("Malformed stats line for remailer %s whilst processing pinger %s", remailer, pinger_name)
                    continue

                data = {'url_ping_name':pinger_name,
                        'url_rem_name':remailer,
                        'url_rem_addy':address_hash[remailer],
                        'url_lat_hist':lat_hist,
                        'url_lat_time':lat_time,
                        'url_up_hist':up_hist,
                        'url_up_time':up_time,
                        'url_options':options,
                        'url_timestamp':genstamp}

                logger.debug("Deleting database entries for remailer %s from pinger %s", remailer, pinger_name)
                db.delete(data)  # Delete old matching entries
                logger.debug("Inserting database entries for remailer %s from pinger %s", remailer, pinger_name)
                db.insert(data)  # Insert new entry to replace those deleted
                
            else:
                # The stats line length is wrong, it must be 59 or 60
                logger.warn("Incorrect stats line length (%d) in %s pinger stats for remailer %s.  Should be 59 or 60.", len(line), pinger_name, remailer)
        else:
            # For some reason we appear to have a remailer entry in stats with no matching address
            logger.warn("No address found in %s stats for remailer %s", pinger_name, remailer)

# Convert latent time in minutes to timestamp string (HH:MM)
def latent_timestamp(mins):
    hours = int(mins / 60)
    minutes = int(mins % 60)
    timestamp = '%d:%02d' % (hours, minutes)
    return timestamp

# Convert minutes to hours and minutes.  Return them as two variables.
def hours_mins(mins):
    hours = int(mins / 60)
    minutes = int(mins % 60)
    return hours, minutes

# Make a filename for each remailer_stats file.
def remailer_filename(dir, url ,name, addy):
    noat = addy.replace('@',".")
    filename = '%s/www/%s.%s.txt' % (dir, name, noat)
    urlname = '%s/%s.%s.txt' % (url, name, noat)
    return filename, urlname

# Take a db row and convert to a textual presentation
def db_process(row):
    ping_name = row[0].ljust(24)
    lat_hist = row[3].ljust(14)
    lat_time1 = latent_timestamp(row[4])
    lat_time = lat_time1.ljust(6)
    up_hist = row[5].ljust(14)
    up_time1 = row[6] / 10.0
    up_time2 = "%3.1f%%" % up_time1
    up_time3 = up_time2.rjust(6)
    up_time = up_time3.ljust(7)
    options = row[7].ljust(17)
    timestamp1 = row[8]
    timestamp = timestamp1.strftime("%Y-%m-%d %H:%M")
    line = " " + ping_name + lat_hist + lat_time + up_hist + up_time + options + timestamp + "\n"
    return line

def gen_remailer_vitals(name, addy, age, future):
    vitals = {}
    vitals["rem_name"] = name
    vitals["rem_addy"] = addy
    vitals["max_age"] = age
    vitals["max_future"] = future
    # First we get some stats based on all responding pingers
    vitals["rem_latency_avg_all"], \
    vitals["rem_uptime_avg_all"], \
    vitals["rem_latency_stddev_all"], \
    vitals["rem_uptime_stddev_all"], \
    vitals["rem_count_all"] = db.remailer_avgs_all(vitals)
    # If any of the above stats return None, set them to an arbitrary default.
    if not vitals["rem_latency_avg_all"]:
        vitals["rem_latency_avg_all"] = 5999
    if not vitals["rem_uptime_avg_all"]:
        vitals["rem_uptime_avg_all"] = 0
    if not vitals["rem_latency_stddev_all"]:
        vitals["rem_latency_stddev_all"] = 0
    if not vitals["rem_uptime_stddev_all"]:
        vitals["rem_uptime_stddev_all"] = 0
    # Now we get some stats for active pings using the criteria defined above.
    vitals["rem_latency_min"], \
    vitals["rem_latency_avg"], \
    vitals["rem_latency_max"], \
    vitals["rem_latency_stddev"], \
    vitals["rem_uptime_min"], \
    vitals["rem_uptime_avg"], \
    vitals["rem_uptime_max"], \
    vitals["rem_uptime_stddev"], \
    vitals["rem_active_count"]= db.remailer_stats(vitals)
    # If any of the above stats return None, set them to an arbitrary default.
    if not vitals["rem_latency_min"]:
        vitals["rem_latency_min"] = 0
    if not vitals["rem_latency_avg"]:
        vitals["rem_latency_avg"] = 0
    if not vitals["rem_latency_max"]:
        vitals["rem_latency_max"] = 5999
    if not vitals["rem_latency_stddev"]:
        vitals["rem_latency_stddev"] = 0
    if not vitals["rem_uptime_min"]:
        vitals["rem_uptime_min"] = 0
    if not vitals["rem_uptime_avg"]:
        vitals["rem_uptime_avg"] = 0
    if not vitals["rem_uptime_max"]:
        vitals["rem_uptime_max"] = 0
    if not vitals["rem_uptime_stddev"]:
        vitals["rem_uptime_stddev"] = 0
    return vitals

# Check to see if there are any remailer names in the mlist2 table that don't
# exist in the genealogy table.  If there are any, then write them along with
# the current time.  Entries in genealogy table are excluded if the already
# have a last_seen address.  This accounts for remailers returning with the
# same name and address.
def gene_find_new(age):
    curs.execute("""SELECT rem_name,rem_addy FROM mlist2 WHERE
                    rem_name IS NOT NULL AND
                    rem_addy IS NOT NULL AND
                    timestamp > cast(%s AS timestamp) AND
                    up_hist !~ '^[0?]{12}$' EXCEPT
                    (SELECT rem_name,rem_addy FROM genealogy WHERE
                    last_seen IS NULL)""", (age,))
    new_remailers = curs.fetchall()
    for new_remailer in new_remailers:
        new_data = {'new_remailer_name':new_remailer[0],
                    'new_remailer_addy':new_remailer[1],
                    'new_remailer_time':utcnow()}
        gene_insert_new(new_data)

# This function is called from gene_find_new for each newly discovered
# remailer.
def gene_insert_new(remailer):
    curs.execute("""INSERT INTO genealogy 
                        (rem_name, rem_addy, first_seen)
                    VALUES (
                        %(new_remailer_name)s,
                        %(new_remailer_addy)s,
                        %(new_remailer_time)s)""", remailer)
    conn.commit()

# Check to see if any remailers exist in genealogy but not in mlist2.  If any
# are found, then add a last_seen date to that entry.  Once an entry has a
# last_seen address, it should never be updated again.  Note, date is 672 hours
# ago as remailers in mlist2 are only dead after not being seen for 28 days.
def gene_find_dead(conf):
    curs.execute("""SELECT rem_name,rem_addy FROM genealogy WHERE
                    last_seen IS NULL AND
                    rem_addy IS NOT NULL EXCEPT
                    (SELECT rem_name,rem_addy FROM mlist2 WHERE
                    timestamp >= cast(%(gene_max_age)s AS timestamp) AND
                    up_hist !~ '^[0?]{12}$')""", conf)
    dead_remailers = curs.fetchall()
    for dead_remailer in dead_remailers:
        dead_data = {'dead_remailer_name':dead_remailer[0],
                     'dead_remailer_addy':dead_remailer[1],
                     'dead_remailer_time':conf['gene_max_age']}
        gene_update_dead(dead_data)

# This function is called from gene_find_dead for each dead remailer.  It writes the
# last_seen date to the genealogy database.
def gene_update_dead(remailer):
    curs.execute("""UPDATE genealogy SET 
                        last_seen = %(dead_remailer_time)s
                    WHERE
                        rem_name = %(dead_remailer_name)s AND
                        rem_addy = %(dead_remailer_addy)s""", remailer)
    conn.commit()

def gene_dup_check(dups):
    for dup in dups:
        name, addy, count = dup
        logger.warn("%d genealogy entries for %s %s", count, name, addy)

def gene_write_text(conf):
    filename = '%s/www/%s.txt' % (config.basedir, config.gene_report_name)
    genefile = open(filename,'w')
    line = "Remailer Geneology as of %s (UTC)\n\n" % utcnow()
    genefile.write(line)
    curs.execute("""SELECT * FROM genealogy WHERE
                    rem_addy IS NOT NULL
                    ORDER BY last_seen DESC,rem_name ASC""")
    genealogies = curs.fetchall()

    # Find the longest length of a remailer_addy.  We can use this to
    # format the width of the column in the resulting test file.
    max_length = 20
    for genealogy in genealogies:
        length = len(genealogy[1])
        if length > max_length:
            max_length = length

    for genealogy in genealogies:
        rem_name = genealogy[0].ljust(12)
        rem_addy = genealogy[1].ljust(max_length)
        line = rem_name + rem_addy
        if genealogy[2]:
            first_seen1 = genealogy[2]
            first_seen = first_seen1.strftime("%Y-%m-%d")
            line = line + "  " + first_seen
        if genealogy[3]:
            last_seen1 = genealogy[3]
            last_seen = last_seen1.strftime("%Y-%m-%d")
            line = line + "  " + last_seen
        line = line + '\n'
        genefile.write(line)
    genefile.close()

# This routine will generate a html formated genealogy file.
def gene_write_html(conf, filename):
    logger.debug("Writing Geneology HTML file %s", filename)
    genefile = open(filename,'w')
    # Write standard html header section
    genefile.write('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">\n')
    genefile.write('<html>\n<head>\n')
    genefile.write('<meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">\n')
    genefile.write('<meta http-equiv="Content-Style-Type" content="text/css2" />\n')
    genefile.write('<meta name="keywords" content="Mixmaster,Echolot,Remailer,Banana,Bananasplit">\n')
    genefile.write('<title>Bananasplit Website - Remailer Genealogy</title>\n')
    genefile.write('<link rel="StyleSheet" href="stats.css" type="text/css">\n')
    genefile.write('</head>\n\n<body>\n')
    genefile.write('<h1>Remailer Genealogy</h1>\n')
    genefile.write('<table border="0" bgcolor="#000000">\n')
    genefile.write('<tr bgcolor="#F08080">\n')
    genefile.write('<th>Remailer Name</th><th>Remailer Address</th>')
    genefile.write('<th>First Seen Date</th><th>Died On Date</th>')
    genefile.write('<th>Failed Date</th><th>Comments</th>\n</tr>\n')

    curs.execute("""SELECT rem_name, rem_addy, first_seen,
                    last_seen, last_fail, comments FROM
                    genealogy ORDER BY last_seen DESC,rem_name ASC""")
    genealogies = curs.fetchall()

    rotate_color = 0
    for genealogy in genealogies:

        #Set up some friendly names for fields
        if genealogy[0]: conf["rem_name"] = genealogy[0]
        if genealogy[1]: conf["rem_addy"] = genealogy[1]
        if genealogy[1]: conf["rem_addy_noat"] = genealogy[1].replace('@','.')
        if genealogy[2]: conf["first_seen"] = genealogy[2].strftime("%Y-%m-%d")
        if genealogy[3]: conf["last_seen"] = genealogy[3].strftime("%Y-%m-%d")
        if genealogy[4]: conf["last_fail"] = genealogy[4].strftime("%Y-%m-%d")
        if genealogy[5]: conf["comments"] = genealogy[5]
        
        # Rotate background colours for rows
        if rotate_color:
            conf["bgcolor"] = "#ADD8E6"
        else:
            conf["bgcolor"] = "#E0FFFF"
        rotate_color = not rotate_color

        if conf.has_key("last_seen"):
            genefile.write('<tr bgcolor="%(bgcolor)s"><th class="tableleft">%(rem_name)s</th>\n' % conf)
        else:
            conf["geneurl"] = '%s/%(rem_name)s.%(rem_addy_noat)s.txt' % (config.baseurl, conf)
            genefile.write('<tr bgcolor="%(bgcolor)s"><th class="tableleft"><a href="%(geneurl)s" title="%(rem_addy)s">%(rem_name)s</a></th>\n' % conf)

        # If the remailer address exists, write a table cell for it
        if conf.has_key("rem_addy"):
            genefile.write('<td>%(rem_addy)s</td>' % conf)
            del conf["rem_addy"]
        else:
            genefile.write('<td></td>')

        # If the remailer has a first_seen entry, write a table cell for it
        if conf.has_key("first_seen"):
            genefile.write('<td>%(first_seen)s</td>' % conf)
            del conf["first_seen"]
        else:
            genefile.write('<td></td>')

        # If thre remailer has a lest_seen entry, write a table cell for it
        if conf.has_key("last_seen"):
            genefile.write('<td>%(last_seen)s</td>' % conf)
            del conf["last_seen"]
        else:
            genefile.write('<td></td>')

        # If the remailer has a lest_fail entry, write a table cell for it
        if conf.has_key("last_fail"):
            genefile.write('<td>%(last_fail)s</td>' % conf)
            del conf["last_fail"]
        else:
            genefile.write('<td></td>')

        # If the remailer has a comment, write a table cell for it
        if conf.has_key("comments"):
            genefile.write('<td>%(comments)s</td>' % conf)
            del conf["comments"]
        else:
            genefile.write('<td></td>')

        genefile.write('<tr>\n')
    genefile.write('</table>\n')
    genefile.write('<br>Last update: %s (UTC)<br>\n' % utcnow())
    genefile.write('</body></html>')
    genefile.close()

def write_remailer_stats(vitals):
    # Create a filename for the remailer details, open it and write a title and timestamp.
    statfile = open("%(filename)s" % vitals, 'w')
    statfile.write("Pinger statistics for the %(rem_name)s remailer (%(rem_addy)s)\n" % vitals)
    statfile.write('Last update: %s (UTC)\n' % utcnow())

    statfile.write("\nPingers\n")
    statfile.write(" Known:\t%d\t" % db.count_total_pingers())
    statfile.write("Alive:\t%d\t" % vitals["rem_count_all"])
    statfile.write("Active:\t%d\n" % vitals["rem_active_count"])
    statfile.write("\nUptime\n")
    statfile.write(" Lowest:\t%3.2f%%\t\t" % (vitals["rem_uptime_min"]/10.00))
    statfile.write("Average:\t%3.2f%%\n" % (float(vitals["rem_uptime_avg"])/10.00))
    statfile.write(" Highest:\t%3.2f%%\t\t" % (vitals["rem_uptime_max"]/10.00))
    statfile.write("StdDev:\t%3.2f%%\n" % (float(vitals["rem_uptime_stddev"])/10.00))
    statfile.write("\nLatency\n")
    statfile.write(" Lowest:\t%d:%02d\t\t" % hours_mins(vitals["rem_latency_min"]))
    statfile.write("Average:\t%d:%02d\n" % hours_mins(vitals["rem_latency_avg"]))
    statfile.write(" Highest:\t%d:%02d\t\t" % hours_mins(vitals["rem_latency_max"]))
    statfile.write("StdDev:\t%d:%02d\n" % hours_mins(vitals["rem_latency_stddev"]))

    line = "\nActive Pings\n"
    statfile.write(line)
    for row in db.remailer_active_pings(vitals):
        entry = db_process(row)
        statfile.write(entry)

    line = "\n\nIgnored Pings\n"
    statfile.write(line)
    for row in db.remailer_ignored_pings(vitals):
        entry = db_process(row)
        statfile.write(entry)
 
    line = "\n\nDead Pings\n"
    statfile.write(line)
    for row in db.remailer_inactive_pings(vitals):
        entry = db_process(row)
        statfile.write(entry)

    statfile.close()
 
def index_generate(html, filename):
    """Write an HTML index/summary file.  The bulk of this comes from a list
    created in index_header and index_remailer."""
    index = open(index_path, 'w')
    # Write standard html header section
    index.write('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">\n')
    index.write('<html>\n<head>\n')
    index.write('<meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">\n')
    index.write('<meta http-equiv="Content-Style-Type" content="text/css2" />\n')
    index.write('<meta name="keywords" content="Mixmaster,Echolot,Remailer,Banana,Bananasplit">\n')
    index.write('<title>Bananasplit Website - Meta Statistics</title>\n')
    index.write('<link rel="StyleSheet" href="stats.css" type="text/css">\n')
    index.write('</head>\n\n<body>\n<table border="0" bgcolor="#000000">\n')

    for line in html:
        index.write(line)

    index.write('</table>\n')
    index.write('<br>Last update: %s (UTC)<br>\n' % utcnow())
    index.write('<br><a href="genealogy.html">Remailer Genealogy</a>')
    index.write('<br><a href="failed.html">Failing Remailers</a>')
    index.write('<br><a href="blocks.html">Newsgroups Blacklist<a>')
    # Write closing tags and close file
    index.write('</body></html>')
    index.close()

def index_header(pingers):
    """Create the header column for the HTML index file"""
    body = ""
    head = '<tr bgcolor="#F08080"><th></th>\n'
    for pinger in pingers:
        result = '<th><a href="%s">%s</a></th>\n' % (pinger[1], pinger[0])
        body = body + result
    summary = '<th>Average</th><th>StdDev</th><th>Count</th></tr>\n'
    text = head + body + summary
    return text

def index_remailers(vitals, rotate_color, ping_names):
    """Create an HTML line for a given remailer.  This gets used in the stats
    index file."""
        # Rotate background colours for rows
    if rotate_color:
        vitals["bgcolor"] = "#ADD8E6"
    else:
        vitals["bgcolor"] = "#E0FFFF"
    rotate_color = not rotate_color

    # Write the remailer name and local URL for it
    head = '<tr bgcolor="%(bgcolor)s"><th class="tableleft"> \
<a href="%(urlname)s" title="%(rem_addy)s"> \
%(rem_name)s</a></th>\n' % vitals

    uptimes = db.remailer_index_pings(vitals)
    body = ""
    # Start of loop to fill row with uptime stats
    for pinger in ping_names:
        ping_name = pinger[0]
        title = "Remailer: %s Pinger: %s" % (vitals["rem_name"], ping_name)
        if ping_name in uptimes:
            result = '<td align="center" title="%s">%3.1f</td>\n' % (title, uptimes[ping_name])
        else:
            result = '<td title="%s"></td>\n' % title
        body = body + result

    # Write an average uptime to the end of each remailer row
    vitals["rem_uptime_avg_all_div10"] = vitals["rem_uptime_avg_all"] / 10
    vitals["rem_uptime_stddev_all_div10"] = vitals["rem_uptime_stddev_all"] / 10
    summary = '<td>%(rem_uptime_avg_all_div10)3.2f</td> \
<td>%(rem_uptime_stddev_all_div10)3.2f</td> \
<td>%(rem_count_all)d</td></tr>\n' % vitals
    text = head + body + summary
    return text

# ----- Start of main routine -----
init_logging() # Before anything else, initialise logging.
logger.info("Beginning process cycle at %s (UTC)", utcnow())
#TODO Get database calls out of this file!
conn = psycopg2.connect(DSN)
curs = conn.cursor()
socket.setdefaulttimeout(config.timeout)
stat_re = re.compile('([0-9a-z]{1,8})\s+([0-9A-H?]{12}\s.*)')
addy_re = re.compile('\$remailer\{\"([0-9a-z]{1,8})\"\}\s\=\s\"\<(.*)\>\s')
numeric_re = re.compile('[0-9]{1,5}')
index_path = '%s/www/%s' % (config.basedir, config.index_file)
gene_html_file = '%s/www/%s.html' % (config.basedir, config.gene_report_name)
age = hours_ago(config.active_age)
future = hours_ahead(config.active_future)
#config["gene_max_age"] = hours_ago(config.gene_age_days * 24)

# Are we running in testmode (without --live)
testmode = 1
if len(sys.argv) > 1:
    if sys.argv[1].startswith('--'):
        option = sys.argv[1] [2:]
        if option == 'live':
                testmode = 0
                logger.debug("Running with 'live' flag set, url's will be retreived")
                
ping_names = db.pinger_names()
# If not in testmode, fetch url's and process them
if not testmode:                
    for row in ping_names:
        url = url_fetch(row[1])
        if url:
            url_process(row[0], url)
else:
    logger.debug("Running in testmode, url's will not be retreived")


gene_find_new(age)
#TODO: Delete the following lines if all seems to be working well.
#TODO: Delete obsolete functions in accordance with above.
# Remarked out gene_find_dead as I think housekeeping should now
# perform this task.  This also negates the need for gene_age_check.
#gene_find_dead(config)
#db.gene_age_check()
gene_write_text(config)
#gene_write_html(config, gene_html_file)
#This function will delete any remailer entries that are over a defined
#age, (672 hours).
db.housekeeping(hours_ago(672))  # 672Hrs = 28Days
gene_dup_check(db.gene_dup_count())

rem_names = db.distinct_rem_names()
ping_names = db.active_pinger_names()
index_html = []
index_html.append(index_header(ping_names))
rotate_color = 0
for rem_list in rem_names:
    name = rem_list[0]
    addy = rem_list[1]
    logger.debug("Generating statsistics for remailer %s", name)
    remailer_vitals = gen_remailer_vitals(name, addy, age, future)
    # We need to append a filename to vitals in order to generate the file
    # within a function.
    remailer_vitals["filename"], \
    remailer_vitals["urlname"] = remailer_filename(config.basedir, config.baseurl, name, addy)
    logger.debug("Writing stats file for %s %s", name, addy)
    write_remailer_stats(remailer_vitals)
    index_html.append(index_remailers(remailer_vitals, rotate_color, ping_names))
    rotate_color = not rotate_color
index_generate(index_html, index_path)
#index.close()
logger.info("Processing cycle completed at %s (UTC)", utcnow())
