#!/usr/bin/python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Jan 25, 18:27:11 by david
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# with the version 2.1 of the License.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307  USA


# Imports from Python


# vim: shiftwidth=4 tabstop=4 expandtab

import sys, os, threading, marshal
import time, select, socket
from struct import pack, unpack

import paramiko

MSG_LOG = 1
MSG_SET = 2
MSG_GET = 3
MSG_GET_RESP = 4
MSG_CALL = 5
MSG_CALL_RESP = 6
MSG_PING = 7
MSG_PONG = 8

mtypes = ('NONE',
          'MSG_LOG',
          'MSG_SET',
          'MSG_GET',
          'MSG_GET_RESP',
          'MSG_CALL',
          'MSG_CALL_RESP',
          'MSG_PING',
          'MSG_PONG',
          )

def _type(mtype):
    if mtype < 0 or mtype >= len(mtypes):
        return '%d' % mtype
    else:
        return mtypes[mtype]

def handle_pong(msg):
    pass

def LOG(self, s):
    print '%s: %s' % (self.kind, s)

def dump(msg):
    msg = message_from_string(str(msg))
    mtype = msg.mtype
    id = msg.id
    try:
        data = msg.data # marshal.loads(msg.get_string())
    except ValueError:
        data = None
    return '<%s (%s) %s>' % (_type(mtype), id % 1000, data)

def message_from_string(s):
    msg = paramiko.Message(content=s)
    mtype = msg.get_int()
    id = msg.get_int64()
    data = msg.get_string()
    if data:
        data = marshal.loads(data)
    return IPCMessage(mtype, id=id, data=data)


class IPCTimeout(Exception):
    pass




class IPCMessage(object):
    def __init__(self, mtype, id=None, data=None):
        self.mtype = mtype
        self.id = id
        self.data = data

    @staticmethod
    def new_id():
        return int(time.time()*1000)


    def get_message(self):
        msg = paramiko.Message()
        msg.add_int(self.mtype)
        if not self.id:
            self.id = self.new_id()
        msg.add_int64(self.id)
        msg.add_string(marshal.dumps(self.data))
        return msg

    def __str__(self):
        return str(self.get_message())




class IPCChannel(threading.Thread):
    kind = 'unknown'
    def __init__(self, channel, interface=None, reconnect=None):
        threading.Thread.__init__(self)
        self.channel = channel
        self._terminated = False
        self.event = threading.Event()
        self.buffer = ''
        self._handlers = {}
        self._handlers[MSG_PING] = self.handle_ping
        self._handlers[MSG_PONG] = self.ignore_message
        self._handlers[MSG_PONG] = handle_pong
        self._handlers[MSG_LOG] = self.handle_log
        self._handlers[MSG_CALL] = self.handle_call
        self.mqueue = {}
        self.equeue = {}
        self.threads = []
        self.lock = threading.Lock()
        self.send_buffer = []
        self.reconnecting = False
        self.reconnect_handler = reconnect
        self.interface = interface(self) or IPCInterface(self)

    def ignore_message(self, msg):
        pass

    def _default_handler(self, mtype, msg):
        #LOG(self, 'default_handler %s' % dump(msg))
        if mtype == MSG_CALL_RESP:
            id = msg.id
            name, data = msg.data
            self.queue_message(msg)
            ev = self.get_event(mtype, id)
            ev.set()
            return
        LOG(self, "Unknown message type %s" % dump(msg))

    def queue_message(self, msg):
        self.lock.acquire()
        mtype = msg.mtype
        id = msg.id
        #LOG(self, 'Queueing %s' % dump(msg))
        self.mqueue[mtype, id] = msg
        self.lock.release()

    def get_event(self, mtype, id):
        if (mtype, id) in self.equeue:
            return self.equeue[mtype, id]
        ev = threading.Event()
        self.equeue[mtype, id] = ev
        return ev

    def wait_response(self, mtype, id, timeout=0.1):
        ev = self.get_event(mtype, id)
        ev.wait(timeout)
        del self.equeue[mtype, id]
        if not ev.isSet():
            raise IPCTimeout('Event not set: TIMEOUT')
        self.lock.acquire()
        response = self.mqueue.pop((mtype, id))
        self.lock.release()
        return response

    def handle_ping(self, msg):
        id = msg.id
        payload = self.interface.ping(msg.data)
        msg = IPCMessage(MSG_PONG, id=id, data=payload)
        try:
            self.send_message(msg)
            sys.stdout.flush()
        except EOFError:
            LOG(self, "EOF detected")
            self._terminated = True

    def get_size(self):
        size = self.recv(4)
        if not len(size):
            raise EOFError
        return unpack('I', size)[0]

    def handle_read(self):
        #self.lock.acquire()
        size = self.get_size()
        packet = self.recv(size)
        #self.lock.release()
        t = threading.Thread(target=self.handle_message, name='%s-read' % self.kind, kwargs={'packet':packet})
        self.threads.append(t)
        t.start()

    def handle_message(self, packet):
        msg = message_from_string(packet)
        mtype = msg.mtype
        #if mtype not in (MSG_PING, MSG_PONG):
        #    LOG(self, 'received %s' % dump(msg))
        if mtype in self._handlers:
            ret = self._handlers[mtype](msg)
            if mtype == MSG_CALL:
                id = msg.id
                msg = IPCMessage(MSG_CALL_RESP, id=id, data=('', ret))
                self.send_message(msg)
        else:
            self._default_handler(mtype, msg)

    def terminate(self):
        self._terminated = True

    def recv(self, size):
        try:
            return self.channel.recv(size)
        except:
            raise EOFError

    def send(self, s):
        while self.send_buffer and self.channel:
            self.channel.send(self.send_buffer.pop(0))

        if self.channel:
            if self.reconnecting:
                self.reconnecting.join()
                self.reconnecting = None
            try:
                return self.channel.send(s)
            except socket.error:
                pass
        if not self.reconnect_handler:
            raise EOFError
        self.send_buffer.append(s)
        if not self.reconnecting:
            t = threading.Thread(target=self.reconnect)
            self.reconnecting = t
            t.start()

    def reconnect(self):
        while not self.channel and not self._terminated:
            try:
                self.channel = self.reconnect_handler()
            except:
                self.channel = None
                time.sleep(1)


    def send_string(self, s):
        s = str(s)
        S = pack('I%ss' % len(s), len(s), s)
        return self.send(S)

    def send_message(self, msg):
        #if msg.mtype not in (MSG_PING, MSG_PONG):
        #    LOG(self, 'sending: %s' % dump(msg))
        return self.send_string(str(msg))

    def call(self, _name, *args, **kw):
        msg = IPCMessage(MSG_CALL, data=(_name, args, kw))
        msg.id = msg.new_id()
        self.get_event(MSG_CALL_RESP, msg.id)
        self.send_message(msg)
        msg = self.wait_response(MSG_CALL_RESP, msg.id, 15.0)
        _name, data = msg.data
        return data

    def ping(self, payload="ping"):
        msg = IPCMessage(MSG_PING, data=payload)
        self.send_message(msg)

    def run(self):
        ping_timeout = 5.0
        timeout = 0.2
        counter = 0.0
        self.interface.connect(self)
        while not self._terminated:
            r, w, e = select.select([self.channel], [], [], timeout)
            if self._terminated:
                break
            if r:
                try:
                    self.handle_read()
                except EOFError:
                    LOG(self, 'EOF')
                    self.channel = None
                    if not self.reconnect_handler:
                        self._terminated = True
                        self.interface.disconnect(self)
                        self.event.set()
                        return
                    if not self.reconnecting:
                        self.reconnect()
                        if self.send_buffer:
                            self.ping()
                counter = 0.0
            else:
                counter += timeout
                if counter > ping_timeout:
                    self.ping()
                    counter = 0.0

        self.interface.disconnect(self)
        if self.channel:
            self.channel.close()
        self.channel = None
        self.event.set()

    def wait_forever(self):
        try:
            self.event.wait()
        except KeyboardInterrupt:
            pass

    def log(self, level, s):
        msg = IPCMessage(MSG_LOG, data=(level, s))
        self.send_message(msg)

    def handle_log(self, msg):
        level, s = msg.data
        LOG(self, 'LOG: %s' % dump(msg))
        self.interface.log(level, s)

    def handle_call(self, msg):
        name, args, kw = msg.data
        #LOG(self, 'CALL: %s' % dump(msg))
        return self.interface.call(name, self, *args, **kw)


def parse_address(address):
    if isinstance(address, tuple):
        if not isinstance(address[0], str) or not isinstance(address[1], int):
            raise TypeError, "%s is not a valid address" % address
        stype = socket.AF_INET
    elif isinstance(address, str):
        stype = socket.AF_UNIX
        if address[0] == '/':
            if not os.path.exists(address):
                # try to create a file
                f = open(address, "w")
                os.unlink(address)
        else:
            address = '\x00%s\x00\xff' % address
    elif address is None:
        stype = socket.AF_UNIX
        address = '\x00sshproxy-control\x00\xff'
    return (address, stype)

class LevelLogger(object):
    # XXX this is ugly
    def __init__(self, ipc):
        self.ipc = ipc

    def __getattr__(self, attr):
        ipc = self.ipc
        class log(object):
            level = attr
            ipc = self.ipc
            def __init__(self, s):
                self.ipc.log(self.level, s)
        return log

class IPCBase(object):
    def __init__(self, address, handler=None):
        address, stype = parse_address(address)
        self.sock = socket.socket(stype, socket.SOCK_STREAM)
        self.sock_addr = address
        self.sock_type = stype
        self._terminated = False
        self.threads = []
        self.handler = handler or IPCInterface
        self.llog = LevelLogger(self)

    def fileno(self):
        assert self.sock, "sock is not yet open"
        return self.sock.fileno()

    def close(self):
        self.terminate()
        self.sock.close()
    
    def terminate(self):
        for chan in self.threads:
            chan.terminate()

        while self.threads:
            chan = self.threads.pop(0)
            chan.join()

    def log(self, level, s):
        return self.chan.log(level, s)


    def call(self, _func, *args, **kw):
        return self.chan.call(_func, *args, **kw)

    def ping(self, payload="ping"):
        return self.chan.ping(payload)


#############################################################################
# High level API
#############################################################################
    
class IPCInterface(object):
    call_prefix = 'func_'

    def __init__(self, chan):
        self.chan = chan

    def call(self, _name, _chan, *args, **kw):
        func = getattr(self, self.call_prefix + _name, None)
        if func:
            return func(_chan, *args, **kw)
        elif getattr(self, 'default_call_handler', None):
            return self.default_call_handler(_name, _chan, *args, **kw)

        return "%s does not exist" % _name

    def ping(self, payload):
        return payload

    def log(self, level, s):
        print "%s: %s" % (level, s)

    def connect(self, chan):
        pass

    def disconnect(self, chan):
        pass

class IPCServer(IPCBase):
    def __init__(self, address, handler=None):
        IPCBase.__init__(self, address, handler)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(self.sock_addr)
        self.sock.listen(10)

    def accept(self):
        sock, address = self.sock.accept()
        print "Accepting new client", address
        chan = IPCChannel(sock, interface=self.handler)
        chan.kind = 'server'
        chan.setName('S'+str(address))
        self.threads.append(chan)
        chan.start()
        return chan


class IPCClient(IPCBase):
    def __init__(self, address, handler=None):
        IPCBase.__init__(self, address, handler)
        self.sock = self.connect()
        self.chan = IPCChannel(self.sock, interface=self.handler,
                                            reconnect=self.connect)
        self.chan.setName('Client-handler')
        self.chan.kind = 'client'
        self.threads.append(self.chan)
        self.chan.start()

    def connect(self):
        sock = socket.socket(self.sock_type, socket.SOCK_STREAM)
        sock.connect(self.sock_addr)
        return sock
        




