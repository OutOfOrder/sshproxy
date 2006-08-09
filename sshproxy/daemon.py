#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Aug 09, 14:37:42 by david
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


import sys, os, os.path, socket, signal, select, time


from registry import Registry
from plugins import init_plugins
import util
import config
import log
from server import Server
from message import Message


class Client(object):
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

class Daemon(Registry):
    _class_id = 'Daemon'
    _singleton = True

    clients = {}
    pids = []

    def __reginit__(self, daemon, sock):
        self._run_server(daemon, sock)

    def service_client(self, client, addr, msg):
        server = Server(client, addr, msg, self.host_key_file)
        server.start()
        return
    
    def kill_child(self, pid, sig=signal.SIGHUP):
        try:
            os.kill(pid, sig)
            return True
        except OSError:
            log.warning('ERROR: child pid %s does not exist', pid)
        return False
    
    def kill_zombies(self, signum=None, frame=None):
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
            if pid and pid in self.pids:
                imqfd = self.imq.index(self.clients[pid].msg)
                del self.imq[imqfd]
                del self.clients[pid]
                del self.pids[self.pids.index(pid)]
                log.info("A child process has been killed and cleaned.")
        except OSError:
            pass
        
    def find_client_pid(self, fd):
        for pid, m in self.clients.items():
            if m.msg == fd:
                return pid
        return None

########################################################################

    def send_message(self, id, cmd, msg):
        self.clients[id].msg.write('%s:\n\n%s\n\n' % (cmd, msg))

    def rq_nb_con(self, id, *args):
        """
        nb_con

        Get number of currently active connections.
        """
        return '%d' % len(self.clients)

    def rq_set_client(self, id, *args):
        for arg in args[1:]:
            k, v = arg.split('=', 1)
            setattr(self.clients[id], k, v)

    def rq_watch(self, id, *args):
        """
        watch

        Display connected users.
        """
        s = []
        for pid, client in self.clients.items():
            # don't show ourself
            if pid == id:
                continue
            if hasattr(client, 'name'):
                s.append('%s@%s ---(%s)--> %s@%s' %
                                (client.username, str(client.ip_addr[0]),
                                client.type,
                                client.login, client.name))
            else:
                s.append('%s@%s -->(%s)' %
                                (client.username, str(client.ip_addr[0]),
                                client.type))
        return '\n'.join(s)

    def rq_message(self, id, *args):
        """
        message user@site <message contents>

        Send a message to user@site.
        """
        if len(args) < 3:
            return 'Need a message'
        for pid, client in self.clients.items():
            cid = '%s@%s' % (client.username, client.ip_addr[0])

            if args[1] == '*' or args[1] == cid:
                msg = ("\007On administrative request, "
                       "your session will be closed.")
                if len(args) > 2:
                    msg = ' '.join(args[2:])
                self.send_message(pid, 'announce', msg)
                #return '%s found and signaled' % cid
            #return "%s couldn't be signaled" % cid
        return '%s not found' % (args[1])

    def rq_kill(self, id, *args):
        """
        kill user@site

        Kill all connections to user@site.
        """
        count = 0
        for pid, client in self.clients.items():
            # don't kill ourself
            if pid == id:
                continue
            if hasattr(client, 'username'):
                username = client.username
            else:
                username = '_'
            cid = '%s@%s' % (username, client.ip_addr[0])
            if hasattr(client, 'name'):
                sid = '%s@%s' % (client.login, client.name)
            else:
                sid = None
            if args[1] in ('*', cid, sid):
                msg = ("\007On administrative request, "
                       "your session will be closed.")
                if len(args) > 2:
                    msg = ' '.join(args[2:])
                self.send_message(pid, 'kill', msg)
                count += 1
        if count:
            return '%d killed connections' % count
        else:
            return '%s not found' % (args[1])

    def rq_shutdown(self, id, *args):
        """Shutdown all active connections"""
        msg = ("The administrator has requested a shutdown.\n"
                "Your session will be closed.")
        for pid, client in self.clients.items():
            if pid == id:
                continue
            self.send_message(pid, 'kill', msg)
        time.sleep(2)
        for pid, client in self.clients.items():
            if pid == id:
                continue
            self.kill_child(pid)
            
    def handle_message_request(self, id, request):
        args = request.split()

        if args[0] == 'help':
            resp = []
            methnames = [ m for m in dir(self) if m[:3] == 'rq_' ]
            methnames.sort()
            for methname in methnames:
                method = getattr(self, methname)
                doc = getattr(method, '__doc__', None)
                if doc:
                    # display only documented methods
                    resp.append('\n%s:' % methname[3:])
                    resp.append('  '+ '\n  '.join(doc.split('\n')))

            return '\n'.join(resp)

        if hasattr(self, 'rq_%s' % args[0]):
            return getattr(self, 'rq_%s' % args[0])(id, *args)
        return 'ERROR: unknown command %s' % request

    def get_public_methods(self):
        methods = []
        for method in dir(self):
            if method[:3] != 'rq_':
                continue
            doc = getattr(getattr(self, method), '__doc__', None)
            if not doc:
                continue
            methods.append(' '.join([ method[3:], doc]))

        return '\n'.join([ m.replace('\n', '\\n') for m in methods ])


    def handle_message(self, fd):
        id = self.find_client_pid(fd)
        if not id:
            log.error("A client has sent a message, but I couldn't find it.")
        fd.reset()
        request = fd.read()
        if request == 'public_methods':
            fd.response(self.get_public_methods())
            return
        resp = self.handle_message_request(id, request)
        if resp is None:
            resp = ''
        fd.response(str(resp))

########################################################################

    def _run_server(self, daemon, sock):
        init_plugins()
    
        # get host key
        host_key_file = os.path.join(config.inipath, 'id_dsa')
        if not os.path.isfile(host_key_file):
            # generate host key
            dsskey = util.gen_dss_key(verbose=True)
            dsskey.write_private_key_file(host_key_file)
    
        self.host_key_file = host_key_file
        # set up the child killer handler
        signal.signal(signal.SIGCHLD, self.kill_zombies)
    
    
        try:
            # set up input message queue
            self.imq = imq = [ sock ]
            # set up output message queue
            omq = []
            # set up error message queue
            emq = []

            while True:
                try:
                    # message ready ?
                    try:
                        imr, omr, emr = select.select(imq, omq, emq, 1)
                    except KeyboardInterrupt:
                        raise
                    except select.error:
                        # may be caused by SIGCHLD
                        self.kill_zombies()
                        continue
                    except socket.error:
                        # may be caused by SIGCHLD
                        self.kill_zombies()
                        continue
                    for x in imr:
                        if x is sock:
                            try:
                                #sock_c = os.dup(sock.fileno())
                                client, addr = sock.accept()
                            except socket.error:
                                continue
                            except Exception, e:
                                log.exception('ERROR: socket accept failed')
                                pass
                                raise
                            log.debug('Got a connection!')
                            msg = Message()
                            pid = os.fork()
                            if pid == 0:
                                # just serve in the child
                                sock.close()
                                log.info("Serving %s", addr)
                                msg = msg.get_child_fd()
                                self.service_client(client, addr, msg)
                                sys.exit()

                            client.close()
                            # XXX: possible race condition here !
                            msg = msg.get_parent_fd()
                            self.clients[pid] = Client(msg=msg, ip_addr=addr)
                            self.pids.append(pid)
                            imq.append(msg)
                        else:
                            # consume the message
                            self.handle_message(x)
    
    
                except KeyboardInterrupt:
                    log.info("Caught KeyboardInterrupt, exiting...")
                    # don't accept connections anymore
                    sock.close()
                    self.imq.pop(0)
                    log.info("Signaling all child processes")
                    msg = ('General shutdown happening.\n'
                           'Please reconnect later.')
                    self.rq_kill(0, '', '*', msg)
                    # let the clients get their messages
                    if len(self.pids):
                        seconds = 2
                        signal.signal(signal.SIGALRM, self.abort)
                        signal.alarm(seconds)
                        log.info("Sleeping %d seconds to let child processes"
                                                    " terminate" % seconds)
                        continue
                    self.abort()
                    break
                except (select.error, socket.error):
                    # this except is here to cache the exception raise
                    # when a SIGCHLD is sent in select.select:
                    # File ".../sshproxy/daemon.py", line 185, in _run_server
                    #    imr, omr, emr = select.select(imq, omq, emq)
                    # error: (4, 'Interrupted system call')
                    # 
                    self.kill_zombies()
                    continue
        finally:
            try:
                # try to finish in a clean manner
                sock.close()
            except:
                pass

    def abort(self, *args, **kw):
        log.info("Terminating all child processes")
        for pid in self.pids:
            self.kill_child(pid, sig=signal.SIGTERM)
        log.info("Terminating master processes")
        sys.exit(0)

Daemon.register()
                

def bind_server(daemon):
    conf = config.get_config('sshproxy')
    # preserve compatibility with 0.4.* (bindip)
    ip = conf['listen_on'] or conf.get('bindip', '')
    port = conf['port']

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((ip, port))
        sock.listen(100)
        if not daemon:
            print "Server ready, clients may login now ..."
        log.debug('Listening for connection ...')
    except Exception, e:
        log.exception("ERROR: Couldn't bind on port %s" % port)
        print "ERROR: Couldn't bind on port %s" % port
        sys.exit(1)

    return sock


def run_server(daemon=False, sock=None):
    log.info("sshproxy starting")

    try:
        try:
            if sock is None:
                sock = bind_server(daemon)
            Daemon(daemon, sock)
        except (KeyboardInterrupt, SystemExit):
            return
        except:
            log.exception("ERROR: sshproxy may have crashed:"
                                                    " AUTORESTARTING...")
    finally:
        log.info("sshproxy ending")


def run_daemon(daemonize, user, pidfile): # Credits: portions of code from TMDA
    sock = bind_server(daemonize)

    if daemonize:
        try:
            pidfd = open(pidfile, 'w')
        except IOError:
            print "Warning: could not open %s for writing" % pidfile
            pidfd = None
    else:
        pidfd = None


    if os.getuid() == 0:
        uid = util.getuid(user)
        os.setegid(util.getgid(user))
        os.setgroups(util.getgrouplist(user))
        os.seteuid(uid)

    if daemonize:
#        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        if os.fork() != 0:
            sys.exit(0)

    if pidfd:
        pidfd.write('%d\n' % os.getpid())
        pidfd.close()

    run_server(daemonize, sock)



if __name__ == '__main__':
    run_server()
