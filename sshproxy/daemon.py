#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Nov 01, 02:17:32 by david
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
from server import Server
import ipc, log
from monitor import Monitor


class Client(object):
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

class Daemon(Registry):
    _class_id = 'Daemon'
    _singleton = True

    clients = {}

    ipc_address = ('127.1', 2244)

    def __reginit__(self, daemon, sock):
        self.imq = {}
        self.monitor = Monitor(input_message_queue=self.imq)
        self._run_server(daemon, sock)

    def handle_incoming_connection(self, sock):
        return sock.accept()

    def service_client(self, client, addr):
        server = Server(client, addr, self.host_key_file)
        server.start()
        return
    
    def _run_server(self, daemon, sock):
        # get host key
        self.host_key_file = os.path.join(config.inipath, 'id_dsa')

        # set up the child killer handler
        signal.signal(signal.SIGCHLD, self.monitor.kill_zombies)
    
    
        try:
            # set up input message queue
            imq = self.imq
            imq[sock] = self
            # set up output message queue
            omq = []
            # set up error message queue
            emq = []

            while True:
                try:
                    # message ready ?
                    try:
                        imr, omr, emr = select.select(imq.keys(), omq, emq, 100)
                    except KeyboardInterrupt:
                        raise
                    except select.error,e:
                        # may be caused by SIGCHLD
                        self.monitor.kill_zombies()
                        continue
                    except socket.error:
                        # may be caused by SIGCHLD
                        self.monitor.kill_zombies()
                        continue

                    for x in imr:
                        if imq[x] is self.monitor:
                            # consume the message
                            self.monitor.handle_incoming_connection(x)
                            continue

                        try:
                            client, addr = imq[x].handle_incoming_connection(x)
                        except socket.error:
                            continue
                        except Exception, e:
                            log.exception('ERROR: socket accept failed')
                            pass
                            raise

                        log.debug('Got a connection!')
                        pid = os.fork()
                        if pid == 0:
                            # just serve in the child
                            x.close()
                            for i in imq:
                                if hasattr(imq[i], 'sock'):
                                    imq[i].sock.close()
                            self.monitor.clean_at_fork()
                            log.info("Serving %s", addr)
                            imq[x].service_client(client, addr)
                            time.sleep(0.5)
                            sys.exit()

                        client.close()
                        self.monitor.add_child(pid, chan=x, ip_addr=addr)
    
    
                except KeyboardInterrupt:
                    log.info("Caught KeyboardInterrupt, exiting...")
                    # don't accept connections anymore
                    sock.close()
                    ### FIX
                    self.imq.pop(0)
                    log.info("Signaling all child processes")
                    msg = ('General shutdown happening.\n'
                           'Please reconnect later.')
                    self.monitor.rq_kill(0, '', '*', msg)
                    # let the clients get their messages
                    if self.monitor.children_count():
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
                    self.monitor.kill_zombies()
                    continue
        finally:
            try:
                # try to finish in a clean manner
                sock.close()
            except:
                pass

    def abort(self, *args, **kw):
        log.info("Terminating all child processes")
        self.monitor.kill_children(sig=signal.SIGTERM)
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
            init_plugins()
        except:
            log.exception("Could not initialize plugins...")
            raise
        try:
            if sock is None:
                sock = bind_server(daemon)
            Daemon(daemon, sock)
        except (KeyboardInterrupt, SystemExit):
            log.info("System exit")
            return
        except Exception, msg:
            log.exception("ERROR: sshproxy may have crashed:"
                                                    " AUTORESTARTING...")
    finally:
        log.info("sshproxy ending")
        os.abort()


def run_daemon(daemonize, user, pidfile): # Credits: portions of code from TMDA

    if os.getuid() == 0:
        uid = util.getuid(user)
        gid = util.getgid(user)

    # Generate host key if not present already
    host_key_file = os.path.join(config.inipath, 'id_dsa')
    if not os.path.isfile(host_key_file):
        # generate host key
        dsskey = util.gen_dss_key(verbose=True)
        dsskey.write_private_key_file(host_key_file)
        os.chown(host_key_file, uid, gid)

    # don't run as a daemon if there are uncatched exceptions
    # not appearing in the logs
    if daemonize:
        # let's secure it all
        os.chdir('/')
        fd = os.open('/dev/null', os.O_RDONLY)
        os.dup2(fd, 0) # stdin
        os.dup2(fd, 1) # stdout
        os.dup2(fd, 2) # stderr
        os.close(fd)

    # open the listening socket before dropping privs
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
        # drop privs
        os.seteuid(0)
        os.setgid(gid)
        os.setgroups(util.getgrouplist(user))
        os.setuid(uid)

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
