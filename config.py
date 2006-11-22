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

# This entry is the default added to the Path header.  If the message
# doesn't contain a Message-ID, this entry is used for the right side
# of that too.

# Directory where this program resides
basedir = "/home/crooks/testing"

# Base URL for access to stats
baseurl = "http://stats.mixmin.org"

# Name of index file
index_file = "index.html"

# Number of hours old a timestamp can be and a pinger
# entry still considered active.
active_age = 8

# How many hours ahead of UTC is considered valid.
active_future =  2

# This is the filename used to create a .txt and .html report file
# for the remailer genealogy section.
gene_report_name = "genealogy"

# Socket timeout, used to prevent url retrieval from hanging.
# Value is the number of seconds to wait for a url to respond.
timeout = 30
