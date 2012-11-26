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
from vmmad.orchestrator import JobInfo
from vmmad.provider.libcloud import DummyCloud, EC2Cloud
from vmmad.webapp import OrchestratorWebApp



class DemoOrchestrator(OrchestratorWebApp):

    def __init__(self, flaskapp):
        OrchestratorWebApp.__init__(
            self,
            flaskapp,
            delay=15,
            cloud=DummyCloud('1', '1'),
            batchsys=RandomJobs(3, 0.25, timer=self.time),
            max_vms=10)


    ##
    ## policy implementation interface
    ##
    def is_cloud_candidate(self, job):
        # every job is a candidate in this simulation
        return True

    def is_new_vm_needed(self):
        pending = len([ job for job in self.jobs.itervalues() if job.state == JobInfo.PENDING ])
        running = len([ job for job in self.jobs.itervalues() if job.state == JobInfo.RUNNING ])
        if pending > 2*running:
            return True
        return False

    def can_vm_be_stopped(self, vm):
        if len(vm.jobs) == 0 and (time.time() - vm.started_at > 90):
            return True
        else:
            return False
