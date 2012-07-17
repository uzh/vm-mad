#! /usr/bin/env python
#
"""
Launch compute node VMs on demand.
"""
# Copyright (C) 2011-2012 ETH Zurich and University of Zurich. All rights reserved.
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
__version__ = '$Revision$'


# stdlib imports
from abc import abstractmethod
import multiprocessing.dummy as mp
import os
import sys
import time

# local imports
from vmmad import log
from vmmad.util import random_password, Struct


class JobInfo(Struct):
    """
    Record data about a job in the batch system.

    A `JobInfo` object is basically a free-form record, but the
    constructor still enforces the following constraints:

    * There must be a `state` attribute, whose value is one of those listed below.
    * There must be a non-empty `jobid` attribute.

    The `state` attribute is set to one of the following strings
    (defaults to `DOWN` if not given in the constructor):

    ========= ============================================================
    state     meaning
    ========= ============================================================
    PENDING   The job is waiting in the batch system queue.
    RUNNING   The job is currently executing on some node.
    FINISHED  The job is done and any exec node it used is now clear
              for re-use by another job.
    OTHER     Unexpected/unhandled state; usually signals an error.
    ========= ============================================================

    Jobs in ``RUNNING`` state have a (string) `exec_node_name`
    attribute, which is used to match the associated VM (if any) by
    host name.

    """

    # job states
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    FINISHED = 'FINISHED'
    OTHER = 'OTHER'

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


    def __hash__(self):
        """Use the Job id as unique hash value."""
        return hash(self.jobid)


    def __str__(self):
        return ("Job %s" % self.jobid)


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
    READY     The machine is ready to run jobs.
    DRAINING  The VM is scheduled to stop, waiting for all batch jobs to terminate
              before issuing the 'halt' command.
    STOPPING  The 'halt' command is about to be issued to the cloud provider.
    DOWN      The VM has been stopped and cannot be restarted/resumed;
              once a VM reaches this state, it is removed from the list
              of VMs at the next `Orchestrator` cycle.
    OTHER     Unexpected/unhandled state; usually signals an error.
    ========= ============================================================


    The following attributes are available after the machine has
    reached the ``READY`` state:

    ============  ========  ================================================
    attribute     type      meaning
    ============  ========  ================================================
    ready_at      datetime  when the machine notified it's ready to run jobs
    jobs          list      list of Job IDs of jobs running on this node
    nodename      str       machine node name (as reported in the batch system listing)
    ============  ========  ================================================
    """

    STARTING = 'STARTING'
    READY = 'READY'
    STOPPING = 'STOPPING'
    DRAINING = 'DRAINING'
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
                VmInfo.READY,
                VmInfo.STOPPING,
                VmInfo.DOWN,
                VmInfo.OTHER
                ]
        if 'bill' not in self:
            self.bill = 0.0
        if 'jobs' not in self:
            self.jobs = set()


    def __str__(self):
        if 'nodename' in self:
            return ("VM Node '%s'" % self.nodename)
        else:
            return ("VM %s" % self.vmid)
    __repr__ = __str__


    def __hash__(self):
        """Use the VM id as unique hash value."""
        return hash(self.vmid)


    def is_alive(self):
        """
        Return `True` if the VM is up or will soon be (i.e., it is starting now).
        """
        return self.state in [VmInfo.STARTING, VmInfo.READY]


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

    The `cloud` argument must be an object that implements the interface
    defined by the abstract class `vmmad.cloud.Cloud`.

    The `batchsys` argument must be an object that implements the
    interface defined by the abstract class
    `vmmad.batchsys.BatchSystem`:class: (which see for details).

    The `threads` argument specifies the size of the thread pool that
    is used to perform blocking operations.

    :param cloud:         A `vmmad.provider.NodeProvider` instance that is used to start/stop VMs.
    :param batchsys:      A `vmmad.batchsys.BathcSystem` instance that is used to poll the batch system for jobs.
    :param int max_vms:   Maximum number of VMs to start.
    :param int max_delta: Maximum number of VMs to start/stop in one cycle.
    :param int vm_start_timeout: Maximum amount of time (seconds) to wait for a VM to turn to ``READY`` state.
    :param int threads:   Size of the thread pool for non-blocking operations.
    """

    def __init__(self, cloud, batchsys, max_vms,
                 max_delta=1,
                 vm_start_timeout=10*60, # 10 minutes
                 threads=8):
        # thread pool to enqueue blocking operations
        self._threadpool = mp.Pool(threads)
        self._async = self._threadpool.apply_async # shortcut

        # allocator for shared memory objects
        self._shm = mp.Manager()

        # cloud provider
        self.cloud = cloud

        # batch system interface
        self.batchsys = batchsys

        # max number of VMs that are allocated on the cloud
        self.max_vms = max_vms

        # max number of VMs that can be started each cycle
        self.max_delta = max_delta

        # VMs controlled by this `Orchestrator` instance (indexed by VMID)
        self.vms = self._shm.dict()
        self._pending_auth = { }
        self._vms_by_nodename = { }

        # mapping jobid to job informations
        self.jobs = { }
        self.candidates = set()

        # VM book-keeping
        self._vmid = 0

        # Time simulation variable
        self.cycle = 0

        # Time the job statuses were last checked
        self.last_update = 0

        # if a VM does not turn to READY state within this time allowance, cancel it
        self.vm_start_timeout = vm_start_timeout


    def run(self, delay=30, max_cycles=0):
        """
        Run the orchestrator main loop until stopped or `max_cycles` reached.

        Every `delay` seconds, the following operations are performed
        in sequence:

        - update job and VM status;
        - start new VMs if needed;
        - stop running VMs if they are no longer needed.
        """
        done = 0
        last_cycle_at = self.time()
        while max_cycles == 0 or done < max_cycles:
            log.debug("Orchestrator %x about to start cycle %d", id(self), self.cycle)
            t0 = time.time() # need real time, not the simulated one
            now = self.time()
            elapsed = now - last_cycle_at

            self.before()

            self.update_job_status()
            # XXX: potentially blocking - should timeout!
            self.cloud.update_vm_status(self.vms.values())
            for vm in self.vms.values():
                if vm.state == VmInfo.DOWN:
                    log.debug("VM %s is DOWN, removing it from managed VM list.", vm.vmid)
                    del self.vms[vm.vmid]
                    continue
                if vm.state == VmInfo.STARTING and (self.time() - vm.started_at) > self.vm_start_timeout:
                    log.debug("VM %s did not turn READY in %d seconds, scheduling its removal.",
                              vm.vmid, self.vm_start_timeout)
                    self._async(self._do_stop_vm, [vm])
                if vm.state in [ VmInfo.READY, VmInfo.STOPPING, VmInfo.OTHER ]:
                    vm.running_time += elapsed
                if not vm.jobs:
                    vm.total_idle += elapsed
                    vm.last_idle += elapsed
                else:
                    vm.last_idle = 0

            # start new VMs if needed
            for _ in xrange(self.max_delta):
                if self.is_new_vm_needed() and len(self.vms) < self.max_vms:
                    self._async(self._do_start_vm, [self.new_vm()])
                else:
                    break # no VM needed or limit reached, exit loop

            # stop VMs that are no longer needed
            # FIXME: The trick of modifying `self.vms` as we
            # iterate on it only works because (in Python 2.x), the
            # `.items()` method returns a *copy* of the items list; in
            # Python 3.x, where it returns an iterator, this construct
            # will *not* work!
            for vmid, vm in self.vms.items():
                if vm.state == VmInfo.READY and self.can_vm_be_stopped(vm):
                    if len(vm.jobs) > 0:
                        log.warning(
                            "Request to stop VM %s, but it's still running jobs: %s",
                            vm.vmid, str.join(' ', vm.jobs))
                    vm.state = VmInfo.STOPPING
                    self._async(self._do_stop_vm, [vm])

            self.after()
            self.cycle +=1
            done += 1
            last_cycle_at = now

            if delay > 0:
                t1 = time.time() # need real time, not the simulated one
                elapsed = t1 - t0
                if elapsed > delay:
                    log.warning("Cycle %d took more than %.2f seconds!"
                                " Starting new cycle without delay."
                                % (self.cycle, delay))
                else:
                    time.sleep(delay - elapsed)

    def _do_start_vm(self, vm):
        assert vm.vmid not in self.vms
        log.info("Starting VM %s ...", vm.vmid)
        try:
            self.cloud.start_vm(vm)
            vm.started_at = self.time()
            self.vms[vm.vmid] = vm
            self._pending_auth[vm.auth] = vm
            log.info("VM %s started, waiting for 'READY' notification.", vm.vmid)
        except Exception, ex:
            vm.state = VmInfo.DOWN
            log.error("Error launching VM %s: %s: %s",
                      vm.vmid, ex.__class__.__name__, str(ex), exc_info=__debug__)

    def _do_stop_vm(self, vm):
        log.info("Stopping VM %s ...", vm.vmid)
        try:
            self.cloud.stop_vm(vm)
            vm.stopped_at = self.time()
            vm.state = VmInfo.DOWN
            try:
                been_running = (vm.stopped_at - vm.ready_at)
                if been_running > 0:
                    log.info("Stopped VM %s (%s);"
                             " it has run for %d seconds, been idle for %d of them (%.2f%%)",
                             vm.vmid, vm.nodename, been_running, vm.total_idle,
                             (100.0 * vm.total_idle / been_running))
                else:
                    log.error("Stopped VM %s (%s), but has been running 0 seconds!", vm.vmid, vm.nodename)
            except AttributeError:
                # if the machine was never ready, `.nodename` and `.ready_at` are unset
                log.warning("Stopped VM %s; it never reached READY status.", vm.vmid)
        except Exception, ex:
            # XXX: This is more delicate than catching errors in the
            # startup phase: if a VM was not stopped when it should
            # have been, we run the chance of being billed from the
            # cloud provider for services we do not use any longer.
            # What's the correct course of action?
            log.error("Error stopping VM %s: %s: %s",
                      vm.vmid, ex.__class__.__name__, str(ex), exc_info=__debug__)


    def before(self):
        """Hook called at the start of the main run() cycle."""
        pass


    def after(self):
        """Hook called at the end of the main run() cycle."""
        pass


    def time(self):
        """
        Return the current time in UNIX epoch format.

        This method exists only for the purpose of overriding it
        insimulator classes, so that a 'virtual' time can be
        implemented.
        """
        return time.time()


    def new_vm(self, **attrs):
        """
        Return a new `VmInfo` object.

        If you need to set attributes on the `VmInfo` object before
        the VM is even started, override this method in a subclass,
        take its return value and manipualte it at will.
        """
        # new VMID
        if 'vmid' not in attrs:
            self._vmid += 1
            attrs['vmid'] = str(self._vmid)
        # generate a random auth token and ensure it's not in use
        if 'auth' not in attrs:
            passwd = random_password()
            while passwd in self._pending_auth:
                passwd = random_password()
            attrs['auth'] = passwd
        # set standard attributes
        attrs.setdefault('state', VmInfo.STARTING)
        attrs.setdefault('total_idle', 0)
        attrs.setdefault('last_idle', 0)
        attrs.setdefault('running_time', 0)
        # bundle up all this into a VM object
        return VmInfo(**attrs)


    def update_job_status(self):
        """
        Update job information based on what the batch system interface returns.

        Return the full list of active job objects (i.e., not just the
        candidates for cloud execution).
        """
        log.debug("Updating job status; last update at %s",
                  time.ctime(self.last_update))
        now = self.time()

        current_jobs = self.batchsys.get_sched_info()
        for job in current_jobs:
            jobid = job.jobid
            if jobid in self.jobs:
                self.jobs[jobid].update(job)
            else:
                self.jobs[jobid] = job
                if 'running_at' in job:
                    log.info(
                        "New job %s %s in state %s appeared; running since %s.",
                        jobid,
                        (("'%s'" % job.name) if 'name' in job else '(no job name)'),
                        job.state,
                        time.ctime(job.running_at))
                    assert job.running_at >= self.last_update
                elif 'submitted_at' in job:
                    log.info(
                        "New job %s %s in state %s appeared; submitted since %s.",
                        jobid,
                        (("'%s'" % job.name) if 'name' in job else '(no job name)'),
                        job.state,
                        time.ctime(job.submitted_at))
                    assert job.submitted_at >= self.last_update
                else:
                    log.info(
                        "New job %s %s in state %s appeared.",
                        jobid,
                        (("'%s'" % job.name) if 'name' in job else '(no job name)'),
                        job.state)

        # remove finished jobs
        jobids = set(self.jobs.iterkeys())
        current_jobids = set(job.jobid for job in current_jobs)
        terminated = jobids - current_jobids
        for jobid in terminated:
            job = self.jobs[jobid]
            if job.state == JobInfo.RUNNING:
                assert 'exec_node_name' in job
                log.info("Job %s terminated its execution on node '%s'",
                         jobid, self.jobs[jobid].exec_node_name)
            elif job.state == JobInfo.PENDING:
                assert ('exec_node_name' not in job) or (job.exec_node_name is None), (
                    "Error in job object '%s': expecting 'exec_node_name' not to be there!"
                    % str.join(', ', [ ("%s=%r" % (k,v)) for k,v in job.items() ]))
                log.info("Job %s (state %s) was cancelled.", jobid, job.state)
            else:
                log.info("Job %s (state %s) was deleted.", jobid, job.state)
            if job in self.candidates:
                self.candidates.remove(job)
            del self.jobs[jobid]
        active_vms = [ vm for vm in self.vms.values()
                       if (vm.state in [ VmInfo.READY, VmInfo.DRAINING ]) ]
        for vm in active_vms:
            # remove jobs that are no longer in the list, i.e., they are finished
            vm.jobs -= terminated

        # update info on running jobs
        for job in self.jobs.values():
            if job.state == JobInfo.RUNNING and job.running_at > self.last_update:
                log.info("Job %s running on node '%s'", job.jobid, job.exec_node_name)
                # job just went running, it's longer a candidate
                if job in self.candidates:
                    self.candidates.remove(job)
                    log.debug("Job %s is no longer candidate for running on the cloud.", job.jobid)
                # record which jobs are running on which VM
                if job.exec_node_name in self._vms_by_nodename:
                    self._vms_by_nodename[job.exec_node_name].jobs.add(job.jobid)
            elif job.state == JobInfo.PENDING and job.submitted_at > self.last_update:
                # update candidates' information
                if self.is_cloud_candidate(job):
                    assert job not in self.candidates
                    self.candidates.add(job)
                    log.info("Enlisting job %s as candidate for running on the cloud.", job.jobid)
            else:
                # ignore
                pass

        self.last_update = now
        return self.jobs


    def vm_is_ready(self, auth, nodename):
        """
        Notify an `Orchestrator` instance that a VM is ready to accept jobs.

        The `auth` argument must match one of the passwords assigned
        to a previously-started VM (which are passed to the VM via
        boot parameters).  If it does not, an error is logged and the
        call immediately returns `False`.

        The `nodename` argument must be the host name that the VM
        reports to the batch system, i.e., the node name as it appears
        in the batch system scheduler listings/config.
        """
        if auth not in self._pending_auth:
            log.error(
                "Received notification that node '%s' is READY,"
                " but authentication data does not match any started VM.  Ignoring.",
                nodename)
            return False
        vm = self._pending_auth.pop(auth)
        assert vm.state == VmInfo.STARTING
        vm.state = VmInfo.READY
        vm.ready_at = self.time()
        vm.nodename = nodename
        if nodename in self._vms_by_nodename:
            log.warning(
                "Node name '%s' already registered to VM %s,"
                " but re-registering to VM %s.",
                nodename, self._vms_by_nodename[nodename].vmid, vm.vmid)
        self._vms_by_nodename[nodename] = vm
        log.info("VM %s reports being ready as node '%s'", vm.vmid, nodename)
        return True


    ##
    ## policy implementation interface
    ##
    @abstractmethod
    def is_cloud_candidate(self, job):
        """
        Return `True` if `job` can be run in a cloud node.

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
        """
        Return `True` if the VM identified by `vm` is no longer
        needed and can be stopped.
        """
        pass



## main: run tests


if "__main__" == __name__:
    # XXX: won't work, as Orchestrator is an abstract class
    Orchestrator().run()
