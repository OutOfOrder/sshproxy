#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jun 02, 03:17:53 by david
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


import os, select, pty, traceback
from Crypto.Cipher import Blowfish
import base64

from SSHproxy import log
from SSHproxy.config import SSHproxyConfig


class SSHProxyError(Exception):
    def __init__(self, msg):
        log.error("PROXY: "+msg)
        Exception.__init__(self, msg)

class SSHProxyAuthError(SSHProxyError):
    def __init__(self, msg):
        log.error("AUTH: "+msg)
        Exception.__init__(self, "Authentication error: "+msg)

class SSHProxyPluginError(SSHProxyError):
    def __init__(self, msg):
        log.error("PLUG: "+msg)
        Exception.__init__(self, "Plugin error: "+msg)

def cipher(text):
    ftext = '%s:%s%s' % (len(text), text, '*'*8)
    ftext = ftext[:len(ftext) - (len(ftext)%8) ]
    prefix = '$cipher$'
    return prefix + base64.b64encode(_cipher_engine.encrypt(ftext))

def decipher(text):
    if text[:8] in ('$cipher$', '$clrb64$'):
        text = text[8:]
        size, ftext = _cipher_engine.decrypt(base64.b64decode(text)).split(':', 1)
        return ftext[:int(size)]
    else:
        return text

class NullCipher(object):
    prefix = "$clrb64$"

    def encrypt(self, text):
        return self.prefix + base64.b64encode(text)

    def decode(self, text):
        return base64.b64decode(text)

    def decrypt(self, text):
        if text[:8] == '$clrb64$':
            return self.decode(text[8:])
        else:
            return text

class BlowfishCipher(NullCipher):
    prefix = "$cipher$"

    def __init__(self, secret):
        conf = SSHproxyConfig()
        self._cipher_engine = Blowfish.new(conf.secret, Blowfish.MODE_ECB)

    def encrypt(self, text):
        ftext = '%s:%s%s' % (len(text), text, '*'*8)
        ftext = ftext[:len(ftext) - (len(ftext)%8) ]
        return NullCipher.encrypt(self, self._cipher_engine.encrypt(ftext))

    def decrypt(text):
        if text[:8] == '$cipher$':
            text = text[8:]
            size, ftext = self._cipher_engine.decrypt(
                    NullCipher.decode(self, text[8:])).split(':', 1)
            return ftext[:int(size)]
        else:
            return NullCipher.decrypt(self, text)



if conf.secret:
    _cipher_engine = BlowfishCipher(conf.secret)
else:
    _cipher_engine = NullCipher()


SUSPEND, SWITCH, CLOSE = range(-4, -1)

