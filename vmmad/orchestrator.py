#! /usr/bin/env python
#
"""
Launch compute node VMs on demand.
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


# stdlib imports
import os
import sys
import time

# apache libcloud
#from libcloud.compute.types import Provider
#from libcloud.compute.providers import get_driver
#import libcloud.security

# local imports
import ge_info



##

class Orchestrator(object):

    def __init__(self, max_vms, max_delta=1):
        
        # the max number of VMs that are allocated on the cloud
        self.max_vms = max_vms

        # the max number of VMs that are started each cycle
        self.max_delta = max_delta
        
        # list of started VMs
        self.pool = [ ]

        # mapping jobid to job informations
        self.candidates = { }

    def update_job_status(self):
        running, pending = self.get_sched_info()

        for job in running:
            # running jobs are no longer candidates
            if job.job_number in self.candidates:
                del self.candidates[job.job_number]

        for job in pending:
            # update candidates' information
            if self.is_cloud_candidate(job):
                self.candidates[job.job_number] = job

    def get_sched_info(self):
        """
        A function returning a pair (running, pending)
        of two lists of running/pending jobs.
        """
        return ge_info.running_and_pending_jobs()

    #@abstractmethod
    def is_cloud_candidate(self, job):
        """Return `True` if `job` can be run in a cloud node.

        Override in subclasses to define a different cloud-burst
        policy.
        """
        return False


    def update_vm_status(self):
        """Query SGE and update `self.pool` with VM node status (busy, idle) info."""
        # also query EC2 about VM status?
        pass


    def is_new_vm_needed(self):
        """Inspect job collection and decide whether we need to start new VMs."""
        if len(self.candidates) > 0:
            return True

    #@abstractmethod
    def start_vm(self):
        """Virtual method for starting a new VM.

        Return the VM ID of the started virtual machine, which can be
        passed to the `stop_vm` method to stop it later.
        """
        pass

    def can_vm_be_stopped(self, vmid):
        """Return `True` if the VM identified by `vmid` is no longer
        needed and can be stopped.
        """
        pass

    #@abstractmethod
    def stop_vm(self, vmid):
        """Virtual method for stopping a VM.

        Takes a `vmid` argument, which is the return value of a
        previous `start_vm` call.
        """
        pass


    def before(self):
        """Hook called at the start of the main run() cycle."""
        pass


    def after(self):
        """Hook called at the end of the main run() cycle."""
        pass


    def run(self, delay=30):
        while True:
            self.before()
            
            self.update_job_status()
            self.update_vm_status()

            if self.is_new_vm_needed() and len(self.pool) < self.max_vms:
                new_vm = self.start_vm()
                if new_vm is not None:
                    self.pool.append(new_vm)

            for vmid in self.pool:
                if self.can_vm_be_stopped(vmid):
                    if self.stop_vm(vmid):
                        self.pool.remove(vmid)

            self.after()

            time.sleep(delay)


## main: run tests


if "__main__" == __name__:
    # XXX: won't work, as Orchestrator is an abstract class
    Orchestrator().run()
