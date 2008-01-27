#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2007 David Guerizec <david@guerizec.net>
#
# Last modified: 2008 Jan 27, 21:21:53 by david
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

__plugin_name__ = "RandomPool security fix"
__description__ = """
    This is a runtime patch to fix a paramiko/pycrypto
    security issue.
"""


def __patch_it__():
    import paramiko.common
    from sshproxy import log

    if paramiko.__version_info__ >= (1, 7, 2):
        return

    import p_paramiko_osrandom
    
    randpool = p_paramiko_osrandom.OSRandomPool()

    impacted_modules = [
                        'common',
                        'dsskey',
                        'hostkeys',
                        'packet',
                        'pkey',
                        'rsakey',
                        'transport',
                        # the following modules do not seem to use the
                        # randpool object, although they import it from common
                        # so let's patch them too, just in case
                        'auth_handler',
                        'channel',
                        'client',
                        'kex_gex',
                        'kex_group1',
                        'server',
                        'sftp',
                        'sftp_attr',
                        'sftp_file',
                        'sftp_handle',
                        'sftp_server',
                        'sftp_si',
                        'util',
                    ]

    for name in impacted_modules:
        modname = 'paramiko.%s' % name
        module = __import__(modname, fromlist=[name])
        module.randpool = randpool

    paramiko.randpool = randpool

    if 'Crypto.Util.randpool.' not in repr(paramiko.common.randpool):
        log.info("Runtime patch to paramiko random generator applied")


def __init_plugin__():
    pass

__patch_it__()

# vim:set ts=4 sw=4 sts=4 expandtab:
