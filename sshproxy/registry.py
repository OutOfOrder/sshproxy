#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2007 David Guerizec <david@guerizec.net>
#
# Last modified: 2008 Jan 24, 22:56:59 by david
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
    _class_base = object


    @classmethod
    def register(cls):
        """
        Register an object class.
        """

        #print '%s.register(%s)' % (cls.__name__, cls._class_id)
        Registry._registry[cls._class_id] = cls


    def __new__(cls, *args, **kw):
        """
        Return an instance of the previously registered class.

        If the class is a singleton, and was already instanciated,
        ignore arguments supplied and return singleton instance.

        """

        obj_class = Registry._registry[cls._class_id]
        if cls._singleton:
            theone = Registry._singletons.get(cls._class_id)
            if theone is None:
                theone = cls._class_base.__new__(obj_class)
                Registry._singletons[cls._class_id] = theone
                theone.__reginit__(*args, **kw)
            return theone
            
        else:
            obj = cls._class_base.__new__(obj_class)
            obj.__reginit__(*args, **kw)
            return obj

    def __reginit__(self, *args, **kw):
        raise NotImplementedError("__reginit__ has not been implemented in %s" % self.__class__.__name__)
        pass

class Dummy(Registry):
    _class_id = "Dummy"
    pass

def get_class(class_id):
    return Registry._registry.get(class_id, Dummy)
