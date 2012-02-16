#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces to cloud providers, using `Apache LibCloud <http://libcloud.apache.org>`
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
from abc import abstractmethod
from copy import copy

# libcloud imports
import libcloud.compute.types
import libcloud.compute.providers

# local imports
from vmmad import log
from vmmad.orchestrator import VmInfo
from vmmad.provider import NodeProvider


class CloudNodeProvider(NodeProvider):
    """
    Abstract base class implementing common functionality for all
    LibCloud providers.
    """
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


class DummyCloud(CloudNodeProvider):
    """
    Interface `Apache LibCloud <http://libcloud.apache.org/>` "dummy" cloud provider.
    """

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
        assert vm.vmid not in self._instance_to_vm_map
        vm.cloud = self.provider
        self._instance_to_vm_map[vm.vmid] = vm
        vm.state = VmInfo.UP


    def stop_vm(self, vm):
        assert vm.vmid in self._instance_to_vm_map
        id = vm.vmid
        self.provider.destroy_node(vm.instance)
        del self._instance_to_vm_map[id]
        vm.state = VmInfo.DOWN


    def update_vm_status(self, vms):
        nodes = [ node for node in self.provider.list_nodes()
                  if node.id in self._instance_to_vm_map ]
        for node in nodes:
            vm = self._instance_to_vm_map[node.uuid]
            vm.instance = node
            vm.state = self._vminfo_state_from_libcloud_status(node.state)



class EC2Cloud(CloudNodeProvider):
    """
    Interface to Amazon EC2 on top of `Apache LibCloud <http://libcloud.apache.org/>`.
    """

    def __init__(self, image, kind, access_id=None, secret_key=None):

        self.image = image
        self.kind = kind
        if access_id is not None:
            self.access_id = access_id
            self.secret_key = secret_key
        else:
            # use same environment variables as Boto
            self.access_id = os.environ['AWS_ACCESS_KEY_ID']
            self.secret_key = os.environ['AWS_SECRET_ACCESS_KEY']

        log.debug("Creating EC2 cloud provider with access ID '%s' ...", access_id)
        driver = libcloud.compute.providers.get_driver(libcloud.compute.types.Provider.EC2)
        self.provider = driver(self.access_id, self.secret_key)
        log.info("Using cloud provider '%s'.", self.provider.friendly_name)

        log.info("Listing available images ...")
        self._images = dict((img.id, img) for img in self.provider.list_images())
        if image not in self._images:
            raise RuntimeError("Image '%s' not available on %s"
                               % (image, self.provider.friendly_name))
        log.info("... done: %d images available.", len(self._images))

        log.info("Listing available sizes ...")
        self._kinds = dict((kind.id, kind) for kind in self.provider.list_sizes())
        if kind not in self._kinds:
            raise RuntimeError("Kind '%s' not available on %s"
                               % (kind, self.provider.friendly_name))
        log.info("... done: %d kinds available.", len(self._kinds))

        log.info("VMs will use image '%s' (%s) on hardware kind '%s' (%s)",
                 self.image, self._images[self.image].name,
                 self.kind, self._kinds[self.kind].name)

        # log.info("Getting list of running instances ...")
        # self.instances = dict((node.uuid, node) for node in self.provider.list_nodes())
        # log.info("... Done: %d instances available.", len(self._sizes))

        # associate the Node ID we get from the cloud provider with
        # the VM object we get from the orchestrator
        self._instance_to_vm_map = { }
        

    def start_vm(self, vm):
        vm.instance = self.provider.create_node(
            name=str(vm.vmid), image=self._images[self.image], size=self._kinds[self.kind])
        vm.cloud = self.provider
        self._instance_to_vm_map[vm.instance.uuid] = vm


    def stop_vm(self, vm):
        # XXX: this is tricky: we must:
        #   1. gracefully shutdown the node, and (after a timeout) proceed to:
        #   2. destroy the node
        # In addition this should not block the main Orchestrator thread.
        id = vm.instance.uuid
        self.provider.destroy_node(vm.instance)
        del self._instance_to_vm_map[id]


    def update_vm_status(self, vms):
        nodes = self.provider.list_nodes(ex_node_ids=[vm.instance.id for vm in vms])
        for node in nodes:
            vm = self._instance_to_vm_map[node.uuid]
            vm.instance = node
            vm.state = self._vminfo_state_from_libcloud_status(node.state)
