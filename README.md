application-aware-sdn-module
=============================

Develope an application-aware SDN module to manage the network with better 
flexibility and fine-grained control. This module utilize application level 
information and pre-defined network policy together to install corresponding 
OpenFlow rule to switches in the network.

1. Overview of System Structure
-------------------------------

The sdn module mainly has two components:

1) application_aware_switch.py

2) proactive-sdn-module.py

Take HTCondor as the example to explain how this works:

For each job in Lark, before the network configuration is finished, a callout 
network setup script is called. The inputs to the setup script are the job 
and machine ClassAds. 

The setup script sends the ClassAds to proactive_sdn_module that runs at the 
same remote host as the openflow controller (in our case, a pox controller) 
does. The proactive_sdn_module performs like a TCP socket server, which can 
handle the request from multiple jobs. Whenever a job sents the ClassAd to the 
proactive_sdn_module, the module parses the ClassAds and gather useful info such
like the username of submitter, the IP address of the machine where the job will
execute. proactive_sdb_module stores all these information in a dictionary and 
the IP address of that job is the key.

A pox controller component (application_aware_switch) is implemented, aiming to 
utilize the parsed info from proactive_sdn_module to make network scheduling. 
The controller sends out corresponding OpenFlow action messages and install 
OpenFlow rules to the OpenVSwitch and higher-level OpenFlow switch to determine
how the switches should handle the incoming packets according to the predefined 
network policies.

After each job finishes executation, the network cleanup script would be invoked
and the inputs to the clenaup script are also the job and machien ClassAds. It 
sends the ClassAds to the proactive_sdn_module to let it know the classad info 
stored for IP address associated with this specific job should be deleted.

GridFTP only utilize the proactive_sdn_module currently to install OpenFlow 
rules according to pre-configured network policy.

2. Network Policy Examples
-------------------------

[HTCondor]

1) Access Control

Currently, there are some example polices applied on the OpenFlow controller. 
The owners of submitted jobs are divided into three groups. Group 1 is for 
blocked users. Users in this group are blocked to communicate with anywhere. As 
long as the OpenFlow controller sees the traffic coming from this user, it would
drop the packet. Group 2 is for users that are not allowed to communicate with 
outside network. At the same time, it cannot communicate with jobs from other 
users. Group 3 has most freedom, it can communicate with outside netowrk. The 
only constraint is that it cannot talk to jobs from other users either. We want 
to isolate jobs from different users by doing this.

2) QoS Management

In HTCondor, there are concepts of accounting group. Users belong to different 
accounting groups usually have different prioirty in terms of sharing resources.
The controller can examine which accounting group each HTCondor related traffic 
flow belongs to and redirect it to corresponding QoS queue when the traffic goes
to WAN.

[GridFTP]

QoS management for file transfers that access different directories is the only 
network policy for GridFTP currently. System admins can indicate a list of 
directories with decreasing priorities, the proactive_sdn_controller examines 
the application level info for each GridFTP file transfer and install the rule 
to proactively direct traffic to corresponding QoS queue at the WAN port.

3. Usage
--------

To use this SDN module, please make sure you have pox controller source code. 
Source code can be found at github: http://github.com/noxrepo/pox. Openvswitch 
is also required to install on worker node if you want to use this openflow 
controller to controll the virtual switch on each worker node.

At each worker node, first set the openvswitch fail mode to be standalone. 
In this mode, if the controller does not work well or the connection to openflow
controller is broken, openvswitch can go back to standalone mode to perform like
a regular l2 virtual switch. 

$ sudo ovs-vsctl set-fail-mode your_bridge_name standalone

Set the openflow controller host and port that openvswitch should listen to:

$ sudo ovs-vsctl set-controller your_bridge_name tcp:$(host):$(port)

The host and port are corresponding to the IP and port openflow controller is 
bind to.

At the controller host, copy the python source codes in this module into 
directory ~/pox/ext/ and make sure you python version is 2.7. Go to pox top 
level directory and do:

$ ./pox.py log.level --DEBUG application_aware_switch proactive_sdn_module

This will make openflow controller listen on all the interface (0.0.0.0) and 
port 6633 by default. If you want to change the port, you can also indicate that
by:

$ ./pox.py OpenFlow.of_01 --address=xxx.xxx.xxx.xxx --port=1234
  application_aware_switch proactive_sdn_module

4. HTCondor Related Configuration
---------------------------------

TODO: this would be moved into the sdn_controller.cfg eventually.

To use this module, serveral macros need to be configured in the HTCondor config
files.

BLOCKED_USERS: condor users who are blocked to communicate with anywhere, 
e.g. BLOCKED_USERS = zzhang, bbockelman

BLOCKED_USERS_OUTSIDE: condor users who are blocked to communicate with outside 
network, e.g. BLOCKED_USERS_OUTSIDE = gattebury

HTCONDOR_MODULE_HOST: IP of the host where the proactive_sdn_module is running

HTCONDOR_MODULE_PORT: Port of the host where the proactive_sdn_module binds to

WHITE_LIST_IP: the white list of IP addresses that job can comminicate with

NETWORK_NAMESPACE_CREATE_SCRIPT = /path/to/lark_setup_script.py

NETWORK_NAMESPACE_DELETE_SCRIPT = /path/to/lark_cleanup_script.py

5. SDN Controller Configuration
-------------------------------

The sdn_config_generator.py can generate an example of the SDN controller config
file. (sdn_controller.cfg is the example generated by this script). There are 
multiple sections in configuration file. "General" and all the applications such
as "HTCondor" and "GridFTP".

TODO: explain all the options

Detailed config options:

[General]

POLICY_MODE: application_oriented or project_oriented.

GENERAL_QOS_BANDWIDTH: bandwidth in Mbps for qos queues in project_oriented 
policy mode
