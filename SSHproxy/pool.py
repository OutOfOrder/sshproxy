#!/usr/bin/python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 jan 18, 12:58:34 by david
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307  USA


# Imports from Python

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

