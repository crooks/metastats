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
from timefunc import utcnow
from db import gene_get_stats

# This routine will generate a html formated genealogy file.
def genealogy():
    #logger.debug("Writing Geneology HTML file %s", config.gene_report_name)
    filename = "%s/%s" % (config.reportdir, config.gene_report_name)
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
    genefile.write('When pingers report a remailer as below %s0%%, ' % config.deadpoint)
    genefile.write('it is timestamped as Last Seen.  If it recovers to above ')
    genefile.write('%s0%%, the timestamp is removed. ' % config.livepoint)
    down_days = config.dead_after_hours / 24
    genefile.write('If the remailer fails to recover after %s days, ' % down_days)
    genefile.write('it is considered dead.  If it returns after this, ')
    genefile.write('it will be considered a new remailer.<br><br>\n')
    genefile.write('<table border="0" bgcolor="#000000">\n')
    genefile.write('<tr bgcolor="#F08080">\n')
    genefile.write('<th>Remailer Name</th><th>Remailer Address</th>')
    genefile.write('<th>First Seen Date</th><th>Died On Date</th>')
    genefile.write('<th>Failed Date</th><th>Comments</th>\n</tr>\n')

    genealogies = gene_get_stats()

    rotate_color = 0
    for genealogy in genealogies:
        #Set up some friendly names for fields
        if genealogy[0]: rem_name = genealogy[0]
        #else: logger.error("Genealogy entry with no remailer name")
        if genealogy[1]:
            rem_addy = genealogy[1]
            rem_addy_noat = genealogy[1].replace('@','.')
        #else: logger.error("Genealogy entry with no remailer address")
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

# Call main function.
if (__name__ == "__main__"):
    genealogy()
