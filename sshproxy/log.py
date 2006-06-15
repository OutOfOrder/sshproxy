#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: Tue May 30 12:05:55 2006 by david
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


import os, sys, logging, logging.handlers
#from paramiko.util import get_thread_id

__all__ = [ 'debug', 'info', 'warning', 'error', 'critical', 'exception' ]

from logging.config import fileConfig

fileConfig('logger.conf')


class PFilter (logging.Filter):
    def filter(self, record):
#        record._threadid = get_thread_id()
        record._pid = os.getpid()
        return True
_pfilter = PFilter('sshproxy')

def get_logger(name):
    l = logging.getLogger(name)
    l.addFilter(_pfilter)
    return l

# the following for loop does the same thing as the
# following line for all __all__ elements
# info = get_logger('sshproxy').info
self = sys.modules[__name__]
logger = get_logger('sshproxy')
for func in __all__:
    setattr(self, func, getattr(logger, func))

# just to tag logger lines to delete after development/debuging
devdebug = debug
__all__ += [ 'devdebug' ]
