#!/usr/bin/python

"""
A script tool used to generate the configuration file 
for the application aware SDN controller. ConfigParser 
module is utilized. The users can easily add new options
in this script.
"""

import ConfigParser

config = ConfigParser.RawConfigParser()

########################################################
#                                                      #
#                 General Section                      #
#                                                      #
########################################################

config.add_section('General')
config.set('General', 'policy_mode', 'application_oriented')
#config.set('General', 'policy_mode', 'project_oriented')
config.set('General', 'general_qos_queues_num', '3')
config.set('General', 'general_qos_queues_start_id', '1')

projects = 'cms,hcc'
cms_users = 'zzhang,bbockelman'
hcc_users = 'larkuser1,larkuser2'
config.set('General', 'projects', projects)
config.set('General', 'cms_users', cms_users)
config.set('General', 'hcc_users', hcc_users)

# set the qos queue bandwidth value, unit in bps (bits/second)
general_qos_bandwidth_values = '1000000000,8000000,4000000,4000000'
config.set('General', 'general_qos_bandwidth', general_qos_bandwidth_values)

application_list = 'General,HTCondor,GridFTP'
config.set('General', 'application_list', application_list)

########################################################
#                                                      #
#                HTCondor Section                      #
#                                                      #
########################################################

config.add_section('HTCondor')
config.set('HTCondor', 'htcondor_qos_queues_num', '3')
config.set('HTCondor', 'htcondor_qos_queues_start_id', '4')
htcondor_qos_bandwidth_values = '4000000,2000000,2000000'
config.set('HTCondor', 'htcondor_qos_bandwidth', htcondor_qos_bandwidth_values)

########################################################
#                                                      #
#                 GridFTP Section                      #
#                                                      #
########################################################

config.add_section('GridFTP')
config.set('GridFTP', 'gridftp_qos_queues_num', '4')
config.set('GridFTP', 'gridftp_qos_queues_start_id', '7')
gridftp_directories = '/test1/.*,/test2/.*,/test3/.*'
config.set('GridFTP', 'gridftp_directory_priority', gridftp_directories)
gridftp_qos_bandwidth_values = '4000000,2000000,1000000,4000000'
config.set('GridFTP', 'gridftp_qos_bandwidth', gridftp_qos_bandwidth_values)

# generate the config file
with open('sdn_controller.cfg', 'wb') as config_file:
    config.write(config_file)
