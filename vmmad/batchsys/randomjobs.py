#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Mock batch system interface, simulating jobs of random duration.
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
from copy import copy
import random

# local imports
from vmmad import log
from vmmad.orchestrator import JobInfo


class UniformlyInRange(object):
    """
    Iterator returning an integer `x` chosen *uniformly at random*
    from the range `low <= x <= high`.  (`low` and
    `high` are constructor parameters.)
    """
    def __init__(self, low, high):
        assert low < high
        self.min = low
        self.max = high

    def next(self):
        return random.randint(self.min, self.max)


class NormallyDistributedInRange(object):
    """
    Iterator returning an integer chosen at random such that
    results are normally distributed.
    
    Each call to the `next()` method returns a result `x` from the
    range `low <= x <= high`.  (`low` and `high` are constructor
    parameters.)
    """
    def __init__(self, low, high, mu, sigma):
        assert low < high
        self.min = low
        self.max = high
        self.mu = mu
        self.sigma = sigma

    def next(self):
        return self.min + random.gauss(self.mu, self.sigma)*(self.high - self.low)


class RandomJobs(object):
    """
    Mock batch system interface, simulating submission of jobs of
    random duration at a specified rate.
    """

    def __init__(self, N, p, duration=(24*60*60)):
        """
        Construct a `RandomJobs` object.

        :param int N: The number of submission attempts per orchestrator cycle.
        :param float p: A real number with `0 < p < 1`; expresses the probabilty that a job is submitted at each attempt.
        :param duration: Maximum number of seconds that a job can last; otherwise this must be a an iterator that returns an integer (expressing duration in seconds) at every invocation of its `next()` method.
        """
        self.N = N
        self.p = p
        if isinstance(duration, int):
            assert duration > 0
            self.duration = UniformlyInRange(1, duration)
        self.jobs = [ ]
        self.next_jobid = 0
        

    def get_sched_info(self):
        """
        Return a list of `JobInfo` objects representing the jobs in
        the batch queue system.

        At every invocation, this method rolls a dice `N` times and
        submits a job iff the result of the dice is greater than `p`.
        So the effective job submission rate is `N * p / (length of an
        orchestrator cycle)`.  The values of `N` and `p` are as
        specified to the constructor.
    
        Job durations are drawn from a random distribution that can be set
        with the `duration` constructor parameter.
        """
        # generate new jobs
        for _ in xrange(N):
            dice = random.random()
            if dice <= self.p:
                continue
            self.next_jobid += 1
            self.jobs.append(
                JobInfo(
                    jobid=str(self.next_jobid),
                    state=JobInfo.PENDING,
                    duration=self.duration.next()
                ))
        return self.jobs
