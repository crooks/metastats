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

from pysqlite2 import dbapi2 as sqlite
import os.path

HOMEDIR = os.path.expanduser('~')
BASEDIR = os.path.join(HOMEDIR, 'metanew')
DBDIR = os.path.join(BASEDIR, 'db')

name = raw_input("Enter Pinger name: ")
mlist2 = raw_input("Enter mlist.txt URL: ")

dbfile = os.path.join(DBDIR, "metastats.db")
con = sqlite.connect(dbfile)
cursor = con.cursor()
cursor.execute("""INSERT INTO pingers
                  (ping_name, mlist2)
                  VALUES ('%s', '%s')""" % (name, mlist2))
con.commit()
