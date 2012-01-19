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
from util import abstractmethod, Struct


class JobInfo(Struct):
    """
    Record data about a job in the batch system.

    A `JobInfo` object is basically a free-form record, but the
    constructor still enforces the following constraints:

    * There must be a non-empty `jobid` attribute.

    Running jobs have a (string) `exec_node_name` attribute, which is
    used to match the associated VM (if any).
    """

    def __init__(self, *args, **kwargs):
        Struct.__init__(self, *args, **kwargs)
        # ensure required fields are there
        assert 'jobid' in self, ("JobInfo object %s missing required field 'vmid'" % self)

    def is_running(self):
        """
        Return `True` if the job is running.

        A running job is guaranteed to have a valid `exec_node_name`
        attribute.
        """
        return 'exec_node_name' in self


class VmInfo(Struct):
    """
    Record data about a started VM instance.

    A `VmInfo` object is mostly a free-form record, but the
    constructor still enforces the following constraints:

    * There must be a non-empty `vmid` attribute.

    .. note::

      The `vmid` attribute must be unique among all `VmInfo` instances!

      **FIXME:** This is not currently enforced by the constructor.
    """

    def __init__(self, *args, **kwargs):
        Struct.__init__(self, *args, **kwargs)
        # ensure required fields are there
        assert 'vmid' in self, ("VmInfo object %s missing required field 'vmid'" % self)
    
    def __hash__(self):
        """Use the VM id as unique hash value."""
        return hash(self.vmid)


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
        
        # list of VMs controlled by this `Orchestrator` instance
        self._started_vms = set()

        # mapping jobid to job informations
        self.candidates = { }


    def update_job_status(self):
        running, pending = self.get_sched_info()

        for job in running:
            # running jobs are no longer candidates
            if job.jobid in self.candidates:
                del self.candidates[job.jobid]

        for job in pending:
            # update candidates' information
            if self.is_cloud_candidate(job):
                self.candidates[job.jobid] = job


    @abstractmethod
    def get_sched_info(self):
        """
        Query the job scheduler and return a pair (running, pending)
        where each item in the pair is a list of jobs.
        """
        pass


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
    def can_vm_be_stopped(self, vm):
        """Return `True` if the VM identified by `vm` is no longer
        needed and can be stopped.
        """
        pass


    @abstractmethod
    def stop_vm(self, vm):
        """Virtual method for stopping a VM.

        Takes a `vm` argument, which is the return value of a
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
                    self._started_vms.add(new_vm)

            # stop VMs that are no longer needed
            for vm in frozenset(self._started_vms):
                if self.can_vm_be_stopped(vm):
                    if self.stop_vm(vm):
                        self._started_vms.remove(vm)

            self.after()

            time.sleep(delay)


## main: run tests


if "__main__" == __name__:
    # XXX: won't work, as Orchestrator is an abstract class
    Orchestrator().run()
