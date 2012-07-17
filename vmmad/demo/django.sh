#! /bin/sh
#
PROG="$(basename $0)"

usage () {
cat <<EOF
Usage: $PROG [options] path/to/module.py django_command [arg1 arg2 ...]

Run a Django server command on the application contained in the
specified Python module.

Options:

  --help, -h  Print this help text.

EOF
}


## helper functions
die () {
  rc="$1"
  shift
  (echo -n "$PROG: ERROR: ";
      if [ $# -gt 0 ]; then echo "$@"; else cat; fi) 1>&2
  exit $rc
}

warn () {
  (echo -n "$PROG: WARNING: ";
      if [ $# -gt 0 ]; then echo "$@"; else cat; fi) 1>&2
}

have_command () {
  type "$1" >/dev/null 2>/dev/null
}

require_command () {
  if ! have_command "$1"; then
    die 1 "Could not find required command '$1' in system PATH. Aborting."
  fi
}

is_absolute_path () {
    expr match "$1" '/' >/dev/null 2>/dev/null
}


## parse command-line 

short_opts='h'
long_opts='help,debug'

if [ "x$(getopt -T)" != 'x--' ]; then
    # GNU getopt
    args=$(getopt --name "$PROG" --shell sh -l "$long_opts" -o "+$short_opts" -- "$@")
    if [ $? -ne 0 ]; then
        die 1 "Type '$PROG --help' to get usage information."
    fi
    # use 'eval' to remove getopt quoting
    eval set -- $args
else
    # old-style getopt, use compatibility syntax
    args=$(getopt "$short_opts" "$@") 
    if [ $? -ne 0 ]; then
        die 1 "Type '$PROG --help' to get usage information."
    fi
    set -- $args
fi

while [ $# -gt 0 ]; do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --debug)   set -x ;;
        --)        shift; break ;;
        *)         break ;;
    esac
    shift
done


## main

require_command django-admin.py

# find settings module
settings=$(find $(pwd) -name settings.py)
module=`basename "$settings" .py`
dir=`dirname "$settings"`

if [ -n "$1" ]; then
    cmd="$1"
    shift
else
    cmd="runserver --noreload 0.0.0.0:8000"
fi

exec django-admin.py $cmd --pythonpath="$dir" --settings="$module" "$@"
