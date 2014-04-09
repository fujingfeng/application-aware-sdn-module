#!/usr/bin/python

import sys
import os

# script used to clear qos and queue record for openvswitch < 1.8
# need to first run the following commands to get qos and queue uuid file
os.system('ovs-vsctl list queue | grep _uuid > queue_uuid.txt')
os.system('ovs-vsctl list qos | grep _uuid > qos_uuid.txt')

qos_file = open('qos_uuid.txt', 'r')
for line in qos_file.readlines():
    uuid = line.split(':')[1].strip()
    os.system('ovs-vsctl destroy qos ' + uuid)

qos_file.close()

queue_file = open('queue_uuid.txt', 'r')
for line in queue_file.readlines():
    uuid = line.split(':')[1].strip()
    os.system('ovs-vsctl destroy queue ' + uuid)

queue_file.close()
