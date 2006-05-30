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


class Pool(object):
    def __init__(self):
        self.connlist = []

    def add_connection(self, conn):
        self.connlist.append(conn)
        return len(self.connlist) - 1

    def del_connection(self, index):
        if len(self.connlist) > index >= 0:
            del self.connlist[index]

    def get_connection(self, index=0):
        if len(self.connlist) > index >= 0:
            return self.connlist[index]
        return None

    def __len__(self):
        return len(self.connlist)

    def __getitem__(self, item):
        return self.connlist[item]

    def list_connections(self):
        return self.connlist

_pool = None

# get the Pool singleton instance
def get_connection_pool(*args, **kwargs):
    global _pool
    if _pool is None:
        _pool = Pool(*args, **kwargs)
    return _pool

