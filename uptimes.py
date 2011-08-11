#!/usr/bin/python
#
# vim: tabstop=4 expandtab shiftwidth=4 autoindent
#
# stats.py -- Harvest and analyse remailer statistics files
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

import config
import timefunc

from db import avg_uptime

def uptimes():
    ago = timefunc.hours_ago(config.active_age)
    ahead = timefunc.hours_ahead(config.active_future)
    uptimes = avg_uptime()
    #logger.debug("Writing Uptime HTML file %s", config.uptime_report_name)
    filename = "%s/%s" % (config.reportdir, config.uptime_report_name)
    uptimefile = open(filename, 'w')
    uptimefile.write("""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">
<meta http-equiv="Content-Style-Type" content="text/css2" />
<meta name="keywords" content="Mixmaster,Remailer,Banana,Bananasplit">
<title>Bananasplit Website - Failing Remailers</title>
<link rel="StyleSheet" href="stats.css" type="text/css">
</head>

<body>
<h1>Remailer Uptimes</h1>
<p>This report provides an overview of the average uptime for each remailer
based on the results from all currently responding pingers.  Consider that this
report doesn't define a scope for acceptable ping results; all are considered
good.  This means a single pinger can skew the average.</p>
<table border="0" bgcolor="#000000">
<tr bgcolor="#F08080">
<th>Remailer Name</th>
<th>Average Uptime</th>
<th>Average Latency</th>
<th>Pingers Reporting</th></tr>\n""")
    rotate_color = 0
    for uptime in uptimes:
        # Rotate background colours for rows
        if rotate_color:
            bgcolor = "#ADD8E6"
        else:
            bgcolor = "#E0FFFF"
        rotate_color = not rotate_color

        name = uptime[0]
        up = uptime[1]
        count = uptime[3]
        lathrs,latmin = timefunc.hours_mins(uptime[2])
        uptimefile.write('<tr bgcolor="%s">' % bgcolor)
        uptimefile.write('<th class="tableleft">%s</th>' % name)
        uptimefile.write('<td>%3.2f</td>' % up)
        uptimefile.write('<td>%d:%02d</td>' % (lathrs, latmin))
        uptimefile.write('<td>%d</td></tr>\n' % (count, ))

    uptimefile.write('</table>\n')
    uptimefile.write('<br>Last update: %s (UTC)<br>\n' % timefunc.utcnow())
    uptimefile.write('<br><a href="index.html">Index</a>\n')
    uptimefile.write('</body></html>')
    uptimefile.close()

# Call main function.
if (__name__ == "__main__"):
    uptimes()
