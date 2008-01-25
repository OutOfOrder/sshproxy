#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2007 David Guerizec <david@guerizec.net>
#
# Last modified: 2008 Jan 25, 00:21:05 by david
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

__plugin_name__ = "TTY Logger"
__description__ = """
    This plugin logs every key stroke by clients on
    shell sessions. Logs can be replayed with ttyreplay
    from the ttyrpld project from Jan Engelhardt
    http://ttyrpld.sourceforge.net/
"""

def __init_plugin__():
    import ttyrpl


def __setup__():
    from sshproxy import menu
    from sshproxy.config import get_config
    import ttyrpl

    cfg = get_config('ttyrpl')
    items = []

    def update(value):
        cfg['logdir'] = value

    items.append(menu.MenuInput('Log directory',
                "",
                cfg.get('logdir', raw=True),
                cb=update))

    return items


