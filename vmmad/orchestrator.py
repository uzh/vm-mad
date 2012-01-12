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
from util import abstractmethod


## the main class of this file

class Orchestrator(object):
    """
    The `Orchestrator` monitors a job queue and starts/stops VMs
    according to a pre-defined policy in order to offload jobs from
    the queue.

    `Orchestrator` is an abstract class that cannot be directly
    instanciated: subclassing is needed to define a policy and
    implement interfaces to an actual queuing system and cloud
    backend.

    The actual VM start/stop policy is defined by overriding methods
    `is_new_vm_needed` and `can_stop_vm`.  Each of these methods can
    access a list of candidate jobs as attribute `self.candidates`;
    the `can_stop_vm` method is additionally passed a VM ID and can
    inspect data from that VM.

    The only method required to interface to a batch queueing system
    is `get_sched_info`, which see for its interface and purpose.

    Methods `start_vm` and `stop_vm` implement the interface to a
    cloud backend; see the method documentation for the exact
    interface.
    """

    def __init__(self, max_vms, max_delta=1):
        
        # max number of VMs that are allocated on the cloud
        self.max_vms = max_vms

        # max number of VMs that can be started each cycle
        self.max_delta = max_delta
        
        # map VM IDs to actual VM objects
        self._started_vms = { }

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

    @abstractmethod
    def is_cloud_candidate(self, job):
        """Return `True` if `job` can be run in a cloud node.

        Override in subclasses to define a different cloud-burst
        policy.
        """
        return False


    def update_vm_status(self):
        """Query cloud providers and update `self._started_vms` with VM node status."""
        pass


    def is_new_vm_needed(self):
        """Inspect job collection and decide whether we need to start new VMs."""
        if len(self.candidates) > 0:
            return True

    @abstractmethod
    def start_vm(self):
        """Virtual method for starting a new VM.

        Return the VM ID of the started virtual machine, which can be
        passed to the `stop_vm` method to stop it later.
        """
        pass

    @abstractmethod
    def can_vm_be_stopped(self, vmid):
        """Return `True` if the VM identified by `vmid` is no longer
        needed and can be stopped.
        """
        pass

    @abstractmethod
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
        """
        Run the orchestrator until stopped.

        Every `delay` seconds, the following operations are performed
        in sequence:
          - update job and VM status;
          - start new VMs if needed;
          - stop running VMs if they are no longer needed.
        """
        while True:
            self.before()
            
            self.update_job_status()
            self.update_vm_status()

            # start new VMs if needed
            if self.is_new_vm_needed() and len(self._started_vms) < self.max_vms:
                new_vm = self.start_vm()
                if new_vm is not None:
                    self._started_vms[new_vm.vmid] = new_vm

            # stop VMs that are no longer needed
            to_stop = [ ]
            for vmid in self._started_vms:
                if self.can_vm_be_stopped(vmid):
                    if self.stop_vm(vmid):
                        to_stop.append(vmid)
            for vmid in to_stop:
                        del self._started_vms[vmid]
                

            self.after()

            time.sleep(delay)


## main: run tests


if "__main__" == __name__:
    # XXX: won't work, as Orchestrator is an abstract class
    Orchestrator().run()
