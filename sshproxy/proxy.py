#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Oct 26, 02:26:10 by david
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


import sys, os, select, socket, fcntl, time, signal
import threading

import paramiko
from paramiko.transport import SSHException, DEBUG
from paramiko import AuthenticationException

from registry import Registry
import cipher, util, log
from util import chanfmt
from message import Message
from acl import ACLDB, ACLTags, ProxyNamespace



class Proxy(Registry):
    def __reginit__(self, proxy_client):
        self.client = proxy_client.chan
        self.client.settimeout(1.0)
        self.tags = {
                'client': proxy_client.pwdb.get_client_tags(),
                'site': proxy_client.pwdb.get_site_tags(),
                'proxy': ProxyNamespace(),
                }
        self.proxy_client = proxy_client
        self.msg = self.proxy_client.msg
        self.name = '%s@%s' % (self.tags['site'].login,
                               self.tags['site'].name)
        now = time.ctime()
        log.info("Connecting to %s by %s on %s" %
                    (self.name, proxy_client.pwdb.get_client().username, now))
        try:
            self.transport = paramiko.Transport((self.tags['site'].ip_address,
                                                 int(self.tags['site'].port)))
            # XXX: debugging code follows
            #self.transport.set_hexdump(1)

            self.connect()

            self.chan = self.transport.open_session()
            self.chan.settimeout(1.0)
            self.x11chan = None
            self.x11chanc = None
            if hasattr(self.proxy_client, 'x11'):
                x = self.proxy_client.x11
                self.transport.client_object = self
                self.x11req = self.chan.request_x11(
                                                x.want_reply,
                                                x.single_connection,
                                                x.x11_auth_proto,
                                                x.x11_auth_cookie,
                                                x.x11_screen_number)
            self.open_connection()

        except Exception, e:
            log.exception("Unable to set up SSH connection to server")
            try:
                self.transport.close()
                del self.transport
            except:
                pass
            return
        now = time.ctime()
        log.info("Connected to %s by %s on %s\n" %
                                    (self.name, proxy_client.username, now))

############################################################################

    def check_x11_channel_request(self, chanid, origin_addr, origin_port):
        from paramiko import OPEN_SUCCEEDED
        from paramiko import OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

        self.x11chanc = self.proxy_client.transport.open_x11_channel(
                                                (origin_addr, origin_port))
        if self.x11chanc:
            self.x11chanc.settimeout(1.0)
            return OPEN_SUCCEEDED
        else:
            return OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def new_x11_channel(self, chan):
        self.x11chan = chan
        self.x11chan.settimeout(1.0)

    def kill(self):
        self.transport.close()

    def handle_message(self):
        msg = self.msg.read()

        parts = msg.split(':', 1)
        if hasattr(self, 'msg_%s' % parts[0]):
            if len(parts) > 1:
                message = parts[1]
            else:
                message = ''
            return getattr(self, 'msg_%s' % parts[0])(message)

    def msg_alert(self, msg):
        self.msg_announce('\007%s' % msg)

    def msg_announce(self, msg):
        self.client.send(chanfmt(msg))

    def msg_kill(self, msg):
        if not msg:
            msg = ("\n\nOn administrative request, "
                   "your session is immediately closed.\n\n")
        self.msg_alert(msg)
        self.proxy_client.exit_status = 254
        self.kill()

############################################################################

    def connect(self):
        hostkey = self.tags['proxy'].get('hostkey', None) or None
        transport = self.transport

        transport.start_client()

        if hostkey is not None:
            transport._preferred_keys = [ hostkey.get_name() ]

            key = transport.get_remote_server_key()
            if (key.get_name() != hostkey.get_name() 
                                                or str(key) != str(hostkey)):
                log.error('Bad host key from server (%s).' % self.name)
                raise AuthenticationError('Bad host key from server (%s).'
                                                                % self.name)
            log.info('Server host key verified (%s) for %s' % (key.get_name(), 
                                                           self.name))

        pkey = cipher.decipher(self.tags['site'].get('pkey', ''))
        password = cipher.decipher(self.tags['site'].get('password', ''))
        if pkey:
            pkey = util.get_dss_key_from_string(pkey)
            try:
                transport.auth_publickey(self.tags['site'].login, pkey)
                return True
            except AuthenticationException:
                log.warning('PKey for %s was not accepted' % self.name)

        if password:
            try:
                transport.auth_password(self.tags['site'].login, password)
                return True
            except AuthenticationException:
                log.error('Password for %s is not valid' % self.name)
                raise

        raise AuthenticationException('No valid authentication token for %s'
                                                                % self.name)
                
    def rx_tx(self, x, name, rx, tx, rfds, sz=4096):
        if len(x) == 0 or rx.closed:
            if rx.closed:
                log.info("Connection closed by %s" % name)
                return False
            elif rx.eof_received:
                # XXX: logging is commented out for half-close
                # because select always returns with rx.recv() == '' (EOF)
                # and this makes too much verbose logs
                #log.info("Connection half-closed by %s" % name)
                rx.shutdown_read()
                tx.shutdown_write()
                if name == 'client' and rx in rfds:
                    del rfds[rfds.index(rx)]
                elif name == 'server':
                    rx.shutdown_write()
            return True
        else:
            try:
                self.chan_send(tx, x)
            except ValueError:
                tx.shutdown_write()
                rx.shutdown_read()
                if name == 'client' and rx in rfds:
                    del rfds[rfds.index(rx)]
                elif name == 'server':
                    rx.shutdown_write()
            return True

    def server_to_client(self, rx, tx, rfds, sz=4096):
        x = rx.recv(sz)
        return self.rx_tx(x, 'server', rx, tx, rfds, sz=4096)

    def client_to_server(self, rx, tx, rfds, sz=4096):
        x = rx.recv(sz)
        return self.rx_tx(x, 'client', rx, tx, rfds, sz=4096)

    def chan_send(self, chan, s):
        SZ = sz = len(s)
        while sz:
            sent = chan.send(s)
            if sent:
                s = s[sent:]
                sz = sz - sent
            else:
                # this is a close on chan
                raise ValueError


    def __del__(self):
        if not hasattr(self, 'chan'):
            return
        try:
            self.chan.close()
        except ValueError:
            pass
            

class ProxyScp(Proxy):
    _class_id = 'ProxyScp'
    def open_connection(self):
        proxy = ProxyNamespace()
        log.info('Executing: scp %s %s' % (proxy['scp_args'], 
                                           proxy['scp_path']))
        self.chan.exec_command('scp %s %s' % (proxy['scp_args'], 
                                              proxy['scp_path']))

    def loop(self):
        if not hasattr(self, 'transport'):
            raise AuthenticationException('Could not authenticate %s'
                                                                % self.name)
        t = self.transport
        chan = self.chan
        client = self.client
        try:
            size = 4096
            while t.is_active() and client.active and not chan.eof_received:
                r, w, e = select.select([self.msg, chan, client],
                                        [chan, client], [], 0.2)

                if chan in r:
                    if client.out_window_size > 0:
                        x = chan.recv(size)
                        client.send(x)
                    if len(x) == 0 or chan.closed or chan.eof_received:
                        log.info("Connection closed by server")
                        break
                if client in r:
                    if chan.out_window_size > 0:
                        x = client.recv(size)
                        chan.send(x)
                    if len(x) == 0:
                        self.chan.shutdown_write()
                        if client.closed:
                            log.info("Connection closed by client")
                            break
                        continue
                if self.msg in r:
                    self.handle_message()

        finally:
            self.chan.shutdown_write()
            exit_status = chan.recv_exit_status()
            self.proxy_client.exit_status = exit_status
            now = time.ctime()
            log.info("Disconnected from %s by %s on %s" %
                                    (self.name, self.tags['site'].login, now))

        self.chan.close()
        return util.CLOSE

ProxyScp.register()


class ProxyCmd(Proxy):
    _class_id = 'ProxyCmd'
    def open_connection(self):
        proxy = ProxyNamespace()
        log.info('Executing: %s' % (proxy['cmdline']))
        if hasattr(self.proxy_client, 'term'):
            self.chan.get_pty(self.proxy_client.term,
                              self.proxy_client.width,
                              self.proxy_client.height)
        self.chan.exec_command(proxy['cmdline'])

    def loop(self):
        if not hasattr(self, 'transport'):
            raise AuthenticationException('Could not authenticate %s'
                                                                % self.name)
        t = self.transport
        chan = self.chan
        client = self.client
        try:
            listen_fd = [self.msg, chan, client]

            size = 40960
            while t.is_active():
                try:
                    r, w, e = select.select(listen_fd, [], [], 2)

                except KeyboardInterrupt:
                    log.warning('ERROR ProxyCmd: select.select() was interrupted')
                    continue
                except select.error:
                    # this happens when a signal was caught
                    log.warning('ERROR ProxyCmd: select.select() failed')
                    continue

                if chan in r:
                    if not self.server_to_client(chan, client,
                                                        listen_fd, size):
                        break

                if client in r:
                    if not self.client_to_server(client, chan,
                                                        listen_fd, size):
                        break

                if self.msg in r:
                    self.handle_message()
        finally:
            self.chan.shutdown_write()
            exit_status = chan.recv_exit_status()
            self.proxy_client.exit_status = exit_status
            now = time.ctime()
            log.info("Disconnected from %s by %s on %s" %
                                    (self.name, self.tags['site'].login, now))

        #self.chan.close()
        return util.CLOSE

ProxyCmd.register()


class _ProxyShell(Proxy):
    _class_id = '_ProxyShell'
    def open_connection(self):
        if hasattr(self.proxy_client, 'term'):
            self.chan.get_pty(self.proxy_client.term,
                              self.proxy_client.width,
                              self.proxy_client.height)
        self.chan.invoke_shell()

    def loop(self):
        if not hasattr(self, 'transport'):
            raise AuthenticationException('Could not authenticate %s'
                                                                % self.name)
        t = self.transport
        chan = self.chan
        client = self.client
        try:
            listen_fd = [self.msg, chan, client]
            while t.is_active():
                if self.x11chan and self.x11chan not in listen_fd:
                    # if there is an x11 channel established,
                    # add it to the listening fds
                    listen_fd.append(self.x11chan)
                    listen_fd.append(self.x11chanc)

                try:
                    r, w, e = select.select(listen_fd, [], [], 2)
                except KeyboardInterrupt:
                    log.warning('ERROR: select.select() was interrupted')
                    continue
                except select.error:
                    # this happens when a signal was caught
                    log.warning('ERROR: select.select() failed')
                    continue

                if chan in r:
                    if not self.server_to_client(chan, client,
                                                            listen_fd):
                        break

                if client in r:
                    if not self.client_to_server(client, chan,
                                                            listen_fd):
                        break

                if self.msg in r:
                    self.handle_message()

                try:
                    # TODO: this block need some cleanup
                    # TODO: implement this in ProxyCmd too
                    if self.x11chan in r:
                        if not self.server_to_client(self.x11chan,
                                                     self.x11chanc,
                                                     listen_fd):
                            if self.x11chanc in listen_fd:
                                del listen_fd[listen_fd.index(self.x11chanc)]
                                #listen_fd.remove(listen_fd.index(self.x11chanc))
                            if self.x11chan in listen_fd:
                                del listen_fd[listen_fd.index(self.x11chan)]
                            self.x11chan = self.x11chanc = None

                    if self.x11chanc in r:
                        if not self.server_to_client(self.x11chanc,
                                                     self.x11chan,
                                                     listen_fd):
                            if self.x11chanc in listen_fd:
                                del listen_fd[listen_fd.index(self.x11chanc)]
                            if self.x11chan in listen_fd:
                                del listen_fd[listen_fd.index(self.x11chan)]
                            self.x11chan = self.x11chanc = None
                except Exception, msg:
                    import traceback, sys
                    print traceback.format_exception(*sys.exc_info())
                    raise

    
        finally:
            self.chan.shutdown_write()
            exit_status = chan.recv_exit_status()
            self.proxy_client.exit_status = exit_status
            now = time.ctime()
            log.info("Disconnected from %s by %s on %s" %
                                    (self.name, self.tags['site'].login, now))

        return util.CLOSE
            

_ProxyShell.register()

#########################################################################
from select import POLLIN, POLLPRI, POLLOUT, POLLERR, POLLHUP, POLLNVAL
import select
POLLREAD = POLLIN | POLLPRI | POLLHUP | POLLERR | POLLNVAL
POLLWRITE = POLLOUT | POLLHUP | POLLERR | POLLNVAL

class ProxyCommon(Registry):
    _event_map = {
            POLLIN:   0,
            POLLPRI:  1,
            POLLOUT:  2,
            POLLERR:  3,
            POLLHUP:  4,
            POLLNVAL: 5,
            }

    default_bufsize = 4096
    poll_timeout = None
    min_chan = 1

    def __reginit__(self, client_chan, site_chan, msg_chan):
        from server import Server
        self.server = Server()
        self.client_chan = client_chan
        self.site_chan = site_chan
        self.msg_chan = msg_chan
        self.bufsize = {}
        self.listeners = {}
        self.x11c_channels = {}
        self.x11s_channels = {}
        self.poller = select.poll()
        self.poll_register(client_chan, POLLREAD, self.copy_client, site_chan)
        self.poll_register(site_chan, POLLREAD, self.copy_site, client_chan)
        self.poll_register(msg_chan, POLLREAD, self.handle_message)

        self.setup_x11()

        self.open_connection()

        client_chan.set_name('client_chan')
        site_chan.set_name('site_chan')

    def open_connection(self):
        raise NotImplemented

    ########## X11 channels ##############################################
    def setup_x11(self):
        if hasattr(self.server, 'x11'):
            x = self.server.x11
            self.site_chan.transport.client_object = self
            self.x11req = self.site_chan.request_x11(x.want_reply,
                                                     x.single_connection,
                                                     x.x11_auth_proto,
                                                     x.x11_auth_cookie,
                                                     x.x11_screen_number)
            msg = Message()
            self.watch_x11 = msg.get_child_fd()
            self.signal_x11 = msg.get_parent_fd()
            # this fd is registered to unblock poll() when a new x11
            # channel is available
            self.poll_register(self.watch_x11, POLLREAD, self.eat_byte)
            self.min_chan = 2

    def eat_byte(self, chan, event):
        self.watch_x11.read(1)

    def check_x11_channel_request(self, chanid, origin_addr, origin_port):
        from paramiko import OPEN_SUCCEEDED
        from paramiko import OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

        log.debug("Channel x11 #%d from %s:%s" % (chanid, origin_addr,
                                                          origin_port))
        x11_client = self.client_chan.transport.open_x11_channel(
                                                (origin_addr, origin_port))
        if x11_client:
            x11_client.settimeout(0.0)
            self.x11c_channels[chanid] = x11_client
            return OPEN_SUCCEEDED
        else:
            return OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def new_x11_channel(self, chan):
        chanid = chan.get_id()
        chan.settimeout(0.0)
        self.x11s_channels[chanid] = chan
        self.poll_register(chan, POLLREAD, self.copy_x11_site,
                                 self.x11c_channels[chanid])
        self.poll_register(self.x11c_channels[chanid], POLLREAD,
                                 self.copy_x11_client, chan)
        # let's signal there is a new channel available
        self.signal_x11.write('k')

    def close_x11_channel_pair(self, chan):
        chanid = None
        if chan in self.x11s_channels.values():
            chanid = chan.get_id()
        else:
            for id, ch in self.x11c_channels.items():
                if chan is ch:
                    chanid = id
                    break

        if chanid is None:
            return # XXX: raise exception ?

        self.poll_unregister(self.x11s_channels[chanid])
        self.poll_unregister(self.x11c_channels[chanid])
        # XXX: actually do something to close, or at least to verify if closed
        del self.x11s_channels[chanid]
        del self.x11c_channels[chanid]

    ########## end X11 channels ##########################################

    def poll(self):
        try:
            return self.poller.poll(self.poll_timeout)
        except:
            pass

    def poll_register(self, chan, event_mask, callback, *args):
        fd = chan.fileno()
        self.poller.register(fd, event_mask)
        self.listeners[fd] = [chan, callback] + list(args)

    def poll_unregister(self, chan):
        fd = chan.fileno()
        if fd in self.listeners:
            self.poller.unregister(fd)
            del self.listeners[fd]


    def loop(self):
        while len(self.listeners) > self.min_chan: # msg is the last one
            for channels in self.poll():
                try:
                    fd, event = channels
                    self.callback(fd, event)
                except TypeError, msg:
                    raise

        log.debug("Ending proxying")
        return util.CLOSE

    def callback(self, fd, event):
        chan = self.listeners[fd][0]
        func = self.listeners[fd][1]
        args = self.listeners[fd][2:]
        all_args = [chan, event] + list(args)
        func(*all_args)

    def handle_message(self, msg, event):
        # TODO
        msg.write('OK')
        return None

    def copy(self, source, event, destination):
        # TODO: handle event
        # read available data
        data = source.recv(self.bufsize.get(source, self.default_bufsize))
        size = len(data)
        if size == 0:
            # channel closed
            log.debug("Channel %s read closed" % source.get_name())
            if source.closed:
                self.poll_unregister(source)
            destination.shutdown_write()
            source.shutdown_read()
            if source.get_name() == 'site_chan':
                source.shutdown_write()
                destination.shutdown_read()
                destination.close()
                source.close()
                self.poll_unregister(destination)
            return 'source closed'
        
        # write data
        sent = destination.send(data)
        while sent and sent < size:
            data = data[sent:]
            size = size - sent
            sent = destination.send(data)
        if sent == 0:
            # channel closed
            log.debug("Channel %s write closed" % source.get_name())
            self.poll_unregister(source)
            source.shutdown_read()
            destination.shutdown_write()
            return 'destination closed'

        return None

    def x11_copy(self, source, event, destination):
        result = self.copy(source, event, destination)
        if result is not None:
            if result == 'source closed':
                self.close_x11_channel_pair(source)
            elif result == 'destination closed':
                self.close_x11_channel_pair(destination)

        return result

    # define default copy functions
    copy_client = copy
    copy_site = copy
    copy_x11_client = x11_copy
    copy_x11_site = x11_copy

class ProxyShell(ProxyCommon):
    _class_id = 'ProxyShell'

    def open_connection(self):
        server = self.server
        if hasattr(server, 'term'):
            self.site_chan.get_pty(server.term,
                                   server.width,
                                   server.height)
        self.site_chan.invoke_shell()


ProxyShell.register()
