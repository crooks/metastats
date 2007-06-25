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
from db import keyrings
from db import insert_key

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

def main():
    global pubring_re
    pubring_re = re.compile('([0-9a-z]{1,8})\s+(\S+@\S+)\s+([0-9a-z]+)\s')
    for url in keyrings():
        ping_name = url[0]
        pubring = url[1]
        content = url_fetch(pubring)
        pubring_process(ping_name, content)

# Call main function.
if (__name__ == "__main__"):
    main()
