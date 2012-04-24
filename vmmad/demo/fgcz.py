#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cloud-bursting of a batch cluster into a cloud.
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
import os
import sys
import random
import threading
import time

# local imports
from vmmad import log
from vmmad.batchsys.randomjobs import RandomJobs
from vmmad.batchsys.gridengine import GridEngine
from vmmad.orchestrator import JobInfo, VmInfo
from vmmad.provider.libcloud import DummyCloud, EC2Cloud
#from vmmad.provider.gc3pie import SmscgProvider
from vmmad.webapp import OrchestratorWebApp



class DemoOrchestrator(OrchestratorWebApp):
    
    def __init__(self, job_number=10, min_duration=1, max_duration=8*60*60):
        OrchestratorWebApp.__init__(
            self,
            delay=30,
            cloud=EC2Cloud(image='ami-c2419aab', kind='m1.small',
                           access_id='AKIAJ4RPJXT5OPX6WW2A', 
                           secret_key='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'),
            #cloud=SmscgProvider(),
            batchsys=GridEngine('bfabric'),
            #batchsys=RandomJobs(3, 0.25, timer=self.time),
            max_vms=2)
        

    ##
    ## policy implementation interface
    ##
    def is_cloud_candidate(self, job):
        # only jobs submitted to the `cloud` queue are candidates
        return (job.name.startswith('fgcz_sge_peakplot_glyco1_ng'))

    def is_new_vm_needed(self):
        running = len([ job for job in self.jobs 
                        if (job.state == JobInfo.RUNNING 
                            and self.is_cloud_candidate(job))])
        if len(self.candidates) > max(running, len(self._started_vms)):
            return True
        return False

    def can_vm_be_stopped(self, vm):
        TIMEOUT = 600 
        if vm.state == VmInfo.READY:
            if len(vm.jobs) == 0 and (self.time() - vm.ready_at > TIMEOUT):
                return True
            else:
                log.debug("Not stopping VM %s: %d jobs running, %d seconds idle.",
                          vm.nodename, len(vm.jobs), (self.time() - vm.ready_at > TIMEOUT))
                return False
        else:
            if self.time() - vm.started_at > TIMEOUT:
                return True
            else:
                log.debug("Not stopping VM %s: started since %d seconds.",
                          vm.vmid, (self.time() - vm.started_at > TIMEOUT))
                return False
