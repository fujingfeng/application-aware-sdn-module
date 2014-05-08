#!/usr/bin/python

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as md
import csv
from time import mktime
from datetime import datetime
from matplotlib.ticker import MultipleLocator

# list the files need to be read
csv_file_1 = '/Users/zhezhang/Desktop/htcondor_8Mbps.csv'
csv_file_2 = '/Users/zhezhang/Desktop/htcondor_4Mbps.csv'

# first read the csv files
f1 = open(csv_file_1, 'rb')
f2 = open(csv_file_2, 'rb')

reader1 = csv.reader(f1)
reader2 = csv.reader(f2)

# define two array of data
# x represent time; y represent bandwidth
x1 = []
y1 = []

x2 = []
y2 = []

for row in reader1:
  x = row[0]
  y = row[1]
  if y != 'NaN':
    x1.append(x)
    y1.append(y)
f1.close()

for row in reader2:
  x = row[0]
  y = row[1]
  if y != 'NaN':
    x2.append(x)
    y2.append(y)
f2.close()

x1.pop(0)
y1.pop(0)
x2.pop(0)
y2.pop(0)

# pre-process the time data
for i in range(len(x1)):
  lines = x1[i].split('T')
  date = lines[0]
  lines = lines[1].split('-')
  time = lines[0]
  date_time = datetime.strptime(date + ' ' + time, "%Y-%m-%d %H:%M:%S")
  #unix_time = mktime(date_time.timetuple())
  x1[i] = date_time

# pre-process the time data
for i in range(len(x2)):
  lines = x2[i].split('T')
  date = lines[0]
  lines = lines[1].split('-')
  time = lines[0]
  date_time = datetime.strptime(date + ' ' + time, "%Y-%m-%d %H:%M:%S")
  #unix_time = mktime(date_time.timetuple())
  x2[i] = date_time

# convert bandwidth Value to Mbps
# (bytes/second * 8 ) / 1000000 (divide by 1M)
for i in range(len(y1)):
  y1[i] = (float(y1[i]))*8/1000000
for i in range(len(y2)):
  y2[i] = (float(y2[i]))*8/1000000

dates1 = md.date2num(x1)
dates2 = md.date2num(x2)

#ax = plt.gca()
fig, ax = plt.subplots()
xfmt = md.DateFormatter('%H:%M')

byminute = (0,10,20,30,40,50)
majorLocator = md.MinuteLocator(byminute)
minorLocator = md.MinuteLocator(interval=2)

ax.xaxis.set_major_locator(majorLocator)
ax.xaxis.set_major_formatter(xfmt)
ax.xaxis.set_minor_locator(minorLocator)
ax.xaxis.grid(True, which='major')
ax.xaxis.grid(True, which='minor')
ax.yaxis.grid(True)


ax.plot_date(dates1, y1, linewidth = 2.5, linestyle='-', color='r', 
            marker='', label='CMS HTCondor Traffic')
plt.fill(dates1, y1, 'r', alpha=0.3)
plt.plot_date(dates2, y2, linewidth = 2.5, linestyle='-', color='b', 
            marker='', label='NonCMS HTCondor Traffic')
plt.fill(dates2, y2, 'b', alpha=0.3)
#plt.grid(True)
plt.xlabel('Time (HH:MM)')
plt.ylabel('Traffic Rate (Mbps)')
plt.legend(('CMS Traffic', 'NonCMS Traffic'), loc = 'upper right')
plt.show()
