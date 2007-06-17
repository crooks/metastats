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
import timefunc
import re

from db import distinct_rem_names
from db import chain_from
from db import chain_to

# Write text files for the remailer chain reports.
def write_remailer_chain_stats(name, addy, ago, ahead):
    noat = addy.replace('@',".")
    file_chfr = '%s/chfr.%s.%s.txt' % (config.reportdir, name, noat)
    file_chto = '%s/chto.%s.%s.txt' % (config.reportdir, name, noat)
    # Open the two files for the From and To broken chain files.
    chain_fr_file = open("%s" % (file_chfr,), 'w')
    chain_to_file = open("%s" % (file_chto,), 'w')

    # Write some headers for the two chainstat reports.
    chain_fr_file.write("Broken chain statistics from the %s remailer (%s)\n" % (name, addy))
    chain_to_file.write("Broken chain statistics to the %s remailer (%s)\n" % (name, addy))
    chain_fr_file.write('Last update: %s (UTC)\n\n' % timefunc.utcnow())
    chain_to_file.write('Last update: %s (UTC)\n\n' % timefunc.utcnow())

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

    for row in chain_from(name, ago, ahead):
        chain_fr_file.write(chainstat_row_process(row))

    for row in chain_to(name, ago, ahead):
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


# ----- Start of main routine -----
def chainstats():
    global chain_re
    chain_re = re.compile('\((\w{1,12})\s(\w{1,12})\)')

    ago = timefunc.hours_ago(config.active_age)
    ahead = timefunc.hours_ahead(config.active_future)

    for name, addy in distinct_rem_names():
        write_remailer_chain_stats(name, addy, ago, ahead)

# Call main function.
if (__name__ == "__main__"):
    chainstats()
