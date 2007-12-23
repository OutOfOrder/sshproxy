#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2007 David Guerizec <david@guerizec.net>
# Copyright (C) 2007 Wallix: Michal Mazurek <michal.mazurek@wallix.com>
#
# Last modified: 2007 Oct 14, 04:55:00 by david
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA

import logging
from logging import handlers
import sys
from config import get_config


logger = logging.getLogger("sshproxyd")

formatter = logging.Formatter("%(name)s[%(process)s] %(message)s")
syslog_h = logging.handlers.SysLogHandler("/dev/log")
syslog_h.setFormatter(formatter)
logger.addHandler(syslog_h)

self = sys.modules[__name__]
for key in dir(logger):
    setattr(self, key, getattr(logger, key))

dev = devdebug = self.debug

# exception is special in that is needs to dump the stack frame
# override the default one to have nicer stack dumps
def exception(*args):
    import traceback
    if len(args):
        error('[exc] ' + (str(args[0]) % args[1:]))
    for line in traceback.format_exception(*sys.exc_info()):
        for line_part in line.strip().split('\n'):
            error('[exc] ' + line_part)



#setting loglevel:

cfg = get_config("sshproxy")

loglevel = cfg.get("loglevel", "debug").upper()

if hasattr(logging, loglevel):
    logger.setLevel(getattr(logging, loglevel))
    

