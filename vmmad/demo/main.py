#! /usr/bin/env python
#
"""
Launch compute node VMs on demand.
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
import os
import sys

# local imports
from vmmad import log
#from vmmad.demo.phony import DemoOrchestrator
from vmmad.demo.fgcz import DemoOrchestrator


# the main program
log.warning(
    "Importing demo.main as module '%s', creating DemoOrchestrator instance.",
    __name__)


# The actual Orchestrator instance.  There should be one and only one
# such instance running.
demo = DemoOrchestrator()

