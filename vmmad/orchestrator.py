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
from __future__ import absolute_import

__docformat__ = 'reStructuredText'
__version__ = '$Revision$'


# stdlib imports
from abc import abstractmethod
import multiprocessing.dummy as mp
import os
import sys
import time

# local imports
from vmmad import log
from util import Struct


class JobInfo(Struct):
    """
    Record data about a job in the batch system.

    A `JobInfo` object is basically a free-form record, but the
    constructor still enforces the following constraints:

    * There must be a `state` attribute, whose value is one of `JobInfo.PENDING`, `JobInfo,RUNNING`, `JobInfo.FINISHED` or `JobInfo.OTHER`.
    * There must be a non-empty `jobid` attribute.

    Running jobs have a (string) `exec_node_name` attribute, which is
    used to match the associated VM (if any) by host name.
    """

    # job states
    PENDING = 1
    RUNNING = 2
    FINISHED = 3
    OTHER = 0

    def __init__(self, *args, **kwargs):
        Struct.__init__(self, *args, **kwargs)
        # ensure required fields are there
        assert 'jobid' in self, ("JobInfo object %s missing required field 'jobid'" % self)
        assert 'state' in self, ("JobInfo object %s missing required field 'state'" % self)
        assert self.state in [
            JobInfo.PENDING,
            JobInfo.RUNNING,
            JobInfo.FINISHED,
            JobInfo.OTHER
            ], \
            ("Invalid state '%s' for JobInfo object %s" % (self.state, self))


    def is_running(self):
        """
        Return `True` if the job is running.

        A running job is guaranteed to have a valid `exec_node_name`
        attribute.
        """
        if self.state == JobInfo.RUNNING:
            assert 'exec_node_name' in self, \
                   ("JobInfo object %s marked RUNNING"
                    " but missing required field 'exec_node_name'"
                    % (self,))
            return True
        else:
            return False


class VmInfo(Struct):
    """
    Record data about a started VM instance.

    A `VmInfo` object is mostly a free-form record, but the
    constructor still enforces the following constraints:

    * There must be a non-empty `vmid` attribute.

    .. note::

      The `vmid` attribute must be unique among all `VmInfo` instances!

      **FIXME:** This is not currently enforced by the constructor.

    The `state` attribute is set to one of the following strings
    (defaults to `DOWN` if not given in the constructor):

    ========= ============================================================
    status    meaning
    ========= ============================================================
    STARTING  A request to start the VM has been sent to the Cloud provider,
              but the VM is not ready yet.
    UP        The machine is up and running, and connected to the network.
    STOPPING  The remote VM has been frozen, but normal execution can be resumed.
    DOWN      The VM has been stopped and cannot be restarted/resumed.
    OTHER     Unexpected/unhandled state; usually signals an error.
    ========= ============================================================


    The following attributes are available after the machine has
    reached the ``UP`` state:

    ============  ========  ================================================
    attribute     type      meaning
    ============  ========  ================================================
    public_ip     str       public IP address in dot quad notation
    private_ip    str       private IP address in dot quad notation
    cloud         str       cloud identifier
    started_at    datetime  when the request to start the machine was issued
    up_at         datetime  when the machine was first detected up and running
    running_time  duration  total running time (in seconds)
    bill          float     total cost to be billed by cloud provider (in US$)
    ============  ========  ================================================
    """

    STARTING = 'STARTING'
    UP = 'UP'
    STOPPING = 'STOPPING'
    DOWN = 'DOWN'
    OTHER = 'OTHER'

    def __init__(self, *args, **kwargs):
        Struct.__init__(self, *args, **kwargs)
        # ensure required fields are there
        assert 'vmid' in self, ("VmInfo object %s missing required field 'vmid'" % self)
        # provide defaults
        if 'state' not in self:
            self.state = VmInfo.DOWN
        else:
            assert self.state in [
                VmInfo.STARTING,
                VmInfo.UP,
                VmInfo.STOPPING,
                VmInfo.DOWN,
                VmInfo.OTHER
                ]
        if 'bill' not in self:
            self.bill = 0.0
        
    
    def __hash__(self):
        """Use the VM id as unique hash value."""
        return hash(self.vmid)


    def is_alive(self):
        """
        Return `True` if the VM is up or will soon be (i.e., it is starting now).
        """
        return self.state in [VmInfo.STARTING, VmInfo.UP]


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
    `is_new_vm_needed` and `can_vm_be_stopped`.  Each of these methods
    can access a list of candidate jobs as attribute
    `self.candidates`; the `can_vm_be_stopped` method is additionally
    passed a `VmInfo` object and can inspect data from that VM.

    The only method required to interface to a batch queueing system
    is `get_sched_info`, which see for its interface and purpose.

    The `cloud` argument must be an object that implements the interface
    defined by the abstract class `vmmad.cloud.Cloud`.

    The `threads` argument specifies the size of the thread pool that
    is used to perform blocking operations.
    """

    def __init__(self, cloud, max_vms, max_delta=1, threads=8):

        # thread pool to enqueue blocking operations
        self._par = mp.Pool(threads)

        # allocator for shared memory objects
        self._shm = mp.Manager()
        
        # cloud provider
        self.cloud = cloud
        
        # max number of VMs that are allocated on the cloud
        self.max_vms = max_vms

        # max number of VMs that can be started each cycle
        self.max_delta = max_delta
        
        # VMs controlled by this `Orchestrator` instance (indexed by VMID)
        self._started_vms = self._shm.dict()

        # mapping jobid to job informations
        self.candidates = { }

        # VM book-keeping
        self._vmid = 0
        
        # Time simulation variable
        self.cycle = 0


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
            t0 = time.time()
            
            self.before()
            self.update_job_status()
            # XXX: potentially blocking - should timeout!
            self.cloud.update_vm_status(self._started_vms.values())

            # start new VMs if needed
            if self.is_new_vm_needed() and len(self._started_vms) < self.max_vms:
                self._vmid += 1
                new_vm = VmInfo(vmid=self._vmid, jobs=set(), state=VmInfo.STARTING)
                self._par.apply_async(self._asynch_start_vm, (new_vm,))

            # stop VMs that are no longer needed
            for vm in self._started_vms.values():
                if self.can_vm_be_stopped(vm):
                    self._par.apply_async(self._asynch_stop_vm, (vm,))

            self.after()
            self.cycle +=1

            if delay > 0:
                t1 = time.time()
                elapsed = t1 - t0
                if elapsed > delay:
                    log.warning("Cycle %d took more than %.2f seconds!"
                                " Starting new cycle without delay."
                                % (self.cycle, delay))
                else:
                    time.sleep(delay - elapsed)

    def _asynch_start_vm(self, vm):
        assert vm.vmid not in self._started_vms
        log.info("Starting VM %s ...", vm.vmid)
        try:
            self.cloud.start_vm(vm)
            self._started_vms[vm.vmid] = vm
            log.info("VM %s started, waiting for 'up' notification.", vm.vmid)
        except Exception, ex:
            vm.state = VmInfo.DOWN
            log.error("Error starting VM %s: %s: %s",
                      vm.vmid, ex.__class__.__name__, str(ex))
            if vm.vmid in self._started_vms:
                del _started_vms[vm.vmid]

    def _asynch_stop_vm(self, vm):
        log.info("Stopping VM %s ...", vm.vmid)
        try:
            self.cloud.stop_vm(vm)
            del self._started_vms[vm.vmid]
            log.info("Stopped VM %s.", vm.vmid)
        except Exception, ex:
            # XXX: This is more delicate than catching errors in the
            # startup phase: if a VM was not stopped when it should
            # have been, we run the chance of being billed from the
            # cloud provider for services we do not use any longer.
            # What's the correct course of action?
            log.error("Error stopping VM %s: %s: %s",
                      vm.vmid, ex.__class__.__name__, str(ex))
            

    def before(self):
        """Hook called at the start of the main run() cycle."""
        pass

    def after(self):
        """Hook called at the end of the main run() cycle."""
        pass


    def update_job_status(self):
        jobs = self.get_sched_info()    
        for job in (j for j in jobs if j.state == JobInfo.RUNNING):
            # running jobs are no longer candidates
            if job.jobid in self.candidates:
                del self.candidates[job.jobid]

        for job in (j for j in jobs if j.state == JobInfo.PENDING):
            # update candidates' information
            if self.is_cloud_candidate(job):
                self.candidates[job.jobid] = job


    ##
    ## interface to the batch queue scheduler
    ##
    @abstractmethod
    def get_sched_info(self):
        """
        Query the job scheduler and return a list of `JobInfo` objects
        representing the jobs in the batch queue system.
        """
        pass

    ##
    ## policy implementation interface
    ##
    @abstractmethod
    def is_cloud_candidate(self, job):
        """Return `True` if `job` can be run in a cloud node.

        Override in subclasses to define a different cloud-burst
        policy.
        """
        return False


    def is_new_vm_needed(self):
        """Inspect job collection and decide whether we need to start new VMs."""
        if len(self.candidates) > 0:
            return True


    @abstractmethod
    def can_vm_be_stopped(self, vm):
        """Return `True` if the VM identified by `vm` is no longer
        needed and can be stopped.
        """
        pass



## main: run tests


if "__main__" == __name__:
    # XXX: won't work, as Orchestrator is an abstract class
    Orchestrator().run()
