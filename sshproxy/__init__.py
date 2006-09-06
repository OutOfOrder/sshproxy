#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Sep 06, 02:05:05 by david
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
__date__ = "$date$"
__version_info__ = (0, 5, 0, "beta2")
__version__ = '-'.join(['.'.join([ str(v) for v in __version_info__[:3]])]
                        + list(__version_info__[3:]))
__license__ = "GNU General Public License (GPL) v2"
__url__ = "http://penguin.fr/sshproxy/"

import sys

if sys.version_info < (2, 4):
    raise RuntimeError('You need python >=2.4 for this module.')

import paramiko

if paramiko.__version_info__ < (1, 6, 1):
    raise RuntimeError('You need paramiko >=1.6.1 for this module.')


from registry import get_class
