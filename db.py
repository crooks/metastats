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

import config
import psycopg2

DSN = 'dbname=%s user=%s' % (config.dbname, config.dbuser)
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

# Delete entries from mlist2 that match ping_name and rem_name
def delete(stat_line):
    curs.execute("""DELETE FROM mlist2 WHERE 
                        ping_name = %(url_ping_name)s AND
                        rem_name = %(url_rem_name)s AND
                        rem_addy = %(url_rem_addy)s""", stat_line)
    conn.commit()

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

    #In genealogy once a remailer is dead (last_seen timestamped), it should
    # no longer have a last_fail timestamp.
    curs.execute("""UPDATE genealogy SET
                    last_fail=NULL WHERE
                    last_seen IS NOT NULL AND
                    last_fail IS NOT NULL""")

# Count the total number of pingers.  This is extracted from the mlist2 table
# in order to exclude dead pingers.
def count_total_pingers():
    curs.execute("SELECT count(distinct ping_name) FROM mlist2")
    total = curs.fetchone()
    return total[0]

# Count pingers that are conisdered active for a given remailer.  Active in
# this context means they have shown a ping for that remailer within a
# defined period of time.

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

def remailer_index_pings(name, addy, ago, ahead):
    curs.execute("""SELECT ping_name,up_time/10.0 FROM mlist2
                    WHERE rem_name = %s AND
                    rem_addy = %s AND
                    timestamp >= cast(%s AS timestamp) AND
                    timestamp <= cast(%s AS timestamp)""", (name, addy, ago, ahead))
    return dict(curs.fetchall())

def remailer_index_count(ago, ahead):
    curs.execute("""SELECT ping_name,count(rem_name) FROM mlist2 WHERE
                    timestamp >= cast(%s AS timestamp) AND
                    timestamp <= cast(%s AS timestamp)
                    GROUP BY ping_name""", (ago, ahead))
    return dict(curs.fetchall())

def remailer_index_stats(name, addy, ago, ahead):
    curs.execute("""SELECT avg(up_time)/10.0, stddev(up_time)/10.0, count(up_time)
                    FROM mlist2 WHERE rem_name = %s AND
                    rem_addy = %s AND
                    timestamp >= cast(%s AS timestamp) AND
                    timestamp <= cast(%s AS timestamp) AND
                    up_time > 0""",
                    (name, addy, ago, ahead))
    return curs.fetchone()

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

# Get a list of all genealogy details for report production.
def gene_get_stats():
    curs.execute("""SELECT rem_name, rem_addy, first_seen,
                    last_seen, last_fail, comments FROM
                    genealogy WHERE
                    rem_name IS NOT NULL AND
                    rem_addy IS NOT NULL
                    ORDER BY last_seen DESC,rem_name ASC""")
    return curs.fetchall()

# Check to see if there are any remailer names in the mlist2 table that don't
# exist in the genealogy table.  If there are any, then write them along with
# the current time.  Entries in genealogy table are excluded if the already
# have a last_seen address.  This accounts for remailers returning with the
# same name and address.
def gene_find_new(age, now):
    curs.execute("""SELECT rem_name,rem_addy FROM mlist2 WHERE
                    rem_name IS NOT NULL AND
                    rem_addy IS NOT NULL AND
                    timestamp > cast(%s AS timestamp) AND
                    up_hist !~ '^[0?]{12}$' EXCEPT
                    (SELECT rem_name,rem_addy FROM genealogy WHERE
                    last_seen IS NULL)""", (age,))
    new_remailers = curs.fetchall()
    #TODO Non database functionality shouldn't be in here
    for new_remailer in new_remailers:
        new_data = {'new_remailer_name':new_remailer[0],
                    'new_remailer_addy':new_remailer[1],
                    'new_remailer_time':now}
        #TODO Remove internall call to another function
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

# First delete any entries from the chainstat2 table where the data matches
# the new entry.  In theory there can be zero or one entry.  After deleting,
# reinsert the new entry with an up to date timestamp.
def chainstat_update(chain):
    curs.execute("""DELETE FROM chainstat2 WHERE
                    ping_name = %(pinger)s AND
                    chain_from = %(from)s AND
                    chain_to = %(to)s""", chain)
    curs.execute("""INSERT INTO chainstat2
                        (ping_name, last_seen, chain_from, chain_to)
                    VALUES (
                        %(pinger)s,
                        %(stamp)s,
                        %(from)s,
                        %(to)s)""", chain)
    conn.commit()

# Count how many broken From chain entries there are for a given remailer
def chain_from_count(conf):
    curs.execute("""SELECT count(chain_from) FROM chainstat2 WHERE
                    chain_from = %(rem_name)s AND
                    last_seen >= cast(%(max_age)s AS timestamp) AND
                    last_seen <= cast(%(max_future)s AS timestamp)""", conf)
    return curs.fetchone()[0]

def chain_from_count2(ago, ahead):
    curs.execute("""SELECT chain_from,count(chain_from) FROM chainstat2 WHERE
                    last_seen >= cast(%s AS timestamp) AND
                    last_seen <= cast(%s AS timestamp) GROUP BY
                    chain_from""", (ago, ahead))
    return dict(curs.fetchall())

# Count how many broken To chain entries there are for a given remailer
def chain_to_count(conf):
    curs.execute("""SELECT count(chain_to) FROM chainstat2 WHERE
                    chain_to = %(rem_name)s AND
                    last_seen >= cast(%(max_age)s AS timestamp) AND
                    last_seen <= cast(%(max_future)s AS timestamp)""", conf)
    return curs.fetchone()[0]

def chain_to_count2(ago, ahead):
    curs.execute("""SELECT chain_to,count(chain_to) FROM chainstat2 WHERE
                    last_seen >= cast(%s AS timestamp) AND
                    last_seen <= cast(%s AS timestamp) GROUP BY
                    chain_to""", (ago, ahead))
    return dict(curs.fetchall())

# Return broken Fom chains for a given remailer
def chain_from(name, ago, ahead):
    curs.execute("""SELECT ping_name,chain_from,chain_to,last_seen
                    FROM chainstat2 WHERE
                    chain_from = %s AND
                    last_seen >= cast(%s AS timestamp) AND
                    last_seen <= cast(%s AS timestamp)
                    ORDER BY chain_to, ping_name""", (name, ago, ahead))
    return curs.fetchall()

# Return broken Fom chains for a given remailer
def chain_to(name, ago, ahead):
    curs.execute("""SELECT ping_name,chain_from,chain_to,last_seen
                    FROM chainstat2 WHERE
                    chain_to = %s AND
                    last_seen >= cast(%s AS timestamp) AND
                    last_seen <= cast(%s AS timestamp)
                    ORDER BY chain_from, ping_name""", (name, ago, ahead))
    return curs.fetchall()

def avg_uptime(ago, ahead):
    curs.execute("""SELECT rem_name,avg(up_time)/10,avg(lat_time),
                    count(ping_name) FROM mlist2 WHERE
                    timestamp >= cast(%s AS timestamp) AND
                    timestamp <= cast(%s AS timestamp)
                    GROUP BY rem_name
                    ORDER BY avg(up_time) DESC""", (ago, ahead))
    return curs.fetchall()

def keyrings():
    curs.execute("""SELECT ping_name,pubring FROM pingers WHERE
                    pubring IS NOT NULL""")
    return curs.fetchall()

def insert_key(ping_name, rem_name, rem_addy, rem_key, rem_version):
    conf = {'ping_name' : ping_name,
            'rem_name' : rem_name,
            'rem_addy' : rem_addy,
            'rem_key' : rem_key,
            'rem_version' : rem_version }
    curs.execute("""UPDATE mlist2 SET
                    key = %(rem_key)s,
                    version = %(rem_version)s
                    WHERE rem_name = %(rem_name)s AND
                    rem_addy = %(rem_addy)s AND
                    ping_name = %(ping_name)s""", conf)
    conn.commit()

def count_active_keys(ago, ahead):
    """Count how many times each remailer name occurs in mlist2.
    This gives us a count of how many pingers return a result for
    each remailer.  We use this routine to check keys, so we're
    only interested in results where keys are not null."""
    curs.execute("""SELECT rem_name,rem_addy,count(rem_name)
                    FROM mlist2 WHERE
                    timestamp > cast(%s AS timestamp) AND
                    timestamp < cast(%s AS timestamp)
                    GROUP BY rem_name,rem_addy
                    ORDER BY rem_name,rem_addy""", (ago, ahead))
    return curs.fetchall()
   

def count_unique_keys(name, addy, ago, ahead):
    """Like count_active_keys, except this routine counts how many unique
    keys there are for each remailer name.  In a perfect would, this routine
    would return 1 for each remailer.  This would indicate that all pingers
    were reporting the same key."""
    curs.execute("""SELECT count(key),count(distinct key)
                    FROM mlist2 WHERE
                    rem_name=%s AND
                    rem_addy=%s AND
                    timestamp > cast(%s AS timestamp) AND
                    timestamp < cast(%s AS timestamp) AND
                    key IS NOT NULL
                    GROUP BY rem_name,rem_addy""", (name, addy, ago, ahead))
    return curs.fetchone()

def remailer_keys(name, addy, ago, ahead):
    """Return all the ping_names and keys reported for a single remailer."""
    curs.execute("""SELECT ping_name,key,version FROM mlist2 WHERE
                    rem_name=%s AND
                    rem_addy=%s AND
                    key IS NOT NULL AND
                    timestamp > cast(%s AS timestamp) AND
                    timestamp < cast(%s AS timestamp)
                    ORDER BY ping_name""", (name, addy, ago, ahead))
    return curs.fetchall()
