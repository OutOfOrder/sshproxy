#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 07, 02:24:21 by david
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


    def __init__(self, username, **tokens):
        """
        Create a new ClientInfo object, and set the username.

        @param username: the client's username
        @type username: str
        @param **kw: optional context information
        @type **kw: dict
        """
        from acl import ACLTags
        self.username = username
        self.load()
        self.tags = ACLTags(obj=self)
        print 'TAGS:', self.tags


    def load(self):
        pass

    def set_password(self, password):
        """
        Set the password of the user. The password is stored encrypted in
        the database if the database engine allows it.

        @param password: the password to be set.
        @type password: str
        @return: True if the password was set, False otherwise.
        @rtype: bool
        """
        return False


    def authenticate(self, **tokens):
        """
        Authenticate the client with C{**tokens}.

        @param **tokens: authentication tokens (password, key, ...)
        @type **tokens: dict
        @return: True if the client was authenticated, False otherwise.
        @rtype: bool
        """
        return False

ClientInfo.register()


class ClientDB(Registry):
    """
    The ClientDB implements the glue between ClientInfo objects and the
    controling program.
    """
    _class_id = 'ClientDB'
    _singleton = True

    def __init__(self, **kw):
        """
        This creates a ClientDB object, and initialize the attribute
        C{clientinfo} to None.
        """
        self.clientinfo = None
        self.tags = ACLTags(obj=self)


    def authenticate(self, username, **tokens):
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
        clientinfo = ClientInfo.get_instance(username, **tokens)

        print "ACL OK?????"
        if not ACLDB.get_instance().check(acl='authenticate', client=clientinfo.tags):
            print "ACL KO"
            return False
        print "ACL OK"

        if clientinfo.authenticate(**tokens):
            self.clientinfo = clientinfo
            print "AUTH OK"
            return True
        else:
            print "AUTH KO"
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
            return ClientInfo.get_instance(username, **kw)
        else:
            return self.username


    def list_users(self, **kw):
        """
        return a list of L{ClientInfo} objects.

        C{**kw} can be used freely to implement filtering.
        """

        return []

ClientDB.register()

