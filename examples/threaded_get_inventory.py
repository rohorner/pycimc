__author__ = 'Rob Horner (robert@horners.org)'

from pycimc import *
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
            #string = self.getName()+':'+host
            #print string
            server = UcsServer(host, config.USERNAME, config.PASSWORD)
            try:
                if server.login():
                    if server.get_fw_versions():
                        out_string = host + '\t'
                        for key,value in server.inventory['fw'].items():
                            # split up the DN (sys/rack-unit-1/adaptor-1/mgmt/fw) key and remove the common
                            # 'sys/rack-unit-1' prefix to reduce text size
                            key = '/'.join(key.split('/')[2:])
                            out_string += key + '\t' + value + '\t'
                        # grab a lock for writing to sysout
                        with self.lock:
                            print out_string
                    #if server.get_chassis_info():
                    #    with self.lock:
                    #        #print host,":",server.chassis_info
                    #        print "{0}: {1}".format(host, server.model)

                    server.logout()
                else:
                    with self.lock:
                        print "Couldn't log in to", host
            except Exception as err:
                with self.lock():
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
