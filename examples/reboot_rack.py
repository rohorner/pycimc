#!/usr/bin/env python

from pycimc import UcsServer
import config
from Queue import Queue
from threading import Thread, Lock
from time import time
import logging

queue = Queue()
WORKERS = 25

class ThreadedFunction(Thread):
    '''Threaded Login'''
    def __init__(self, queue, screenlock):
        Thread.__init__(self)
        self.queue = queue
        self.screenlock = screenlock

    def run(self):
        while True:
            host = self.queue.get()

            with UcsServer(host, config.USERNAME, config.PASSWORD) as server:
                if server is None:
                    # The login failed, skip this server and go on to the next
                    logging.info('Login failed for %r user %r' % (host, config.USERNAME))
                    return
                if server.get_chassis_info():
                    with self.screenlock:
                        print 'Server', server.ipaddress, 'is', server.inventory['chassis']['operPower']
                    # server.set_power_state('bmc-reset-immediate', force=True)
                else:
                    with self.screenlock:
                        print host,'get_chassis_info() returned False'

            self.queue.task_done()

def main():

    screenlock = Lock()
    #spawn a pool of threads, and pass them queue instance
    for _ in range(WORKERS):
        t = ThreadedFunction(queue, screenlock)
        t.daemon = True
        t.start()

    #populate queue with server addresses
    for server in config.SERVERS:
        queue.put(server)

    #wait on the queue until everything has been processed
    queue.join()

# Run following code when the program starts
if __name__ == '__main__':

    start = time()
    main()
    print "\nTotal Elapsed Time: %s" % (time() - start)
