#!/usr/bin/python

import ConfigParser

class ConfigRetrieval:

  """
  A class used to get the detailed configuration items in 
  the application-aware controller configuration file
  """
    
  def __init__(self, config_file_name):

    self.config_file_name = config_file_name
    self.delimiter = ','
    self.config = ConfigParser.RawConfigParser()
    self.config.optionxform = str
    self.config.read(self.config_file_name)

  def get_policy_mode(self):
        
    """
    return the network policy mode, either 'application_oriented'
    or 'user_oriented'
    """
    return self.config.get('General', 'POLICY_MODE')

  def get_application_list(self):
        
    """
    return the list of applications in the config file,
    the order of the application in the list matters, it
    determines the order of QoS queue id for each app accordingly.
    """
    return self.config.get('General', 'APPLICATION_LIST').split(self.delimiter)

  def get_projects_list(self):

    """
    return the list of projects, such as CMS, ATLAS, etc.
    """
    return self.config.get('General', 'PROJECTS').split(self.delimiter)

  def get_project_users(self, project_name):

    """
    return the list of usernames that belongs to one project,
    if users option corresponding to this project name is not
    defined in config file, return None instead.
    """
    option = project_name.upper() + '_USERS'
    try:
      return self.config.get('General', option).split(self.delimiter)
    except ConfigParser.NoOptionError:
      return None

  def check_user_project(self, username):
        
    """
    return the project name that a given username belongs to, 
    if not found any affliations, return None instead.
    """
    projects = self.get_projects_list()
    for project in projects:
      user_list = self.get_project_users(project)
      if user_list is not None and username in user_list:
        return project

    return None

  def get_gridftp_directory_priority(self):
        
    """
    return a list of GridFTP file transfer directory priorities,
    the priorities is indicated by the order in the list, the 
    directory apperas in the front has higher priority.
    """
    return self.config.get('GridFTP', 
                           'GRIDFTP_DIRECTORY_PRIORITY').split(self.delimiter)

  def get_qos_info(self, application):
        
    """
    return the number of pre-configured QoS queus and the starting queue ID.
    The result is application dependent, can be HTCondor, GridFTP, General...
    """
    queue_num = self.config.get(application, 
                                application.upper()+'_QOS_QUEUES_NUM')
    queue_start_id = self.config.get(application, 
                                     application.upper()+'_QOS_QUEUES_START_ID')
    return int(queue_num), int(queue_start_id)

  def get_qos_bandwidth(self, application):
        
    """
    return the list of pre-configured QoS queue bandwidth for one application.
    The result is application dependent, can be HTCondor, GridFTP, General...
    """
    qos_bandwidth = self.config.get(application, 
                                    application.upper()+'_QOS_BANDWIDTH')
    qos_bandwidth = qos_bandwidth.split(self.delimiter)
    return qos_bandwidth

# some constants used in other modules
HARD_TIMEOUT = 600
IDLE_TIMEOUT = 5
CONFIG_FILENAME = '/home/bockelman/zzhang/pox/ext/sdn_controller.cfg'

# retrieval all the option value for other modules to use
config = ConfigRetrieval(CONFIG_FILENAME)
policy_mode = config.get_policy_mode()
projects_list = config.get_projects_list()
gridftp_directory_priority = config.get_gridftp_directory_priority()
gridftp_queues_num, gridftp_queues_start_id = config.get_qos_info('GridFTP')
htcondor_queues_num, htcondor_queues_start_id = config.get_qos_info('HTCondor')
general_queues_num, general_queues_start_id = config.get_qos_info('General')
