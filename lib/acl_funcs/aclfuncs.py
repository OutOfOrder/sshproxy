#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 23, 20:50:27 by david
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


class ACLRuleParser(get_class('ACLRuleParser')):

    def func_len(self, *args):
        if len(args) != 1:
            print "Warning: function len takes exactly 1 argument."
            return
        return len(args[0])

    def func_substr(self, *args):
        if len(args) != 3:
            print "Warning: function substr takes exactly 3 arguments."
            return
        start = args[0]
        end = args[1]
        var = args[2]
        return var[start:end]

    def call(self, namespace):
        # self.right = "start end ns.var"
        try:
            start, end, var = self.right.split()
        except ValueError:
            return False
        sub = str(self.left.eval(namespace, Token(str(var))))[int(start):int(end)]
        return sub

ACLRuleParser.register()

