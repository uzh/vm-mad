#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces to the Sun/Oracle/Open Grid Engine batch queueing systems.
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
from __future__ import absolute_import

__docformat__ = 'reStructuredText'
__version__ = '$Revision$'


# stdlib imports
from collections import Mapping, defaultdict
import os
import subprocess
import sys
import time
import UserDict
import xml.sax

# local imports
from vmmad import log
from vmmad.batchsys import BatchSystem
from vmmad.orchestrator import JobInfo
from vmmad.util import Struct


class _QstatXmlHandler(xml.sax.ContentHandler):
    """
    SAX `ContentHandler` implementation for parsing the output of
    `qstat -u ... -xml`.
    """

    # XML attributes *not* in this list are ignored
    JOB_ATTRIBUTES = [
        'JB_job_number',
        'JB_submission_time',
        'JAT_start_time',
        'JAT_prio',
        'JB_name',
        'state',
        'queue_name',
        'slots'
        ]

    # conversion of XML fields to Python data
    CONVERT = defaultdict(
        # by default, return `str`
        lambda: str,
        # return other values in particular cases:
        JB_job_number=int,
        JB_submission_time=str,
        JAT_prio=float,
        slots=int,          
        )

    # rename fields to adhere to what the `JobInfo` ctor expects
    @staticmethod
    def rename(field):
        try:
            # map field names according to this...
            return {
                'JB_job_number':'jobid',
                'JB_name':'name',
                'JB_submission_time':'submit_time',
                'JAT_start_time':'start_time',
                }[field]
        except KeyError:
            # ...and by default, keep field name unchanged
            return field


    def __init__(self, dest):
        self.jobs = dest
        self.value = [ ]
        self._level = 0

    def startElement(self,name,attrs):
        self._level += 1
        if name == 'job_list':
            assert 'state' in attrs
            self.current = JobInfo(jobid='invalid', state=JobInfo.OTHER)
            self.current_job_state = attrs['state']

        ## for other elements, just reset `value` so we can
        ## accumulate characters in `self.characters`
        else:
            self.value = []


    def characters(self, chrs):
        self.value.append(chrs)


    def endElement(self,name):
        self._level -= 1
        #self.current.submit_time = "1970-01-01T00:00:00"
        if 0 == self._level:
            # end of XML
            return

        if 'job_list' == name:
            # end of job description, commit
            self.jobs.append(self.current)
            return

        # process job-level elements
        value_str = str(str.join('', self.value))
        if 'queue_name' == name:
            if '' == value_str:
                self.current['queue_name'] = None
                self.current['exec_node_name'] = None
            else:
                self.current['queue_name'] = value_str
                # FIXME: GE's queue names have the form queue@hostname;
                # raise an appropriate exception if this is not the case!
                at = value_str.index('@') + 1
                self.current['exec_node_name'] = value_str[at:]
        elif 'state' == name:
            # the GE state letters are explained in the `qstat` man page
            if (('E' in value_str)
                or ('h' in value_str)
                or ('T' in value_str) 
                or ('s' in value_str) or ('S' in value_str)
                or ('d' in value_str)):
                self.current.state = JobInfo.OTHER
            elif 'q' in value_str:
                self.current.state = JobInfo.PENDING
            elif 'r' in value_str:
                self.current.state = JobInfo.RUNNING
        elif 'JB_job_number' == name:
            self.current.jobid = value_str
        elif 'JB_submission_time' == name:
            self.current.submitted_at = time.strptime(value_str, '%Y-%m-%dT%H:%M:%S')
        elif 'JAT_start_time' == name:
            self.current.running_at = time.strptime(value_str, '%Y-%m-%dT%H:%M:%S')
        elif name in self.JOB_ATTRIBUTES:
            # convert each XML attribute to a Python representation
            # (defaulting to `str`, see CONVERT above)
            self.current[self.rename(name)] = self.CONVERT[name](value_str)

        return


class GridEngine(BatchSystem):
    """
    Abstract base class describing the interface that a node provider
    should implement.
    """

    def __init__(self, user='*'):
        """
        Set up parameters for querying SGE.
        """
        self.user = user


    def run_qstat(self):
        try:
            qstat_cmd = ['qstat', '-u', self.user, '-xml']
            qstat_process = subprocess.Popen(
                qstat_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False)
            stdout, stderr = qstat_process.communicate()
            return stdout
        except subprocess.CalledProcessError, ex:
            logging.error("Error running '%s': '%s'; exit code %d",
                          str.join(' ', qstat_cmd), stderr, ex.returncode)
            raise


    @staticmethod
    def parse_qstat_xml_output(qstat_xml_out):
        """
        Parse the output of a `qstat -xml` command and return a
        tuple `(jobid,submit_time,duration)`, where each item is a list of
        dictionary-like objects whose keys/attributes directly map the
        XML contents.
        """
        jobs = [ ]
        xml.sax.make_parser()
        xml.sax.parseString(qstat_xml_out, _QstatXmlHandler(jobs))
        return jobs


    def get_sched_info(self):
        """
        Query SGE through ``qstat -xml`` and return a list of
        `JobInfo` objects representing the jobs in the batch queue
        system.
        """
        qstat_xml_out = self.run_qstat()
        return self.parse_qstat_xml_output(qstat_xml_out)
