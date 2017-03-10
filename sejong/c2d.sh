#!/bin/bash

set -o nounset
set -o errexit
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
CDIR=$(readlink -f $(dirname $(readlink -f ${BASH_SOURCE[0]})))

[[ -f ${CDIR}/env.sh ]] && . ${CDIR}/env.sh || exit

# -----------------------------------------------------------------------------
# functions


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

if [ ! -e ${CDIR}/wdir ]; then
	mkdir ${CDIR}/wdir
fi
WDIR=${CDIR}/wdir
if [ ! -e ${CDIR}/log ]; then
	mkdir ${CDIR}/log
fi
LDIR=${CDIR}/log

for SET in training tuning test; do
	${python} ${CDIR}/c2d.py --mode=0 < ${WDIR}/sejong_treebank.txt.v1.${SET} > ${WDIR}/sejong_treebank.txt.v2.${SET} 2> ${WDIR}/sejong_treebank.txt.v2.${SET}.err
	${python} ${CDIR}/c2d.py --mode=1 < ${WDIR}/sejong_treebank.txt.v2.${SET} > ${WDIR}/deptree.txt.v2.${SET}         2> ${WDIR}/deptree.txt.v2.${SET}.err
	${python} ${CDIR}/align.py < ${WDIR}/deptree.txt.v2.${SET} > ${WDIR}/deptree.txt.v3.${SET}
done



close_fd

# end main
# -----------------------------------------------------------------------------
