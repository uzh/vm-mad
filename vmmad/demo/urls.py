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

# 3rd party imports
import django.conf
from django.conf.urls.defaults import patterns

# local imports
from vmmad import log
from vmmad.demo.main import demo


# the main program
log.warning("Importing demo.urls as module '%s'", __name__)

urlpatterns = patterns(
    '',
    # home page
    (r'^$',         demo.status),
    # the `/x/` hierarchy is used for methods not meant for user consumption
    (r'^x/ready$', demo.ready),
    )
