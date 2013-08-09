#!/usr/bin/python

"""
An htcondor job-aware switch.

It should perform basic switch functionality, which means that
if there are no special policies are predefined, the network 
traffic should be able to go through the switch like a regular 
l2 switch. The difference between this job-aware switch and 
regular l2 switch is that when PacketIn event occurs, the handler 
would ask for network classad of corresponding job that causes 
this network flow before it assign actions on this flow. It 
contacts the htcondor module "htcondor_module.py" to get the 
network classad.
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import str_to_bool
from pox.lib.util import dpid_to_str
import time
import sys
import socket
import classad
import htcondor

log = core.getLogger()

HARD_TIMEOUT = 10
IDLE_TIMEOUT = 5

class JobAwareSwitch ():
    
    def __init__ (self, connection):
        # Switch we will be adding L2 learning switch capabilitites to
        self.connection = connection
        self.macToPort = {}
        connection.addListeners(self)

    def _handle_PacketIn (self, event):
        # parsing the input packet
        packet = event.parsed
        
        # update mac to port mapping
        self.macToPort[packet.src] = event.port

        # drop LLDP packet
        # send command without actions
        if packet.type == packet.LLDP_TYPE:
            # log.debug("dropping LLDP packets")
            msg = of.ofp_packet_out()
            msg.buffer_id = event.ofp.buffer_id
            msg.in_port = event.port
            self.connection.send(msg)

        # get the IPv4 src and dst
        ipv4src = None
        ipv4dst = None
        ipv4pkt = packet.find('ipv4')
        if ipv4pkt is not None:
            ipv4src = ipv4pkt.srcip
            ipv4dst = ipv4pkt.dstip

        # connect to htcondor module to ask for the network classad
        # corresponding to this source ipv4 address
        if ipv4src is not None:
            HOST, PORT = "129.93.244.211", 9008
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # log.debug("Connecting %s.%i for network classad for IP %s", HOST, PORT, str(ipv4src))
            try:
                sock.connect((HOST, PORT))
                sock.sendall("REQUEST" + "\n" + str(ipv4src))
                # receive response from the server
                received = sock.recv(1024).strip()
            finally:
                sock.close()

            # check whether network classad is found at htcondor module
            lines = received.split("\n")
            if lines[0] == "FOUND":
                
                log.debug("Network classad for IP %s is found.", str(ipv4src))

                # parse the network classad string into classad format
                # debug to print out received classad string
                log.debug("Received classad string is:")
                network_classad = str()
                for line in lines[1:]:
                    print line
                    network_classad = network_classad + line

                network_classad = classad.ClassAd(network_classad)
                owner = network_classad["Owner"]
                # query htcondor config files to get the list of blocked users
                # if the owner is in the list, drop the packets from this user.

                blocked_users = htcondor.param["BLOCKED_USERS"]
                blocked_users = blocked_users.split(',')
                if owner in blocked_users:
                    # drop
                    log.debug("Packet is from htcondor job whose owner is in the blocked user list. Drop.")
                    # installing openflow rule
                    log.debug("Installing openflow rule to switch to continue dropping similar packets for a while.")
                    msg = of.ofp_flow_mod()
                    msg.priority = 12
                    msg.match.nw_src = ipv4src
                    msg.match.dl_src = packet.src
                    msg.idle_timeout = IDLE_TIMEOUT
                    msg.hard_timeout = HARD_TIMEOUT
                    msg.buffer_id = event.ofp.buffer_id
                    self.connection.send(msg)
                    return
                else:
                    # job owner is not in blocked user list, check the destination of this flow
                    # if the ipv4dst is corresponding to htcondor jobs from other users, also 
                    # drop the packet to achieve job isolation among different users.
                    if ipv4dst is not None:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        try:
                            sock.connect((HOST, PORT))
                            sock.sendall("REQUEST" + "\n" + str(ipv4dst))
                            received = sock.recv(1024).strip()
                        finally:
                            sock.close()

                        lines = received.split("\n")
                        if lines[0] == "FOUND":
                            log.debug("Network classad for IP %s is found.", str(ipv4dst))
                            network_classad = str()
                            for line in lines[1:]:
                                network_classad = network_classad + line
                            network_classad = classad.ClassAd(network_classad)
                            owner_dst = network_classad["Owner"]

                            if owner != owner_dst:
                                # drop packet
                                log.debug("HTCondor job from user %s is trying to communicate with job from user %s. Drop packet.", owner, owner_dst)
                                # installing openflow rule to drop similar packets for a while
                                msg = of.ofp_flow_mod()
                                msg.priority = 12
                                msg.match.nw_src = ipv4src
                                msg.match.dl_src = packet.src
                                msg.match.nw_dst = ipv4dst
                                msg.idle_timeout = IDLE_TIMEOUT
                                msg.hard_timeout = HARD_TIMEOUT
                                msg.buffer_id = event.ofp.buffer_id
                                self.connection.send(msg)
                                return

            elif lines[0] == "NOFOUND":
                # proceed as normal packet using l2 switch rules
                pass

        if packet.dst not in self.macToPort:
            # does not know out port
            # flood the packet
            # log.debug("Port for %s unkown -- flooding", packet.dst)
            msg = of.ofp_packet_out()
            msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
            msg.buffer_id = event.ofp.buffer_id
            msg.in_port = event.port
            self.connection.send(msg)

        else:
            # check whether the packet's destination is the same port it come from
            port = self.macToPort[packet.dst]
            if port == event.port:
                # log.warning("Same port for packet from %s -> %s on %s.%s. Drop."
                #    % (packet.src, packet.dst, dpid_to_str(event.dpid), port))
                # install openflow rule to drop similar packets for a while
                msg = of.ofp_flow_mod()
                msg.match = of.ofp_match.from_packet(packet)
                msg.idle_timeout = IDLE_TIMEOUT
                msg.hard_timeout = HARD_TIMEOUT
                msg.buffer_id = event.ofp.buffer_id
                self.connection.send(msg)
            else:
                # we know which port this packet should go
                # just send out a of_packet_out message
                # log.debug("packet from %s.%i -> %s.%i", packet.src, event.port, packet.dst, port)
                # log.debug("installing openflow rule for this match")
                msg = of.ofp_flow_mod()
                msg.priority = 10
                msg.match.dl_src = packet.src
                msg.match.dl_dst = packet.dst
                msg.idle_timeout = IDLE_TIMEOUT
                msg.hard_timeout = HARD_TIMEOUT
                msg.actions.append(of.ofp_action_output(port = port))
                msg.buffer_id = event.ofp.buffer_id
                self.connection.send(msg)


class job_aware_switch (object):
    """
    Waits for OpenFlow switches to connect and makes them htcondor job-aware switches
    """
    def __init__ (self):
        core.openflow.addListeners(self)

    def _handle_ConnectionUp (self, event):
        log.debug("Connection %s" % (event.connection,))
        JobAwareSwitch(event.connection)

def launch ():
    """
    Starts an htcondor job-aware switch
    """
    core.registerNew(job_aware_switch)
