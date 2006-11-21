#!/usr/bin/python
#
# vim: tabstop=4 expandtab shiftwidth=4 autoindent
#
# mail.py -- Some routines for sending emails
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

import os

def sendmail_failing(criteria):
    # We need to multiple uptime by 10 to get percentages correct
    criteria['uptime10'] = criteria['uptime'] * 10
    SENDMAIL = "/usr/sbin/sendmail" # sendmail location
    p = os.popen("%s -t -f nobody@mixmin.net -F RemWatch" % SENDMAIL, "w")
    p.write("""To: %(op_name)s <%(op_addy)s>
Reply-To: Bananasplit Operator <admin@bananasplit.info>
Subject: [RemWatch} %(rem_name)s remailer failure at %(fail_began)s(UTC)

Hi %(op_name)s,

You are receiving this email because your remailer (%(rem_name)s) is
currently returning low results across the majority of pingers.

This email was triggered when your average ping return dropped below
50%%. It's currently averaging %(uptime10)d%%.  You will receive another
email if it drops a futher 10%%.

Best Regards
Bananasplit Operator""" % criteria)
    sts = p.close()
    if sts:
        print "Sendmail exit status", sts

def sendmail_failed(criteria):
    SENDMAIL = "/usr/sbin/sendmail" # sendmail location
    p = os.popen("%s -t -f nobody@mixmin.net -F RemWatch" % SENDMAIL, "w")
    p.write("""To: %(op_name)s <%(op_addy)s>
Reply-To: Bananasplit Operator <admin@bananasplit.info>
Subject: [RemWatch} %(rem_name)s remailer failure at %(fail_began)s(UTC)

Hi %(op_name)s,

You are receiving this email because your remailer (%(rem_name)s) is
currently not responding at all to the majority of pingers.

You will not receive further emails from this automated service unless
your remailer is restored and subsequently fails again.

Best Regards
Bananasplit Operator""" % criteria)
    sts = p.close()
    if sts:
        print "Sendmail exit status", sts

def sendmail_update(criteria):
    criteria['uptime10'] = criteria['uptime'] * 10
    criteria['last_uptime10'] = criteria['last_uptime'] * 10
    SENDMAIL = "/usr/sbin/sendmail" # sendmail location
    p = os.popen("%s -t -f nobody@mixmin.net -F RemWatch" % SENDMAIL, "w")
    p.write("""To: %(op_name)s <%(op_addy)s>
Reply-To: Bananasplit Operator <admin@bananasplit.info>
Subject: [RemWatch} %(rem_name)s remailer failure at %(fail_began)s(UTC)

Hi %(op_name)s,

The situation with your remailer %(rem_name)s appears to have worsened.
Since this report last ran, your ping returns have dropped from %(last_uptime10)d
to %(uptime10)d.

If ping returns reach zero, (indicating a complete remailer failure), you will
receive no further emails through this service.

Best Regards
Bananasplit Operator""" % criteria)
    sts = p.close()
    if sts:
        print "Sendmail exit status", sts

