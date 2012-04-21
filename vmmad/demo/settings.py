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
import vmmad.demo.main

# the main program
log.debug("Importing demo.settings as module '%s'", __name__)

DEBUG = True

# Minimal Django setup.  This *must* point to a different file,
# otherwise Django will load this file twice: once for reading the
# settings, and once for reading the URLs.  (In addition, the URLconf
# file is reloaded each time it's changed, which does not happen with
# the settings file.)
ROOT_URLCONF = 'urls'
