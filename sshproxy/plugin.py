#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 30, 23:39:09 by david
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


class Plugin(object):
    def __init__(self, name, module, enabled):
        self.name = name
        self.module = module
        self.plugin_name = getattr(module, '__plugin_name__', name)
        self.description = getattr(module, '__description__', '')
        self.enabled = enabled and True or False
        self.backend = getattr(module, '__backend__', False) and True or False

    def init(self):
        self.module.__init_plugin__()

    def setup(self, *args, **kw):
        if getattr(self.module, '__setup__', None):
            return self.module.__setup__(*args, **kw)
        return None



