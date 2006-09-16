#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Sep 17, 01:37:29 by david
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


import os, os.path, sys, logging, logging.handlers
#from paramiko.util import get_thread_id

__all__ = [ 'debug', 'info', 'warning', 'error', 'critical', 'exception' ]

from logging.config import fileConfig

from config import get_config, inipath

cfg = get_config('sshproxy')
if os.path.exists(cfg['logger_conf']):
    logfile = cfg['logger_conf']
else:
    logfile = os.path.join(inipath, 'logger.conf')

if not os.path.exists(logfile):
    raise 'Log configuration file %s does not exist' % logfile

if cfg['log_dir'][0] != '/':
    log_dir = os.path.join(inipath, cfg['log_dir'])
else:
    log_dir = cfg['log_dir']

try:
    os.chdir(log_dir)
except OSError, msg:
    print "No such directory: creating '%s'" % log_dir
    try:
        os.makedirs(log_dir)
    except OSError, msg:
        print "Could not create directory '%s'" % log_dir
        if not os.environ.get('SSHPROXY_WIZARD', None):
            sys.exit(1)

fileConfig(logfile)

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
