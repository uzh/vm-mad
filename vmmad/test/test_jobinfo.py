#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Run tests for the `JobInfo` class.
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
from orchestrator import JobInfo


class TestJobInfo(unittest.TestCase):

    def test_required_attributes(self):
        # should raise assertion since `jobid` is required
        self.assertRaises(AssertionError, JobInfo, ())

    def test_is_running(self):
        job1 = JobInfo(jobid=1, exec_node_name='compute-0-0')
        self.assertTrue(job1.is_running())
        job2 = JobInfo(jobid=2)
        self.assertFalse(job2.is_running())


## main: run tests

if __name__ == "__main__":
    # tests defined here
    unittest.main()
