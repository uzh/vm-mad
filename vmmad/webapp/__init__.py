#! /usr/bin/env python
#
"""
A minimal web application for running the VM-MAD orchestrator.

Provides a URL to mark a VM as ready (given VMID and host name) over
HTTP, plus a status page reporting some basic metrics about the
orchestrator.

Based on `Django <http://django-project.org>`.
"""
# Copyright (C) 2011, 2012 ETH Zurich and University of Zurich. All rights reserved.
#
# Authors:
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

import traceback

# 3rd party imports
from flask import Blueprint, request, render_template, url_for

# local imports
from vmmad import log
from vmmad.orchestrator import Orchestrator, JobInfo, VmInfo


class OrchestratorWebApp(Blueprint, Orchestrator):

    def __init__(self,
                 delay, cloud, batchsys, max_vms, chkptfile=None,
                 name='vmmad',
                 **kwargs):
        Orchestrator.__init__(self, cloud, batchsys, max_vms,
                              chkptfile=chkptfile,
                              **kwargs)

        # run the Orchestrator main loop in a separate thread
        def run_main_loop():
            while True:
                try:
                    self.run(delay)
                except Exception, ex:
                    log.error("%s in Orchestrator's main loop: %s",
                              ex.__class__.__name__, str(ex), exc_info=True)
        self._daemon = threading.Thread(target=run_main_loop)
        self._daemon.daemon = True
        self._daemon.start()

        Blueprint.__init__(self, name, __name__,
                           template_folder='templates',
                           static_folder='ui')
        # register URLs with the Flask Blueprint
        self.route('/')(self.status)
        self.route('/x/ready')(self.ready)


    def ready(self):
        # try to extract nodename from HTTP request
        addr = request.remote_addr
        hostname = request.environ['HTTP_REMOTE_HOST'] if ('HTTP_REMOTE_HOST' in request.environ) else None
        # look for POST/GET parameters
        auth = request.values['auth']
        nodename = request.values['hostname']
        # perform registration
        nodename = nodename.split('.')[0]
        log.info("Host '%s' (%s) registering as node '%s'",
                 (hostname if hostname is not None else "<UNKNOWN>"),
                 (addr if addr is not None else "unknown address"),
                 nodename)
        self.vm_is_ready(auth, nodename)
        return 'OK'


    def status(self):
        params = dict(
            bootstrap_url=url_for('.static', filename='bootstrap'),
            appname=self.__class__.__name__,
            cycles=self.cycle,
            num_started=len(self.vms),
            num_active=len(self._vms_by_nodename),
            vms=[ dict(vmid=vm.vmid,
                       state=vm.state,
                       nodename=(vm.nodename if 'nodename' in vm else "(unknown)"),
                       is_not_yet_ready=(vm.state == VmInfo.STARTING),
                       ready_url=("/x/ready?auth=%s&hostname=vm-%s" % (vm.auth, vm.vmid)),
                    ) for vm in sorted(self.vms.values(), key=(lambda vm: vm.vmid))
                  ],
            )
        return render_template('status.html', **params)
