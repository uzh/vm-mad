#! /usr/bin/env python
#
"""
Misc. utility functions and classes.
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


# stdlib imports
from collections import Mapping
import functools


def abstractmethod(fn):
    """
    Make a method "abstract": if it is ever called,
    raises a `NotImplementedError` telling user
    that the method should have been implemented in a subclass.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        raise NotImplementedError("Called abstract method '%s.%s':"
                                  " should have been implemented in a subclass."
                                  % (fn.im_class.__name__, fn.im_func.__name__))
    return wrapper


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
