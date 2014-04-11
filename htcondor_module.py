#!/usr/bin/python

"""
A module that is used to handle all kinds of relevant application 
transfers in SDN environment. It identifies the application level
information for each traffic flow and proactively install openflow 
rule according to pre-configured network policy to switch.
"""

####################################################################
#                                                                  #
#  This module has been extended for supporting multiple possible  #
#  cluster computing related softwares, such as HTCondor, GridFTP. #
#  The movitation for this is to provide a general framework to    #  
#  utilize the application level information to assist the network #
#  layer in terms of network scheduling since all the applications #
#  would have extensive network activites.                         #
#                                                                  #
#  For HTCondor, this module receives job and machine classads as  #
#  strings from lark setup callout scripts and parses these        #
#  received strings to job and machine classads. It looks for      #
#  interesting classad attribute values and later application      #
#  aware switch would uses it for network scheduling passively.    #
#                                                                  #
#  For GridFTP, the application level information such as the      #
#  username and filename are sent to this module, this module      #
#  would check the priority for each file transfer and proactively #
#  install corresponding openflow rules to the underlying switches #
#  in order to prioritize different GridFTP file transfers, e.g.   #
#  direct them to different QoS queues with different bandwidth.   #
#                                                                  #
####################################################################

import re
import time
import threading
import SocketServer
import classad
import htcondor
from collections import namedtuple
from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpid_to_str
from pox.lib.addresses import IPAddr
from job_aware_switch import check_within_local_network
import sdn_controller_config as controller_config

log = core.getLogger()

classad_thread_lock = threading.Lock()
gridftp_thread_lock = threading.Lock()

# use a dictionary to store all the network classads
# internal IPv4 address is used as the key
classad_dict = {}

# use a dictionary to store all the GridFTP event info
# IP + Port is used as the key
gridftp_dict = {}
AddressPort = namedtuple('AddressPort', ['ip','port'])
GridftpTransferInfo = namedtuple('GridftpTransferInfo', 
                                 ['username', 'filename', 'transfer_type'])

# define the dpid for core switch which connect to WAN
core_switch_mac = "00-1a-a0-09-fb-c9"
core_switch_dpid = 0

# hard and idle timeout config
HARD_TIMEOUT = 600
IDLE_TIMEOUT = 5

# application-aware controller configuration related variables
policy_mode = ''
projects_list = []
gridftp_directory_priority = []
gridftp_queues_num = 0
gridftp_queues_start_id = 0
general_queues_num = 0
general_queues_start_id = 0
CONFIG_FILENAME = '/home/bockelman/zzhang/pox/ext/sdn_controller.cfg'

class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):

  """
  A customized TCP request handler class.
  """

  def handle(self):
  
    # The received requests can be from different applications,
    # currently HTCondor and GridFTP are supported. It is very likely
    # the supported applications will be expanded in the future.
    # For each application, a set of event types are supported.
    
    # TODO: need to implement a better function to receive the data
    # if use standard recv, sometimes the full machine + job classad 
    # sent from lark_setup_script could be truncated; if use recv_timeout,
    # GridFTP event info could not be successfully delivered.

    data = self.request.recv(16384).strip()
    #data = self.recv_timeout(0.01)

    log.debug("received data is %s", data)
    lines = data.split("\n")

    # check the dpid for core switch
    global core_switch_dpid
    if core_switch_dpid == 0:
      for connection in core.openflow.connections:
        if(core_switch_mac == dpid_to_str(connection.dpid)):
          core_switch_dpid = connection.dpid
          break
          
    # TODO: break processing for different applications into functions
    if(lines[0] == "HTCONDOR"):
      if (lines[1] == "SEND"):
        log.info("job classad string is: %s", lines[2])
        log.info("machine classad string is: %s", lines[3])
        job_ad = classad.ClassAd(lines[2])
        machine_ad = classad.ClassAd(lines[3])
        # parse out the IP address of internal eth device and the job owner
        ip_src = machine_ad.eval("LarkInnerAddressIPv4")
        job_owner = job_ad.eval("Owner")
        group = None
        if "AcctGroup" in job_ad:
          group = job_ad.eval("AcctGroup")
          log.info("The accounting group the user belongs to is: %s", group)
          log.info("IP address of internal ethernet device is: %s", ip_src)
          log.info("The owner of submitted job is: %s", job_owner)

          network_classad = classad.ClassAd()
          # insert network policy related classad attributes to network classad
          network_classad["Owner"] = job_owner
          network_classad["LarkInnerAddressIPv4"] = ip_src
          if group is not None:
            network_classad["AcctGroup"] = group
            classad_thread_lock.acquire()
            classad_dict[ip_src] = network_classad.__str__()
            classad_thread_lock.release()
            
      elif (lines[1] == "REQUEST"):
        network_classad = None
        ip_src = lines[2]
        classad_thread_lock.acquire()
        # first check whether classad_dict has the given key
        if ip_src in classad_dict:
          network_classad = classad_dict[ip_src]
          classad_thread_lock.release()
          if network_classad is not None:
            log.info("Network classad is %s", network_classad)
            log.info("Found network classad for IP %s, send it back.", ip_src)
            self.request.sendall("FOUND" + network_classad)
          else:
            log.debug("Can't find network classad" \
                       " for IP %s, send back no found.", ip_src)
            self.request.sendall("NOFOUND" + "\n")

      elif (lines[1] == "CLEAN"):
        ip_src = lines[1]
        classad_thread_lock.acquire()
        # check whether classad_dict has the given key and delete corresponding
        # network classad if it is in the dictionary
        log.info("Delete network classad in classad " \
                 "dictionary for IP address %s", ip_src)
        if ip_src in classad_dict:
          del classad_dict[ip_src]
        classad_thread_lock.release()

      else:
        log.debug("Unknown message type for HTCONDOR event, ignore.")

    elif (lines[0] == "GRIDFTP"):
      if (lines[1] == "STARTUP"):
        log.info("GRIDFTP STARTUP event occurs")

        address_port = AddressPort(lines[2], lines[3])
        gridftp_transfer_info = GridftpTransferInfo(lines[4], lines[5], lines[6])
        gridftp_thread_lock.acquire()
        gridftp_dict[address_port] = gridftp_transfer_info
        gridftp_thread_lock.release()
        self.process_rule_for_gridftp_traffic(core_switch_dpid, address_port, 
                                              gridftp_transfer_info, lines[1])

      elif (lines[1] == "UPDATE"):
        #TODO: handle "UPDATE" event, currently use IDLE_TIMEOUT is sufficient
        log.info("GRIDFTP UPDATE event occurs")

      elif (lines[1] == "SHUTDOWN"):
        log.info("GRIDFTP SHUTDOWN event occurs")

        address_port = AddressPort(lines[2], lines[3])
        gridftp_transfer_info = GridftpTransferInfo(lines[4], lines[5], lines[6])
        gridftp_thread_lock.acquire()
        if address_port in gridftp_dict:
          del gridftp_dict[address_port]
        gridftp_thread_lock.release()
        self.process_rule_for_gridftp_traffic(core_switch_dpid, address_port, 
                                              gridftp_transfer_info, lines[1])

      elif (lines[1] == "REQUEST"):

        address_port = AddressPort(lines[2], lines[3])
        gridftp_transfer_info = None

        gridftp_thread_lock.acquire()
        if address_port in gridftp_dict:
          gridftp_transfer_info = gridftp_dict[address_port]
        gridftp_thread_lock.release()

        if gridftp_transfer_info is not None:
          log.info("GridFTP file transfer username and filename are: %s, %s", 
                   gridftp_transfer_info.username, 
                   gridftp_transfer_info.filename)
          log.info("GridFTP file transfer type is %s", 
                    gridftp_transfer_info.transfer_type)
          log.info("Send back to job_aware_switch")
          self.request.sendall("FOUND" + "\n" + gridftp_transfer_info.username 
                               + "\n" + gridftp_transfer_info.filename)
        else:
          log.debug("Can't find GridFTP transfer for IP + Port combination:" \
                    "%s, %s", address_port.ip, address_port.port)
          self.request.sendall("NOFOUND" + "\n")

      else:
        log.debug("Unknown GridFTP event type, ignore.")

    else:
      log.debug("Unkonwn application type %s, ignore.", lines[0])

    self.request.close()

  def recv_timeout(self, timeout):
        
    """ 
    A timeout-based receive function for socket in order to make sure 
    that the data received by the server is completed instead of being
    truncated possibly. This tries to solve the problem that the classad 
    string is truncated when it is sent from lark callout script to this 
    module.
    """

    # make socket non-blocking
    self.request.setblocking(0)
    total_data = []
    recv_data = ''
    start_time = time.time()

    while 1:
      # if receives something then break after timeout
      if total_data and time.time()-start_time > timeout:
        log.debug("Timed out and we received some data, break!")
        break
      # if nothing received then wait double the timeout
      elif time.time()-start_time > timeout*2:
        log.debug("After double time out, received nothing, break!")
        break
      # actual receive something
      try:
        recv_data = self.request.recv(16384)
        if recv_data:
          log.debug("Received something and append it to total data.")
          log.debug("Received data is %s", recv_data)
          total_data.append(recv_data)
          start_time = time.time()
        else:
          log.debug("recv function didn't get any data, sleep for a while.")
          time.sleep(timeout/2)
      except:
        pass

    return ''.join(total_data)

  def process_rule_for_gridftp_traffic(self, dpid, address_port, 
                                       gridftp_transfer_info, event_type):
  
    """
    Process relevant openflow rule to switches for GridFTP transfers when 
    GridFTP event occurs. STARTUP event leads to a installation, SHUTDOWN
    event leads to a deletion.
    """

    # check whether the gridftp client is within LAN or in WAN
    # 1. if client is within the same LAN with server, don't install
    #    specific rule for this file transfer, because bottleneck is
    #    usually at WAN part.
    # 2. if client is in WAN, prioritize the traffic stream based on
    #    the username and filename information.

    address = address_port.ip
    # TODO: this function needs to be rewritten
    #if (!check_within_local_network(address)):
    if(True):

      # figure out whether this gridftp transfer is upload or download
      # 1. If this is a gridftp upload, we don't have a lot of control
      #    over the incoming bandwidth, don't install specific openflow rule
      # 2. If this is a gridftp download, we can direct different file 
      #    transfer streams to different qos queues with different priorities

      # There are two policy modes:
      # 1. If policy mode is "application_oriented", GridFTP-only queues 
      #    would be used, the queue id is determined by the priority of file 
      #    directory, if directory is not in the priority list, the last default
      #    queue is applied;
      # 2. If policy mode is "project_oriented", queues for project users would 
      #    be used, the queue id is determined by the priority of project user.
      #    If username does not belong to any project, the last default queue 
      #    is applied.

      if gridftp_transfer_info.transfer_type == "download":
        filename = gridftp_transfer_info.filename
        queue_id = None
        if policy_mode == 'application_oriented':
          for index, directory in enumerate(gridftp_directory_priority):
            match = re.match(directory, filename)
            if match is not None and filename == match.group(0):
              queue_id = index + gridftp_queues_start_id
              break

          if queue_id == None:
            queue_id = gridftp_queues_start_id + gridftp_queues_num - 1

        elif policy_mode == 'project_oriented':
          config = controller_config.ConfigRetrieval(CONFIG_FILENAME)
          username = gridftp_transfer_info.username
          project = config.check_user_project(username)
          if project is not None:
            index = projects_list.index(project)
            queue_id = index + general_queues_start_id
          else:
            queue_id = general_queues_start_id + general_queues_num - 1

        if event_type == 'STARTUP':
          log.info("install rule for GridFTP file transfer in %s", policy_mode)
          log.info("GridFTP file transfer directory is %s", filename)
          msg = of.ofp_flow_mod()
          msg.priority = 12
          msg.match.dl_type = 0x800
          msg.match.nw_proto = 6
          msg.match.nw_dst = IPAddr(address_port.ip)
          msg.match.tp_dst = int(address_port.port)
          msg.idle_timeout = IDLE_TIMEOUT
          msg.actions.append(of.ofp_action_enqueue(port=1, queue_id=queue_id))
          core.openflow.sendToDPID(dpid, msg)

        elif event_type == 'SHUTDOWN':
          log.info("delete rule for GridFTP file transfer in %s", policy_mode)
          log.info("GridFTP file transfer directory is %s", filename)
          msg = of.ofp_flow_mod(command=of.OFPFC_DELETE)
          msg.priority = 12
          msg.match.dl_type = 0x800
          msg.match.nw_proto = 6
          msg.match.nw_dst = IPAddr(address_port.ip)
          msg.match.tp_dst = int(address_port.port)
          core.openflow.sendToDPID(dpid, msg)

        else:
          pass

      else:
        pass

    else:
      pass

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):

  """
  A threaded TCP server used for checking application-level info 
  of traffic flows.
  """
    
  # Ctrl-C will cleanly kill all spawned threads
  daemon_threads = True
  # faster rebinding
  allow_reuse_address = True

  def __init__(self, server_address, RequestHandlerClass):
    SocketServer.TCPServer.__init__(self, server_address, RequestHandlerClass)

def launch():
  
  """
  lanuch the Threaded TCP server, which is used to check traffic
  flow from different applications, store application-level meta
  data for passive network management and also proactively install 
  openflow rule to core switch according to pre-configure policy.
  """

  # load configuration and check relevant config options
  config = controller_config.ConfigRetrieval(CONFIG_FILENAME)
  global policy_mode
  global gridftp_directory_priority
  global projects_list
  global gridftp_queues_num
  global gridftp_queues_start_id
  global general_queues_num
  global general_queues_start_id

  policy_mode = config.get_policy_mode()
  projects_list = config.get_projects_list()
  gridftp_directory_priority = config.get_gridftp_directory_priority()
  gridftp_queues_num, gridftp_queues_start_id = config.get_qos_info('GridFTP')
  general_queues_num, general_queues_start_id = config.get_qos_info('General')
    
  # make host to be IPv4 address of the host where the pox controller is running
  host = htcondor.param["HTCONDOR_MODULE_HOST"]
  port = int(htcondor.param["HTCONDOR_MODULE_PORT"])
  server = ThreadedTCPServer((host, port), ThreadedTCPRequestHandler)
  core.register("TCPServer", server)

  def run():
    try:
      log.debug("Server starts and listens on %s:%i", host, port)
      server.serve_forever()
    except:
      pass
    log.info("Server quit")

  thread = threading.Thread(target=run)
  thread.daemon = True
  thread.start()
