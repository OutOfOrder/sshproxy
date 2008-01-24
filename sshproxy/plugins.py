#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2007 David Guerizec <david@guerizec.net>
#
# Last modified: 2008 Jan 24, 23:15:15 by david
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
import util
from plugin import Plugin

#plugindir = os.path.join(os.path.dirname(sys.modules[__name__].__file__), 'lib')
conf = config.get_config('sshproxy')
plugindir = conf['plugin_dir']
plugin_list = []

sys.path.append(plugindir)


if os.path.exists(plugindir+'/disabled'):
    disabled = open(plugindir+'/disabled').readlines()
    disabled = [ m.strip() for m in disabled ]
else:
    disabled = []

enabled_plugins = conf['plugin_list'].split()
available_plugins = {}

for name in os.listdir(plugindir):
    if os.path.exists(os.path.join(plugindir, name, '__init__.py')):
        if not name in disabled and not name[0] == '.':
            try:
                module = __import__(name, globals(), locals(), [])
            except ImportError:
                log.warn("Could not load plugin %s" % name)
                continue
            plugin = Plugin(name, module, name in enabled_plugins)
            plugin_list.append(plugin)
            available_plugins[name] = plugin
            log.info("Loaded plugin %s" % name)

plugin_list.sort(lambda x, y: cmp(x.plugin_name.lower(), y.plugin_name.lower()))

loaded_plugins = util.OrderedDict()

def init_plugins():
  try:
    for plugin in enabled_plugins:
        if plugin in available_plugins.keys():
            try:
                available_plugins[plugin].init()
                log.info('Initialized plugin %s' % available_plugins[plugin].name)
                loaded_plugins[plugin] = available_plugins[plugin]
            except Exception, msg:
                log.exception('init_plugins: plugin %s failed to load (%s)'
                                                        % (plugin, msg))
  except:
      log.exception("init_plugins:")

