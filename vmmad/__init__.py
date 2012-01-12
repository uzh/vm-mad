#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Basic functions to operate on Virtual Machines in a set of clouds.

In more detail, `vmlibs` provides a functional interface to:

* Start/check status/stop a VM in a cloud infrastructure.
* List VM images and their associated metadata.
* List available machine types/sizes.
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
__docformat__ = 'reStructuredText'
__version__ = '$Revision$'


class VMControl(object):
    """
    Control the lifecycle of a VM.
    """

    def __init__(self):
        """
        Initialize an empty VMControl object.  You must run
        configuration methods in order to get a working object.
        """
        pass

    def import_configuration(self, filename):
        """
        Read `filename` and use it to configure this `VMControl` instance.
        """
        pass

    def list_available_machtypes(self):
        """
        Query cloud servers and return a list of machine types available.

        The return value is a list of "machine type IDs";
        you should run `get_machtype_info` to translate the IDs into
        information that can be programmatically consumed.
        """
        pass

    def get_machtype_info(self, mtid):
        """
        Return complete information on the machine type identified by
        `mtid`.

        The return value is a named tuple object, with the following fields:

        =========  =====  ==================================
        attribute  type   meaning
        =========  =====  ==================================
        id         str    a copy of `mtid`
        ram        int    amount of RAM, in MB
        slots      int    number of CPU cores available
        bandwidth  int    max bandwidth, in MB/s
        cloud      str    identifier of the Cloud provider
        =========  =====  ==================================
        """
        pass

    def start(self, vmid, mtid):
        """
        Start a VM given a "VM image ID" `vmid` and a "machine type ID" `mtid`.
        Return a unique `hid` ("VM handle id") that can be used to operate on
        the started instance.
        """
        pass

    def stop(self, hid):
        """
        Stop the VM identified by `hid`.
        """
        pass

    def get_status(self, hid):
        """
        Return the status of the VM instance identified by `hid`.

        The returned status is one of the following strings:

        ========= ============================================================
        status    meaning
        ========= ============================================================
        WAITING   A request to start the VM has been sent to the Cloud server, but the VM is not ready yet.
        UP        The machine is up and running, and connected to the network.
        STOPPED   The remote VM has been frozen, but normal execution can be resumed.
        DOWN      The VM has been stopped and cannot be restarted/resumed.
        ========= ============================================================

        Raise `ValueError` if `hid` is not a valid "VM handle"
        as returned by the `self.start`:meth: method.
        """
        pass

    def get_info(self, hid):
        """
        Return information on the VM instance identified by `hid`.

        The return value is a named tuple object, conforming to the
        following specification:

        ============  ========  ================================================
        attribute     type      meaning
        ============  ========  ================================================
        public_ip     str       public IP address in dot quad notation
        private_ip    str       private IP address in dot quad notation
        vmid          str       the VM image ID used to create the image
        mtid          str       the machine type ID used to create the image
        cloud         str       cloud identifier
        started_at    datetime  when the request to start the machine was issued
        up_at         datetime  when the machine was detected up and running
        running_time  duration  total running time (in seconds)
        bill          float     total cost to be billed by cloud provider
        ============  ========  ================================================
        """
        pass


class MetadataQuery(object):
    """
    Perform queries to a VM-MAD metadata server.
    """

    def __init__(self, endpoint):
        """
        Initialize a `MetadataQuery` object for interacting with the
        server at `endpoint`.
        """
        self.endpoint = endpoint
    

    def search_image(self, tags):
        """
        Given a set of tags, return the set of VM image IDs that have all
        the given tags.
        """
        pass


    def get_image_info(self, vmid):
        """
        Query the metadata server and return all the metadata available
        for the image identified by `vmid`.

        The return value is a Python dictionary; both keys and values are
        string types (or subclasses thereof).
        """
        pass


## main: run tests

if "__main__" == __name__:
    import doctest
    doctest.testmod(name="__init__",
                    optionflags=doctest.NORMALIZE_WHITESPACE)
