import logging
L = lambda: logging.getLogger(__name__)
import sys
import select
from .concepts import Transport


class StdioTransport(Transport):
    def stop(self):
        L().info('StdioTransport.stop() called')
        self.running=False

    def send(self, data, receivers=None):
        if receivers is not None and 'stdio' not in receivers:
            return
        L().debug('StdioTransport.send %r'%data)
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()

    def run(self):
        '''run, blocking.'''
        L().info('StdioTransport.run() called')
        self.running = True
        leftover = b''
        while self.running:
            # FIXME: This loses bytes on startup.
            data = self._input()
            #data = input().encode('utf8') + b'\n'
            if data is None: 
                continue
            L().info("received: %r"%data)
            leftover = self.received(sender='stdio', data=leftover + data)
        L().info('StdioTransport has finished')
            
    def _input(self, timeout=0.1):
        '''Input with 0.1s timeout. Return None on timeout.'''
        i, o, e = select.select([sys.stdin.buffer], [], [], timeout)
        if i:
            return sys.stdin.buffer.read1(65536)
        else:
            return None


def test():
    t = StdioTransport()
    print('enter something, Ctrl+C to quit')
    t.run()

if __name__ == '__main__':
    test()
