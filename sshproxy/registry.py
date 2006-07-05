#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 04, 22:48:17 by david
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


class Registry(object):
    _registry = {}
    _singletons = {}
    _singleton = False

    @classmethod
    def register(cls):
        """
        Register an object class.
        """

        Registry._registry[cls._class_id] = cls

    @classmethod
    def get_instance(cls, *args, **kw):
        """
        Return an instance of the previously registered class.

        If the class is a singleton, and was already instanciated,
        ignore arguments supplied and return singleton instance.

        """

        obj_class = Registry._registry[cls._class_id]
        if cls._singleton:
            if not Registry._singletons.has_key(cls._class_id):
                Registry._singletons[cls._class_id] = obj_class(*args, **kw)
            return Registry._singletons[cls._class_id]
        else:
            return obj_class(*args, **kw)



