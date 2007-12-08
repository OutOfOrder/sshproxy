#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Dec 08, 20:10:26 by david
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

import os, os.path, sha
from ConfigParser import NoSectionError, SafeConfigParser as ConfigParser

from sshproxy.config import ConfigSection, path, get_config
from sshproxy.client import ClientDB, ClientInfo
from sshproxy.util import istrue


class FileClientConfigSection(ConfigSection):
    section_id = 'client_db.ini'
    section_defaults = {
        'file': '@client.db',
        }
    types = {
        'file': path,
        }


FileClientConfigSection.register()

class FileClientInfo(ClientInfo):
    def get_config_file(self):
        clientfile = get_config('client_db.ini')['file']
        if not os.path.exists(clientfile):
            open(clientfile, 'w').close()
            os.chmod(clientfile, 0600)
            # no need to parse an empty file
            return None

        file = ConfigParser()
        file.read(clientfile)
        return file

    def load(self):
        file = self.get_config_file()
        if not file:
            return

        try:
            tokens = dict(file.items(self.username))
        except NoSectionError:
            return

        self.set_tokens(**tokens)


    def save(self, file=None):
        if not file:
            file = self.get_config_file()
        if not file:
            return

        if self.username:
            if not file.has_section(self.username):
                file.add_section(self.username)

            for tag, value in self.tokens.items():
                if tag in ('username', 'ip_addr'):
                    continue
                elif value and str(value):
                    file.set(self.username, tag, str(value))
                elif file.has_option(self.username, tag):
                    file.remove_option(self.username, tag)

        clientfile = get_config('client_db.ini')['file']
        fd = open(clientfile+'.new', 'w')
        file.write(fd)
        fd.close()
        os.rename(clientfile+'.new', clientfile)
        
    def delete(self, username):
        file = self.get_config_file()
        if not file:
            return

        if file.has_section(username):
            file.remove_section(username)
        self.save(file)

    def auth_token_order(self):
        return ('pubkey', 'pkey', 'password')

    def authenticate(self, **tokens):
        from sshproxy import log
        resp = False
        for token in self.auth_token_order():
            if token in tokens.keys() and tokens[token] is not None:
                if token == 'password':
                    if (sha.new(tokens[token]).hexdigest()
                                           == self.get_token(token)):
                        resp = True
                        break
                elif token in ('pubkey', 'pkey'):
                    pubkeys = self.get_token('pubkey',
                              self.get_token('pkey', '')).split('\n')
                    pubkeys = [ pk.split()[0] for pk in pubkeys if len(pk) ]
                    for pk in pubkeys:
                        if pk == tokens[token]:
                            resp = True
                            break
                    ClientDB()._unauth_pubkey = tokens[token]

                elif self.get_token(token) == tokens[token]:
                    resp = True
                    break
        return resp

    def exists(self, username):
        file = self.get_config_file()
        if not file:
            return

        return file.has_section(username)

    def list_clients(self, **kw):
        file = self.get_config_file()
        if not file:
            return

        return file.sections()

class FileClientDB(ClientDB):
    def exists(self, username, **tokens):
        if not getattr(self, 'clientinfo', None):
            return ClientInfo(None).exists(username)
        return self.clientinfo.exists(username)

    def list_clients(self, **kw):
        return ClientInfo(None).list_clients(**kw)

    def add_client(self, username, **tokens):
        if self.exists(username):
            return 'Client %s does already exist' % username
        client = ClientInfo(username, **tokens)
        client.save()
        return 'Client %s added' % username

    def del_client(self, username, **tokens):
        if not self.exists(username):
            return 'Client %s does not exist'

        ClientInfo(None).delete(username)

        return 'Client %s deleted.' % username

