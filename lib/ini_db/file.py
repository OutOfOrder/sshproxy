#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Aug 31, 02:23:07 by david
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

from ConfigParser import NoSectionError, SafeConfigParser as BaseConfigParser
from sshproxy.util import SortedDict



class FileConfigParser(BaseConfigParser):
    """
    This class is a wrapper to python's ConfigParser to avoid the
    automatic merge between a section and the DEFAULT section.
    It also forces ConfigParser to use SortedDict instead of builtin
    dict.
    """
    import ConfigParser as CP
    CP.__builtins__['dict'] = SortedDict

    def read(self, filenames):
        # read the ini file the standard way
        BaseConfigParser.read(self, filenames)

        # convert _defaults to SortedDict int _mydefaults
        self._mydefaults = SortedDict(self._defaults)

        # set it empty to avoid interference with other sections
        self._defaults = SortedDict()

        # convert as well all sections to SortedDict
        for section in self._sections:
            self._sections[section] = SortedDict(self._sections[section])

        # and finally, convert the section list itself to SortedDict
        self._sections = SortedDict(self._sections)


    def defaults(self):
        # returns the real defaults
        return self._mydefaults

    def add_section(self, section):
        # add a section the standard way
        BaseConfigParser.add_section(self, section)
        # and convert it to a SortedDict
        self._sections[section] = SortedDict()

    def write(self, fp):
        # put _defaults back in place before writing
        self._mydefaults.update(self._defaults)
        self._defaults = self._mydefaults
        # write in alpha-sorted order
        BaseConfigParser.write(self, fp)
        # and set it back to an empty dict
        self._defaults = SortedDict()


