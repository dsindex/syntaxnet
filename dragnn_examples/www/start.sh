#!/bin/bash

set -o nounset
set -o errexit

# code from http://stackoverflow.com/a/1116890
function readlink()
{
    TARGET_FILE=$2
    cd `dirname $TARGET_FILE`
    TARGET_FILE=`basename $TARGET_FILE`

    # Iterate down a (possible) chain of symlinks
    while [ -L "$TARGET_FILE" ]
    do
        TARGET_FILE=`readlink $TARGET_FILE`
        cd `dirname $TARGET_FILE`
        TARGET_FILE=`basename $TARGET_FILE`
    done

    # Compute the canonicalized name by finding the physical path
    # for the directory we're in and appending the target file.
    PHYS_DIR=`pwd -P`
    RESULT=$PHYS_DIR/$TARGET_FILE
    echo $RESULT
}
export -f readlink

VERBOSE_MODE=0

function error_handler()
{
  local STATUS=${1:-1}
  [ ${VERBOSE_MODE} == 0 ] && exit ${STATUS}
  echo "Exits abnormally at line "`caller 0`
  exit ${STATUS}
}
trap "error_handler" ERR

PROGNAME=`basename ${BASH_SOURCE}`

function print_usage_and_exit()
{
  set +x
  local STATUS=$1
  echo "Usage: ${PROGNAME} [-v] [-v] [-h] [--help] [mode] [process]"
  echo ""
  echo " mode                0 : devel,  1 : service"
  echo " process             0 : max to #core, [1...n] : number of process"
  echo " Options -"
  echo "  -v                 enables verbose mode 1"
  echo "  -v -v              enables verbose mode 2"
  echo "  -h, --help         shows this help message"
  exit ${STATUS:-0}
}

function debug()
{
  if [ "$VERBOSE_MODE" != 0 ]; then
    echo $@
  fi
}

GETOPT=`getopt vh $*`
if [ $? != 0 ] ; then print_usage_and_exit 1; fi

eval set -- "${GETOPT}"

while true
do case "$1" in
     -v)            let VERBOSE_MODE+=1; shift;;
     -h|--help)     print_usage_and_exit 0;;
     --)            shift; break;;
     *) echo "Internal error!"; exit 1;;
   esac
done

if (( VERBOSE_MODE > 1 )); then
  set -x
fi


# template area is ended.
# -----------------------------------------------------------------------------
if [ ${#} != 2 ]; then print_usage_and_exit 1; fi

# current dir of this script
CDIR=$(readlink -f $(dirname $(readlink -f ${BASH_SOURCE[0]})))
PDIR=$(readlink -f $(dirname $(readlink -f ${BASH_SOURCE[0]}))/..)
PPDIR=$(readlink -f $(dirname $(readlink -f ${BASH_SOURCE[0]}))/../..)
PPPDIR=$(readlink -f $(dirname $(readlink -f ${BASH_SOURCE[0]}))/../../..)
[[ -f ${CDIR}/env.sh ]] && . ${CDIR}/env.sh || exit

# -----------------------------------------------------------------------------
# functions

function check_running
{
	progname=$1
	count_pgrep=`pgrep -f ${progname} | wc -l`
	count_pgrep=$(( ${count_pgrep} - 1 ))
	if (( count_pgrep > 0 )); then
		revert_calmness
		echo "count_pgrep = ${count_pgrep}"
		echo "${progname} is already running"
		exit 0
	fi
}


# end functions
# -----------------------------------------------------------------------------



# -----------------------------------------------------------------------------
# main 

make_calmness
child_verbose=""
if (( VERBOSE_MODE > 1 )); then
	revert_calmness
	child_verbose="-v -v"
fi

MODE=$1
PROCESS=$2

check_running ${daemon_name}

cd ${CDIR}

if (( MODE == 0 )); then
	nohup ${python} ${PPPDIR}/bazel-bin/work/dragnn_examples/${daemon_name} \
		--debug=True \
		--port=${port_devel} \
		--enable_konlpy=${enable_konlpy} \
		--dragnn_spec=${DRAGNN_SPEC_FILE} \
		--resource_path=${DATA_DIR} \
		--checkpoint_filename=${CHECKPOINT_FILE} \
		--enable_tracing=False \
		--tf_master=${TF_MASTER} \
		--log_file_prefix=${CDIR}/log/access.log \
		> /dev/null 2> /dev/null &
else
	nohup ${python}  ${PPPDIR}/bazel-bin/work/dragnn_examples/${daemon_name} \
		--debug=False \
		--port=${port_service} \
		--process=${PROCESS} \
		--enable_konlpy=${enable_konlpy} \
		--dragnn_spec=${DRAGNN_SPEC_FILE} \
		--resource_path=${DATA_DIR} \
		--checkpoint_filename=${CHECKPOINT_FILE} \
		--enable_tracing=False \
		--tf_master=${TF_MASTER} \
		--log_file_prefix=${CDIR}/log/access.log \
		> /dev/null 2> /dev/null &
fi
cd ${CDIR}

close_fd

# end main
# -----------------------------------------------------------------------------
