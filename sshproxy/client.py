#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 09, 22:54:57 by david
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

from registry import Registry
from acl import ACLDB, ACLTags


class ClientInfo(Registry):
    """
    A UserInfo holds client context information.
    """
    _class_id = 'ClientInfo'


    def __reginit__(self, username, **tokens):
        """
        Create a new ClientInfo object, and set the username.

        @param username: the client's username
        @type username: str
        @param **kw: optional context information
        @type **kw: dict
        """
        self.tokens = ACLTags(tokens)
        self.username = username
        self.load()


    def load(self):
        pass


    def save(self):
        pass


    def get_token(self, token, default=None):
        return self.tokens.get(token, default)


    def set_tokens(self, **tokens):
        """
        Set the authentication or context token of the user.

        @param **tokens: the tokens to be set.
        @type **tokens: dict
        @return: None
        """
        for token, value in tokens.items():
            # XXX: how to encrypt the tokens ? encrypt them all ?
            self.tokens.add_tag(token, str(value))


    def get_tags(self):
        tags = ACLTags(self.tokens)
        tags.add_tag('username', self.username)
        return tags


    def auth_token_order(self):
        return ()


    def authenticate(self, **tokens):
        """
        Authenticate the client with C{**tokens}.

        @param **tokens: authentication tokens (password, key, ...)
        @type **tokens: dict
        @return: True if the client was authenticated, False otherwise.
        @rtype: bool
        """
        for token in self.auth_token_order():
            if token in tokens and tokens[token] is not None:
                if self.get_token(token) == tokens[token]:
                    return True
        return False


ClientInfo.register()


class ClientDB(Registry):
    """
    The ClientDB implements the glue between ClientInfo objects and the
    controling program.
    """
    _class_id = 'ClientDB'
    _singleton = True

    def __reginit__(self, **kw):
        """
        This creates a ClientDB object, and initialize the attribute
        C{clientinfo} to None.
        """
        self.clientinfo = None


    def authenticate(self, username, auth_tokens, **tokens):
        """
        Authenticate the client connecting as C{username} with C{**tokens}.
        If authentication is successful, set the attribute C{clientinfo} as
        an instance of L{ClientInfo}.
        This only controls the connection from the client to the proxy.

        @param username: the username
        @type username: str
        @param **tokens: the authentication tokens (password, key, ...)
        @type **tokens: dict
        @return: True if authenticated, False otherwise.
        @rtype: bool
        """
        clientinfo = ClientInfo(username, **tokens)

        if not ACLDB().check(acl='authenticate',
                                          client=clientinfo.get_tags()):
            return False

        if clientinfo.authenticate(**auth_tokens):
            self.clientinfo = clientinfo
            return True
        else:
            return False



    def get_user_info(self, username=None, **kw):
        """
        This method is an accessor for the attribute C{clientinfo} if the
        client was authenticated.
        If C{username} is supplied, return a L{ClientInfo} instance
        corresponding to C{username}.
        '**kw' can be used freely to pass contextual information to the
        database backend.

        @param username: an optional username
        @type username: str
        @param **kw: optional context information
        @type **kw: dict
        @return: L{ClientInfo} instance
        @rtype: ClientInfo
        """

        if username:
            return ClientInfo(username, **kw)
        else:
            return self.clientinfo


    def get_tags(self):
        return self.clientinfo.get_tags()

    def list_users(self, **kw):
        """
        return a list of L{ClientInfo} objects.

        C{**kw} can be used freely to implement filtering.
        """

        return []

ClientDB.register()

