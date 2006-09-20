#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Sep 20, 17:21:55 by david
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

from sshproxy import get_class
from sshproxy.dispatcher import Dispatcher
from sshproxy.server import Server

base = get_class('Dispatcher')

class ConsoleExtra_Dispatcher(base):
    acl_open = "acl(cmd_open)"
    def cmd_open(self, *args):
        """
        open user@site

        Open a shell session on user@site.
        """
        self.check_args(1, args, strict=True)

        server = Server()

        server.args = list(args)
        server.do_shell_session()


    acl_run = "acl(cmd_run)"
    def cmd_run(self, *args):
        """
        run user@site cmd args...

        Run a command remotely on user@site.

        WARNING: You could experience locks-up using this command with some
                 SSH servers. I still don't know why but I'm investigating.
        """
        self.check_args(2, args)

        server = Server()

        server.args = list(args)
        server.do_remote_execution()

ConsoleExtra_Dispatcher.register()

