htcondor-sdn-module
===================

Developing SDN module to support job scheduling at network layer

The sdn module has three components: network setup script, htcondor module and 
pox controller component.

For each job in Lark, before the network configuration is finished, a callout 
network setup script is called. The input to the setup script is just the job 
and machine ClassAds. 

The setup script sents the ClassAds to a htcondor module that runs at the same 
remote host as the openflow controller (in our case, a pox controller) does. 
The htcondor module performs like a TCP socket server, which can handle the 
request from multiple jobs. Whenever a job sents the ClassAd to the htcondor 
module, the module parses the ClassAds and gather useful info such like 
the username of submitter, the IP address of the machine where the job will 
execute.

A pox controller component is also implemented, aiming to utilize the parsed 
info from the htcondor module to make network scheduling. The controller sends 
out corresponding openflow action messages to the openvswitch or higher-level 
openflow switch to determine how the switches should handle the incoming 
packets according to the predefined network policies.
