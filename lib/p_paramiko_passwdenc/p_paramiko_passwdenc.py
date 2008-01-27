#!/usr/bin/python
# -*- coding: ascii -*-
# Copyright (C) 2008  Dwayne C. Litzenberger <dlitz@dlitz.net>
#
# This file is part of paramiko.
#
# Paramiko is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# Paramiko is distrubuted in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Paramiko; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# This is a runtime patch to fix a security issue in paramiko until it has
# officially been patched.
# For more information, see:
# http://www.lag.net/pipermail/paramiko/2008-January/000599.html
#
#              -- David Guerizec <david@guerizec.net>

import sys

from paramiko.auth_handler import *

def _parse_service_accept(self, m):
    service = m.get_string()
    if service == 'ssh-userauth':
        self.transport._log(DEBUG, 'userauth is OK')
        m = Message()
        m.add_byte(chr(MSG_USERAUTH_REQUEST))
        m.add_string(self.username)
        m.add_string('ssh-connection')
        m.add_string(self.auth_method)
        if self.auth_method == 'password':
            m.add_boolean(False)
            password = self.password
            if isinstance(password, unicode):
                password = password.encode('UTF-8')
            m.add_string(self.password)
        elif self.auth_method == 'publickey':
            m.add_boolean(True)
            m.add_string(self.private_key.get_name())
            m.add_string(str(self.private_key))
            blob = self._get_session_blob(self.private_key, 'ssh-connection', self.username)
            sig = self.private_key.sign_ssh_data(self.transport.randpool, blob)
            m.add_string(str(sig))
        elif self.auth_method == 'keyboard-interactive':
            m.add_string('')
            m.add_string(self.submethods)
        elif self.auth_method == 'none':
            pass
        else:
            raise SSHException('Unknown auth method "%s"' % self.auth_method)
        self.transport._send_message(m)
    else:
        self.transport._log(DEBUG, 'Service request "%s" accepted (?)' % service)


AuthHandler._handler_table[MSG_SERVICE_ACCEPT] = _parse_service_accept

# vim:set ts=4 sw=4 sts=4 expandtab:

