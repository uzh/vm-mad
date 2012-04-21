#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces to VM/node providers.
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

# local imports
from vmmad import log
from vmmad.orchestrator import VmInfo


class NodeProvider(object):
    """
    Abstract base class describing the interface that a node provider
    should implement.
    """

    def __init__(self, image, kind):
        """
        Initialize a node provider instance.

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
