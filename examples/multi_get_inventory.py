#!/usr/bin/env python

__author__ = 'Rob Horner (robert@horners.org)'

from pycimc import UcsServer
import config
from Queue import Queue
from threading import Thread, Lock
from time import time

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

            with UcsServer(host, config.USERNAME, config.PASSWORD) as server:
                out_string = server.ipaddress
                if server.get_interface_inventory():
                    for int in server.inventory['adaptor']:
                        out_string += ',SLOT-'+int['pciSlot']
                        for port in int['port']:
                            out_string += ',port-'+str(port['portId'])+','+port['adminSpeed']+','+port['linkState']
                            for vnic in port['vnic']:
                                out_string += ','+str(vnic['name'])+','+str(vnic['mac'])
                    with self.lock:
                        print out_string
                else:
                    with self.lock:
                        print host,'get_interface_inventory() returned False'

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
