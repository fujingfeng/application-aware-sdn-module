#!/usr/bin/python

"""
A script tool to generate and execute corresponding openvswitch
qos configuration command. The number of queues and bandwidth for 
each queue is retrieved from SDN controller config file. The order 
of queues are created in the order of application list; within 
each application, the queues are created in the same order as the
pre-configured priority.
"""

import sdn_controller_config as controller_config
import os

config_file = '/home/bockelman/zzhang/pox/ext/sdn_controller.cfg'
config_retrieval = controller_config.config_retrieval(config_file)

app_queue_num_list = []
app_queue_start_id_list = []

# list of bandwidths for all the qos queues in order
qos_bandwidth_list = []

application_list = config_retrieval.get_application_list()

for application in application_list:
    queue_num, queue_start_id = config_retrieval.get_qos_info(application)
    app_queue_num_list.append(queue_num)
    app_queue_start_id_list.append(queue_start_id)
    app_qos_bandwidth = config_retrieval.get_qos_bandwidth(application)
    for bandwidth in app_qos_bandwidth:
        qos_bandwidth_list.append(bandwidth)

eth_dev = 'eth0'
queues = 'queues='
queue_num = len(qos_bandwidth_list)
for i in range(queue_num):
    queues = queues + str(i) + '=@q' + str(i)
    if i != len(qos_bandwidth_list)-1:
        queues = queues + ','

ovs_command = 'ovs-vsctl set port ' + eth_dev + ' qos=@newqos -- --id=@newqos ' \
            + 'create qos type=linux-htb other-config:max-rate=' + qos_bandwidth_list[0]

ovs_command = ovs_command + ' ' + queues

for i in range(queue_num):
    create_queue_str = '-- --id=@q' + str(i) + ' create queue other-config:min-rate=' \
                    + qos_bandwidth_list[i] + ' other-config:max-rate=' + qos_bandwidth_list[i]
    ovs_command = ovs_command + ' ' + create_queue_str

#print ovs_command
os.system(ovs_command)
