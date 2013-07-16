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
        # there are two possible kinds of request to handle
        # 1. lark setup script sends full job and machine classad
        # 2. pox controller component ask for network classad for specific IP
        # they are represented as "SEND" and "REQUEST" respectively
        
        data = self.request.recv(16384).strip()
        cur_thread = threading.current_thread()
        lines = data.split("\n")

        if (lines[0] == "SEND"):
            job_ad = classad.ClassAd(lines[1])
            machine_ad = classad.ClassAd(lines[2])
            # parse out the IP address of internal eth device and the job owner
            ip_src = machine_ad.eval("LarkInnerAddressIPv4")
            job_owner = job_ad.eval("Owner")
            print "IP address of internal ethernet device is: " + ip_src
            print "The owner of submitted job is: " + job_owner

            self.request.close()

            network_classad = classad.ClassAd()
            # insert all the network policy related classad attr to network classad
            network_classad["Owner"] = job_owner
            network_classad["LarkInnerAddressIPv4"] = ip_src
        
            threadLock.acquire()
            self.classadDict[ip_src] = network_classad.__str__()
            threadLock.release()
        elif (lines[0] == "REQUEST"):
            network_classad = None
            ip_src = lines[1]
            threadLock.acquire()
            # first check whether classadDict has the given key
            if ip_src in classadDict:
                network_classad = classadDict[ip_src]
            threadLock.release()
            if network_classad is not None:
                self.request.sendall("FOUND"+ "\n" + network_classad)
            else:
                self.request.sendall("NOFOUND" + "\n")
            self.request.close()
        else:
            print "Unknown message type, ignoring"
            self.request.close()

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    # Ctrl-C will cleanly kill all spawned threads
    daemon_threads = True
    # faster rebinding
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass):
        SocketServer.TCPServer.__init__(self, server_address, RequestHandlerClass)
        # use a dictionary to store all the network classads, internal IPv4 address
        # is used as the key
        self.classadDict = {}

if __name__ == "__main__":

    threadLock = threading.Lock()

    HOST, PORT = "localhost", 9008
    server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
    server.serve_forever()




