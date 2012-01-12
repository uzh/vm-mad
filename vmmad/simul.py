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
__version__ = '$Revision$'


import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(name)s: [%(asctime)s] %(levelname)-8s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

import random
import os
import sys


from orchestrator import Orchestrator
from util import Struct


class OrchestratorSimulation(Orchestrator):

    def __init__(self, max_vms, max_delta=1, max_idle=0, startup_delay=60,
                 job_number=20, min_duration=1800, max_duration=3600):
        Orchestrator.__init__(self, max_vms, max_delta)

        # no jobs are running at the onset, all are pending
        self._running = [ ]
        self._pending = [ Struct(job_number=random.randint(1,job_number*10),
                                 duration=random.randint(min_duration, max_duration))
                          for _ in range(0,job_number) ]

        self.max_idle = max_idle
        self.startup_delay = startup_delay
        
        # info about running VMs
        self._vmid = 0
        self._started_vms = { }
        self._idle_vm_count = 0

        self._steps = 0
        
    def update_job_status(self):
        # do regular work
        Orchestrator.update_job_status(self)
        # book-keeping
        done = [ ]
        for job in self._running:
            job.duration -= 1
            if job.duration <= 0:
                vm_for_job = job.vm
                vm_for_job.jobs.remove(job.job_number)
                done.append(job)
                self._idle_vm_count += 1
                logging.info("Job %s just finished; VM %s is now idle.", job.job_number, vm_for_job.vmid)
        for job in done:
            self._running.remove(job)
        # simulate SGE scheduler starting job
        for vmid in self._started_vms:
            vm = self._started_vms[vmid]
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
        self._started_vms[self._vmid] = Struct(vmid=self._vmid, been_running=0, total_idle=0, last_idle=(-self.startup_delay), jobs=[])
        logging.info("Started VM %s", self._vmid)
        return self._vmid

    def update_vm_status(self):
        for vmid in self._started_vms:
            self._started_vms[vmid].been_running += 1
            if not self._started_vms[vmid].jobs:
                self._started_vms[vmid].total_idle += 1
                self._started_vms[vmid].last_idle += 1

    def stop_vm(self, vmid):
        logging.info("Stopping VM %s: has run for %d steps, been idle for %d of them",
                     vmid,
                     self._started_vms[vmid].been_running,
                     self._started_vms[vmid].total_idle)
        if self._started_vms[vmid].last_idle > 0:
            self._idle_vm_count -= 1
        del self._started_vms[vmid]
        return True

    def is_new_vm_needed(self):
        if len(self._pending) > 2 * len(self._running):
            return True

    def can_vm_be_stopped(self, vmid):
        if self._started_vms[vmid].last_idle > self.max_idle:
            return True

    def before(self):
        self._steps += 1
        if len(self._pending) == 0 and len(self._running) == 0:
            logging.info("No more jobs, stopping simulation.")
            sys.exit(0)
        
        with open(("main_sim.txt"), "a") as output:
            output.write(
                "%s,%s,%s,%s,%s\n"
                #  no. of steps,      pending jobs,       running jobs,            started VMs,            idle VMs,
                %(self._steps, len(self._pending), len(self._running), len(self._started_vms), self._idle_vm_count))

        logging.info("At step %d: pending jobs %d, running jobs %d, started VMs %d, idle VMs %d",
                     self._steps, len(self._pending), len(self._running), len(self._started_vms), self._idle_vm_count)



if "__main__" == __name__:
    OrchestratorSimulation(max_vms=20, max_idle=30, startup_delay=60, job_number=200, min_duration=3*360, max_duration=4*360).run(0.00001)
