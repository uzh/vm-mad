#!/usr/bin/python
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


# see:
# http://docs.python.org/library/curses.html
# http://svn.python.org/projects/python/trunk/Demo/curses/
# http://fgcz-data.uzh.ch/cgi-bin/fgcz_ge_info.py


class Struct(Mapping):
    """
    A `dict`-like object, whose keys can be accessed with the usual
    '[...]' lookup syntax, or with the '.' get attribute syntax.

    Examples::

      >>> a = Struct()
      >>> a['x'] = 1
      >>> a.x
      1
      >>> a.y = 2
      >>> a['y']
      2

    Values can also be initially set by specifying them as keyword
    arguments to the constructor::

      >>> a = Struct(z=3)
      >>> a['z']
      3
      >>> a.z
      3
    """
    def __init__(self, initializer=None, **kw):
        if initializer is not None:
            try:
                # initializer is `dict`-like?
                for name, value in initializer.items():
                    self[name] = value
            except AttributeError: 
                # initializer is a sequence of (name,value) pairs?
                for name, value in initializer:
                    self[name] = value
        for name, value in kw.items():
            self[name] = value

    # the `Mapping` abstract class defines all std `dict` methods,
    # provided that `__getitem__`, `__setitem__` and `keys` and a few
    # others are defined.

    def __iter__(self):
            return iter(self.__dict__)
    
    def __len__(self):
            return len(self.__dict__)

    def __setitem__(self, name, val):
        self.__dict__[name] = val

    def __getitem__(self, name):
        return self.__dict__[name]

    def keys(self):
        return self.__dict__.keys()


class myQstatHandler(xml.sax.ContentHandler):
        """
Example:

  $ qstat -u '*' -xml
  <?xml version='1.0'?>
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
      <job_list state="running">
        <JB_job_number>390527</JB_job_number>
        <JAT_prio>0.50500</JAT_prio>
        <JB_name>KasalathS3_1-tophat.sh</JB_name>
        <JB_owner>hubert</JB_owner>
        <state>r</state>
        <JAT_start_time>2011-12-13T07:02:51</JAT_start_time>
        <queue_name>GT@fgcz-c-065</queue_name>
        <slots>1</slots>
      </job_list>
      <job_list state="running">
        <JB_job_number>390548</JB_job_number>
        <JAT_prio>0.50500</JAT_prio>
        <JB_name>fgcz_sge_rserver__108707</JB_name>
        <JB_owner>bfabric</JB_owner>
        <state>r</state>
        <JAT_start_time>2011-12-13T09:32:21</JAT_start_time>
        <queue_name>rserver@fgcz-c-051</queue_name>
        <slots>1</slots>
      </job_list>
      <job_list state="running">
        <JB_job_number>390553</JB_job_number>
        <JAT_prio>0.50500</JAT_prio>
        <JB_name>fgcz_sge_rserver__108708</JB_name>
        <JB_owner>bfabric</JB_owner>
        <state>r</state>
        <JAT_start_time>2011-12-13T11:02:36</JAT_start_time>
        <queue_name>rserver@fgcz-c-063</queue_name>
        <slots>1</slots>
      </job_list>
      <job_list state="running">
        <JB_job_number>390554</JB_job_number>
        <JAT_prio>0.60500</JAT_prio>
        <JB_name>p582_POG</JB_name>
        <JB_owner>tanguy</JB_owner>
        <state>r</state>
        <JAT_start_time>2011-12-13T11:04:45</JAT_start_time>
        <queue_name>GT@fgcz-c-054</queue_name>
        <slots>8</slots>
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


def running_and_pending_jobs():
        jobs = Struct()
        xml.sax.make_parser()
        qstat_cmd = ['qstat', '-u', '*', '-xml']
        try:
                qstat_process = subprocess.Popen(
                        qstat_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=False)
                qstat_stdout, stderr = qstat_process.communicate()
                xml.sax.parseString(qstat_stdout, myQstatHandler(jobs))
        except subprocess.CalledProcessError, ex:
                logging.error("Error running '%s': exit code %d",
                              str.join(' ', qstat_cmd), ex.returncode)
        except Exception, ex:
                logging.error("Unexpected error: %s: %s",
                              ex.__class__.__name__, str(ex))
                raise
        return (jobs.running, jobs.pending)


if __name__ == '__main__':
        jobs = running_and_pending_jobs()
        print "Running jobs:"
        print(jobs.running)
        print "Pending jobs:"
        print(jobs.pending)
