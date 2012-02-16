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


# stdlib imports
from copy import copy
import random
import os
import sys
import argparse
import csv
import time
from time import mktime
from datetime import datetime


# local imports
from vmmad import log
import cloud
from orchestrator import Orchestrator, JobInfo, VmInfo

class OrchestratorSimulation(Orchestrator, cloud.DummyCloud):

    def __init__(self, max_vms, max_delta, max_idle, startup_delay,
                 job_number, min_duration, max_duration, output_file, csv_file, start_time, time_interval, cluster_size):
        # implement the `Cloud` interface to simulate a cloud provider
        cloud.DummyCloud.__init__(self, '1', '1')

        # init the Orchestrator part, using `self` as cloud provider
        Orchestrator.__init__(self, self, max_vms, max_delta)

        # Convert starting time to UNIX time
        struct_time = time.strptime(start_time, "%Y-%m-%dT%H:%M:%S" )
        dt = datetime.fromtimestamp(mktime(struct_time))
        self.sched_time = int(mktime(dt.timetuple()))
	
        # Set simulation settings
        self.max_idle = max_idle
        self.startup_delay = startup_delay
        self.output_file = output_file
        self.cluster_size = int(cluster_size) 
        self.time_interval = int(time_interval)
        self.job_time_interval = int(time_interval)
        self._next_row = None

        # info about running VMs
        self._vmid = 0 
        self._idle_vm_count = 0
        self._steps = 0
      
        self._running = [ ]
        self._pending = [ JobInfo(jobid=1, state=JobInfo.PENDING, duration=0) ]

        self.input_file = open(csv_file, 'r')
        self.csv_file = csv.reader(self.input_file, delimiter=' ')

    def update_job_status(self):
        # do regular work	
        Orchestrator.update_job_status(self)
        # simulate job run time passing and stop finished jobs
        for job in copy(self._running):
            job.duration -= self.job_time_interval
            if job.duration <= 0:
                vm = job.vm
                vm.jobs.remove(job.jobid)
                self._running.remove(job)
                if not vm.ever_running:
                    self._idle_vm_count += 1
                    log.info("Job %s just finished; VM %s is now idle.",
                        job.jobid, vm.vmid)
        # simulate SGE scheduler starting a new job
        for vm in self._started_vms:
            if vm.last_idle > 0:
                if not self._pending:
                    break
                job = self._pending.pop()
                vm.jobs.add(job.jobid)
                job.vm = vm
                vm.last_idle = 0
                if not vm.ever_running: 
                    if self._idle_vm_count > 0:
                        self._idle_vm_count -= 1
                self._running.append(job)
                log.info("Job %s just started running on VM %s.", job.jobid, vm.vmid)

    def before(self):
        self._steps += 1
        if len(self._running) == 0 and len(self._pending) == 0 and self.csv_file is None:
            log.info("No more jobs to read from file '%s', stopping here", self.input_file.name)
            sys.exit(0)
            
        with open((self.output_file), "a") as output:
            output.write(
                "%s,%s,%s,%s,%s\n"
                #  no. of steps,      pending jobs,       running jobs,            started VMs,            idle VMs,
                %(self._steps, len(self._pending), len(self._running), len(self._started_vms), self._idle_vm_count))

        log.info("At time %d: pending jobs %d, running jobs %d, started VMs %d, idle VMs %d",
                     (self.sched_time + self.time_interval*self._steps), len(self._pending), len(self._running), len(self._started_vms), self._idle_vm_count)


    ##
    ## Interface to the CSV file format
    ##
    def get_sched_info(self):
        time_step =  Orchestrator.get_time_step(self)
        previous_time = self.sched_time + (time_step-1)*self.time_interval
        new_time= self.sched_time + time_step*self.time_interval
        for job in self.read_next_jobs(previous_time, new_time): 
            self._pending.append(job)
        return (self._running + self._pending)

    def read_next_jobs(self, since, until):
        while self.csv_file is not None:
            try:    
                row = self._next_row or self.csv_file.next()
            except StopIteration:
                self.csv_file = None
                raise
            submit_time = int(row[1])
            if since > submit_time:
                if since <= until:
                    self._next_row = None
                    yield JobInfo(jobid=int(row[0]), state=JobInfo.PENDING, duration=int(row[2]))
                else:
                    # job is in the past (relative to the Simulator's conecpt of time) so ignore it
                    pass
            else:
                # job is in the future: stop here and use it next time around
                self._next_row = row
                raise StopIteration


    ##
    ## policy implementation interface
    ##
    def is_cloud_candidate(self, job):
        # every job is a candidate in this simulation
        return True

    def is_new_vm_needed(self):
        if len(self._pending) > 2 * len(self._running):
            return True

    def can_vm_be_stopped(self, vm):
        if vm.last_idle > self.max_idle:
            return True


    ##
    ## (fake) cloud provider interface
    ##

    def start_vm(self, vm):
        cloud.DummyCloud.start_vm(self, vm)
        log.info("Started VM %d (%s).", vm.vmid, vm.instance.uuid)
        vm.been_running=0
        vm.total_idle=0

        # Setting the first "cluster_size" machines to be ever_running. 
        if vm.vmid <= self.cluster_size:
            vm.ever_running = True 
            vm.last_idle = 1 
        else:
            vm.ever_running = False 
            vm.last_idle=(-self.startup_delay)

    def update_vm_status(self, vms):
        cloud.DummyCloud.update_vm_status(self, vms)
        for vm in self._started_vms:
            if not vm.ever_running:
                vm.been_running += self.time_interval
                if not vm.jobs:
                    vm.total_idle += self.time_interval
                    vm.last_idle += self.time_interval
            else:
                if not vm.jobs:
                    vm.last_idle = 1  

    def stop_vm(self, vm):
        log.info("Stopping VM %s (%s): has run for %d steps, been idle for %d of them",
                     vm.vmid, vm.instance.uuid, vm.been_running, vm.total_idle)
        cloud.DummyCloud.stop_vm(self, vm)
        if vm.last_idle > 0 and self._idle_vm_count > 0 and not vm.ever_running:
            self._idle_vm_count -= 1
        return True



if "__main__" == __name__:
    parser = argparse.ArgumentParser(description='Simulates a cloud orchestrator')
    parser.add_argument('--max-vms', '-mv', metavar='N', dest="max_vms", default=10, type=int, help="Maximum number of VMs to be started, default is %(default)s")
    parser.add_argument('--max-delta', '-md', metavar='N', dest="max_delta", default=1, type=int, help="To be defined")    
    parser.add_argument('--max-idle', '-mi', metavar='NUM_SECS', dest="max_idle", default=7200, type=int, help="Maximum idle time (in seconds) before swithing off a VM, default is %(default)s")
    parser.add_argument('--startup-delay', '-s', metavar='NUM_SECS', dest="startup_delay", default=3600, type=int, help="Time (in seconds) delay before staring up a VM, default is %(default)s")
    parser.add_argument('--job-number', '-jn', metavar='N', dest="job_number", default=50, type=int, help="Number of job to be started, default is %(default)s")
    parser.add_argument('--min-duration', '-mind', metavar='NUM_SECS', dest="min_duration", default=30, type=int, help="Lower bound for job's time (in seconds) execution, default is %(default)s")
    parser.add_argument('--max-duration', '-maxd', metavar='NUM_SECS', dest="max_duration", default=120, type=int, help="Upper bound for job's time (in seconds)  execution, default is %(default)s")
    parser.add_argument('--csv-file', '-csvf',  metavar='String', dest="csv_file", default="output.csv", help="File containing the CSV information, %(default)s")
    parser.add_argument('--output-file', '-o',  metavar='String', dest="output_file", default="main_sim.txt", help="File name where the output of the simulation will be stored, %(default)s") 
    parser.add_argument('--cluster-size', '-cs',  metavar='NUM_CPUS', dest="cluster_size", default="20", help="Number of VMs, used for the simulation of real available cluster: %(default)s")
    parser.add_argument('--start-time', '-stime',  metavar='String', dest="start_time", default="1970-01-01T00:00:00", help="Start time for the simulation, default: %(default)s")
    parser.add_argument('--time-interval', '-timei',  metavar='NUM_SECS', dest="time_interval", default="3600", help="UNIX interval in seconds used as parsing interval for the jobs in the CSV file, default: %(default)s")
    parser.add_argument('--version', '-V', action='version',
                        version=("%(prog)s version " + __version__))
    args = parser.parse_args()
    OrchestratorSimulation(args.max_vms, args.max_delta, args.max_idle, args.startup_delay, args.job_number, args.min_duration, args.max_duration, args.output_file, args.csv_file, args.start_time, args.time_interval, args.cluster_size).run(0)
