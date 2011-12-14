#! /usr/bin/env python
#
"""
Launch compute node VMs on demand.
"""
# Copyright (C) 2011 ETH Zurich and University of Zurich. All rights reserved.
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


import ge_info

import os
import sys


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
        running, pending = self.sched_info_fn()

        for job in running:
            # jobs that are running are no longer candidates
            if job.job_number in self.candidates:
                del self.candidates[job.job_number]

        for job in pending:
            # update candidates' information
            if self.is_cloud_candidate(job):
                self.candidates[job.job_number] = job

    def _get_sched_info(self):
        """
        A function returning a pair (running, pending)
        of two lists of running/pending jobs.
        """
        return ge_info.running_and_pending_jobs()

    @abstractmethod
    def is_cloud_candidate(self, job):
        """Return `True` if `job` can be run in a cloud node."""
        return False


    def update_vm_status(self):
        """Query SGE and update `self.pool` with VM node status (busy, idle) info."""
        # also query EC2 about VM status?
        

    def start_vm_if_needed(self):
        """Inspect job collection and decide whether we need to start new VMs."""
        if len(self.candidates) > 0:
            pass

    @abstractmethod
    def _started_vm(self):
        """Virtual mehtod for starting a new VM."""


    def stop_vm_if_needed(self):
        ""

    @abstractmethod
    def _stop_vm(self):
        """Virtual method for stopping a VM."""


    def run(self, delay=30):
        while True:
            self.update_job_status()
            self.update_vm_status()

            self.start_vm_if_needed()
            self.stop_vm_if_needed()

            time.sleep(delay)


## main: run tests


if "__main__" == __name__:
    run()

