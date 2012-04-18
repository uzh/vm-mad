#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Library for submiting VMMAD Virtual Machines to the SMSCG infrastructure
"""
# Copyright (C) 2011, 2012 ETH Zurich and University of Zurich. All rights reserved.
#
# Authors:
#   Tyanko Aleksiev <tyanko.alexiev@gmail.com>
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
from copy import copy

# libcloud imports
import libcloud.compute.types
import libcloud.compute.providers
import gc3libs.persistence
import gc3libs 
import gc3libs.core

# local imports
from vmmad import log
from vmmad.orchestrator import VmInfo
from vmmad.provider import NodeProvider

class VmmadAppPot(gc3libs.Application):
        def __init__(self, vmid):
            vm_output_dir=("smscg.vm.%s" % vmid)
            gc3libs.Application.AppPotApplication.__init__(
                self,
                executable = "sleep",
                arguments = ["365d"],
                inputs = [], 
                outputs = [],   
                output_dir = vm_output_dir,
                apppot_img = "$APPPOT_IMAGE",
                stdout = "apppot.out",
                jobname = "VMMAD",
                tags = ["TEST/APPPOT_VM-MAD-1.0"],
                requested_architecture = gc3libs.Run.Arch.X86_64,
                memory = 2,)

class SmscgProvider(NodeProvider):

    """
    Interface for submiting VM as job to the SMSCG infrastructure 
    """

    def __init__(self, image=None, kind=None):

        self.image = image
        self.kind = kind
        log.debug("Creating and submiting a VM as job to the SMSCG infrastructure...")

        self.g = gc3libs.core.Core(* gc3libs.core.import_config(gc3libs.Default.CONFIG_FILE_LOCATIONS, True))
        self.store = gc3pie.persistence.FilesystemStore(self.__class__.__name__ + ".jobs")

        # associate the Node ID we get from the cloud provider with
        # the VM object we get from the orchestrator
        self._instance_to_vm_map = { }


    def start_vm(self, vm):
        """
        Start a VM as a job to the SMSCG infrastructure
        """
        # Insert the node in the list
        vm.instance = self.provider.create_node(
            name=str(vm.vmid), image=self._images[self.image], size=self._kinds[self.kind])
        # Start the job to the SMSCG infrastructure 
        vm.gc3pie_app = VmmadAppPot(vm.vmid)
        self.g.submit(vm.gc3pie_app)
        self._instance_to_vm_map[vm.vmid] = vm
    
    def update_vm_status(self, vms):
        """
        Update the status of a VM (get the status of the job)
        """
        nodes = [ node for node in self.provider.list_nodes()
            if node.id in self._instance_to_vm_map ]
        for node in nodes:
            self.g.update_job_state(vm.gc3pie_app)
            if vm.gc3pie_app.execution.state == gc3libs.Run.State.RUNNING:
                vm.state = VmInfo.UP
            elif vm.gc3pie_app.execution.state in [ gc3libs.Run.State.TERMINATING, gc3libs.Run.State.TERMINATED ]:
                vm.state = VmInfo.DOWN
            elif vm.gc3pie_app.execution.state == gc3libs.Run.State.STOPPED:
                vm.state = VmInfo.OTHER

    def stop_vm(self, vm):
        """
        Kill the VM by kill the job
        """
        assert vm.vmid in self._instance_to_vm_map
        g.kill(self.app) 
        g.fetch_output(app)
        g.free(app)
        del self._instance_to_vm_map[vm.vmid]
        vm.state = VmInfo.DOWN
