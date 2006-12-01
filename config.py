#!/usr/bin/python
#
# vim: tabstop=4 expandtab shiftwidth=4 noautoindent
#
# config.py -- This is the config file for metastats
#
# Copyright (C) 2006 Steve Crook <steve@mixmin.org>
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

# Directory where this program resides
basedir = "/home/crooks/testing"

# Base URL for access to stats
baseurl = "http://stats.mixmin.org"

# Fully qualified logfile name
logfile = "/home/crooks/metalog"

# Loglevel, can be debug, info, warn or error
loglevel = "debug"

# Name of the metastats database
dbname = "metastats"

# Name of the database user account
dbuser = "crooks"

# Name of index file
index_file = "index.html"

# The path where the index will be placed
index_path = '%s/www/%s' % (basedir, index_file)

# Number of hours old a timestamp can be and a pinger
# entry still considered active.
active_age = 8

# How many hours ahead of UTC is considered valid.
active_future =  2

# When a remailer uptime drops below this level, flag it as dead.
# Note, this figure is %/10 so 10% = 1.
deadpoint = 1

# When a remailer uptime climbs beyond this level, remove any dead flags.
# As with deadpoint, 10% = 1.
livepoint = 5

# As with above parameters, except this one is the threshold at which a
# remailer is considered failing.  Not dead, just failing.
failpoint = 7

# This is the filename used to create a .txt and .html report file
# for the remailer genealogy section.
gene_report_name = "genealogy.html"

# Path to the genealogy report
gene_path = '%s/www/%s' % (basedir, gene_report_name)

# The filename for the failing remailers report.
failed_report_name = "failed.html"

# The filesystem path to the above report.
failed_path = '%s/www/%s' % (basedir, failed_report_name)

# Socket timeout, used to prevent url retrieval from hanging.
# Value is the number of seconds to wait for a url to respond.
timeout = 30
