#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Nov 20, 01:51:33 by david
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


from select import POLLIN, POLLPRI, POLLOUT, POLLERR, POLLHUP, POLLNVAL
import os, select, socket

from paramiko import Channel
from paramiko import OPEN_SUCCEEDED
from paramiko import OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED


from registry import Registry
import util, log
from ipc import IPC
from acl import ProxyNamespace

POLLREAD = POLLIN | POLLPRI | POLLHUP | POLLERR | POLLNVAL
#unused: POLLWRITE = POLLOUT | POLLHUP | POLLERR | POLLNVAL

class Proxy(Registry):
    # TODO: keepalive, key renegotiation, connection timeout
    default_bufsize = 4096
    poll_timeout = None
    min_chan = 1

    def __reginit__(self, client_chan, site_chan, ipc_chan):
        from server import Server
        self.server = Server()
        self.client_chan = client_chan
        self.site_chan = site_chan
        self.ipc_chan = ipc_chan
        self.bufsize = {}
        self.listeners = {}
        self.poller = select.poll()

        client_chan.set_name('client_chan')
        site_chan.set_name('site_chan')
        self.poll_register(client_chan, POLLREAD, self.copy_client, site_chan)
        self.poll_register(site_chan, POLLREAD, self.copy_site, client_chan)
        self.poll_register(ipc_chan, POLLREAD, self.handle_message)

        self.open_connection()
        #self.client_chan.transport.set_hexdump(True)

    def __del__(self):
        # derive this method for extra cleanup
        pass

    def open_connection(self):
        raise NotImplemented

    ########## Messaging with parent daemon ##############################

    def kill(self):
        self.site_chan.transport.close()

    def handle_message(self, source, event):
        want_reply, msg = self.ipc_chan.recv_message()

        parts = msg.split(':', 1)
        if hasattr(self, 'ipc_%s' % parts[0]):
            if len(parts) > 1:
                message = parts[1]
            else:
                message = ''
            return getattr(self, 'ipc_%s' % parts[0])(message)

    def ipc_alert(self, msg):
        self.ipc_announce('\007%s' % msg)

    def ipc_announce(self, msg):
        self.client_chan.send(util.chanfmt(msg))

    def ipc_kill(self, msg):
        if not msg:
            msg = ("\n\nOn administrative request, "
                   "your session is immediately closed.\n\n")
        self.ipc_alert(msg)
        self.kill()
        self.client_chan.send_exit_status(254)

    ########## End messaging with parent daemon ##########################

    ########## File descriptor related methods ###########################

    def poll(self):
        return self.poller.poll(self.poll_timeout)

    def poll_register(self, chan, event_mask, callback, *args):
        if isinstance(chan, int):
            fd = chan
        else:
            fd = chan.fileno()
        try:
            log.debug("REGISTER chan #%d (%s)" % (fd, chan.get_name()))
        except:
            log.debug("REGISTER chan #%d" % (fd))
        if fd not in self.listeners:
            self.poller.register(fd, event_mask)
            self.listeners[fd] = [chan, callback] + list(args)
            return True
        else:
            return False

    def poll_unregister(self, chan):
        if isinstance(chan, int):
            fd = chan
        else:
            fd = chan.fileno()
        try:
            log.debug("UNREGISTER chan #%d [%d/%d] (%s)" % (fd,
                        self.min_chan, len(self.listeners), chan.get_name()))
        except:
            log.debug("UNREGISTER chan #%d [%d/%d]" % (fd, self.min_chan, 
                                                        len(self.listeners)))
        if fd in self.listeners:
            self.poller.unregister(fd)
            self.listeners[fd] = None
            del self.listeners[fd]
            return True
        else:
            return False

    def recv_exit_status(self):
        return self.site_chan.recv_exit_status()

    def loop(self):
        log.debug("Starting proxying")
        try:
            while len(self.listeners) > self.min_chan: # ipc is the last one
                for channels in self.poll():
                    try:
                        fd, event = channels
                        self.callback(fd, event)
                    except TypeError, msg:
                        raise

            exit_status = self.recv_exit_status()
            self.poll_unregister(self.ipc_chan)
            #self.ipc_chan.close()
            log.debug("Ending proxying (%s)" % exit_status)
            return util.CLOSE, exit_status
        except util.SSHProxyError, m:
            return util.CLOSE, -42
        except Exception, m:
            for c in self.listeners:
                if not isinstance(c, Channel):
                    continue
                try:
                    self.poll_unregister(c)
                    c.close()
                except:
                    pass
            log.exception("An exception occured %s" % repr(m))
            raise

    def callback(self, fd, event):
        if fd not in self.listeners:
            log.warning("Data from unknown fd #%d" % fd)
            return
        chan = self.listeners[fd][0]
        func = self.listeners[fd][1]
        args = self.listeners[fd][2:]
        all_args = [chan, event] + list(args)
        return func(*all_args)

    def recv_data(self, source, name):
        return source.recv(self.bufsize.get(source, self.default_bufsize))

    def send_data(self, destination, data, size, name):
        i = 5
        while i:
            try:
                sent = destination.send(data)
                break
            except socket.timeout:
                sent = 0
                i -= 1
                if not i:
                    log.debug('Window is not set for %s' % name)
            except Exception, m:
                log.debug('unknown exception: %s' % m)
        while sent and sent < size:
            data = data[sent:]
            size = size - sent
            i = 5
            while i:
                try:
                    sent = destination.send(data)
                    break
                except socket.timeout:
                    pass
                    i -= 1
                    if not i:
                        log.debug('Window is not growing for %s' % name)
                except Exception, m:
                    log.debug('unknown exception: %s' % m)
        return sent

    def channel_copy(self, source, event, destination,
                                  recv_data=recv_data, send_data=send_data):
        sname = source.name
        dname = destination.name

        if source.recv_stderr_ready():
            destination.send_stderr(source.recv_stderr(4096))
            return

        if ((source.eof_received and not source.recv_ready())
                                        or destination.closed):
            source.shutdown_read()
            destination.shutdown_write()
            if source.closed:
                destination.shutdown_read()
                self.poll_unregister(destination)
                self.poll_unregister(source)
            return

        data = recv_data(self, source, sname)
        size = len(data)

        if size == 0 and not source.transport.active:
            raise util.SSHProxyError('Source %s is dead, closing connection' % sname)
            return

        sent = send_data(self, destination, data, size, dname)

        if sent == 0 and not destination.transport.active:
            raise util.SSHProxyError('Destination %s is dead, closing connection' % dname)

    # define default copy functions
    copy_client = channel_copy
    copy_site = channel_copy




class ProxyScp(Proxy):
    _class_id = 'ProxyScp'

    def open_connection(self):
        proxy = ProxyNamespace()
        log.info('Executing: scp %s %s' % (proxy['scp_args'], 
                                           proxy['scp_path']))
        self.site_chan.exec_command('scp %s %s' % (proxy['scp_args'], 
                                                   proxy['scp_path']))

ProxyScp.register()

class ProxySession(Proxy):
    """
    Implements X11 forwarding, local and remote port forwarding.
    """
    def open_connection(self):
        self.setup_watcher()
        self.setup_x11()
        self.setup_remote_port_forwarding()
        self.setup_local_port_forwarding()
        self.new_channel_handlers = []

    def __del__(self):
        if hasattr(self, 'watcher'):
            os.close(self.watcher)
            #self.watcher.close()
        if hasattr(self, 'signal'):
            os.close(self.signal)
            #self.signal.close()

    def setup_watcher(self):
        if not hasattr(self, 'watcher'):
            self.watcher, self.signal = os.pipe()

    def handle_signal(self, chan, event):
        x = os.read(self.watcher, 1)
        #x = self.watcher.read(1)
        if len(self.new_channel_handlers):
            new_channel_handler, transport, chan = self.new_channel_handlers.pop(0)
            newchan = transport.accept(1.0)
            if newchan:
                new_channel_handler(chan, newchan)
            else:
                self.new_channel_handlers.insert(0, (new_channel_handler,
                                                        transport, chan))
                os.write(self.signal, x)
                #self.signal.write(x)


    ########## Reverse Port Forwarding ###################################
    def setup_remote_port_forwarding(self):
        if self.server.check_remote_port_forwarding():
            if not hasattr(self.site_chan.transport,
                                        'set_remote_forwarding_handler'):
                self.client_chan.send("Remote port forwarding unavailable\r\n")
                return
            self.site_chan.transport.set_remote_forwarding_handler(
                                    self.check_remote_forward_channel_request)
            ip = self.server.tcpip_forward_ip
            port = self.server.tcpip_forward_port
            self.setup_watcher()
            try:
                ret = self.site_chan.transport.global_request('tcpip-forward',
                                                        (ip, int(port)), True)
                if not ret:
                    raise Exception('Denied')
            except Exception, m:
                log.debug('An exception occured while opening a pfwd chan: %s' %
                                                                            m)
                self.client_chan.send('Port Forwarding to %s:%s forbidden\n' %
                                                                (ip, port))
                return

            # this fd is registered to unblock poll() when a new
            # channel is available
            if self.poll_register(self.watcher, POLLREAD, self.handle_signal):
                self.min_chan += 1

    def check_remote_forward_channel_request(self, chanid, origin, destination):
        log.debug("Channel rfw #%d from %s:%s to %s:%s" % (chanid,
                                            origin[0], origin[1],
                                            destination[0], destination[1]))
        try:
            fwd_client = self.client_chan.transport.open_channel(
                                                        'forwarded-tcpip',
                                                        origin, destination)
        except Exception, m:
            log.exception("Exception while connecting remote forwarding: %s"
                                                                        % m)
            fwd_client = None

        if fwd_client:
            fwd_client.set_name("rfwc%s" % fwd_client.get_id())
            fwd_client.settimeout(0.1)
            self.new_channel_handlers.append((self.new_remote_forward_channel,
                                                self.site_chan.transport,
                                                fwd_client))
            os.write(self.signal, 'r')
            #self.signal.write('r')
            return OPEN_SUCCEEDED
        else:
            return OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def new_remote_forward_channel(self, chan, newchan):
        chanid = newchan.get_id()
        newchan.settimeout(0.1)
        newchan.set_name("rfws%s" % chanid)
        if chan.active and newchan.active:
            if not chan.closed:
                self.poll_register(chan, POLLREAD, self.copy_rfw_site, newchan)
            if not newchan.closed:
                self.poll_register(newchan, POLLREAD, self.copy_rfw_client, chan)

    copy_rfw_client = Proxy.channel_copy
    copy_rfw_site = Proxy.channel_copy

    ########## /Reverse Port Forwarding ##################################

    ########## Port Forwarding ###########################################
    def setup_local_port_forwarding(self):
        self.server.setup_forward_handler(self.check_local_forward_channel)

        self.setup_watcher()
        # this fd is registered to unblock poll() when a new
        # channel is available
        if self.poll_register(self.watcher, POLLREAD, self.handle_signal):
            self.min_chan += 1
        
    def check_local_forward_channel(self, chanid, origin, destination):
        log.debug("Channel lfw #%d from %s:%s to %s:%s" % (chanid,
                                            origin[0], origin[1],
                                            destination[0], destination[1]))

        if not self.server.check_direct_tcpip_acl(chanid, origin, destination):
            return OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

        try:
            fwd_client = self.site_chan.transport.open_channel(
                                                        'direct-tcpip',
                                                        origin, destination)
        except Exception, m:
            log.exception("Exception while connecting local forwarding: %s"
                                                                        % m)
            fwd_client = None

        if fwd_client:
            fwd_client.set_name("lfwc%s" % fwd_client.get_id())
            fwd_client.settimeout(0.1)
            self.new_channel_handlers.append((self.new_local_forward_channel,
                                                self.client_chan.transport,
                                                fwd_client))
            os.write(self.signal, 'l')
            #self.signal.write('l')
            return OPEN_SUCCEEDED
        else:
            return OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def new_local_forward_channel(self, chan, newchan):
        chanid = newchan.get_id()
        newchan.settimeout(0.1)
        newchan.set_name("rfws%s" % chanid)
        if chan.active and newchan.active:
            if not chan.closed:
                self.poll_register(chan, POLLREAD, self.copy_lfw_site, newchan)
            if not newchan.closed:
                self.poll_register(newchan, POLLREAD, self.copy_lfw_client, chan)

    copy_lfw_client = Proxy.channel_copy
    copy_lfw_site = Proxy.channel_copy

    ########## /Port Forwarding ##########################################

    ########## X11 channels ##############################################
    def setup_x11(self):
        if self.server.check_x11_acl():
            x = self.server.x11
            self.site_chan.transport.client_object = self
            self.site_chan.transport.set_x11_handler(
                                        self.check_x11_channel_request)
            self.x11req = self.site_chan.request_x11(True,
                                                     x.single_connection,
                                                     x.x11_auth_proto,
                                                     x.x11_auth_cookie,
                                                     x.x11_screen_number)
            self.setup_watcher()
            # this fd is registered to unblock poll() when a new
            # channel is available
            if self.poll_register(self.watcher, POLLREAD, self.handle_signal):
                self.min_chan += 1

    def check_x11_channel_request(self, chanid, origin_addr_port):
        origin_addr, origin_port = origin_addr_port
        log.debug("Channel x11 #%d from %s:%s" % (chanid, origin_addr,
                                                          origin_port))
        x11_client = self.client_chan.transport.open_x11_channel(
                                                (origin_addr, origin_port))
        if x11_client:
            x11_client.set_name("x11c%s" % x11_client.get_id())
            x11_client.settimeout(0.0)
            self.new_channel_handlers.append((self.new_x11_channel,
                                                self.site_chan.transport,
                                                x11_client))
            os.write(self.signal, 'x')
            #self.signal.write('x')
            return OPEN_SUCCEEDED
        else:
            return OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def new_x11_channel(self, chan, newchan):
        chanid = newchan.get_id()
        newchan.settimeout(0.1)
        newchan.set_name("x11s%s" % chanid)
        if chan.active and newchan.active:
            if not chan.closed:
                self.poll_register(chan, POLLREAD, self.copy_x11_site, newchan)
            if not newchan.closed:
                self.poll_register(newchan, POLLREAD, self.copy_x11_client, chan)

    copy_x11_client = Proxy.channel_copy
    copy_x11_site = Proxy.channel_copy

    ########## end X11 channels ##########################################


class ProxyCmd(ProxySession):
    _class_id = 'ProxyCmd'

    def open_connection(self):
        ProxySession.open_connection(self)

        proxy = ProxyNamespace()
        server = self.server
        log.info('Executing: %s' % (proxy['cmdline']))
        if hasattr(server, 'term'):
            self.site_chan.get_pty(server.term,
                                   server.width,
                                   server.height)
        self.site_chan.exec_command(proxy['cmdline'])


ProxyCmd.register()



class ProxyShell(ProxySession):
    _class_id = 'ProxyShell'

    def open_connection(self):
        ProxySession.open_connection(self)
        log.info('Opening shell session on %s' %
                        (self.site_chan.transport.getpeername(),))

        server = self.server
        if hasattr(server, 'term'):
            self.site_chan.get_pty(server.term,
                                   server.width,
                                   server.height)
        self.site_chan.invoke_shell()


ProxyShell.register()
