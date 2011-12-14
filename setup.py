#!/usr/bin/env python

# See http://packages.python.org/distribute/setuptools.html for details
from distribute_setup import use_setuptools
use_setuptools()


# XXX: `./setup.py` fails with "error: invalid command 'develop'" when
# package `distribute` is first downloaded by `distribute_setup`;
# subsequent invocations of it (when the `distribute-*.egg` file is
# already there run fine, apparently.  So, let us re-exec ourselves
# to ensure that `distribute` is loaded properly.
REINVOKE = "__SETUP_REINVOKE"
import sys
import os
if not os.environ.has_key(REINVOKE):
    # mutating os.environ doesn't work in old Pythons
    os.putenv(REINVOKE, "1")
    try:
        os.execvp(sys.executable, [sys.executable] + sys.argv)
    except OSError, x:
        sys.stderr.write("Failed to re-exec '%s' (got error '%s');"
                         " continuing anyway, keep fingers crossed.\n"
                         % (str.join(' ', sys.argv), str(x)))
if hasattr(os, "unsetenv"):
    os.unsetenv(REINVOKE)


def read_whole_file(path):
    stream = open(path, 'r')
    text = stream.read()
    stream.close
    return text


# see http://peak.telecommunity.com/DevCenter/setuptools
# for an explanation of the keywords and syntax of this file.
#
import setuptools
import setuptools.dist
setuptools.setup(
    name = "vmmad",
    version = "0.1.dev", # see: http://packages.python.org/distribute/setuptools.html

    packages = setuptools.find_packages("vmmad", exclude=['ez_setup']),

    # metadata for upload to PyPI
    description = "A Python library and simple command-line frontend for computational job submission to multiple resources.",
    long_description = read_whole_file('README.txt'),
    author = "VM-MAD Project (ETH Zurich and University of Zurich)",
    author_email = "virtualization@gc3.lists.uzh.ch",
    license = "Apache Software License 2.0",
    keywords = "virtualization cloud ec2 sge gridengine batch job",
    url = "http://vm-mad.googlecode.com/", # project home page

    # see http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers = [
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "License :: DFSG approved",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.4",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Topic :: Scientific/Engineering",
        "Topic :: System :: Clustering",
        "Topic :: System :: Distributed Computing",
        ],

    entry_points = {
        'console_scripts': [
            # the generic, catch-all script:
            'vm-mad = vmutils.frontend:main',
            ],
       },

    # run-time dependencies
    install_requires = [
        # Apache LibCloud
        'apache_libcloud>=0.5',
        # texttable -- format tabular text output
        'texttable',
        # pyCLI -- object-oriented command-line app programming
        'pyCLI==2.0.2',
        ],

    # additional non-Python files to be bundled in the package
    package_data = {
        'vmlibs': [
            #'etc/vm-mad.conf.example',
            ],
        },

    # `zip_safe` can ease deployment, but is only allowed if the package
    # do *not* do any __file__/__path__ magic nor do they access package data
    # files by file name (use `pkg_resources` instead).
    zip_safe = True,
)
