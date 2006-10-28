#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Oct 29, 01:42:08 by david
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
import select

from paramiko import OPEN_SUCCEEDED
from paramiko import OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED


from registry import Registry
import util, log
from message import Message
from acl import ProxyNamespace

POLLREAD = POLLIN | POLLPRI | POLLHUP | POLLERR | POLLNVAL
#unused: POLLWRITE = POLLOUT | POLLHUP | POLLERR | POLLNVAL

class Proxy(Registry):
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

        client_chan.set_name('client_chan')
        site_chan.set_name('site_chan')
        self.poll_register(client_chan, POLLREAD, self.copy_client, site_chan)
        self.poll_register(site_chan, POLLREAD, self.copy_site, client_chan)
        self.poll_register(msg_chan, POLLREAD, self.handle_message)

        self.setup_x11()

        self.open_connection()

    def open_connection(self):
        raise NotImplemented

    ########## X11 channels ##############################################
    def setup_x11(self):
        if self.server.check_x11_acl():
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
            self.min_chan += 1

    def eat_byte(self, chan, event):
        self.watch_x11.read(1)

    def check_x11_channel_request(self, chanid, origin_addr, origin_port):
        log.debug("Channel x11 #%d from %s:%s" % (chanid, origin_addr,
                                                          origin_port))
        x11_client = self.client_chan.transport.open_x11_channel(
                                                (origin_addr, origin_port))
        if x11_client:
            x11_client.set_name("x11c%s" % x11_client.get_id())
            x11_client.settimeout(0.0)
            self.x11c_channels[chanid] = x11_client
            return OPEN_SUCCEEDED
        else:
            return OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def new_x11_channel(self, chan):
        chanid = chan.get_id()
        chan.settimeout(0.0)
        self.x11s_channels[chanid] = chan
        chan.set_name("x11s%s" % chanid)
        self.poll_register(chan, POLLREAD, self.copy_x11_site,
                                 self.x11c_channels[chanid])
        self.poll_register(self.x11c_channels[chanid], POLLREAD,
                                 self.copy_x11_client, chan)
        # let's signal there is a new channel available
        self.signal_x11.write('x')

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
            # this should not happen
            return # XXX: raise exception ?

        self.poll_unregister(self.x11s_channels[chanid])
        self.poll_unregister(self.x11c_channels[chanid])
        del self.x11s_channels[chanid]
        del self.x11c_channels[chanid]

    ########## end X11 channels ##########################################

    ########## Messaging with parent daemon ##############################

    def kill(self):
        self.site_chan.transport.close()

    def handle_message(self, source, event):
        msg = self.msg_chan.read()

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
        self.client_chan.send(util.chanfmt(msg))

    def msg_kill(self, msg):
        if not msg:
            msg = ("\n\nOn administrative request, "
                   "your session is immediately closed.\n\n")
        self.msg_alert(msg)
        self.kill()
        self.client_chan.send_exit_status(254)

    ########## End messaging with parent daemon ##########################

    ########## File descriptor related methods ###########################

    def poll(self):
        try:
            return self.poller.poll(self.poll_timeout)
        except:
            pass

    def poll_register(self, chan, event_mask, callback, *args):
        fd = chan.fileno()
        #try:
        #    log.debug("REGISTER chan #%d (%s)" % (fd, chan.get_name()))
        #except:
        #    log.debug("REGISTER chan #%d" % (fd))
        self.poller.register(fd, event_mask)
        self.listeners[fd] = [chan, callback] + list(args)

    def poll_unregister(self, chan):
        fd = chan.fileno()
        #try:
        #    log.debug("UNREGISTER chan #%d (%s)" % (fd, chan.get_name()))
        #except:
        #    log.debug("UNREGISTER chan #%d" % (fd))
        if fd in self.listeners:
            self.poller.unregister(fd)
            del self.listeners[fd]


    def loop(self):
        log.debug("Starting proxying")
        while len(self.listeners) > self.min_chan: # msg is the last one
            for channels in self.poll():
                try:
                    fd, event = channels
                    self.callback(fd, event)
                except TypeError, msg:
                    raise

        if self.min_chan > 1:
            self.watch_x11.close()
            self.signal_x11.close()
        self.msg_chan.close()
        log.debug("Ending proxying")
        return util.CLOSE

    def callback(self, fd, event):
        if fd not in self.listeners:
            log.warning("Data from unknown fd #%d" % fd)
        chan = self.listeners[fd][0]
        func = self.listeners[fd][1]
        args = self.listeners[fd][2:]
        all_args = [chan, event] + list(args)
        return func(*all_args)

    def recv_data(self, source, name):
        if source.eof_received:
            data = ''
        else:
            # read available data
            data = source.recv(self.bufsize.get(source, self.default_bufsize))
        return data

    def send_data(self, destination, data, size, name):
        # write data
        sent = destination.send(data)
        while sent and sent < size:
            data = data[sent:]
            size = size - sent
            sent = destination.send(data)
        return sent

    def copy(self, source, event, destination,
                                  recv_data=recv_data, send_data=send_data):
        # Take care to pass unbound methods in recv_data and send_data!!
        sname = source.get_name()
        dname = destination.get_name()
        if source.closed:
            if sname == 'site_chan':
                xs = source.recv_exit_status()
                destination.send_exit_status(xs)
            destination.close()
            self.poll_unregister(source)
            log.debug("source %s closed" % sname)

        if destination.closed:
            source.shutdown_write()
            self.poll_unregister(destination)
            log.debug("destination %s closed" % dname)
            return

        if source.closed:
            return

        data = recv_data(self, source, sname)

        size = len(data)
        if size == 0 and not destination.eof_sent:
            # channel closed
            log.debug("source %s half-closed" % sname)
            destination.shutdown_write()
            if destination.eof_sent:
                source.close()
            else:
                source.shutdown_read()
            return 'source closed'
        
        sent = send_data(self, destination, data, size, dname)

        if sent == 0 and not destination.eof_sent:
            # channel closed
            log.debug("destination %s half-closed" % dname)
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

        


class ProxyScp(Proxy):
    _class_id = 'ProxyScp'

    def open_connection(self):
        proxy = ProxyNamespace()
        log.info('Executing: scp %s %s' % (proxy['scp_args'], 
                                           proxy['scp_path']))
        self.site_chan.exec_command('scp %s %s' % (proxy['scp_args'], 
                                                   proxy['scp_path']))
    def setup_x11(self):
        pass

ProxyScp.register()


class ProxyCmd(Proxy):
    _class_id = 'ProxyCmd'

    def open_connection(self):
        proxy = ProxyNamespace()
        server = self.server
        log.info('Executing: %s' % (proxy['cmdline']))
        if hasattr(server, 'term'):
            self.site_chan.get_pty(server.term,
                                   server.width,
                                   server.height)
        self.site_chan.exec_command(proxy['cmdline'])


ProxyCmd.register()



class ProxyShell(Proxy):
    _class_id = 'ProxyShell'

    def open_connection(self):
        server = self.server
        if hasattr(server, 'term'):
            self.site_chan.get_pty(server.term,
                                   server.width,
                                   server.height)
        self.site_chan.invoke_shell()


ProxyShell.register()
