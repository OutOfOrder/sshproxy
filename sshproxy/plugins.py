#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jun 15, 13:55:36 by david
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


import os, sys

import log
import config

#plugindir = os.path.join(os.path.dirname(sys.modules[__name__].__file__), 'lib')
conf = config.get_config('sshproxy')
plugindir = conf['plugin_dir']
pluginInfo = []

sys.path.append(plugindir)


if os.path.exists(plugindir+'/disabled'):
    disabled = open(plugindir+'/disabled').readlines()
    disabled = [ m.strip() for m in disabled ]
else:
    disabled = []

enabled = conf['plugin_list'].split()

for module in os.listdir(plugindir):
    if os.path.isdir(os.path.join(plugindir, module)):
        fn = module
        if module not in enabled or module in disabled:
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
            log.info("Loaded plugin %s" % name)


def init_plugins():
    for name, dummy, plugin, dummy, disabled in pluginInfo:
        if not disabled:
            plugin.__init_plugin__()

