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
from vmmad.provider.gc3pie import SmscgProvider
from vmmad.webapp import OrchestratorWebApp



class DemoOrchestrator(OrchestratorWebApp):
    
    def __init__(self, job_number=10, min_duration=1, max_duration=8*60*60):
        OrchestratorWebApp.__init__(
            self,
            delay=30,
            #cloud=EC2Cloud(image='ami-c2419aab', kind='m1.small',
            cloud=SmscgProvider(),
            batchsys=GridEngine('bfabric'),
            #batchsys=RandomJobs(3, 0.25, timer=self.time),
            max_vms=8,
            chkptfile='vm-mad.state')


    ##
    ## policy implementation interface
    ##
    def is_cloud_candidate(self, job):
        # only jobs submitted to the `cloud` queue are candidates
        return (job.name.startswith('OMSSACL_SMSCG'))

    def is_new_vm_needed(self):
        # if we have more jobs queued than started VMs, start a new one
        if len(self.candidates) > 2*len(self.vms):
            return True
        return False

    def can_vm_be_stopped(self, vm):
        TIMEOUT = 10*60 # 10 minutes
        if len(vm.jobs) == 0 and (vm.last_idle > TIMEOUT):
            return True
        else:
            log.debug(
                "Not stopping VM %s: %d jobs running, %d seconds idle.",
                vm.nodename, len(vm.jobs), vm.last_idle)
            return False
