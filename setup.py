#!/usr/bin/python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005 David Guerizec <david@guerizec.net>
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

from distutils.core import setup

setup(name='SSHproxy',
      version='0.2.0',
      description='pure python implementation of an ssh proxy',
      author='David Guerizec',
      author_email='david@guerizec.net',
      url='http://www.nongnu.org/sshproxy/',
      packages=['SSHproxy','SSHproxy/client','SSHproxy/server','SSHproxy/pwdb'],
      scripts=['sshproxy'],
      )
