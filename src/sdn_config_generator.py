#!/usr/bin/python

"""
A script tool used to generate the configuration file 
for the application aware SDN controller. ConfigParser 
module is utilized. The users can easily add new options
in this script.
"""

import ConfigParser

config = ConfigParser.RawConfigParser()
config.optionxform = str

########################################################
#                                                      #
#                 General Section                      #
#                                                      #
########################################################

config.add_section('General')
config.set('General', 'POLICY_MODE', 'application_oriented')
#config.set('General', 'POLICY_MODE', 'project_oriented')
config.set('General', 'GENERAL_QOS_QUEUES_NUM', '3')
config.set('General', 'GENERAL_QOS_QUEUES_START_ID', '1')

projects = 'cms,hcc'
cms_users = 'zzhang,bbockelman'
hcc_users = 'larkuser1,larkuser2'
config.set('General', 'PROJECTS', projects)
config.set('General', 'CMS_USERS', cms_users)
config.set('General', 'HCC_USERS', hcc_users)

# set the qos queue bandwidth value, unit in bps (bits/second)
general_qos_bandwidth_values = '1000000000,8000000,4000000,4000000'
config.set('General', 'GENERAL_QOS_BANDWIDTH', general_qos_bandwidth_values)

application_list = 'General,HTCondor,GridFTP'
config.set('General', 'APPLICATION_LIST', application_list)

########################################################
#                                                      #
#                HTCondor Section                      #
#                                                      #
########################################################

config.add_section('HTCondor')
config.set('HTCondor', 'HTCONDOR_QOS_QUEUES_NUM', '3')
config.set('HTCondor', 'HTCONDOR_QOS_QUEUES_START_ID', '4')
htcondor_qos_bandwidth_values = '4000000,2000000,2000000'
config.set('HTCondor', 'HTCONDOR_QOS_BANDWIDTH', htcondor_qos_bandwidth_values)

########################################################
#                                                      #
#                 GridFTP Section                      #
#                                                      #
########################################################

config.add_section('GridFTP')
config.set('GridFTP', 'GRIDFTP_QOS_QUEUES_NUM', '4')
config.set('GridFTP', 'GRIDFTP_QOS_QUEUES_START_ID', '7')
gridftp_directories = '/test1/.*,/test2/.*,/test3/.*'
config.set('GridFTP', 'GRIDFTP_DIRECTORY_PRIORITY', gridftp_directories)
gridftp_qos_bandwidth_values = '4000000,2000000,1000000,4000000'
config.set('GridFTP', 'GRIDFTP_QOS_BANDWIDTH', gridftp_qos_bandwidth_values)

# generate the config file
with open('sdn_controller.cfg', 'wb') as config_file:
  config.write(config_file)
