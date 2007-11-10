#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2007 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Nov 10, 22:39:09 by david
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

class I18n(Registry):
    _class_id = "I18n"
    _singleton = True

    messages = {}
    seen = {}
    encoding = 'latin1'

    def __reginit__(self):
        pass

    def _(self, message):
        h = hash(message)

        if not self.messages.has_key(h):
            if (self.__class__.__name__ != self._class_id and
                    not self.seen.has_key(h)):
                import log
                log.debug("i18n: unknown hash %s: %s" % (h, repr(message)))
                self.seen[h] = None
            return message.encode(self.encoding)

        return self.messages[h]


I18n.register()

def _(message):
    return I18n()._(message)

__builtins__['_'] = _
