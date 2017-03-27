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
PDIR=$(readlink -f $(dirname $(readlink -f ${BASH_SOURCE[0]}))/..)

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

cd ${PDIR}

python=/usr/bin/python
SYNTAXNET_HOME=${PDIR}
BINDIR=$SYNTAXNET_HOME/bazel-bin/syntaxnet

CONTEXT=${CDIR}/sejong/context.pbtxt_p
TMP_DIR=${CDIR}/sejong/tmp_p/syntaxnet-output
mkdir -p ${TMP_DIR}
cat ${CONTEXT} | sed "s=OUTPATH=${TMP_DIR}=" > ${TMP_DIR}/context
MODEL_DIR=${CDIR}/models_sejong

HIDDEN_LAYER_SIZES=512,512
HIDDEN_LAYER_PARAMS=512,512
BATCH_SIZE=256
BEAM_SIZE=16

LP_PARAMS=${HIDDEN_LAYER_PARAMS}-0.08-4400-0.85
function pretrain_parser {
	${BINDIR}/parser_trainer \
	  --arg_prefix=brain_parser \
	  --batch_size=${BATCH_SIZE} \
	  --compute_lexicon \
	  --decay_steps=4400 \
	  --graph_builder=greedy \
	  --hidden_layer_sizes=${HIDDEN_LAYER_SIZES} \
	  --learning_rate=0.08 \
	  --momentum=0.85 \
	  --beam_size=1 \
	  --output_path=${TMP_DIR} \
	  --task_context=${TMP_DIR}/context \
	  --projectivize_training_set \
	  --training_corpus=tagged-training-corpus \
	  --tuning_corpus=tagged-tuning-corpus \
	  --params=${LP_PARAMS} \
	  --num_epochs=20 \
	  --report_every=100 \
	  --checkpoint_every=1000 \
	  --logtostderr
}

function evaluate_pretrained_parser {
	for SET in training tuning test; do
		${BINDIR}/parser_eval \
		--task_context=${TMP_DIR}/brain_parser/greedy/${LP_PARAMS}/context \
		--batch_size=${BATCH_SIZE} \
		--hidden_layer_sizes=${HIDDEN_LAYER_SIZES} \
		--beam_size=1 \
		--input=tagged-${SET}-corpus \
		--output=parsed-${SET}-corpus \
		--arg_prefix=brain_parser \
		--graph_builder=greedy \
		--model_path=${TMP_DIR}/brain_parser/greedy/${LP_PARAMS}/model
	done
}

function evaluate_pretrained_parser_by_eoj {
	for SET in training tuning test; do
		cut -f8 ${CDIR}/sejong/wdir/deptree.txt.v3.${SET} > ${CDIR}/sejong/wdir/deptree.txt.v3.${SET}.deprel
		paste ${TMP_DIR}/brain_parser/greedy/${LP_PARAMS}/parsed-${SET}-corpus ${CDIR}/sejong/wdir/deptree.txt.v3.${SET}.deprel > ${TMP_DIR}/brain_parser/greedy/${LP_PARAMS}/parsed-${SET}-corpus-add
		${python} ${CDIR}/sejong/align_r.py < ${TMP_DIR}/brain_parser/greedy/${LP_PARAMS}/parsed-${SET}-corpus-add > ${TMP_DIR}/brain_parser/greedy/${LP_PARAMS}/parsed-${SET}-corpus-eoj
		${python} ${CDIR}/sejong/eval.py -a ${CDIR}/sejong/wdir/deptree.txt.v2.${SET} -b ${TMP_DIR}/brain_parser/greedy/${LP_PARAMS}/parsed-${SET}-corpus-eoj \
			> ${TMP_DIR}/brain_parser/greedy/${LP_PARAMS}/parsed-${SET}-corpus-eoj-ret
	done
}

GP_PARAMS=${HIDDEN_LAYER_PARAMS}-0.02-100-0.9
function train_parser {
	${BINDIR}/parser_trainer \
	  --arg_prefix=brain_parser \
	  --batch_size=${BATCH_SIZE} \
	  --compute_lexicon \
	  --decay_steps=100 \
	  --graph_builder=structured \
	  --hidden_layer_sizes=${HIDDEN_LAYER_SIZES} \
	  --learning_rate=0.02 \
	  --momentum=0.9 \
	  --beam_size=${BEAM_SIZE} \
	  --output_path=${TMP_DIR} \
	  --task_context=${TMP_DIR}/brain_parser/greedy/${LP_PARAMS}/context \
	  --training_corpus=projectivized-training-corpus \
	  --tuning_corpus=tagged-tuning-corpus \
	  --params=${GP_PARAMS} \
	  --pretrained_params=${TMP_DIR}/brain_parser/greedy/${LP_PARAMS}/model \
	  --pretrained_params_names=embedding_matrix_0,embedding_matrix_1,embedding_matrix_2,bias_0,weights_0,bias_1,weights_1 \
	  --num_epochs=10 \
	  --report_every=25 \
	  --checkpoint_every=200 \
	  --logtostderr
}

function evaluate_parser {
	for SET in training tuning test; do
		${BINDIR}/parser_eval \
		--task_context=${TMP_DIR}/brain_parser/structured/${GP_PARAMS}/context \
		--batch_size=${BATCH_SIZE} \
		--hidden_layer_sizes=${HIDDEN_LAYER_SIZES} \
		--beam_size=${BEAM_SIZE} \
		--input=tagged-${SET}-corpus \
		--output=beam-parsed-${SET}-corpus \
		--arg_prefix=brain_parser \
		--graph_builder=structured \
		--model_path=${TMP_DIR}/brain_parser/structured/${GP_PARAMS}/model
	done
}

function evaluate_parser_by_eoj {
	for SET in training tuning test; do
		cut -f8 ${CDIR}/sejong/wdir/deptree.txt.v3.${SET} > ${CDIR}/sejong/wdir/deptree.txt.v3.${SET}.deprel
		paste ${TMP_DIR}/brain_parser/structured/${GP_PARAMS}/beam-parsed-${SET}-corpus ${CDIR}/sejong/wdir/deptree.txt.v3.${SET}.deprel > ${TMP_DIR}/brain_parser/structured/${GP_PARAMS}/beam-parsed-${SET}-corpus-add
		${python} ${CDIR}/sejong/align_r.py < ${TMP_DIR}/brain_parser/structured/${GP_PARAMS}/beam-parsed-${SET}-corpus-add > ${TMP_DIR}/brain_parser/structured/${GP_PARAMS}/beam-parsed-${SET}-corpus-eoj
		${python} ${CDIR}/sejong/eval.py -a ${CDIR}/sejong/wdir/deptree.txt.v2.${SET} -b ${TMP_DIR}/brain_parser/structured/${GP_PARAMS}/beam-parsed-${SET}-corpus-eoj \
			> ${TMP_DIR}/brain_parser/structured/${GP_PARAMS}/beam-parsed-${SET}-corpus-eoj-ret
	done
}

function xcopy_model {
	cp -rf ${TMP_DIR}/brain_parser/structured/${GP_PARAMS}/model ${MODEL_DIR}/parser-params
	cp -rf ${TMP_DIR}/*-map ${MODEL_DIR}/
	cp -rf ${TMP_DIR}/*-table ${MODEL_DIR}/
	cp -rf ${TMP_DIR}/tag-to-category ${MODEL_DIR}/
}

function copy_model {
	mkdir -p ${MODEL_DIR}/parser-params
	cp -rf ${TMP_DIR}/brain_parser/structured/${GP_PARAMS}/model.* ${MODEL_DIR}/parser-params
	cp -rf ${TMP_DIR}/*-map ${MODEL_DIR}/
	cp -rf ${TMP_DIR}/*-table ${MODEL_DIR}/
	cp -rf ${TMP_DIR}/tag-to-category ${MODEL_DIR}/
}

pretrain_parser
evaluate_pretrained_parser
evaluate_pretrained_parser_by_eoj
train_parser
evaluate_parser
evaluate_parser_by_eoj
copy_model

close_fd

# end main
# -----------------------------------------------------------------------------
