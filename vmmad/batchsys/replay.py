#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Mock batch system interface, reading submitted jobs from a history file.
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
import csv
import time

# local imports
from vmmad import log
from vmmad.orchestrator import JobInfo


class JobsFromFile(object):
    """
    Mock batch system interface, replaying submitted jobs info from a CSV file.
    """

    def __init__(self, filename, timer=time.time, start_time=-1):
        """
        Construct a `JobsFromFile` object.

        Read job history from `filename`, which must be a CSV file
        with the following format:

        - the first line is a header line with the column names;
        - column names are all uppercase;
        - the number and type of columns is abritrary,
          but at least these columns *must* be present:

            + ``JOBID``: a string uniquely identifying the job
            + ``SUBMITTED_AT``: time the job was submitted, as a UNIX epoch
            + ``RUN_DURATION``: duration of the job, in seconds

        Only jobs that were submitted after `start_time` are loaded;
        if `start_time` is `None`, then all jobs are loaded and the
        `.start_time` attribute is set to the first submitted job in
        the list.

        Passing of time is controlled via the `timer` parameter: this
        must be a callable that returns the 'current time' in UNIX
        epoch format (just like Pythons `time.time`).

        :param str filename: The CSV file to read job history from.
        :param timer: A function returning the (possibly simulated) current time in UNIX epoch format.
        :param int start_time: Replay start time, as a UNIX epoch.

        """
        self.timer = timer
        self.time_last_checked = 0
        
        # auto-detect CSV delimiter, etc.
        with open(filename, 'r') as input_file:
            sample = input_file.read(1024)
            input_file.seek(0)
            rows = csv.DictReader(input_file,
                                  dialect = csv.Sniffer().sniff(sample))
            # load all jobs into memory, ordered by descending
            # submission time, so that the last item is the next job
            # to be submitted and we can just .pop() it
            self.future_jobs = list(
                sorted((JobInfo(jobid=row['JOBID'],
                                state=JobInfo.PENDING,
                                submitted_at=float(row['SUBMITTED_AT']),
                                duration=float(row['RUN_DURATION']))
                        for row in rows if float(row['SUBMITTED_AT']) > start_time),
                    # sort list of jobs by submission time
                    cmp=(lambda x,y: cmp(x.submitted_at, y.submitted_at)),
                    reverse=True))
        log.info("Loaded %d jobs from file '%s'", len(self.future_jobs), filename)
        assert (len(self.future_jobs) < 2
                or (self.future_jobs[0].submitted_at >= self.future_jobs[1].submitted_at))
        
        # if `start_time` has not been set, then use earliest job
        # submission time as starting point
        if start_time == -1:
            self.start_time = self.future_jobs[-1].submitted_at 
        else:
            self.start_time = start_time

        # list of jobs currently in the (simulated) batch system
        self.jobs = [ ]
        

    def get_sched_info(self):
        """
        Return a list of `JobInfo` objects representing the jobs in
        the batch queue system.

        Each invocation of `get_sched_info` returns the list of jobs
        that are either running or submitted to the batch system in
        the interval between the 'current time' (as returned by the
        `timer` function) and the time of the previous invocation.

        """
        now = self.timer()
        # add jobs that were submitted since last check
        for job in self.next_jobs(self.time_last_checked, now):
            self.jobs.append(job)
        self.time_last_checked = now
        # remove jobs that have terminated since
        for i, job in enumerate(self.jobs):
            if job.submitted_at + job.duration < now:
                del self.jobs[i]
        return self.jobs

    def next_jobs(self, since, until):
        assert until > since
        while len(self.future_jobs) > 0:
            job = self.future_jobs.pop()
            if until >= job.submitted_at:
                if job.submitted_at >= since:
                    yield job
                else:
                    # job is in the past (relative to the Simulator's concept of time) so ignore it
                    pass
            else:
                # job is in the future: put it back for next round
                self.future_jobs.append(job)
                raise StopIteration
