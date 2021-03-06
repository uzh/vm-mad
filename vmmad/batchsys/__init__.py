#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces to batch queueing systems.
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
from vmmad.orchestrator import JobInfo


class BatchSystem(object):
    """
    Abstract base class describing the interface that a node provider
    should implement.
    """

    def __init__(self):
        """
        Initialize a batch system interface.

        There's no default set of arguments; each class should
        implement its own constructor signature.
        """
        pass
        

    @abstractmethod
    def get_sched_info(self):
        """
        Query the job scheduler and return a list of `JobInfo` objects
        representing the jobs in the batch queue system.
        """
        pass
