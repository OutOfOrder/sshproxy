#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Mar 21, 11:16:58 by david
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


import sys
import syslog # syslog is the default

from config import get_config

_levels = {
        'exception': syslog.LOG_EMERG,
        'alert':     syslog.LOG_ALERT,
        'critical':  syslog.LOG_CRIT,
        'error':     syslog.LOG_ERR,
        'warning':   syslog.LOG_WARNING,
        'notice':    syslog.LOG_NOTICE,
        'info':      syslog.LOG_INFO,
        'debug':     syslog.LOG_DEBUG,
        }

__all__ = _levels.keys()



cfg = get_config('sshproxy')
log_level = cfg.get('log_level', ' '.join(_levels.keys()))

syslog.openlog('sshproxyd',
               syslog.LOG_PID|syslog.LOG_CONS|syslog.LOG_NDELAY|syslog.LOG_NOWAIT|syslog.LOG_PERROR,
               syslog.LOG_DAEMON)

def set_log_level(log_level):
    if isinstance(log_level, str):
        mask = 0
        for level in [ _levels[lvl] for lvl in [ 
                            o.strip() for o in log_level.split(',')
                            ] if lvl in _levels ]:
            mask |= level
        log_level = mask
        
    syslog.setlogmask(log_level)

set_log_level(log_level)

def _get_logger_func(name, level):
    def logger_func(msg, *args):
        syslog.syslog(level, ('[%s] ' % name[:3]) + (msg % args))
    return logger_func

self = sys.modules[__name__]
for func_name, level_value in _levels.items():
    setattr(self, func_name, _get_logger_func(func_name, level_value))
    


# just to tag logger lines to delete after development/debuging
devdebug = debug
__all__ += [ 'devdebug' ]
