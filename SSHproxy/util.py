
import sys, os, select, pty, traceback

class FreeStructure(object):
    pass


def pty_run(chan, code, *args, **kwargs):
    cin, cout = os.pipe()
    pid, master_fd = pty.fork()
    if pid: # main process
        os.close(cout)
        while master_fd and chan.active:
            rfds, wfds, xfds = select.select(
                    [master_fd, chan, cin], [], [],5)
            if master_fd in rfds:
                data = pty._read(master_fd)
                chan.send(data)
            if chan in rfds:
                data = chan.recv(1024)
                if chan.closed or chan.eof_received:
                    break 
                if data == '':
                    break
                pty._writen(master_fd, data)
            if cin in rfds:
#                try:
#                    data = os.read(cin, 1024)
#                except OSError:
#                    pass
                os.close(cin) # stop the loop
#                os.waitpid(pid, 0)
#                chan.send('closed')
                break
#                if data == 'END':
#                    os.close(cin) # stop the loop
#                    break
#                if data[:8] == 'connect ':
#                    site = data[8:].strip()
    else: # child process
        os.close(cin)
        try:
            code(*args, **kwargs)
        except Exception, e:
            print '*** function %s: %s\n' % (code.__name__, str(e))
            print traceback.format_exc()
            pass
#        sys.stdout.flush()
        os.write(cout, ' ') # stop
        os.close(cout)
        os.abort() # squash me! (don't let me close paramiko channels)


