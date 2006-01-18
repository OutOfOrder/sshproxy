
import os, select, pty, traceback

class SSHProxyError(Exception):
    pass

class FreeStructure(object):
    pass

SUSPEND, CLOSE = range(1, 3)

class PTYWrapper(object):
    def __init__(self, chan, code, msg, *args, **kwargs):
        self.chan = chan
        self.cin = msg.get_parent_fd()
        pid, self.master_fd = pty.fork()
        if not pid: # child process
            cout = msg.get_child_fd()
            try:
                code(cout, *args, **kwargs)
            except Exception, e:
                print '*** function %s: %s\n' % (code.__name__, str(e))
                print traceback.format_exc()
                pass
            cout.write('EOF')
            cout.close()
            os.abort() # squash me! (don't let me close paramiko channels)

    def loop(self):
        chan = self.chan
        master_fd = self.master_fd
        cin = self.cin
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
                data = cin.read(1024)
                # since this is a pipe, it seems to always return EOF ('')
                if not len(data):
                    continue
                if data == 'EOF':
                    cin.close() # stop the loop
                    return None
                return data


