#!/usr/bin/python

#
# The script takes the job and machine classad from stdin, and 
# sends it to the htcondor module that runs at the remote host 
# (where pox controller also runs) for further processing 
#


import sys
import classad
import re
import socket

# get job classad from stdin
job_ad = sys.stdin.readline()

# get seperator line
separator_line = sys.stdin.readline()
assert separator_line == "------\n"

# get machine classad from stdin
machine_ad = sys.stdin.readline()

send_data = job_ad + "\n" + machine_ad + "\n"


# connect to the htcondor module and send out the classads
HOST, PORT = "localhost", 9008

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
  sock.connect((HOST, PORT))
  sock.sendall(send_data)
finally:
  sock.close()
