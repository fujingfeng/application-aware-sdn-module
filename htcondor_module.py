#!/usr/bin/python

#
# This htcondor module receives job and machine classad as 
# strings from lark setup callout script and parses these
# received strings to job and machine classads. It looks for 
# interesting classad attributes value and uses it for network 
# scheduling.
#

import socket
import threading
import SocketServer
import classad

class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        data = self.request.recv(16384).strip()
        cur_thread = threading.current_thread()
        lines = data.split("\n")
        job_ad = classad.ClassAd(lines[0])
        machine_ad = classad.ClassAd(lines[1])
        # parse out the IP address of internal eth device and the job owner
        ip_src = machine_ad.eval("LarkInnerAddressIPv4")
        job_owner = job_ad.eval("Owner")
        print "IP address of internal ethernet device is: " + ip_src
        print "The owner of submitted job is: " + job_owner

        self.request.close()

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    # Ctrl-C will cleanly kill all spawned threads
    daemon_threads = True
    # faster rebinding
    allow_reuse_address = True

if __name__ == "__main__":
    HOST, PORT = "localhost", 9008

    server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    # keep the server thread alive when the main thread terminates
    server_thread.daemon = False
    server_thread.start()




