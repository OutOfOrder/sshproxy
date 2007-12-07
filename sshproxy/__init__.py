#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Dec 07, 20:55:21 by david
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


__author__ = "David Guerizec"
__author_email__ = "david@guerizec.net"
__date__ = "2007-12-07"
__version_info__ = (0, 6, 0, "alpha0")
__version__ = '-'.join(['.'.join([ str(v) for v in __version_info__[:3]])]
                        + list(__version_info__[3:]))
__license__ = "GNU General Public License (GPL) v2"
__url__ = "http://sshproxy-project.org/"

import sys
import i18n

if sys.version_info < (2, 4):
    raise RuntimeError('You need python >=2.4 for this module.')

import paramiko

if paramiko.__version_info__ < (1, 6, 3):
    raise RuntimeError('You need paramiko >=1.6.2 for this module.')

# patch paramiko logging
import paramiko.util
class _Logger(object):
    import logging as l
    levels = {
            l.DEBUG:    'debug',
            l.INFO:     'info',
            l.WARNING:  'warning',
            l.ERROR:    'error',
            l.CRITICAL: 'critical',
            }

    def log(self, level, msg, *args):
        try:
            import log
            getattr(log, self.levels[level])(msg, *args)
        except:
            import traceback
            f = open('/var/log/sshproxy/sshproxy.log', 'a')
            f.write("args: %s %s %s\n" % (level, msg, args))
            if len(args):
                f.write('[exc] ' + (msg % args) + '\n')
            else:
                f.write('[exc] ' + (msg) + '\n')
            for line in traceback.format_exception(*sys.exc_info()):
                for line_part in line.strip().split('\n'):
                    f.write('[exc] ' + line_part + '\n')
            f.close()
            raise
        pass
def get_logger(*args):
    return _Logger()
paramiko.util.get_logger = get_logger


from registry import get_class
