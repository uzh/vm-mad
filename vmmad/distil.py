#! /usr/bin/env python
#
"""
Parse the output of a ``qstat -xml`` command or an SGE accounting information file,
and outputs the relevant "orchestrator" information in CSV format.
"""
# Copyright (C) 2011, 2012 ETH Zurich and University of Zurich. All rights reserved.
#
# Authors:
#   Tyanko Aleksiev <tyanko.alexiev@gmail.com>
#   Riccardo Murri <riccardo.murri@gmail.com>
#   Christian Panse <cp@fgcz.ethz.ch>
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
from __future__ import absolute_import

__docformat__ = 'reStructuredText'
__version__ = "1.0dev (SVN $Revision$)"


# stdlib imports
from copy import copy
import random
import os
import sys
import argparse
import gzip
import ge_info
import time
import csv
from time import mktime
from datetime import datetime

# local VM-MAD imports
from vmmad.orchestrator import JobInfo


class Distil():

    def __init__(self, data_dir, output_file, xml_parse,
                 accounting_file=None, output_delimiter=','):

        if accounting_file is not None:
            self.accounting_file = os.path.join(data_dir, accounting_file)
        else:
            self.accounting_file = None
        self.xml_parse = xml_parse
        self.output_file = output_file
        self.output_delimiter = output_delimiter
        ## load xml files
        self.qstat_xml_files = list(
            reversed(
                sorted(os.path.join(data_dir, filename)
                    for filename in os.listdir(data_dir)
                        if (filename.endswith('.xml') or filename.endswith('.xml.gz')) )))
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
            with  open(self.output_file, 'w') as f:
                csv_output = csv.writer(f, delimiter=self.output_delimiter)
                for job in self.__jobs:
                    if job.state == JobInfo.PENDING:
                        # Convert the submit time to UNIX time
                        struct_time = time.strptime(job.submit_time, "%Y-%m-%dT%H:%M:%S" )
                        dt = datetime.fromtimestamp(mktime(struct_time))
                        unix_sub_time = mktime(dt.timetuple())
                        # Calculate the duration
                        time_now = datetime.now()
                        unix_time_now = mktime(time_now.timetuple())
                        duration = unix_time_now - unix_sub_time
                        # Write the results to file
                        csv_output.writerow([job.jobid, unix_sub_time, duration])

    def parse_accounting_file(self):
        time_now = datetime.now()
        unix_time_now = int(mktime(time_now.timetuple()))
        outputFile = csv.writer(open(self.output_file, 'w'),
                                delimiter=self.output_delimiter)
        for line in open(self.accounting_file,'r').readlines():
            arrgs = line.split(':')
            if len(arrgs) >= 11 and int(arrgs[8]) !=0:
                duration = int(arrgs[10]) - int(arrgs[9])
                outputFile.writerow([arrgs[5]] + [(arrgs[8])] + [(duration)])

    def run(self):
        # Populate with the sched info. from the xml files.
        if self.xml_parse:
            self.parse_xml_files()
        if self.accounting_file is not None:
            # populate with the sched info. from the accounting files
            self.parse_accounting_file()

if "__main__" == __name__:
    parser = argparse.ArgumentParser(description='Distils `qstat -xml` and SGE account info ')
    parser.add_argument('data_dir', help="Path to the directory contaning qstat output files.")
    parser.add_argument('--output-file', '-o',  metavar='String', dest="output_file", default="accounting.csv", help="File name where the output of the distilation will be stored, %(default)s")
    parser.add_argument('--delimiter', '--output-delimiter', '-d', metavar='CHAR',
                        dest='output_delimiter', default=',',
                        help="Separator for the output fields.  Default: '%(default)s'")
    parser.add_argument('--accounting-file', '-I',  metavar='PATH', dest="accounting_file", default=None, help="Parse SGE 'accounting' file located at PATH.")
    parser.add_argument('--no-xml', '-nxml',  metavar='Boolean', dest="xml_parse", default=False , help="Disable parsing xml file, %(default)s")
    parser.add_argument('--version', '-V', action='version', version=("%(prog)s version " + __version__))
    args = parser.parse_args()
    Distil(args.data_dir, args.output_file,
           args.xml_parse, args.accounting_file,
           output_delimiter=args.output_delimiter).run()
