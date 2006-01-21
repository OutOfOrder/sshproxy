#!/usr/bin/python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 jan 12, 15:52:19 by david
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

import os
#from itools import get_abspath
import sys

plugindir = os.path.join(os.path.dirname(sys.modules[__name__].__file__), 'lib')
pluginInfo = []

sys.path.append(plugindir)

if os.path.exists(plugindir+'/disabled'):
    disabled = open(plugindir+'/disabled').readlines()
    disabled = [ m.strip() for m in disabled ]
else:
    disabled = []
for module in os.listdir(plugindir):
    if os.path.isdir(os.path.join(plugindir, module)):
        fn = module
        if module in disabled:
            pluginInfo.append((module, module, module, "", 1))
        else:
            m=__import__(module, globals(), locals(), [])
            if hasattr(m, "__pluginname__"):
                name = m.__pluginname__
            else:
                name = module
            if hasattr(m, "__description__"):
                desc = m.__description__
            else:
                desc = "No description specified"
            pluginInfo.append((name, m.__name__, m, desc, 0))


def init_plugins():
    for name, dummy, plugin, dummy, dummy in pluginInfo:
        plugin.__init_plugin__()

