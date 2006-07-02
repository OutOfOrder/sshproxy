#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 02, 23:54:56 by david
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


import sys, os, os.path, socket, signal


from plugins import init_plugins
import util
import config
import log
from server import Server


def service_client(client, addr, host_key_file):
    server = Server(client, addr, host_key_file)
    server.start()
    return


servers = []
def kill_zombies(signum, frame):
    try:
        pid, status = os.wait()
        if pid in servers:
            del servers[servers.index(pid)]
    except OSError:
        pass
        


def _run_server(daemon, sock):
    init_plugins()

    # get host key
    host_key_file = os.path.join(config.inipath, 'id_dsa')
    if not os.path.isfile(host_key_file):
        # generate host key
        dsskey = util.gen_dss_key(verbose=True)
        dsskey.write_private_key_file(host_key_file)

    # set up the child killer handler
    signal.signal(signal.SIGCHLD, kill_zombies)


    try:
        while True:
            try:
                client, addr = sock.accept()
            except KeyboardInterrupt:
                for pid in servers:
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except OSError:
                        log.exception('ERROR: child pid %s already dead', pid)
                raise
                sys.exit(1)
            except socket.error:
                continue
            except Exception, e:
                log.exception('ERROR: socket accept failed')
                raise
            log.debug('Got a connection!')
            pid = os.fork()
            if pid == 0:
                # just serve in the child
                log.info("Serving %s", addr)
                service_client(client, addr, host_key_file)
                os._exit(0)
            # (im)probable race condition here !
            servers.append(pid)
    finally:
        try:
            sock.close()
        except:
            pass
            

def bind_server(daemon):
    conf = config.get_config('sshproxy')
    ip = conf['bindip']
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
            _run_server(daemon, sock)
        except KeyboardInterrupt:
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
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        if os.fork() != 0:
            sys.exit(0)

    if pidfd:
        pidfd.write('%d\n' % os.getpid())
        pidfd.close()

    run_server(daemonize, sock)



if __name__ == '__main__':
    run_server()
