#! /usr/bin/env python
#
"""
Parses the output of the `qstat -xml` command or `SGE accounting information` putting everything in CVS format 
"""
# Copyright (C) 2011, 2012 ETH Zurich and University of Zurich. All rights reserved.
#
# Authors:
#   Christian Panse <cp@fgcz.ethz.ch>
#   Riccardo Murri <riccardo.murri@gmail.com>
#   Tyanko Aleksiev <tyanko.alexiev@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
__docformat__ = 'reStructuredText'
__version__ = "1.0dev (SVN $Revision$)"


import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(name)s: %(asctime)s: %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

from copy import copy
import random
import os
import sys
import argparse
import gzip 
import ge_info
import time 
from time import mktime
from datetime import datetime


class Distil():

    def __init__(self, data_dir, output_file):

	self.output_file = output_file
        # load data files
	## load xml files
	self.qstat_xml_files = list(
            reversed(
                sorted(os.path.join(data_dir, filename)
                       for filename in os.listdir(data_dir)
                       if (filename.endswith('.xml') or filename.endswith('.gz')) )))
	## load accounting files 
	self.accounting_files = list( 
	    reversed(
		sorted(os.path.join(data_dir, filename)
			for filename in os.listdir(data_dir) 
			if ((filename == "accounting") or (filename.endswith('\d') )))))	
        self.__jobs = [ ]
        self.__starting = 0

    def parse_xml_files(self):
	for filename in self.qstat_xml_files: 	
		if filename.endswith('.gz'):
               		with gzip.open(filename, 'r') as xml_file:    
      				xml_data = xml_file.read()
		else:
			with open(filename, 'r') as xml_file:
				xml_data = xml_file.read()
       		self.__jobs = ge_info.get_sched_info(xml_data)
		f = open(self.output_file, 'w')	
		for job in self.__jobs:
			if job.state == 1:
				# Convert the submit time to UNIX time 
				struct_time = time.strptime(job.submit_time, "%Y-%m-%dT%H:%M:%S" )
				dt = datetime.fromtimestamp(mktime(struct_time))
				unix_sub_time = mktime(dt.timetuple())
				# Calculate the duration 
				time_now = datetime.now()
				unix_time_now = mktime(time_now.timetuple())
				duration = unix_time_now - unix_sub_time
				# Write the results to file
				to_file = job.jobid + ' ' + str(unix_sub_time) + ' ' + str(duration) 
				f.write(to_file)
				f.write('\n')
						

    def run(self):
	self.parse_xml_files()
 
if "__main__" == __name__:
    parser = argparse.ArgumentParser(description='Distils `qstat -xml` and SGE account info ')
    parser.add_argument('data_dir', help="Path to the directory contaning qstat output files.")
    parser.add_argument('--output-file', '-O',  metavar='String', dest="output_file", default="output.txt", help="File name where the output of the distilation will be stored, %(default)s")
    parser.add_argument('--version', '-V', action='version', version=("%(prog)s version " + __version__))
    args = parser.parse_args()
    Distil(args.data_dir, args.output_file).run()
