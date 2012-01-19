#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Run tests for the `ge_info` module.

As with all modules that deal with external state, this is only half
of the problem: the other half is ensuring that `qstat` and other GE
commands produce output in the format we are expecting here.  But this
cannot be enforced nor tested except at program run time...
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

# stdlib imports
import unittest

# local imports
import ge_info


# qstat -u '*' -xml
EXAMPLE_QSTAT_XML_OUTPUT = """<?xml version='1.0'?>
  <job_info  xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <queue_info>
      <job_list state="running">
        <JB_job_number>389524</JB_job_number>
        <JAT_prio>0.50500</JAT_prio>
        <JB_name>QRLOGIN</JB_name>
        <JB_owner>cpanse</JB_owner>
        <state>r</state>
        <JAT_start_time>2011-11-23T17:20:34</JAT_start_time>
        <queue_name>cloud@fgcz-cloud-002</queue_name>
        <slots>1</slots>
      </job_list>
      <job_list state="running">
        <JB_job_number>390489</JB_job_number>
        <JAT_prio>0.50500</JAT_prio>
        <JB_name>fgcz_sge_rserver__108564</JB_name>
        <JB_owner>bfabric</JB_owner>
        <state>r</state>
        <JAT_start_time>2011-12-12T18:46:06</JAT_start_time>
        <queue_name>rserver@fgcz-c-054</queue_name>
        <slots>1</slots>
      </job_list>
    </queue_info>
    <job_info>
      <job_list state="pending">
        <JB_job_number>389632</JB_job_number>
        <JAT_prio>0.50500</JAT_prio>
        <JB_name>STDIN</JB_name>
        <JB_owner>cpanse</JB_owner>
        <state>qw</state>
        <JB_submission_time>2011-11-26T08:41:59</JB_submission_time>
        <queue_name></queue_name>
        <slots>1</slots>
      </job_list>
    </job_info>
  </job_info>
"""


class TestGEInfo(unittest.TestCase):

    def test_running_and_pending_jobs_number(self):
        (running, pending) = ge_info.running_and_pending_jobs(EXAMPLE_QSTAT_XML_OUTPUT)
        self.assertEqual(len(running), 2)
        self.assertEqual(len(pending), 1)
 
    def test_running_job_attribute_types(self):
        (running, pending) = ge_info.running_and_pending_jobs(EXAMPLE_QSTAT_XML_OUTPUT)
        for job in running:
            self.assertTrue(isinstance(job.JAT_prio, float))
            self.assertTrue(isinstance(job.jobid, int))
            self.assertTrue(isinstance(job.JB_name, str))
            self.assertTrue(isinstance(job.queue_name, str))
            self.assertTrue(isinstance(job.exec_node_name, str))
            self.assertTrue(isinstance(job.state, str))

    def test_running_job_attribute_values(self):
        (running, pending) = ge_info.running_and_pending_jobs(EXAMPLE_QSTAT_XML_OUTPUT)
        job = running[0]
        self.assertEqual(job.JAT_prio, 0.505)
        self.assertEqual(job.jobid, 389524)
        self.assertEqual(job.JB_name, 'QRLOGIN')
        self.assertEqual(job.queue_name, 'cloud@fgcz-cloud-002')
        self.assertEqual(job.exec_node_name, 'fgcz-cloud-002')
        self.assertEqual(job.state, 'r')

    def test_pending_job_attribute_types(self):
        (running, pending) = ge_info.running_and_pending_jobs(EXAMPLE_QSTAT_XML_OUTPUT)
        for job in pending:
            self.assertTrue(isinstance(job.JAT_prio, float))
            self.assertTrue(isinstance(job.jobid, int))
            self.assertTrue(isinstance(job.JB_name, str))
            self.assertTrue(isinstance(job.state, str))
            self.assertTrue(job.queue_name is None)
            self.assertTrue(job.exec_node_name is None)

    def test_pending_job_attribute_values(self):
        (running, pending) = ge_info.running_and_pending_jobs(EXAMPLE_QSTAT_XML_OUTPUT)
        job = pending[0]
        self.assertEqual(job.JAT_prio, 0.505)
        self.assertEqual(job.jobid, 389632)
        self.assertEqual(job.JB_name, 'STDIN')
        self.assertEqual(job.queue_name, None)
        self.assertEqual(job.exec_node_name, None)
        self.assertEqual(job.state, 'qw')


## main: run tests

if __name__ == "__main__":
    # tests defined here
    unittest.main()
    import doctest
    # module doctests
    doctest.testmod(name="ge_info",
                    optionflags=doctest.NORMALIZE_WHITESPACE)
