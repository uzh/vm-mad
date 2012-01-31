#! /usr/bin/env python
#
"""
Simulate an `Orchestrator` run given example `qstat` output.
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

from cloud import Cloud
from orchestrator import Orchestrator, JobInfo, VmInfo
import ge_info


class GEOrchestratorSimulation(Orchestrator, Cloud):

    def __init__(self, qstat_xml_dir, max_vms, max_delta, max_idle, startup_delay, output_file):
        # implement the `Cloud` interface to simulate a cloud provider
        Cloud.__init__(self, None, None)

        # init the Orchestrator part, using `self` as cloud provider
        Orchestrator.__init__(self, self, max_vms, max_delta)

        self._steps = 0

        self.max_idle = max_idle
        self.startup_delay = startup_delay
        self.output_file = output_file

        # load data files
        self.qstat_xml_files = list(
            reversed(
                sorted(os.path.join(qstat_xml_dir, filename)
                       for filename in os.listdir(qstat_xml_dir)
                       if (filename.endswith('.xml') or filename.endswith('.gz')) )))

        self.__jobs = [ ]
        self.__starting = 0

    def before(self):
        self._steps += 1
        if 0 == len(self.qstat_xml_files):
            logging.info("No more data files, stopping simulation.")
            sys.exit(0)

        # reset counter of "starting" VMs
        self.__starting = 0

    def after(self):
        running = [job for job in self.__jobs if job.state == JobInfo.RUNNING]
        pending = [job for job in self.__jobs if job.state == JobInfo.PENDING]
        
        with open((self.output_file), "a") as output:
            output.write(
                "%s,%s,%s,%s,%s\n"
                #no. of steps, pending jobs, running jobs, started VMs,     idle VMs,
                %(self._steps, len(pending), len(running), self.__starting, 0))

        logging.info("At step %d: pending jobs %d, running jobs %d, starting VMs %d, idle VMs %d",
                     self._steps, len(pending),    len(running),    self.__starting, 0)


    ##
    ## interface to the batch queue scheduler
    ##
    def get_sched_info(self):
        # read data from next file
        filename = self.qstat_xml_files.pop()
        if filename.endswith('.gz'):
            with gzip.open(filename, 'r') as xml_file:    
                xml_data = xml_file.read()
        else:
            with open(filename, 'r') as xml_file:
                xml_data = xml_file.read()

        self.__jobs = ge_info.get_sched_info(xml_data)
        return self.__jobs


    ##
    ## policy implementation interface
    ##
    def is_cloud_candidate(self, job):
        # XXX: only jobs submitted to the "cloud@" queue are candidates?
        return True

    def is_new_vm_needed(self):
        if len(self.candidates) > 0:
            return True


    def can_vm_be_stopped(self, vm):
        return True


    ##
    ## (fake) cloud provider interface
    ##
    def start_vm(self, vm):
        logging.warning("Would start a new VM (if this were a real Orchestrator)")
        self.__starting += 1
        # ...but fail!
        vm.state = VmInfo.DOWN


    def update_vm_status(self, vms):
        pass


    def stop_vm(self, vm):
        logging.error("Request to stop VM %s,"
                      " which was never started in the first place",
                      vm.vmid)
        return False



if "__main__" == __name__:
    parser = argparse.ArgumentParser(description='Simulates a cloud orchestrator')
    parser.add_argument('data_dir', 
                        help="Path to the directory contaning qstat output files.")
    parser.add_argument('--max-vms', '-mv', metavar='N', dest="max_vms", default=10, type=int, help="Maximum number of VMs to be started, default is %(default)s")
    parser.add_argument('--max-delta', '-md', metavar='N', dest="max_delta", default=1, type=int, help="To be defined")    
    parser.add_argument('--max-idle', '-mi', metavar='NUM_SECS', dest="max_idle", default=30, type=int, help="Maximum idle time (in seconds) before swithing off a VM, default is %(default)s")
    parser.add_argument('--startup-delay', '-S', metavar='NUM_SECS', dest="startup_delay", default=60, type=int, help="Time (in seconds) delay before staring up a VM, default is %(default)s")
    parser.add_argument('--output-file', '-O',  metavar='String', dest="output_file", default="main_sim.txt", help="File name where the output of the simulation will be stored, %(default)s")
    parser.add_argument('--version', '-V', action='version',
                        version=("%(prog)s version " + __version__))
    args = parser.parse_args()
    GEOrchestratorSimulation(args.data_dir, args.max_vms, args.max_delta, args.max_idle, args.startup_delay, args.output_file).run(0)
