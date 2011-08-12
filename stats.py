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
from pysqlite2 import dbapi2 as sqlite
import time
import re
import os.path
import sys
from calendar import timegm

HOMEDIR = os.path.expanduser('~')
BASEDIR = os.path.join(HOMEDIR, 'metanew')

class Database():
    def __init__(self):
        dbdir = os.path.join(BASEDIR, 'db')
        if not os.path.isdir(dbdir):
            print "%s: Directory does not exist. Aborting." % dbdir
            sys.exit(1)
        dbfile = os.path.join(dbdir, "metastats.db")
        con = sqlite.connect(dbfile)
        self.con = con
        cursor = con.cursor()
        self.cursor = cursor
        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        if not tables or not "mlist2" in tables:
            # Create the mlist2 table
            cursor.execute("""CREATE TABLE mlist2 (
                ping_name TEXT,
                rem_name TEXT,
                rem_addy TEXT,
                lat_hist TEXT,
                lat_time INTEGER,
                up_hist TEXT,
                up_time INTEGER,
                options TEXT,
                generated INTEGER)""")
            con.commit()
        if not tables or not "pingers" in tables:
            # Create the pingers table
            cursor.execute("""CREATE TABLE pingers (
                ping_name TEXT,
                type2 TEXT,
                mlist2 TEXT,
                rlist2 TEXT,
                pubring TEXT
                )""");
            con.commit()
            # Insert a row into pingers, otherwise nothing can work
            cursor.execute("""INSERT INTO pingers
                (ping_name, type2, mlist2, rlist2, pubring)
                VALUES (
                'banana',
                'http://pinger.banana.mixmin.net/type2.list',
                'http://pinger.banana.mixmin.net/mlist2.txt',
                'http://pinger.banana.mixmin.net/rlist2.txt',
                'http://pinger.banana.mixmin.net/pubring.mix'
                )""");
            cursor.execute("""INSERT INTO pingers
                (ping_name, type2, mlist2, rlist2, pubring)
                VALUES (
                'mixmin',
                'http://pinger.mixmin.net/type2.list',
                'http://pinger.mixmin.net/mlist2.txt',
                'http://pinger.mixmin.net/rlist2.txt',
                'http://pinger.mixmin.net/pubring.mix'
                )""");
            con.commit()

    def pingers_mlist2(self):
        self.cursor.execute("""SELECT ping_name, mlist2 FROM pingers
                               WHERE mlist2 IS NOT NULL
                               ORDER BY ping_name""")
        return self.cursor.fetchall()

    def delete_mlist2_by_pinger(self, pinger):
        self.cursor.execute("""DELETE FROM mlist2
                               WHERE ping_name='%s'""" % pinger)
        self.con.commit()

    def insert_mlist2(self, mlist2):
        self.cursor.execute("""INSERT INTO mlist2
            (ping_name, rem_name, rem_addy, lat_hist, lat_time, up_hist,
             up_time, options, generated)
             VALUES (
             '%(ping_name)s',
             '%(rem_name)s',
             '%(rem_addy)s',
             '%(lat_hist)s',
             '%(lat_time)s',
             '%(up_hist)s',
             '%(up_time)s',
             '%(options)s',
             '%(generated)s'
             )""" % mlist2)
        self.con.commit()

    def mlist2_by_remailer(self, rem_name):
        self.cursor.execute("""SELECT ping_name, lat_hist, lat_time, up_hist,
                                      up_time, options, generated
                               FROM mlist2
                               WHERE rem_name='%s'
                               ORDER BY ping_name""" % rem_name)
        return self.cursor.fetchall()

class Pingers():
    def __init__(self):
        g1 = "(\S+)\s+"                     # Remailer Name
        g2 = "([0-9A-H?]{12})\s+"           # Latent History
        g3 = "([0-9:]+)\s+"                 # Latency Time
        g4 = "(\S{12})\s+"                  # Uptime History
        g5 = "([0-9]{1,3}\.[0-9])%\s{2}"    # Uptime
        g6 = "([ D].{14})$"                 # Options
        self.stat_re = re.compile(g1 + g2 + g3 + g4 + g5 + g6)
        self.rem_addy_re = re.compile('\$remailer\{"(\w+)"\} = "<([^>]+)')
        # Stats Versions consideed valid. (Currently v2.0)
        self.valid_versions = [2]


    def geturl(self, url):
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

    def getpings(self):
        pingers = db.pingers_mlist2()
        for pinger in pingers:
            ping_name = pinger[0]
            mlist2 = pinger[1]
            rc, content, type = self.geturl(mlist2)
            lines = content.split("\n")
            # At this point, the assumption is that a URL has been retreived
            # for a pinger. We can therfore delete old entries relating to
            # that pinger.
            db.delete_mlist2_by_pinger(ping_name)
            rem_addy_xref = {}
            for line in lines:
                ll = line.lower()
                if ll.startswith("stats-version:"):
                    version = float(ll.split(": ")[1])
                    if version not in self.valid_versions:
                        # Take some kind of action at this point
                        print "Invalid Version"
                    continue
                if ll.startswith("generated:"):
                    generated = line.split(": ")[1]
                    epoch = utc2epoch(arpa2utc(generated))
                    continue
                rem_addy_hit = self.rem_addy_re.match(line)
                if rem_addy_hit:
                    rem_name = rem_addy_hit.group(1)
                    rem_addy = rem_addy_hit.group(2)
                    rem_addy_xref[rem_name] = rem_addy
            for line in lines:
                stat_hit = self.stat_re.match(line)
                if stat_hit:
                    rem_name = stat_hit.group(1)
                    if rem_name in rem_addy_xref:
                        # To get a single decimal place, uptime is multiplied
                        # by 10 and stored as an integer.
                        uptime = int(float(stat_hit.group(5)) * 10)
                        mlist2 = {
                        "ping_name" :   ping_name,
                        "rem_name"  :   rem_name,
                        "rem_addy"  :   rem_addy_xref[rem_name],
                        "lat_hist"  :   stat_hit.group(2),
                        "lat_time"  :   time2int(stat_hit.group(3)),
                        "up_hist"   :   stat_hit.group(4),
                        "up_time"   :   uptime,
                        "options"   :   stat_hit.group(6),
                        "generated" :   epoch
                        }
                        db.insert_mlist2(mlist2)



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
    url = Pingers()
    url.getpings()
    print db.mlist2_by_remailer('banana')

# Call main function.
if (__name__ == "__main__"):
    db = Database()
    main()
