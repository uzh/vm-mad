#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Functions to get information about a Sun/Oracle/Open Grid Engine
cluster status.
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


import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(name)s: [%(asctime)s] %(levelname)-8s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# stdlib imports
from collections import Mapping, defaultdict
import os
import subprocess
import sys
import time
import UserDict
import xml.sax

# local imports
from util import Struct

# see:
# http://docs.python.org/library/curses.html
# http://svn.python.org/projects/python/trunk/Demo/curses/
# http://fgcz-data.uzh.ch/cgi-bin/fgcz_ge_info.py


class _QstatXmlHandler(xml.sax.ContentHandler):
        """
        SAX `ContentHandler` implementation for parsing the output of
        `qstat -u ... -xml`.
        """

        # these XML elements yield information about a job
        JOB_ATTRIBUTES = [
                'JB_job_number',
                'JAT_prio',
                'JB_name',
                'state',
                'JB_submission_time',
                'queue_name',
                'slots'
                ]

        # conversion of XML fields to Python data
        CONVERT = defaultdict(
                # by default, return `str`
                lambda: str,
                # return other values in particular cases:
                JB_job_number=int,
                JAT_prio=float,
                slots=int,
                )

        def __init__(self, dest):
                self.dest = dest
                self.running = [ ]
                self.pending = [ ]
                self.value = [ ]
                self._level = 0

        def startElement(self,name,attrs):
                self._level += 1
                if name == 'job_list':
                        assert 'state' in attrs
                        self.current = Struct()
                        self.current_job_state = attrs['state']

                ## for other elements, just reset `value` so we can
                ## accumulate characters in `self.characters`
                else:
                        self.value = []


        def characters(self, chrs):
                self.value.append(chrs)


        def endElement(self,name):
                self._level -= 1

                if 0 == self._level:
                        # end of XML, output data structure
                        self.dest.running = self.running
                        self.dest.pending = self.pending
                        return

                if 'job_list' == name:
                        # end of job description, commit
                        if 'running' == self.current_job_state:
                                self.running.append(self.current)
                        elif 'pending' == self.current_job_state:
                                self.pending.append(self.current)
                        else:
                                raise AssertionError("Unexpected job state '%s'"
                                                     % self.current_job_state)
                        return

                # process job-level elements
                value_str = str(str.join('', self.value))
                if 'queue_name' == name:
                        if '' == value_str:
                                self.current['queue_name'] = None
                        else:
                                self.current['queue_name'] = value_str
                elif name in self.JOB_ATTRIBUTES:
                        # convert each XML attribute to a Python representation
                        # (defaulting to `str`, see CONVERT above)
                        self.current[name] = self.CONVERT[name](value_str)

                return


def _run_qstat(user='*'):
        try:
                qstat_cmd = ['qstat', '-u', '*', '-xml']
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


def running_and_pending_jobs(qstat_xml_out=None):
        """
        Parse the output of a `qstat -u ... -xml` command and return a
        pair `(running, pending)`, where each item is a list of
        dictionary-like objects whose keys/attributes directly map the
        XML contents.
        """
        if qstat_xml_out is None:
                qstat_xml_out = _run_qstat()
        jobs = Struct()
        xml.sax.make_parser()
        xml.sax.parseString(qstat_xml_out, _QstatXmlHandler(jobs))
        return (jobs.running, jobs.pending)


## main: run tests

if __name__ == "__main__":
    import doctest
    doctest.testmod(name="ge_info",
                    optionflags=doctest.NORMALIZE_WHITESPACE)
