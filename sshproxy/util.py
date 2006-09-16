#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Sep 16, 18:09:31 by david
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

import sys, pwd
import StringIO

import paramiko


# save the original dict to avoid infinite recursive loops
# when this class overrides the dict builtin in a module, ie.:
#   import module
#   module.__builtins__['dict'] = SortedDict
odict = dict
class SortedDict(odict):
    """
    This class implements a dict with sorted keys.
    This is less efficient than dict, but much nicer
    to read for a human creature.
    """
    def values(self):
        items = odict.items(self)
        items.sort()
        return [ odict.__getitem__(self, item) for item in items ]

    def items(self):
        items = odict.items(self)
        items.sort()
        return items

    def keys(self):
        keys = odict.keys(self)
        keys.sort()
        return keys

    def __iter__(self):
        for key in self.keys():
            yield key

class OrderedDict(odict):
    """
    This class implements a dict with ordered keys.
    This means that key insertion order is respected.
    """
    def __init__(self, *args, **kw):
        self._keys = []
        odict.__init__(self, *args, **kw)

    def __setitem__(self, item, value):
        self._keys.append(item)
        odict.__setitem__(self, item, value)

    def values(self):
        return [ odict.__getitem__(self, key) for key in self._keys ]

    def items(self):
        return [ (key, odict.__getitem__(self, key)) for key in self._keys ]

    def keys(self):
        return self._keys[:]

    def __iter__(self):
        return iter(self._keys)

    def __delitem__(self, item):
        self._keys.remove(item)

class SSHProxyError(Exception):
    def __init__(self, msg):
        import log
        log.error("PROXY: "+msg)
        Exception.__init__(self, msg)

class SSHProxyAuthError(SSHProxyError):
    def __init__(self, msg):
        import log
        log.error("AUTH: "+msg)
        Exception.__init__(self, "Authentication error: "+msg)

class SSHProxyPluginError(SSHProxyError):
    def __init__(self, msg):
        import log
        log.error("PLUG: "+msg)
        Exception.__init__(self, "Plugin error: "+msg)

def istrue(s):
    istrue = False
    if s.lower().strip() in ('yes', 'true', 'on', '1'):
        istrue = True
    else:
        try:
            if int(s) != 0:
                istrue = True
        except ValueError:
            pass
    return istrue

def chanfmt(msg):
    # ensure the \n are prefixed with \r
    return msg.replace('\r\n', '\n').replace('\n', '\r\n')
        
class CommandLine(object):
    def __init__(self, args):
        if type(args) == type(''):
            self.args = self.decode(args)
        else:
            self.args = args

    def __len__(self):
        return len(self.args)

    def __getitem__(self, item):
        return self.args[item]

    def decode(self, args):
        l = [ e.strip() for e in args.split() ]
        l = [ e for e in l if e ]
        return l

    def encode(self, args=None):
        if not args:
            args = self.args
        return ' '.join(args)

SUSPEND, SWITCH, CLOSE = range(-4, -1)


def getgid(username): # Credits: TMDA
    """Return username's numerical group ID."""
    return pwd.getpwnam(username)[3]

def getgrouplist(username): # Credits: TMDA
    """Read through the group file and calculate the group access
    list for the specified user.  Return a list of group ids."""
    import grp
    # calculate the group access list
    gids = [ i[2] for i in grp.getgrall() if username in i[-1] ]
    # include the base gid
    gids.insert(0, getgid(username))
    return gids

def getuid(username): # Credits: TMDA
    """Return username's numerical user ID."""
    return pwd.getpwnam(username)[2]

def gethomedir(username): # Credits: TMDA
    """Return the home directory of username."""
    return pwd.getpwnam(username)[5]


def progress(arg=None):

    if not arg:
        print '0%\x08\x08\x08',
        sys.stdout.flush()
    elif arg[0] == 'p':
        print '25%\x08\x08\x08\x08',
        sys.stdout.flush()
    elif arg[0] == 'h':
        print '50%\x08\x08\x08\x08',
        sys.stdout.flush()
    elif arg[0] == 'x':
        print '75%\x08\x08\x08\x08',
        sys.stdout.flush()

def gen_dss_key(verbose=False):
    if verbose:
        pfunc = progress
        print "Generating DSS private key:",
        progress()
    else:
        pfunc = None

    dsskey = paramiko.DSSKey.generate(progress_func=pfunc)

    if verbose:
        print "Done."

    return dsskey



def get_dss_key_as_string(dsskey=None, password=None):
    if dsskey is None:
        dsskey = gen_dss_key()
    #if hasattr(dsskey, 'write_private_key'):
    if hasattr(paramiko.DSSKey, 'write_private_key'):
        fd = StringIO.StringIO()
        dsskey.write_private_key(fd, password)
        fd.seek(0L)
        return fd.read()
    # if paramiko <= 1.6 
    else:
        return _get_dss_key_as_string(dsskey, password)
        

def _get_dss_key_as_string(dsskey=None, password=None):
    
    # patching paramiko to get a string instead of a file
    self = dsskey
    from paramiko.dsskey import SSHException, BER, BERException, randpool, util
    from paramiko.pkey import base64

    # adapted from DSSKey.write_private_key_file()
    if self.x is None:
        raise SSHException('Not enough key information')
    keylist = [ 0, self.p, self.q, self.g, self.y, self.x ]
    try:
        b = BER()
        b.encode(keylist)
    except BERException:
        raise SSHException('Unable to create ber encoding of key')

    f = []

    # adapted from PKey._write_private_key_file()
    tag, data, password = 'DSA', str(b), password
    
    f.append('-----BEGIN %s PRIVATE KEY-----\n' % tag)
    if password is not None:
        # since we only support one cipher here, use it
        cipher_name = self._CIPHER_TABLE.keys()[0]
        cipher = self._CIPHER_TABLE[cipher_name]['cipher']
        keysize = self._CIPHER_TABLE[cipher_name]['keysize']
        blocksize = self._CIPHER_TABLE[cipher_name]['blocksize']
        mode = self._CIPHER_TABLE[cipher_name]['mode']
        salt = randpool.get_bytes(8)
        key = util.generate_key_bytes(MD5, salt, password, keysize)
        if len(data) % blocksize != 0:
            n = blocksize - len(data) % blocksize
            #data += randpool.get_bytes(n)
            # that would make more sense ^, but it confuses openssh.
            data += '\0' * n
        data = cipher.new(key, mode, salt).encrypt(data)
        f.append('Proc-Type: 4,ENCRYPTED\n')
        f.append('DEK-Info: %s,%s\n' % (cipher_name, util.hexify(salt)))
        f.append('\n')
    s = base64.encodestring(data)
    # re-wrap to 64-char lines
    s = ''.join(s.split('\n'))
    s = '\n'.join([s[i : i+64] for i in range(0, len(s), 64)])
    f.append(s)
    f.append('\n')
    f.append('-----END %s PRIVATE KEY-----\n' % tag)

    return ''.join(f)

def get_dss_key_from_string(dsskeystr=None, password=None):
    if hasattr(paramiko.DSSKey, 'write_private_key'):
        fd = StringIO.StringIO()
        fd.write(dsskeystr)
        fd.seek(0L)
        return paramiko.DSSKey(file_obj=fd, password=password)
    # if paramiko <= 1.6 
    else:
        return _get_dss_key_from_string(dsskeystr, password)

def _get_dss_key_from_string(dsskeystr=None, password=None):
    from paramiko.dsskey import DSSKey, SSHException, BER, BERException, randpool, util
    from paramiko.pkey import base64, PasswordRequiredException

    class MyDSSKey(DSSKey):
        def __init__(self): pass

    self = MyDSSKey()

    tag = 'DSA'
    lines = dsskeystr.split('\n')
    # adapted from PKey._read_private_key_file()
    while True:
        start = 0
        while (start < len(lines)) and (lines[start].strip() != '-----BEGIN ' + tag + ' PRIVATE KEY-----'):
            start += 1
        if start >= len(lines):
            raise SSHException('not a valid ' + tag + ' private key file')
        # parse any headers first
        headers = {}
        start += 1
        while start < len(lines):
            l = lines[start].split(': ')
            if len(l) == 1:
                break
            headers[l[0].lower()] = l[1].strip()
            start += 1
        # find end
        end = start
        while (lines[end].strip() != '-----END ' + tag + ' PRIVATE KEY-----') and (end < len(lines)):
            end += 1
        # if we trudged to the end of the file, just try to cope.
        try:
            data = base64.decodestring(''.join(lines[start:end]))
        except base64.binascii.Error, e:
            raise SSHException('base64 decoding error: ' + str(e))
        if not headers.has_key('proc-type'):
            # unencryped: done
            break
        # encrypted keyfile: will need a password
        if headers['proc-type'] != '4,ENCRYPTED':
            raise SSHException('Unknown private key structure "%s"' % headers['proc-type'])
        try:
            encryption_type, saltstr = headers['dek-info'].split(',')
        except:
            raise SSHException('Can\'t parse DEK-info in private key file')
        if not self._CIPHER_TABLE.has_key(encryption_type):
            raise SSHException('Unknown private key cipher "%s"' % encryption_type)
        # if no password was passed in, raise an exception pointing out that we need one
        if password is None:
            raise PasswordRequiredException('Private key file is encrypted')
        cipher = self._CIPHER_TABLE[encryption_type]['cipher']
        keysize = self._CIPHER_TABLE[encryption_type]['keysize']
        mode = self._CIPHER_TABLE[encryption_type]['mode']
        salt = util.unhexify(saltstr)
        key = util.generate_key_bytes(MD5, salt, password, keysize)
        data = cipher.new(key, mode, salt).decrypt(data)    
        break




    # adapted from DSSKey._from_private_key_file()
    # private key file contains:
    # DSAPrivateKey = { version = 0, p, q, g, y, x }
    #data = self._read_private_key_file('DSA', filename, password)
    try:
        keylist = BER(data).decode()
    except BERException, x:
        raise SSHException('Unable to parse key file: ' + str(x))
    if (type(keylist) is not list) or (len(keylist) < 6) or (keylist[0] != 0):
        raise SSHException('not a valid DSA private key file (bad ber encoding)')
    self.p = keylist[1]
    self.q = keylist[2]
    self.g = keylist[3]
    self.y = keylist[4]
    self.x = keylist[5]
    self.size = util.bit_length(self.p)

    return self


def get_site_pkey(site):
    from sshproxy.backend import Backend
    from sshproxy.cipher import decipher


    pwdb = Backend()
    try:
        site = pwdb.get_site(site)
        rlogin = site.get_tags().login
    except SSHProxyAuthError:
        rlogin, site = None, None

    if not rlogin or not site:
        # site or rlogin do not exist
        return None

    spkey = decipher(site.get_tags().get('pkey'))
    if len(spkey):
        return get_public_key(spkey)
    else:
        # no key found
        return ()


def get_public_key(pkey):
    # accept a string or a PKey object
    from sshproxy.config import get_config

    if isinstance(pkey, str):
        if len(pkey):
            pkey = get_dss_key_from_string(pkey)
        else:
            return None

    cfg = get_config('sshproxy')
    pkey_id = cfg.get('pkey_id', 'sshproxy@penguin.fr')

    return (pkey.get_name(), pkey.get_base64(), pkey_id)


