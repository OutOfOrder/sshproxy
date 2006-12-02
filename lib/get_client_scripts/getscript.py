#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Nov 24, 01:53:03 by david
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
from sshproxy.util import chanfmt

pssh = """#!/bin/bash

PROXY_PORT=${SSHPROXY_PORT:-%(port)d}
PROXY_HOST=${SSHPROXY_HOST:-%(ip_addr)s}
PROXY_USER=${SSHPROXY_USER:-%(user)s}

[ -n "$verbose" ] && echo ssh -tp $PROXY_PORT $PROXY_USER@$PROXY_HOST -- "$@"
exec ssh -tp $PROXY_PORT $PROXY_USER@$PROXY_HOST -- "$@"
"""

pscp = """#!/bin/bash

PROXY_PORT=${SSHPROXY_PORT:-%(port)s}
PROXY_HOST=${SSHPROXY_HOST:-%(ip_addr)s}
PROXY_USER=${SSHPROXY_USER:-%(user)s}

REMOTE=$PROXY_USER@$PROXY_HOST

OPTS=( )
remote_set=
args=( )
while [ $# -gt 0 ]; do
    case "$1" in
        -*)
            if [ "$1" = "-d" ]; then
                verbose=true
            else
                OPTS=( "${OPTS[@]}" "$1" )
            fi
            ;;
        *:*)
            if [ -z "$remote_set" ]; then
                args=( "${args[@]}" "$REMOTE:$1" )
                remote_set=yes
            else
                echo "Cannot have two remote locations"
                exit 1
            fi
            ;;
        *)
            args=( "${args[@]}" "$1" )

            ;;
    esac
    shift
done


[ -n "$verbose" ] && echo scp -oPort=$PROXY_PORT "${OPTS[@]}" "${args[@]}"
exec scp -oPort=$PROXY_PORT "${OPTS[@]}" "${args[@]}"
"""

base_class = get_class('Server')

class Server(base_class):
    def add_cmdline_options(self, parser, namespace):
        base_class.add_cmdline_options(self, parser, namespace)
        parser.add_option("", "--get-pssh", dest="action",
                help="display pssh client script.",
                action="store_const",
                const="get_pssh",
                )
        parser.add_option("", "--get-pscp", dest="action",
                help="display pscp client script.",
                action="store_const",
                const="get_pscp",
                )

    def opt_get_pssh(self, options, *args):
        user = self.pwdb.get_client().username
        ip_addr, port = self.ip_addr, self.port
        self.chan.send(pssh % locals())

    def opt_get_pscp(self, options, *args):
        user = self.pwdb.get_client().username
        ip_addr, port = self.ip_addr, self.port
        self.chan.send(pscp % locals())




Server.register()


