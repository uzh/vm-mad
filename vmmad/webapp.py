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
from django.http import HttpResponse

# local imports
from vmmad import log
from vmmad.orchestrator import Orchestrator, JobInfo, VmInfo


class OrchestratorWebApp(Orchestrator):

    def __init__(self, delay, cloud, batchsys, max_vms, chkptfile=None, **kwargs):
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


    def ready(self, request):
        # try to extract nodename from HTTP request
        hostname = None
        addr = None
        if 'REMOTE_HOST' in request.META:
            hostname = request.META['REMOTE_HOST']
        if 'REMOTE_ADDR' in request.META:
            addr = request.META['REMOTE_ADDR']
        # look for POST/GET parameters
        if 'auth' in request.REQUEST:
            auth = request.REQUEST['auth']
        else:
            # missing required parameter
            return HttpResponse("ERROR: Missing required parameter 'auth'",
                                status=400, content_type='text/plain')
        if 'hostname' in request.REQUEST:
            nodename = request.REQUEST['hostname']
        else:
            # missing required parameter
            return HttpResponse("ERROR: Missing required parameter 'hostname'",
                                status=400, content_type='text/plain')
        # perform registration
        nodename = nodename.split('.')[0]
        log.info("Host '%s' (%s) registering as node '%s'",
                 (hostname if hostname is not None else "<UNKNOWN>"),
                 (addr if addr is not None else "unknown address"),
                 nodename)
        self.vm_is_ready(auth, nodename)
        return HttpResponse("OK", content_type='text/plain')


    def status(self, request):
        html = """
            <html>
            <head>
              <title>%(app)s status</title>
            </head>
            <body>
            <p>
              %(app)s is up and running!
            </p>
            <h2>Orchestrator status</h2>
            <p>
              The current orchestrator status is as follows:
              <ul>
                <li>%(cycles)s cycles have passed
                <li>%(num_started)s VMs have been started
                <li>%(num_active)s VMs are currently active (ready for processing jobs)
              </ul>
            </p>
            """ % dict(
                app=self.__class__.__name__,
                cycles=self.cycle,
                num_started=len(self.vms),
                num_active=len(self._vms_by_nodename),
            )
        # make a table of the started VMs
        html += """
            <h2>Started VMs</h2>
              <table>
                <tr>
                  <th>ID</th>
                  <th>State</th>
                  <th>Node name</th>
                </tr>
              """
        for vm in self.vms.values():
            html += """
            <tr>
              <td>%(vmid)s</td>
              <td>%(state)s</td>
              <td>%(nodename)s</td>
              <td>%(ready_url)s</td>
            </tr>
            """ % dict(
              vmid=vm.vmid,
              state=vm.state,
              nodename=(vm.nodename if 'nodename' in vm else "(unknown)"),
              ready_url=(('''
                  <a href="/x/ready?auth=%s&hostname=vm-%s">Manually mark as ready</a>
                          ''' % (vm.auth, vm.vmid))
                         if vm.state != VmInfo.READY else ""),
            )
        html += """</table>"""
        # end it all
        html += """</body>"""

        return HttpResponse(html)
