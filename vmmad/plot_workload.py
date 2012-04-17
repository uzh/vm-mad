#! /usr/bin/env python
#
"""
Read a 'workload' file (as produced by ``simul.py``) and convert it to
an interractive HTML+JavaScript plot.
"""
# Copyright (C) 2011, 2012 ETH Zurich and University of Zurich. All rights reserved.
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


## stdlib imports
import csv
import argparse
import os
import os.path
import sys
import time


## main: run tests

if "__main__" == __name__:
    
    ## parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Produce an HTML plot of the data in a workload file.")
    parser.add_argument('input',
                        help="Input file.  Must be a CSV file, in the format"
                        " produced by `simul.py`.")
    parser.add_argument('output', nargs='?', default=None,
                        help="Output file. If not specified, output goes to STDOUT.")
    args = parser.parse_args()

    ## setup I/O
    infile = open(args.input, 'r')
    csv_input = csv.reader(infile)

    if args.output is not None:
        outfile = open(args.output, 'w')
    else:
        outfile = sys.stdout

    ## header
    outfile.write(r'''
<html>
<head>
<script type="text/javascript"
  src="http://dygraphs.com/dygraph-combined.js"></script>
</head>
<body>
<div id="graphdiv"></div>
<script type="text/javascript">
  g = new Dygraph(
    // containing div
    document.getElementById("graphdiv"),
    // CSV or URL of a CSV file.
    "Date/Time,Pending jobs,Running jobs,Started nodes,Idle nodes\n"
    ''')

    ## main loop: one line per data point
    for row in csv_input:
        timestamp = time.strftime('%Y/%m/%d %H:%M:%S', time.localtime(float(row[0])))
        outfile.write(
            r' + "' + 
            str.join(',', [
                timestamp,
                row[1], # pending
                row[2], # running
                row[3], # started nodes
                row[4], # idle nodes
                ])
            + r'\n"')

    ## footer
    outfile.write(r'''
    );
</script>
</body>
</html>
    ''')
