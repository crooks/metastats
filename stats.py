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

import datetime
import socket
import urllib2
import logging
import re
import sys

import config
import db
from timefunc import utcnow
from timefunc import hours_ago
from timefunc import hours_ahead
from timefunc import arpa_check

# --- Configuration ends here -----

def init_logging():
    """Initialise logging.  This should be the first thing done so that all
    further operations are logged."""
    loglevels = {'debug': logging.DEBUG, 'info': logging.INFO,
                'warn': logging.WARN, 'error': logging.ERROR}
    level = loglevels[config.loglevel]
    global logger
    logger = logging.getLogger('stats')
    hdlr = logging.FileHandler(config.logfile)
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
    chainstat = False # Flag to indicate if we are in the Type2 Chainstats
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

        # Lets gather some information about chain stats.  If a stats line
        # starts with 'Broken type-II' we'll assume the info we require follows
        # immediately after and continues until we hit a line that does match
        # a chainstat format.  We must find a timestamp to log against each
        # stat.  Without this, it's future validity cannot be proven.
        if row.startswith('Broken type-II') and genstamp:
            chainstat = True
            logger.debug("Found header for Broken Type-II chains from pinger %s", pinger_name)
            continue
        # Once chain2 flag is True, we assume each line that looks like a chain
        # stat entry is a valid chain stat entry.
        if chainstat:
            is_chain = chain_re.match(row)
            if is_chain:
                chain = { 'from': is_chain.group(1),
                          'to': is_chain.group(2),
                          'stamp': genstamp,
                          'pinger': pinger_name }
                db.chainstat_update(chain)
                logger.debug("Processing broken chain from %(from)s to %(to)s", chain)
            else:
                # When we find a line that isn't a chainstat, reset the chain2
                # flag to indicate we are no longer interested in lines that
                # match the regex.
                chainstat = False
                logger.debug("Finished processing Broken Type-II chains for %s", pinger_name)
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
def remailer_filename(name, addy, type):
    noat = addy.replace('@',".")
    filename = '%s/%s/%s.%s.txt' % (config.reportdir, type, name, noat)
    filename_chfr = '%s/%s/chfr.%s.%s.txt' % (config.reportdir, type, name, noat)
    filename_chto = '%s/%s/chto.%s.%s.txt' % (config.reportdir, type, name, noat)
    urlname = '%s.%s.txt' % (name, noat)
    return filename, filename_chfr, filename_chto, urlname

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

# For a given remailer name, return the average uptime for today from up_hist.
# In up_hist, a '+' indicates a score of 10.
def up_today(entries):
    total = 0.0
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
    return total / len(entries)

def fail_recover(name, addy, active_pings):
    if len(active_pings) == 0:
        logger.info("We have no active pingers for %s", name)
        db.mark_failed(name, addy, utcnow())
    else:
        uptime = up_today(active_pings)
        # If a remailers uptime is < 20%, then we mark it as failed and
        # record the time of failure in the genealogy table.  This has to
        # be a low percentage or bunker would be considered dead.
        if uptime < config.deadpoint:
            logger.debug("%s is under %d%%, flagging it failed", name, config.deadpoint * 10)
            db.mark_failed(name, addy, utcnow())
        # Stats are greater than 50%, so delete any entries for this
        # remailer from the failed table.
        if uptime > config.livepoint:
            logger.debug("%s is healthy, deleting any failed flags it might have", name)
            db.mark_recovered(name, addy)

# Are we running in testmode (without --live)
def live_or_test(mode):
    if len(mode) > 1:
        if mode[1].startswith('--'):
            option = mode[1] [2:]
            if option == 'live':
                logger.debug("Running with 'live' flag set, url's will be retreived")
                return False
    logger.debug("Running in test mode, urls will not be retreived")
    return True

def gen_remailer_vitals(name, addy):
    vitals = {}
    vitals["rem_name"] = name
    vitals["rem_addy"] = addy
    vitals["max_age"] = hours_ago(config.active_age)
    vitals["max_future"] = hours_ahead(config.active_future)
    vitals["chain_from"] = db.chain_from_count(vitals)
    vitals["chain_to"] = db.chain_to_count(vitals)
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

# This routine will generate a html formated genealogy file.
def gene_write_html(type):
    logger.debug("Writing Geneology HTML file %s", config.gene_report_name)
    filename = "%s/%s/%s" % (config.reportdir, type, config.gene_report_name)
    genefile = open(filename, 'w')
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

    genealogies = db.gene_get_stats()

    rotate_color = 0
    for genealogy in genealogies:
        #Set up some friendly names for fields
        if genealogy[0]: rem_name = genealogy[0]
        else: logger.error("Genealogy entry with no remailer name")
        if genealogy[1]:
            rem_addy = genealogy[1]
            rem_addy_noat = genealogy[1].replace('@','.')
        else: logger.error("Genealogy entry with no remailer address")
        if genealogy[2]: first_seen = genealogy[2].strftime("%Y-%m-%d")
        else: first_seen = False
        if genealogy[3]: last_seen = genealogy[3].strftime("%Y-%m-%d")
        else: last_seen = False
        if genealogy[4]: last_fail = genealogy[4].strftime("%Y-%m-%d")
        else: last_fail = False
        if genealogy[5]: comments = genealogy[5]
        else: comments = ""
        
        # Rotate background colours for rows
        if rotate_color:
            bgcolor = "#ADD8E6"
        else:
            bgcolor = "#E0FFFF"
        rotate_color = not rotate_color

        if last_seen:
            genefile.write('<tr bgcolor="%s">' % bgcolor)
            genefile.write('<th class="tableleft">%s</th>\n' % rem_name)
        else:
            geneurl = '%s.%s.txt' % (rem_name, rem_addy_noat)
            genefile.write('<tr bgcolor="%s"><th class="tableleft">' % bgcolor)
            genefile.write('<a href="%s" title="%s">' % (geneurl, rem_addy))
            genefile.write('%s</a></th>\n' % rem_name)

        # If the remailer address exists, write a table cell for it
        if rem_addy:
            genefile.write('<td>%s</td>' % rem_addy)
        else:
            genefile.write('<td></td>')

        # If the remailer has a first_seen entry, write a table cell for it
        if first_seen:
            genefile.write('<td>%s</td>' % first_seen)
        else:
            genefile.write('<td></td>')

        # If thre remailer has a lest_seen entry, write a table cell for it
        if last_seen:
            genefile.write('<td>%s</td>' % last_seen)
        else:
            genefile.write('<td></td>')

        # If the remailer has a lest_fail entry, write a table cell for it
        if last_fail:
            genefile.write('<td>%s</td>' % last_fail)
        else:
            genefile.write('<td></td>')

        # If the remailer has a comment, write a table cell for it
        if comments:
            genefile.write('<td>%s</td>' % comments)
        else:
            genefile.write('<td></td>')
        genefile.write('<tr>\n')
    genefile.write('</table>\n')
    genefile.write('<br>Last update: %s (UTC)<br>\n' % utcnow())
    genefile.write('<br><a href="index.html">Index</a>\n')
    genefile.write('<br><a href="%s">Failing Remailers</a>\n' % config.failed_report_name)
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

# Write text files for the remailer chain reports.
def write_remailer_chain_stats(vitals):
    # Open the two files for the From and To broken chain files.
    chain_fr_file = open("%(filename_chfr)s" % vitals, 'w')
    chain_to_file = open("%(filename_chto)s" % vitals, 'w')

    # Write some headers for the two chainstat reports.
    chain_fr_file.write("Broken chain statistics from the %(rem_name)s remailer (%(rem_addy)s)\n" % vitals)
    chain_to_file.write("Broken chain statistics to the %(rem_name)s remailer (%(rem_addy)s)\n" % vitals)
    chain_fr_file.write('Last update: %s (UTC)\n\n' % utcnow())
    chain_to_file.write('Last update: %s (UTC)\n\n' % utcnow())

    # Insert a header row and underline it.
    headers = "Pinger".ljust(24)
    headers = headers + "Chain From".ljust(16)
    headers = headers + "Chain To".ljust(16)
    headers = headers + "Last Reported\n"
    chain_fr_file.write(headers)
    chain_to_file.write(headers)
    headers = "------".ljust(24)
    headers = headers + "----------".ljust(16)
    headers = headers + "--------".ljust(16)
    headers = headers + "-------------\n"
    chain_fr_file.write(headers)
    chain_to_file.write(headers)

    for row in db.chain_from(vitals):
        chain_fr_file.write(chainstat_row_process(row))

    for row in db.chain_to(vitals):
        chain_to_file.write(chainstat_row_process(row))

    # Close the two chainstat files.
    chain_fr_file.close()
    chain_to_file.close()

def chainstat_row_process(entry):
    ping_name = entry[0].ljust(24)
    chain_from = entry[1].ljust(16)
    chain_to = entry[2].ljust(16)
    stamp1 = entry[3]
    stamp = stamp1.strftime("%Y-%m-%d %H:%M")
    return ping_name + chain_from + chain_to + stamp + "\n"

def index_generate(type, html):
    """Write an HTML index/summary file.  The bulk of this comes from a list
    created in index_header and index_remailer."""
    filename = "%s/%s/index.html" % (config.reportdir, type)
    index = open(filename, 'w')
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
    index.write('<br><a href="%s">Remailer Genealogy</a>' % config.gene_report_name)
    index.write('<br><a href="%s">Failing Remailers</a>' % config.failed_report_name)
    index.write('<br><a href="blocks.html">Newsgroups Blacklist<a>')
    # Write closing tags and close file
    index.write('</body></html>')
    index.close()

def index_header(pingers):
    """Create the header column for the HTML index file"""
    body = ""
    head = '<tr bgcolor="#F08080"><th></th><th>Chain From</th><th>Chain To</th>\n'
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
    chfr = '<td align="center"> \
<a href="chfr.%(urlname)s" title="Broken Chains To %(rem_addy)s"> \
%(chain_from)s</a></td>\n' % vitals
    chto = '<td align="center"> \
<a href="chto.%(urlname)s" title="Broken Chains To %(rem_addy)s"> \
%(chain_to)s</a></td>\n' % vitals

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
    text = head + chfr + chto + body + summary
    return text

# ----- Start of main routine -----
def main():
    init_logging() # Before anything else, initialise logging.
    logger.info("Beginning process cycle at %s (UTC)", utcnow())
    socket.setdefaulttimeout(config.timeout)
    global stat_re
    stat_re = re.compile('([0-9a-z]{1,8})\s+([0-9A-H?]{12}\s.*)')
    global addy_re
    addy_re = re.compile('\$remailer\{\"([0-9a-z]{1,8})\"\}\s\=\s\"\<(.*)\>\s')
    global chain_re
    chain_re = re.compile('\((\w{1,12})\s(\w{1,12})\)')
    global numeric_re
    numeric_re = re.compile('[0-9]{1,5}')

    # Are we running in testmode?  Testmode implies the script was executed
    # without a --live argument.
    testmode = live_or_test(sys.argv)

    # Do we wish to collect type1 or type2 stats?
    #TODO: This will become a loop in the future
    stattype = 'mlist2'

    # If not in testmode, fetch url's and process them
    if not testmode:                
        pingers = db.pinger_names()
        for row in pingers:
            url = url_fetch(row[1])
            if url:
                url_process(row[0], url)
    else:
        logger.debug("Running in testmode, url's will not be retreived")


    # We need to do some periodic housekeeping.  It's not very process
    # intensive so might as well do it every time we run.
    db.housekeeping(hours_ago(config.dead_after_hours))

    # For a pinger to be considered active, it must appear in tables mlist2
    # and pingers.  This basically means, don't create empty pinger columns
    # in the index file.
    active_pingers = db.active_pinger_names()

    # Create an empty list to contain each line of html for the index file.
    # Then populate it with header lines.
    index_html = []
    index_html.append(index_header(active_pingers))

    # A boolean value to rotate row colours within the index 
    rotate_color = 0

    # The main loop.  This creates individual remailer text files and
    # indexing data based on database values.
    for name, addy in db.distinct_rem_names():
        logger.debug("Generating statsistics for remailer %s", name)

        # remailer_vitals is a dictionary of standard deviation and average
        # values for a specific remailer.
        remailer_vitals = gen_remailer_vitals(name, addy)

        # remailer_active_pings: Based on the vitals generated above, we now
        # extract stats lines for pingers considered active.  The up_hist
        # part is used by the fail_recover routine.
        remailer_active_pings = db.remailer_active_pings(remailer_vitals)
        # If a remailers is perceived to be dead, timestamp it in the
        # genealogy table.  Likewise, if it's not dead, unstamp it.
        fail_recover(name, addy, remailer_active_pings)

        # We need to append a filename to vitals in order to generate the file
        # within a function.
        remailer_vitals["filename"], \
        remailer_vitals["filename_chfr"], \
        remailer_vitals["filename_chto"], \
        remailer_vitals["urlname"] = remailer_filename(name, addy, stattype)

        # Write the remailer text file that contains pinger stats and averages
        logger.debug("Writing stats file for %s %s", name, addy)
        write_remailer_stats(remailer_vitals)
        write_remailer_chain_stats(remailer_vitals)

        # Create a single row entry for use in the html index file.
        index_html.append(index_remailers(remailer_vitals, rotate_color, active_pingers))

        # Rotate the colour used in index generation.
        rotate_color = not rotate_color

    index_generate(stattype, index_html)
    db.gene_find_new(hours_ago(config.active_age), utcnow())
    gene_write_html(stattype)
    logger.info("Processing cycle completed at %s (UTC)", utcnow())

# Call main function.
if (__name__ == "__main__"):
    main()
