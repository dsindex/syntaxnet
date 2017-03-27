#!/bin/bash

set -o nounset
set -o errexit

# code from https://github.com/bazelbuild/bazel/blob/master/scripts/packages/bazel.sh
function get_realpath() {
    if [ "$(uname -s)" == "Darwin" ]; then
        local queue="$1"
        if [[ "${queue}" != /* ]] ; then
            # Make sure we start with an absolute path.
            queue="${PWD}/${queue}"
        fi
        local current=""
        while [ -n "${queue}" ]; do
            # Removing a trailing /.
            queue="${queue#/}"
            # Pull the first path segment off of queue.
            local segment="${queue%%/*}"
            # If this is the last segment.
            if [[ "${queue}" != */* ]] ; then
                segment="${queue}"
                queue=""
            else
                # Remove that first segment.
                queue="${queue#*/}"
            fi
            local link="${current}/${segment}"
            if [ -h "${link}" ] ; then
                link="$(readlink "${link}")"
                queue="${link}/${queue}"
                if [[ "${link}" == /* ]] ; then
                    current=""
                fi
            else
                current="${link}"
            fi
        done

        echo "${current}"
    else
        readlink -f "$1"
    fi
}

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
  echo "Usage: ${PROGNAME} [-v] [-v] [-h] [--help]"
  echo ""
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
if [ ${#} != 0 ]; then print_usage_and_exit 1; fi

# current dir of this script
CDIR=$(get_realpath $(dirname $(get_realpath ${BASH_SOURCE[0]})))
PDIR=$(get_realpath $(dirname $(get_realpath -f ${BASH_SOURCE[0]}))/..)

# -----------------------------------------------------------------------------
# functions

function make_calmness()
{
	exec 3>&2 # save 2 to 3
	exec 2> /dev/null
}

function revert_calmness()
{
	exec 2>&3 # restore 2 from previous saved 3(originally 2)
}

function close_fd()
{
	exec 3>&-
}

function jumpto
{
	label=$1
	cmd=$(sed -n "/$label:/{:a;n;p;ba};" $0 | grep -v ':$')
	eval "$cmd"
	exit
}


# end functions
# -----------------------------------------------------------------------------



# -----------------------------------------------------------------------------
# main 

make_calmness
if (( VERBOSE_MODE > 1 )); then
	revert_calmness
fi

python=/usr/bin/python

SRC_CORPUS_DIR=${CDIR}/UD_English
DATA_DIR=${CDIR}/dragnn_examples/data
TRAIN_FILE=${DATA_DIR}/en-ud-train.conllu.conv
DEV_FILE=${DATA_DIR}/en-ud-dev.conllu.conv

function convert_corpus {
	corpus_dir=$1
	for corpus in $(ls ${corpus_dir}/*.conllu); do
		${python} ${CDIR}/convert.py < ${corpus} > ${corpus}.conv
	done
}

function prepare_data {
	mkdir -p ${DATA_DIR}
	cp -rf ${SRC_CORPUS_DIR}/*.conllu ${DATA_DIR}
	convert_corpus ${DATA_DIR}
}

function train {
	cp -rf ${CDIR}/dragnn_examples/BUILD ${PDIR}/examples/dragnn
	cp -rf ${CDIR}/dragnn_examples/test_dragnn.py ${PDIR}/examples/dragnn
	cd ${PDIR}
	bazel build -c opt //examples/dragnn:test_dragnn
	./bazel-bin/examples/dragnn/test_dragnn --data_dir=${DATA_DIR} --train_file=${TRAIN_FILE} --dev_file=${DEV_FILE}
}

prepare_data
train

close_fd

# end main
# -----------------------------------------------------------------------------
