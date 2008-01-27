#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2007 David Guerizec <david@guerizec.net>
#
# Last modified: 2008 Jan 27, 21:19:49 by david
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

__plugin_name__ = "Password encoding fix"
__description__ = """
    This is a runtime patch to fix a paramiko bug
    about non-UTF8 password.
"""


def __patch_it__():
    import paramiko
    from sshproxy import log


    if paramiko.__version_info__ <= (1, 7, 2):
        import p_paramiko_passwdenc
        log.info("Runtime patch to paramiko password encoding applied")


def __init_plugin__():
    pass

__patch_it__()

# vim:set ts=4 sw=4 sts=4 expandtab:
