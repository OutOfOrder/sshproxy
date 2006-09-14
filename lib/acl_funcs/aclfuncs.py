#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Sep 14, 01:58:13 by david
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

import os

from sshproxy import get_class
from sshproxy import aclparser
from sshproxy import log

base = get_class('ACLRuleParser')

class ACLRuleParser(base):

    def func_len(self, *args):
        if len(args) != 1:
            log.warning("Warning: function len takes exactly 1 argument.")
            return
        return len(args[0])

    def func_substr(self, *args):
        if len(args) != 3:
            log.warning("Warning: function substr takes exactly 3 arguments.")
            return
        start = args[0]
        end = args[1]
        var = args[2]
        return var[start:end]

    def func_diskspace(self, *args):
        """
        diskspace("/var") -> 125 (12.5% used)
        """
        if len(args) != 1:
            log.warning("Warning: function diskspace takes exactly 1 argument.")
            return
        mountpoint = args[0]

        fd = os.open(mountpoint, os.O_RDONLY)
        stats = os.fstatvfs(fd)
        os.close(fd)
        size = stats[1] * stats[2]
        free = stats[1] * stats[4]
        diskspace = 1000 * (size - free) / size
        return diskspace

ACLRuleParser.register()

