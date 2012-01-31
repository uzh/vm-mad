#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Run tests for the `VmInfo` class.
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

# stdlib imports
import unittest

# local imports
from orchestrator import VmInfo


class TestVmInfo(unittest.TestCase):

    def test_ctor_required_attributes(self):
        # should raise assertion since `vmid` is required
        self.assertRaises(AssertionError, VmInfo, ())

    def test_ctor_default_values(self):
        vm = VmInfo(vmid=1)
        self.assertEqual(vm.state, VmInfo.DOWN)
        self.assertEqual(vm.bill,  0.0)

    def test_ctor_nondefault_values(self):
        vm = VmInfo(vmid=1, state=VmInfo.STARTING, bill=1.00)
        self.assertEqual(vm.state, VmInfo.STARTING)
        self.assertEqual(vm.bill,  1.00)

    def test_ctor_invalid_state(self):
        with self.assertRaises(AssertionError):
            vm = VmInfo(vmid=1, state='whatever but invalid')
        

## main: run tests

if __name__ == "__main__":
    # tests defined here
    unittest.main()
