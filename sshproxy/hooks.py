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

