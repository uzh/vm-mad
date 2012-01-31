#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces to specific cloud providers, using `Apache LibCloud <http://libcloud.apache.org>`
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
__docformat__ = 'reStructuredText'
__version__ = '$Revision$'


import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(name)s: %(asctime)s: %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger(__package__)

# stdlib imports
from copy import copy


# libcloud imports
import libcloud.compute.types
import libcloud.compute.providers


# local imports
from orchestrator import VmInfo
from util import abstractmethod


class Cloud:
    """
    Abstract base class describing the interface that a cloud provider
    should implement.
    """

    def __init__(self, image, kind):
        """
        Initialize a cloud provider instance.

        The `image` and `kind` arguments specify the features of the
        VM instances that are later created by `start_vm`.
        """
        pass
        

    @abstractmethod
    def start_vm(self, vm):
        """
        Start a new VM.

        Return a `VmInfo` object describing the started virtual
        machine, which can be passed to the `stop_vm` method to stop
        it later.
        """
        pass


    @abstractmethod
    def update_vm_status(self, vms):
        """
        Query cloud providers and update each `VmInfo` object in list
        `vms` *in place* with the current VM node status.
        """
        pass


    @abstractmethod
    def stop_vm(self, vm):
        """
        Stop a running VM.

        After this method has successfully completed, the VM must no
        longer be running, all of its resources have been freed, and
        -most importantly- nothing is being charged to the account
        used for initialization.

        The `vm` argument is a `VmInfo` object, on which previous
        `start_vm` call should have recorded instance information.
        """
        pass


    @staticmethod
    def _vminfo_state_from_libcloud_status(status):
        """
        Return the `orchestrator.VmInfo` state word corresponding to
        LibCloud's `NodeState`.
        """
        return {
            libcloud.compute.types.NodeState.RUNNING:    VmInfo.UP,
            libcloud.compute.types.NodeState.REBOOTING:  VmInfo.STARTING,
            libcloud.compute.types.NodeState.TERMINATED: VmInfo.DOWN,
            libcloud.compute.types.NodeState.PENDING:    VmInfo.STARTING,
            libcloud.compute.types.NodeState.UNKNOWN:    VmInfo.OTHER,
            }[status]
        


class DummyCloud(Cloud):

    def __init__(self, image='1', kind='1'):

        self.image = image
        self.kind = kind

        log.debug("Creating LibCloud's 'Dummy' provider ...")
        driver = libcloud.compute.providers.get_driver(libcloud.compute.types.Provider.DUMMY)
        self.provider = driver(0)
        # LibCloud's "dummy" provider always starts two instances; remove them
        for node in copy(self.provider.list_nodes()):
            node.destroy()
        log.info("Using cloud provider '%s'.", self.provider.__class__.__name__)

        log.info("Listing available images ...")
        self._images = dict((img.id, img) for img in self.provider.list_images())
        log.debug("Available images: %s", self._images.keys())
        if image not in self._images:
            raise RuntimeError("Image '%s' not available on %s"
                               % (image, self.provider.__class__.__name__))
        log.info("... done: %d images available.", len(self._images))

        log.info("Listing available kinds ...")
        self._kinds = dict((kind.id, kind) for kind in self.provider.list_sizes())
        log.debug("Available kinds: %s", self._kinds.keys())
        if kind not in self._kinds:
            raise RuntimeError("Kind '%s' not available on %s"
                               % (kind, self.provider.__class__.__name__))
        log.info("... done: %d kinds available.", len(self._kinds))

        log.info("VMs will use image '%s' (%s) on hardware kind '%s' (%s)",
                 self.image, self._images[self.image].name,
                 self.kind, self._kinds[self.kind].name)

        # associate the Node ID we get from the cloud provider with
        # the VM object we get from the orchestrator
        self._instance_to_vm_map = { }
        

    def start_vm(self, vm):
        vm.instance = self.provider.create_node(
            name=str(vm.vmid), image=self._images[self.image], size=self._kinds[self.kind])
        vm.cloud = self.provider
        self._instance_to_vm_map[vm.instance.uuid] = vm
        vm.state = VmInfo.UP


    def stop_vm(self, vm):
        id = vm.instance.uuid
        self.provider.destroy_node(vm.instance)
        del self._instance_to_vm_map[id]
        vm.state = VmInfo.DOWN


    def update_vm_status(self, vms):
        nodes = [ node for node in self.provider.list_nodes()
                  if node.id in self._instance_to_vm_map ]
        for node in nodes:
            self._instance_to_vm_map[node.uuid].instance = node
            self._instance_to_vm_map[node.uuid].state = node.state

