#! /usr/bin/env python
# -*- coding: latin1 -*-
# 


"""
vm-mad simulator by  
    <riccardo.murri@uzh.ch>
    CHristian Panse <cp@fgcz.ethz.ch>
2011-12-14 @ GC3
2011-12-15 @ KafiSchnaps
2011-12-16 @ FGCZ 


aim of the simulations:
    find out how the orchestrator is behaving under 'pressure'

see also:
http://www.ifi.uzh.ch/pax/web/uploads/pdf/publication/1408/thesis.pdf
@mastersthesis{instance1408,
title = {{Investigation of economical and practical aspects of commercial cloud computing for Life Sciences}},
author = {Aleksandar Markovic},
editor = {Burkhard Stiller and Christian Panse},
group = {csg},
year = {2010},
school = {University of Zurich},
month = {March},
Date-Added = {2010-05-06 13:46:02},
Date-Modified = {2010-05-06 13:57:45}
}

pages: 57-60

"""

# Copyright (C) 2011 ETH Zurich and University of Zurich. All rights reserved.
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

import os
import sys
import time
import random

def signal_handler(signal, frame):
    sys.exit(0)

class Sim(object):
    """
        each integer item in the pending list cor. to the jobs runtime
        
        a host is idle if the item in the running list is less than zero

        if those hosts keep idle they can be removed.

        note we turn on / halt only one host within  time step
    """

    def __init__(self):
        self.maxVM=10
        self.pending=[ ]
        self.running=[ ]
        self.steps=0

    def startVM(self):
        print "starting vm ..."
        if len(self.running) < self.maxVM:
            self.running.append(-1)
        else:
            print "can not allocate more VMs"

    def stopVM(self, j):
        del self.running[j]              

    """
    todo: 
        * use real world data; do boot straping
        * random populated queue

    """
    def populate(self):
        for i in range(0,20):
            self.pending.append(random.randint(1800, 3600))

            
    def printStatus(self):
        vmidleC=0
        runningC=0
        for i in self.running:
            if i < 0:
                vmidleC +=1
            else:
                runningC += 1

        try:
            f = open("main_sim.txt", "a")
        except:
            print ("could not open file")
            sys.exit(1)

        f.write(str(self.steps) + ','
            + str(len(self.pending)) + ','
            + str(runningC) + ','
            + str(vmidleC) + '\n')
        f.close()

        #print "number of pending jobs =", len(self.pending)
        #print "number of running jobs =", (runningC)
        #print "number of idle hosts =", (vmidleC)
        #print self.running


    def run(self):
        # as long as we have things to do
        while (len(self.pending) > 0) or (len(self.running) > 0):
            self.steps+=1
            # time is going on
            for j in range(0, len(self.running)):
                self.running[j] -= 1

            for j in range(0, len(self.running)):
                # check if we run an other job
                if self.running[j] < 0 and len(self.pending) > 0:
                    self.running[j]=self.pending.pop(0)
                    break;
                # in case the pending queue is empty lets check if we can halt stop a VM 
                elif self.running[j] < 0:
                    self.stopVM(j)
                    break;

            # print some data to a file for later plotting
            self.printStatus()

            if len(self.pending) / 2  > len(self.running):
                  self.startVM()
            
            #time.sleep(1)

if "__main__" == __name__:
    mySim=Sim()
    mySim.populate()
    mySim.run()
