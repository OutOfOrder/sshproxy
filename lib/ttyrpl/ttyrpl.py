#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2007 David Guerizec <david@guerizec.net>
#
# Last modified: 2008 Jan 28, 00:41:52 by david
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


import os, os.path, time, struct
import datetime

from sshproxy import get_class, __version__
from sshproxy.config import get_config, ConfigSection, path
from sshproxy.util import istrue
from sshproxy.proxy import ProxyShell
from sshproxy import log

class TTYrplConfigSection(ConfigSection):
    section_id = 'ttyrpl'
    section_defaults = {
        'logdir': '@ttyrpl',
        }
    types = {
        'logdir': path,
        }

TTYrplConfigSection.register()



class TTYrplLogger(object):
    EVT_OPEN = 0x01
    EVT_READ = 0x02
    EVT_WRITE = 0x03
    EVT_LCLOSE = 0x64
    EVT_MAGIC = 0x4A
    EVT_ID_PROG = 0xF0
    EVT_ID_DEVPATH = 0xF1
    EVT_ID_TIME = 0xF2
    EVT_ID_USER = 0xF3


    def __init__(self, filename):
        self.filename = filename
        self.log = open(self.filename, 'a')
        self.log_it(self.EVT_MAGIC,   "RPL2_50")
        self.log_it(self.EVT_ID_PROG, "sshproxy v%s" % __version__)
        self.log_it(self.EVT_ID_TIME, time.ctime())

    def open(self, filename):
        self.log_it(self.EVT_OPEN, filename)

    def read(self, data):
        self.log_it(self.EVT_READ, data)

    def write(self, data):
        self.log_it(self.EVT_WRITE, data)

    def lclose(self):
        self.log_it(self.EVT_LCLOSE)

    def log_user(self, user):
        self.log_it(self.EVT_ID_USER, user)

    def log_it(self, event, data=None):
        if not data:
            return
        while len(data):
            if len(data) > 4096:
                payload, data = data[:4096], data[4096:]
            else:
                payload, data = data, ''

            pkt = self.make_packet(event, payload)
            self.log.write(pkt)

    def make_packet(self, event, data=None):
        t = time.time()
        sec = int(t)
        usec = int((t - sec) * 1000000)

        if data is not None:
            data = str(data)
        else:
            data = ''

        # struct rpltime {
        #     uint64_t tv_sec;
        #     uint32_t tv_usec;
        # };
        # struct rpldsk_packet {
        #      uint16_t size;
        #      uint8_t event, magic;
        #      struct rpltime time;
        # } __attribute__((packed));
        packet = struct.pack("HBBQL", len(data), event, 0xEE, sec, usec)

        return packet + data

    def __del__(self):
        self.log.close()



Server = get_class('Server')

class TTYrplServer(Server):
    def do_shell_session(self):
        client_enable = istrue(self.get_ns_tag('client', 'log_me', 'no'))
        # The following line is useless because the site namespace is not
        # yet set up at this point. We get the site 'log_me' tag by
        # overriding the authorize method, hence the UGLY HACK comment.
        site_enable = istrue(self.get_ns_tag('site', 'log_me', 'no'))
        if client_enable or site_enable:
            TTYrplProxyShell.register()
        return Server.do_shell_session(self)

    def authorize(self, user_site, need_login=True):
        # UGLY HACK
        auth = Server.authorize(self, user_site, need_login=True)
        if auth:
            if istrue(self.get_ns_tag('site', 'log_me', 'no')):
                TTYrplProxyShell.register()
        return auth

TTYrplServer.register()


ProxyShell = get_class('ProxyShell')

class TTYrplProxyShell(ProxyShell):
    def __reginit__(self, *args, **kw):
        conf = get_config('ttyrpl')
        if not os.path.isdir(conf['logdir']):
            os.makedirs(conf['logdir'])
        
        self.logdir = conf['logdir']

        ProxyShell.__reginit__(self, *args, **kw)

        user = self.ipc_chan.call('get_ns_tag', namespace='client',
                                                tag='username')
        path = os.path.join(self.logdir, user)
        if not os.path.isdir(path):
            os.makedirs(path)

        site_login = self.ipc_chan.call('get_ns_tag', namespace='site',
                                                tag='login')
        site_name = self.ipc_chan.call('get_ns_tag', namespace='site',
                                                tag='name')
        site = '%s@%s' % (site_login, site_name)
        path = os.path.join(path, site)
        if not os.path.isdir(path):
            os.makedirs(path)

        date = datetime.datetime.now().isoformat()
        logfile = os.path.join(path, date)
        self.log = TTYrplLogger(logfile)
        self.log.log_user("%s->%s" % (user, site))

    def client_recv_data(self, source, name):
        data = ProxyShell.recv_data(self, source, name)
        self.log.read(data)
        return data

    def site_recv_data(self, source, name):
        data = ProxyShell.recv_data(self, source, name)
        self.log.write(data)
        return data

    def copy_client(self, source, event, destination,
                                         recv_data=None, send_data=None):
        try:
            return self.channel_copy(source, event, destination,
                recv_data=TTYrplProxyShell.client_recv_data)
        except:
            self.log.lclose()
            raise

    def copy_site(self, source, event, destination,
                                         recv_data=None, send_data=None):
        try:
            return self.channel_copy(source, event, destination,
                recv_data=TTYrplProxyShell.site_recv_data)
        except:
            self.log.lclose()
            raise



