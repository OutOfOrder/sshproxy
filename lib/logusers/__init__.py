#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Sep 17, 16:14:58 by david
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

__plugin_name__ = "Log User Session"
__description__ = """
    This plugin logs every key stroke by clients on
    shell sessions.
"""

def __init_plugin__():
    from logusers import LoggedProxyShell
    LoggedProxyShell.register()


def __setup__():
    from sshproxy import menu
    from sshproxy.config import get_config
    import logusers

    cfg = get_config('logusers')
    items = []

    def update(value):
        cfg['logdir'] = value
    items.append(menu.MenuInput('Log directory',
                "",
                cfg.get('logdir', raw=True),
                cb=update))

    return items


