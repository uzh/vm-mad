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
from __future__ import absolute_import

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
from vmmad.provider.libcloud import DummyCloud
from orchestrator import Orchestrator, JobInfo, VmInfo


class OrchestratorSimulation(Orchestrator, DummyCloud):

    def __init__(self, max_vms, max_delta, max_idle, startup_delay,
                 job_number, min_duration, max_duration,
                 output_file, csv_file, start_time, time_interval, cluster_size):
        # implement the `Cloud` interface to simulate a cloud provider
        DummyCloud.__init__(self, '1', '1')

        # init the Orchestrator part, using `self` as cloud provider
        Orchestrator.__init__(self, cloud=self,
                              max_vms=(max_vms+cluster_size),
                              max_delta=max_delta)

        # no jobs are running at the onset, all are pending
        self._running = [ ]             
        
        #Random generated pending jobs
        #self._pending = [ JobInfo(jobid=random.randint(1,job_number*10),
        #                          state=JobInfo.PENDING,
        #                          duration=random.randint(min_duration, max_duration))
        #                  for _ in range(0,job_number) ]
        
        self._pending = [ JobInfo(jobid=0, state=JobInfo.PENDING, duration=1) ]
        
        # Set simulation settings
        self.max_idle = max_idle
        self.startup_delay = startup_delay
        self.cluster_size = cluster_size

        self.output_file = open(output_file, "wb") 
        self.writer = csv.writer(self.output_file, delimiter=',')
        self.writer.writerow(
            ['#TimeStamp'] + ['Pending Jobs'] + ['Running Jobs'] + ['Started VMs'] + ['Idle VMS'])
           
        self.time_interval = int(time_interval)
        self._next_row = None

        # info about running VMs
        self._vmid = 0 
        self._idle_vm_count = 0
      
        self._running = [ ]
        self._pending = [ JobInfo(jobid=1, state=JobInfo.PENDING, duration=0) ]

        # Convert starting time to UNIX time (may read the first CSV file line)
        if start_time is not None: 
            self.starting_time = mktime(time.strptime(start_time, "%Y-%m-%dT%H:%M:%S" ))
        else:
            # use an impossible value that makes us accept all jobs
            # from the CSV file; will correct this later on
            self.starting_time = -1
        
        # auto-detect CSV delimiter, etc.
        with open(csv_file, 'r') as input_file:
            sample = input_file.read(1024)
            input_file.seek(0)
            rows = csv.DictReader(input_file,
                                  dialect = csv.Sniffer().sniff(sample))
            # load all jobs into memory, ordered by descending
            # submission time, so that the last item is the next job
            # to be submitted and we can just .pop() it
            self.__jobs = list(
                sorted((JobInfo(jobid=row['JOBID'],
                                state=JobInfo.PENDING,
                                submitted_at=float(row['SUBMITTED_AT']),
                                duration=float(row['RUN_DURATION']))
                        for row in rows if float(row['SUBMITTED_AT']) > self.starting_time),
                    # sort list of jobs by submission time
                    cmp=(lambda x,y: cmp(x.submitted_at, y.submitted_at)),
                    reverse=True))
            assert self.__jobs[0].submitted_at >= self.__jobs[1].submitted_at
        log.info("Loaded %d jobs from file '%s'", len(self.__jobs), csv_file)
        
        # if `starting_time` has not been set, then use earliest job
        # submission time as starting point
        if self.starting_time == -1:
            self.starting_time = self.__jobs[-1].submitted_at - self.time_interval
            log.info("Starting simulation at %s",
                     time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(self.starting_time)))


    def update_job_status(self):
        # do regular work       
        Orchestrator.update_job_status(self)
        # simulate job run time passing and stop finished jobs
        for job in copy(self._running):
            job.duration -= self.time_interval
            if job.duration <= 0:
                vm = job.vm
                vm.jobs.remove(job.jobid)
                self._running.remove(job)
                if not vm.ever_running:
                    self._idle_vm_count += 1
                    log.info("Job %s just finished; VM %s is now idle.",
                        job.jobid, vm.vmid)
        # simulate SGE scheduler starting a new job
        for vm in self._started_vms.values():
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
        if len(self._running) == 0 and len(self._pending) == 0 and len(self.__jobs) == 0:
            log.info("No more jobs, stopping here")
            self.output_file.close()
            sys.exit(0)        
    
        self.writer.writerow(
            #  timestamp,         pending jobs,       running jobs,            started VMs,            idle VMs,
            [self.starting_time + (self.time_interval*self.cycle), 
                                  len(self._pending), len(self._running),      len(self._started_vms), self._idle_vm_count])

        log.info("At time %d: pending jobs %d, running jobs %d, started VMs %d, idle VMs %d",
                     (self.starting_time + self.time_interval*self.cycle), len(self._pending), len(self._running), len(self._started_vms), self._idle_vm_count)


    ##
    ## Interface to the CSV file format
    ##
    def get_sched_info(self):
        now = self.starting_time + self.cycle * self.time_interval
        for job in self.next_jobs(now, now + self.time_interval):
            self._pending.append(job)
        return (self._running + self._pending)

    def next_jobs(self, since, until):
        while len(self.__jobs) > 0:
            job = self.__jobs.pop()
            if since > job.submitted_at:
                if job.submitted_at <= until:
                    yield job
                else:
                    # job is in the past (relative to the Simulator's conecpt of time) so ignore it
                    pass
            else:
                # job is in the future: put it back for next round
                self.__jobs.append(job)
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
        if not vm.ever_running and (vm.last_idle > self.max_idle):
            return True
        else:
            return False


    ##
    ## (fake) cloud provider interface
    ##

    def start_vm(self, vm):
        DummyCloud.start_vm(self, vm)
        vm.been_running=0
        vm.total_idle=0

        # Setting the first "cluster_size" machines to be ever_running. 
        if vm.vmid <= self.cluster_size:
            vm.ever_running = True 
            vm.last_idle = 1 
        else:
            vm.ever_running = False 
            vm.last_idle=(-self.startup_delay)
        log.info("Started VM %d (%s).", vm.vmid, vm.instance.uuid)

    def update_vm_status(self, vms):
        DummyCloud.update_vm_status(self, vms)
        for vm in self._started_vms.values():
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
        DummyCloud.stop_vm(self, vm)
        if vm.last_idle > 0 and self._idle_vm_count > 0 and not vm.ever_running:
            self._idle_vm_count -= 1
        return True



if "__main__" == __name__:
    parser = argparse.ArgumentParser(description='Simulates a cloud orchestrator')
    parser.add_argument('--max-vms', '-mv', metavar='N', dest="max_vms", default=10, type=int, help="Maximum number of VMs to be started, default is %(default)s")
    parser.add_argument('--max-delta', '-md', metavar='N', dest="max_delta", default=1, type=int, help="Cap the number of VMs that can be started or stopped in a single orchestration cycle. Default is %(default)d.")    
    parser.add_argument('--max-idle', '-mi', metavar='NUM_SECS', dest="max_idle", default=7200, type=int, help="Maximum idle time (in seconds) before swithing off a VM, default is %(default)s")
    parser.add_argument('--startup-delay', '-s', metavar='NUM_SECS', dest="startup_delay", default=3600, type=int, help="Time (in seconds) delay before staring up a VM, default is %(default)s")
    parser.add_argument('--job-number', '-jn', metavar='N', dest="job_number", default=50, type=int, help="Number of job to be started, default is %(default)s")
    parser.add_argument('--min-duration', '-mind', metavar='NUM_SECS', dest="min_duration", default=30, type=int, help="Lower bound for job's time (in seconds) execution, default is %(default)s")
    parser.add_argument('--max-duration', '-maxd', metavar='NUM_SECS', dest="max_duration", default=120, type=int, help="Upper bound for job's time (in seconds)  execution, default is %(default)s")
    parser.add_argument('--csv-file', '-csvf',  metavar='String', dest="csv_file", default="accounting.csv", help="File containing the CSV information, %(default)s")
    parser.add_argument('--output-file', '-o',  metavar='String', dest="output_file", default="main_sim.txt", help="File name where the output of the simulation will be stored, %(default)s") 
    parser.add_argument('--cluster-size', '-cs',  metavar='NUM_CPUS', dest="cluster_size", default="20", type=int, help="Number of VMs, used for the simulation of real available cluster: %(default)s")
    parser.add_argument('--start-time', '-stime',  metavar='String', dest="start_time", default=None, help="Start time for the simulation, default: %(default)s")
    parser.add_argument('--time-interval', '-timei',  metavar='NUM_SECS', dest="time_interval", default="3600", help="UNIX interval in seconds used as parsing interval for the jobs in the CSV file, default: %(default)s")
    parser.add_argument('--version', '-V', action='version',
                        version=("%(prog)s version " + __version__))
    args = parser.parse_args()
    OrchestratorSimulation(args.max_vms, args.max_delta, args.max_idle, args.startup_delay, args.job_number, args.min_duration, args.max_duration, args.output_file, args.csv_file, args.start_time, args.time_interval, args.cluster_size).run(0)
