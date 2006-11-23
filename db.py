#!/usr/bin/python
#
# vim: tabstop=4 expandtab shiftwidth=4 autoindent
#
# db.py - Database functions associated with stats.py
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

import psycopg2

#TODO Use a config file to define db and username
DSN = 'dbname=metastats user=crooks'
try:
    conn = psycopg2.connect(DSN)
except:
    #TODO initialise logging so we don't have printed errors
    print "Failed to connect to database"

curs = conn.cursor()

# Insert a new entry into the mlist2 table
def insert(stat_line):
    curs.execute("""INSERT INTO mlist2 
                        (ping_name, rem_name, rem_addy, lat_hist, lat_time,
                         up_hist, up_time, options, timestamp)
                    VALUES (
                        %(url_ping_name)s,
                        %(url_rem_name)s,
                        %(url_rem_addy)s,
                        %(url_lat_hist)s,
                        %(url_lat_time)s,
                        %(url_up_hist)s,
                        %(url_up_time)s,
                        %(url_options)s,
                        %(url_timestamp)s)""", stat_line)
    conn.commit()

# Update a stats entry where the ping_name and rem_name match
# those being fed to the function.  Note, this function isn't currently
# called.
def update(stat_line):
    curs.execute("""UPDATE mlist2 SET 
                        lat_hist = %(url_lat_hist)s,
                        lat_time = %(url_lat_time)s,
                        up_hist = %(url_up_hist)s,
                        up_time = %(url_up_time)s,
                        options = %(url_options)s,
                        timestamp = %(url_timestamp)s
                    WHERE
                        ping_name = %(url_ping_name)s AND
                        rem_name = %(url_rem_name)s""", stat_line)
    conn.commit()

# Delete entries from mlist2 that match ping_name and rem_name
def delete(stat_line):
    curs.execute("""DELETE FROM mlist2 WHERE 
                        ping_name = %(url_ping_name)s AND
                        rem_name = %(url_rem_name)s AND
                        rem_addy = %(url_rem_addy)s""", stat_line)
    conn.commit()

# Select entries in mlist2 that match ping_name and rem_name.
# This function is not currently called.
def select(stat_line):
    curs.execute("""SELECT * FROM mlist2 WHERE
                        ping_name = %(url_ping_name)s AND
                        rem_name = %(url_rem_name)s""", stat_line)
    return curs.fetchall()

# Called from stats.py to perform various housekeeping tasks.
def housekeeping(age):
    # First delete entries from mlist2 where the timestamp is > age (hours)
    # Age defaults to 28 days but the sky is the limit on this one.
    curs.execute("""DELETE FROM mlist2 WHERE
                        timestamp < cast(%s AS timestamp)""", (age,))
    
    # Now we've deleted old entries from mlist2, this query will delete
    # entries from pingers that don't exist in mlist2.
    # Eg. If there are no entries in mlist2 for a pinger, delete that pinger.
    curs.execute("""DELETE FROM pingers WHERE ping_name NOT IN (
                    SELECT ping_name FROM mlist2)""")

    # Look through the genealogy table for records where last_fail is
    # more than 'age' old.  If it is, consider that remailer dead by
    # setting last_seen to last_fail.
    curs.execute("""UPDATE genealogy SET
                    last_seen=last_fail WHERE
                    last_seen IS NULL AND
                    last_fail < cast(%s AS timestamp)""", (age,))
    conn.commit()

# This is a passive routine that counts duplicate entries in genealogy.
# Duplicates are quite feasible but bad code could make them run wild.
def gene_dup_count():
    curs.execute("""SELECT rem_name,rem_addy,count(*) AS Num FROM genealogy
                    GROUP BY rem_name,rem_addy having ( count(*) > 10)""")
    return curs.fetchall()

# Count the total number of pingers.  This is extracted from the mlist2 table
# in order to exclude dead pingers.
def count_total_pingers():
    curs.execute("SELECT count(distinct ping_name) FROM mlist2")
    total = curs.fetchone()
    return total[0]

# Count pingers that are conisdered active for a given remailer.  Active in
# this context means they have shown a ping for that remailer within a
# defined period of time.
def count_active_pings(conf):
    curs.execute("""SELECT count(*) FROM mlist2 WHERE
                    rem_name = %(rem_name)s AND
                    rem_addy = %(rem_addy)s AND
                    timestamp > cast(%(max_age)s AS timestamp)""", conf)
    ping_count = curs.fetchone()
    return ping_count[0]

# Return a list of remailer names in mlist2.  Just that.
def distinct_rem_names():
    curs.execute("""SELECT DISTINCT rem_name,rem_addy FROM mlist2
                    ORDER BY rem_name""")
    return curs.fetchall()

# Return a list of the pinger entries in table pingers.  The check for
# NULL entries is just to be on the safe side.
def pinger_names():
    curs.execute("""SELECT ping_name, mlist2 FROM pingers
                    WHERE mlist2 IS NOT NULL
                    ORDER BY ping_name""")
    return curs.fetchall()

# Return all the pingers listed in pingers where they also exist in mlist2.
# This accounts for dead pingers that have no entries at all in mlist2.
def active_pinger_names():
    curs.execute("""SELECT ping_name,mlist2 FROM pingers p WHERE EXISTS
                    (SELECT ping_name FROM mlist2 m WHERE
                    m.ping_name = p.ping_name) ORDER BY ping_name""")
    return curs.fetchall()
    
def remailer_avgs_all(conf):
    curs.execute("""SELECT avg(lat_time), avg(up_time), stddev(lat_time),
                    stddev(up_time), count(*) FROM mlist2 WHERE
                    rem_name = %(rem_name)s AND
                    rem_addy = %(rem_addy)s AND
                    timestamp >= cast(%(max_age)s AS timestamp) AND
                    timestamp <= cast(%(max_future)s AS timestamp) AND
                    lat_time < 5999 AND
                    up_time > 0""", conf)
    return curs.fetchone()

# Calculate the average latency for a given remailer.  The figure 5940
# is significant as it results in excluding remailers with a latency of 99.59.
def remailer_average_latency_all(conf):
    curs.execute("""SELECT avg(lat_time) FROM mlist2
                    WHERE rem_name = %(rem_name)s AND
                    rem_addy = %(rem_addy)s AND
                    timestamp >= cast(%(max_age)s AS timestamp) AND
                    lat_time < 5940""", conf)
    average = curs.fetchone()
    if average[0]:
        return average[0]
    else:
        return 0

# Calculate the lowest latency for a given remailer.
def remailer_low_latency(conf):
    curs.execute("""SELECT min(lat_time) FROM mlist2
                    WHERE rem_name = %(rem_name)s AND
                    rem_addy = %(rem_addy)s AND
                    timestamp >= cast(%(max_age)s AS timestamp)""", conf)
    return curs.fetchone()

def remailer_stats(conf):
    curs.execute("""SELECT min(lat_time), avg(lat_time), max(lat_time), stddev(lat_time),
                    min(up_time), avg(up_time), max(up_time), stddev(up_time), count(*) FROM mlist2 WHERE
                    rem_name = %(rem_name)s AND
                    rem_addy = %(rem_addy)s AND
                    timestamp >= cast(%(max_age)s AS timestamp) AND
                    timestamp <= cast(%(max_future)s AS timestamp) AND
                    up_time >= cast(%(rem_uptime_avg_all)s - %(rem_uptime_stddev_all)s AS int) AND
                    up_time <= cast(%(rem_uptime_avg_all)s + %(rem_uptime_stddev_all)s AS int) AND
                    lat_time >= cast(%(rem_latency_avg_all)s - %(rem_latency_stddev_all)s AS int) AND
                    lat_time <= cast(%(rem_latency_avg_all)s + %(rem_latency_stddev_all)s AS int) AND
                    up_hist !~ '^[0?]{12}$' and
                    lat_time < 5999""", conf)
    return curs.fetchone()

# Calculate the average uptime of remailers that fall within defined
# boundaries.  Uptime is stored in the database *10 so that 0.1 accuracy
# can be held in an integer.  This is resolved before returning.  The condition
# is required, just in case no remailers meet the criteria.  This would result in
# average[0] being non-existant.
def remailer_average_uptime(conf):
    curs.execute("""SELECT avg(up_time) FROM mlist2
                    WHERE rem_name = %(rem_name)s AND
                    rem_addy = %(rem_addy)s AND
                    timestamp >= cast(%(max_age)s AS timestamp) AND
                    up_time >= cast(%(rem_uptime_avg_all)s - %(rem_uptime_stddev_all)s AS int) AND
                    up_time <= cast(%(rem_uptime_avg_all)s + %(rem_uptime_stddev_all)s AS int)""",conf)
    average = curs.fetchone()
    if average[0]:
        return average[0] / 10.0
    else:
        return 0

# Calculate the average uptime of a remailer.  Just like the previous function
# but ignoring the upper and lower boundaries.
def remailer_average_uptime_all(conf):
    curs.execute("""SELECT avg(up_time) FROM mlist2
                    WHERE rem_name = %(rem_name)s AND
                    rem_addy = %(rem_addy)s AND
                    timestamp >= cast(%(max_age)s AS timestamp) AND
                    up_time >= cast(%(low_bound)s AS smallint)""", conf)
    average = curs.fetchone()
    if average[0]:
        return average[0]
    else:
        return 0

# Calculate the Standard Deviation of a selected remailer.  Ignore remailer
# that fail to meet the lower boundary.
def remailer_stddev_uptime(conf):
    curs.execute("""SELECT stddev(up_time) FROM mlist2
                    WHERE rem_name = %(rem_name)s AND
                    rem_addy = %(rem_addy)s AND
                    timestamp >= cast(%(max_age)s AS timestamp) AND
                    up_time >= cast(%(low_bound)s AS smallint) AND
                    lat_time < 5940""", conf)
    stddev = curs.fetchone()
    if stddev[0]:
        return stddev[0]
    else:
        return 0

# Calculate the latency Standard Deviation of a selected remailer.
def remailer_stddev_latency(conf):
    curs.execute("""SELECT stddev(lat_time) FROM mlist2
                    WHERE rem_name = %(rem_name)s AND
                    rem_addy = %(rem_addy)s AND
                    timestamp >= cast(%(max_age)s AS timestamp) AND
                    up_time >= cast(%(low_bound)s AS smallint) AND
                    lat_time < 5940""", conf)
    stddev = curs.fetchone()
    if stddev[0]:
        return stddev[0]
    else:
        return 0

# Calculate the average latency of a remailer based on it's Standard Deviation
def remailer_average_latency(conf):
    curs.execute("""SELECT avg(lat_time) FROM mlist2
                    WHERE rem_name = %(rem_name)s AND
                    rem_addy = %(rem_addy)s AND
                    timestamp >= cast(%(max_age)s AS timestamp) AND
                    lat_time >= cast(%(rem_latency_avg_all)s - %(rem_latency_stddev_all)s AS int) AND
                    lat_time <= cast(%(rem_latency_avg_all)s + %(rem_latency_stddev_all)s AS int)""", conf)
    latavg = curs.fetchone()
    if latavg[0]:
        return latavg[0]
    else:
        return 0

def remailer_index_pings(conf):
    curs.execute("""SELECT ping_name,up_time/10.0 FROM mlist2
                    WHERE rem_name = %(rem_name)s AND
                    rem_addy = %(rem_addy)s AND
                    timestamp >= cast(%(max_age)s AS timestamp) AND
                    timestamp <= cast(%(max_future)s AS timestamp)""", conf)
    return dict(curs.fetchall())

# This routine collects all the pings that are considered 'Active'.  Active
# implies they fall between defined boundaries of uptime and also are less
# then a defined number of hours old.
def remailer_active_pings(conf):
    curs.execute("""SELECT * FROM mlist2 WHERE
                    rem_name = %(rem_name)s AND
                    rem_addy = %(rem_addy)s AND
                    timestamp >= cast(%(max_age)s AS timestamp) AND
                    timestamp <= cast(%(max_future)s AS timestamp) AND
                    up_time >= cast(%(rem_uptime_avg_all)s - %(rem_uptime_stddev_all)s AS int) AND
                    up_time <= cast(%(rem_uptime_avg_all)s + %(rem_uptime_stddev_all)s AS int) AND
                    lat_time >= cast(%(rem_latency_avg_all)s - %(rem_latency_stddev_all)s AS int) AND
                    lat_time <= cast(%(rem_latency_avg_all)s + %(rem_latency_stddev_all)s AS int) AND
                    up_hist !~ '^[0?]{12}$' and
                    lat_time < 5999
                    ORDER BY up_time DESC, ping_name ASC""", conf)
    return curs.fetchall()

# Almost identical to remailer_active_pings, but this routine capures the
# pings that fall outside the boundaries of uptime, although must still
# comply with not exceeding a defined age in hours.
def remailer_inactive_pings(conf):
    curs.execute("""SELECT * FROM mlist2 WHERE
                    rem_name = %(rem_name)s AND
                    rem_addy = %(rem_addy)s AND
                    (timestamp > cast(%(max_future)s AS timestamp) OR
                    (timestamp < cast(%(max_age)s AS timestamp)))
                    ORDER BY up_time DESC, ping_name ASC""", conf)
    return curs.fetchall()

# Last in the pinger series, this one doesn't care about uptime boundaries,
# it simply checks to see if pings exceed an acceptable age.  If they do,
# then they are inactive pings.
def remailer_ignored_pings(conf):
    curs.execute("""SELECT * FROM mlist2 WHERE
                    rem_name = %(rem_name)s AND
                    rem_addy = %(rem_addy)s AND
                    timestamp >= cast(%(max_age)s AS timestamp) AND
                    timestamp <= cast(%(max_future)s AS timestamp) AND
                    (up_time < cast(%(rem_uptime_avg_all)s - %(rem_uptime_stddev_all)s AS int) OR
                    up_time > cast(%(rem_uptime_avg_all)s + %(rem_uptime_stddev_all)s AS int) OR
                    lat_time < cast(%(rem_latency_avg_all)s - %(rem_latency_stddev_all)s AS int) OR
                    lat_time > cast(%(rem_latency_avg_all)s + %(rem_latency_stddev_all)s AS int) OR
                    up_hist ~ '^[0?]{12}$' OR
                    lat_time = 5999)
                    ORDER BY up_time DESC, ping_name ASC""", conf)
    return curs.fetchall()

# This routine will attempt to fetch a remailer operator's contact details
# from the rem_name and rem_addy.  If these are defined, the failed remailers
# routine will send them an email if the remailer is failing.
def remailer_getop(name, addy):
    curs.execute("""SELECT op_name, op_addy FROM contacts WHERE
                    rem_name = %s AND
                    rem_addy = %s""", (name, addy))
    return curs.fetchone()

# Called from failed.py, this routine puts a last_fail timestamp in the
# genealogy table providing there isn't already one set and last_seen
# is also unset.  The mark_recovered routine removes the last_fail
# timestamp when a remailer recovers.
def mark_failed(name, addy, time):
    details = { 'rem_name' : name,
                'rem_addy' : addy,
                'fail_time' : time }
    curs.execute("""UPDATE genealogy SET
                    last_fail = cast(%(fail_time)s AS timestamp) WHERE
                    last_seen IS NULL AND
                    last_fail IS NULL AND
                    rem_name = %(rem_name)s AND
                    rem_addy = %(rem_addy)s""", details)
    conn.commit()

# Remove a fail_time timestamp from the genealogy table providing
# last_seen is not set.  This is called from failed.py.
def mark_recovered(name, addy):
    details = { 'rem_name' : name,
                'rem_addy' : addy }
    curs.execute("""UPDATE genealogy SET
                    last_fail = NULL WHERE
                    last_seen IS NULL and
                    rem_name = %(rem_name)s AND
                    rem_addy = %(rem_addy)s""", details)
    conn.commit()
                    
def update_contacts():
    curs.execute("""SELECT DISTINCT rem_name,rem_addy FROM mlist2 EXCEPT
                    (SELECT rem_name,rem_addy FROM contacts)""")
    data = curs.fetchall()
    
    for entry in data:
        print entry
        curs.execute("""INSERT INTO contacts (rem_name,rem_addy)
                        VALUES(%s, %s)""", (entry[0], entry[1]))
        conn.commit()

# For a given remailer name, return the average uptime for today from up_hist.
# In up_hist, a '+' indicates a score of 10.
def up_today(entries):
    count = 0
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
        count += 1
    if count:
        return int(total/count)
    else:
        return 100
