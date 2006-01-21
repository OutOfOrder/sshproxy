#!/usr/bin/python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 jan 12, 15:39:39 by david
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
hooks = {}

def register_hook(hid, hook, index=0):
    if not hooks.has_key(hid):
        hooks[hid] = []

    if index < 0:
        index = 0
    if index > len(hooks[hid]):
        index = len(hooks[hid])
    
    hooks[hid].insert(index, hook)

def call_hooks(hid, *args, **kwargs):
    if not hooks.has_key(hid):
        hooks[hid] = []

    for hook in hooks[hid]:
        hook(*args, **kwargs)

def get_hook_index(hid, hook):
    if not hooks.has_key(hid):
        hooks[hid] = []

    return hooks[hid].index(hook)

