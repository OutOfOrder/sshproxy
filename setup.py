#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 14, 22:31:50 by david
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

import os, os.path
from distutils.core import setup

version = '0.4.3'
url = 'http://penguin.fr/sshproxy/'

def get_data_files(target, root, path=''):
    l = []
    for item in os.listdir(os.path.join(root, path)):
        if os.path.isdir(os.path.join(root, path, item)):
            l = l + get_data_files(target, root, os.path.join(path, item))
        else:
            l.append((os.path.join(target, path),
                        [ os.path.join(root, path, item) ]))
    return l

long_description = '''
sshproxy is an ACL proxy to allow (or deny) users to connect to remote
sites.

It contains a password database which relieve the users from having to
know the password or key of the remote sites.

`Read more...`_

.. _`Read more...`: http://penguin.fr/sshproxy/
'''

classifiers = """Development Status :: 4 - Beta
Environment :: Console
Environment :: No Input/Output (Daemon)
Intended Audience :: System Administrators
License :: OSI Approved :: GNU General Public License (GPL)
Operating System :: POSIX
Programming Language :: Python
Topic :: Internet :: Proxy Servers
Topic :: Security
Topic :: System :: Networking
Topic :: System :: Systems Administration""".split('\n')


data_files = ( get_data_files('lib/sshproxy', 'lib')
                 + get_data_files('share/sshproxy', 'share') )

setup(name='sshproxy',
      version=version,
      description='pure python implementation of an ssh proxy',
      author='David Guerizec',
      author_email='david@guerizec.net',
      url=url,
      download_url='%sdownload/sshproxy-%s.tar.gz' % (url, version),
      packages=['sshproxy'],
      scripts=['bin/sshproxyd', 'bin/pssh', 'bin/pscp'],
      long_description=long_description,
      data_files=data_files,
      classifiers=classifiers,
      )
