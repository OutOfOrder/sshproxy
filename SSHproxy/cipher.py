#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jun 05, 22:58:20 by david
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


from Crypto.Cipher import Blowfish
import base64

from SSHproxy.config import Config, ConfigSection, get_config

_engine_registry = {}


def register_engine(cls):
    _engine_registry[cls.cipher_id] = cls

def get_engine(cipher_type):
    engine = _engine_registry.get(cipher_type, None)
    if engine is None:
        if cipher_type != 'plain':
            raise ValueError('Unknown cipher_type %s' % cipher_type)
        engine = PlainCipher
    return engine

def cipher(text, **kw):
    engine = _default_engine[0]
    if kw.has_key('type'):
        engine = get_engine(kw['type'])
    return '%s%s' % (engine.prefix(), engine.encrypt(text, **kw))

def decipher(text, **kw):
    # guess the encryption method
    tokens = text.split('$', 2)

    # default decoder is Plain
    engine = PlainCipher
    if len(tokens) == 3:
        try:
            engine = get_engine(tokens[1])
            text = tokens[2]
        except ValueError:
            # maybe the text contains the magic prefix...
            # let's try to decode it as plain text
            pass

    return engine.decrypt(text, **kw)

class BaseCipher(object):
    # cipher_id = ''

    @classmethod
    def set_default(cls):
        _default_engine[0] = cls

    @classmethod
    def prefix(cls):
        return '$%s$' % cls.cipher_id

    @classmethod
    def encrypt(cls, text, **kw):
        raise NotImplementedError

    @classmethod
    def decrypt(cls, text, **kw):
        raise NotImplementedError

class PlainCipher(BaseCipher):
    cipher_id = 'plain'

    @classmethod
    def prefix(cls):
        return ''

    @classmethod
    def encrypt(cls, text, **kw):
        return text

    @classmethod
    def decrypt(cls, text, **kw):
        return text

class Base64Cipher(BaseCipher):
    cipher_id = "base64"

    @classmethod
    def encrypt(cls, text, **kw):
        return base64.b64encode(text)

    @classmethod
    def decrypt(cls, text, **kw):
        return base64.b64decode(text)

register_engine(Base64Cipher)

class BlowfishCipher(BaseCipher):
    cipher_id = "blowfish"

    @classmethod
    def set_default(cls):
        cls.engine = cls.get_engine(get_config('blowfish')['secret'])
        _default_engine[0] = cls

    @classmethod
    def get_engine(cls, secret=None):
        if secret is None:
            secret = getattr(cls, 'secret', get_config('blowfish')['secret'])
        return Blowfish.new(secret, Blowfish.MODE_ECB)

    @classmethod
    def encrypt(cls, text, **kw):
        engine = kw.get('engine', getattr(cls, 'engine', None))
        if not engine:
            engine = cls.get_engine(kw.get('secret', None))
        ftext = '%s:%s%s' % (len(text), text, '*'*8)
        ftext = ftext[:len(ftext) - (len(ftext)%8) ]
        return base64.b64encode(engine.encrypt(ftext))

    @classmethod
    def decrypt(cls, text, **kw):
        engine = kw.get('engine', getattr(cls, 'engine', None))
        if not engine:
            engine = cls.get_engine(kw.get('secret', None))
        size, ftext = engine.decrypt(
                    base64.b64decode(text)).split(':', 1)
        return ftext[:int(size)]

register_engine(BlowfishCipher)

_default_engine = [ PlainCipher ]

class BlowfishConfigSection(ConfigSection):
    section_defaults = {
        'secret': ('Enoch Root has an old cigar box on his lap.'
        ' Golden light is shining out of the crack around its lid.'),
        }

Config.register_handler('blowfish', BlowfishConfigSection)

def _init_cipher():
    cipher_type = get_config('sshproxy')['cipher_type']
    get_engine(cipher_type).set_default()

_init_cipher()

