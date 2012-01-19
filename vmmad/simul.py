#! /usr/bin/env python
#
"""
Simulate an `Orchestrator` run given some parameters.
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

import random
import os
import sys
import argparse

from orchestrator import Orchestrator, VmInfo
from util import Struct


class OrchestratorSimulation(Orchestrator):

    def __init__(self, max_vms, max_delta, max_idle, startup_delay,
                 job_number, min_duration, max_duration, output_file):
        Orchestrator.__init__(self, max_vms, max_delta)

        # no jobs are running at the onset, all are pending
        self._running = [ ]
        self._pending = [ Struct(job_number=random.randint(1,job_number*10),
                                 duration=random.randint(min_duration, max_duration))
                          for _ in range(0,job_number) ]

        self.max_idle = max_idle
        self.startup_delay = startup_delay
        self.output_file = output_file 

        # info about running VMs
        self._vmid = 0
        self._idle_vm_count = 0

        self._steps = 0
        
    def update_job_status(self):
        # do regular work
        Orchestrator.update_job_status(self)
        # simulate job run time passing and stop finished jobs
        done = [ ]
        for job in self._running:
            job.duration -= 1
            if job.duration <= 0:
                vm = job.vm
                vm.jobs.remove(job.job_number)
                done.append(job)
                self._idle_vm_count += 1
                logging.info("Job %s just finished; VM %s is now idle.",
                             job.job_number, vm.vmid)
        for job in done:
            self._running.remove(job)
        # simulate SGE scheduler starting a new job
        for vm in self._started_vms:
            if vm.last_idle > 0:
                if not self._pending:
                    break
                job = self._pending.pop()
                vm.jobs.append(job.job_number)
                job.vm = vm
                vm.last_idle = 0
                if self._idle_vm_count > 0:
                    self._idle_vm_count -= 1
                self._running.append(job)
                logging.info("Job %s just started running on VM %s.", job.job_number, vm.vmid)

    def get_sched_info(self):
        return (self._running, self._pending)

    def is_cloud_candidate(self, job):
        # every job is a candidate in this simulation
        return True

    def start_vm(self):
        self._vmid += 1
        logging.info("Started VM %s", self._vmid)
        return VmInfo(vmid=self._vmid,
                      been_running=0,
                      total_idle=0,
                      last_idle=(-self.startup_delay),
                      jobs=[])

    def update_vm_status(self):
        for vm in self._started_vms:
            vm.been_running += 1
            if not vm.jobs:
                vm.total_idle += 1
                vm.last_idle += 1

    def stop_vm(self, vm):
        logging.info("Stopping VM %s: has run for %d steps, been idle for %d of them",
                     vm.vmid, vm.been_running, vm.total_idle)
        if vm.last_idle > 0:
            self._idle_vm_count -= 1
        # nothing else to do, since the VM object is deleted by the
        # main `Orchestrator` class.
        return True

    def is_new_vm_needed(self):
        if len(self._pending) > 2 * len(self._running):
            return True

    def can_vm_be_stopped(self, vm):
        if vm.last_idle > self.max_idle:
            return True

    def before(self):
        self._steps += 1
        if len(self._pending) == 0 and len(self._running) == 0:
            logging.info("No more jobs, stopping simulation.")
            sys.exit(0)
        
        with open((self.output_file), "a") as output:
            output.write(
                "%s,%s,%s,%s,%s\n"
                #  no. of steps,      pending jobs,       running jobs,            started VMs,            idle VMs,
                %(self._steps, len(self._pending), len(self._running), len(self._started_vms), self._idle_vm_count))

        logging.info("At step %d: pending jobs %d, running jobs %d, started VMs %d, idle VMs %d",
                     self._steps, len(self._pending), len(self._running), len(self._started_vms), self._idle_vm_count)


if "__main__" == __name__:
    parser = argparse.ArgumentParser(description='Simulates a cloud orchestrator')
    parser.add_argument('--max-vms', '-mv', metavar='N', dest="max_vms", default=10, type=int, help="Maximum number of VMs to be started, default is %(default)s")
    parser.add_argument('--max-delta', '-md', metavar='N', dest="max_delta", default=1, type=int, help="To be defined")    
    parser.add_argument('--max-idle', '-mi', metavar='NUM_SECS', dest="max_idle", default=30, type=int, help="Maximum idle time (in seconds) before swithing off a VM, default is %(default)s")
    parser.add_argument('--startup-delay', '-S', metavar='NUM_SECS', dest="startup_delay", default=60, type=int, help="Time (in seconds) delay before staring up a VM, default is %(default)s")
    parser.add_argument('--job-number', '-jn', metavar='N', dest="job_number", default=50, type=int, help="Number of job to be started, default is %(default)s")
    parser.add_argument('--min-duration', '-mind', metavar='NUM_SECS', dest="min_duration", default=30, type=int, help="Lower bound for job's time (in seconds) execution, default is %(default)s")
    parser.add_argument('--max-duration', '-maxd', metavar='NUM_SECS', dest="max_duration", default=120, type=int, help="Upper bound for job's time (in seconds)  execution, default is %(default)s")
    parser.add_argument('--output-file', '-O',  metavar='String', dest="output_file", default="main_sim.txt", help="File name where the output of the simulation will be stored, %(default)s")
    parser.add_argument('--version', '-V', action='version',
                        version=("%(prog)s version " + __version__))
    args = parser.parse_args()
    OrchestratorSimulation(args.max_vms, args.max_delta, args.max_idle, args.startup_delay, args.job_number, args.min_duration, args.max_duration, args.output_file).run(0)
