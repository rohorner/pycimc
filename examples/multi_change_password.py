#!/usr/bin/env python

__author__ = 'Rob Horner (robert@horners.org)'

from pycimc import UcsServer
import config
from Queue import Queue
from threading import Thread, Lock
from time import time

USERNAME = 'admin'
CURRENT_PASSWORD = 'cisco'
NEW_PASSWORD = 'password'
queue = Queue()
WORKERS = 25

class ThreadLogin(Thread):
    '''Threaded Login'''
    def __init__(self, queue, lock):
        Thread.__init__(self)
        self.queue = queue
        self.lock = lock

    def run(self):
        while True:
            host = self.queue.get()
            #with self.lock:
            #    string = self.getName()+': '+host
            #print string
            server = UcsServer(host, USERNAME, CURRENT_PASSWORD)
            try:
                if server.login():
                    if server.set_password(USERNAME, NEW_PASSWORD):
                        with self.lock:
                            print "%s: Changed user '%s' password to '%s'" % (host, USERNAME, NEW_PASSWORD)
                    else:
                        with self.lock:
                            print "%s: Error changing password" % host
                    server.logout()
                #else:
                #    with self.lock:
                #        print "Couldn't log in to", host
            except Exception as err:
                with self.lock:
                    print "Server Error:", host, err
            finally:
                #print 'Queue size:',queue.qsize()
                self.queue.task_done()

def main():

    lock = Lock()
    #spawn a pool of threads, and pass them queue instance
    for _ in range(WORKERS):
        t = ThreadLogin(queue, lock)
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

    print "Total Elapsed Time: %s" % (time() - start)
