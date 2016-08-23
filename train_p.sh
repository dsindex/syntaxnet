#!/bin/bash

set -o nounset
set -o errexit

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
DRY_RUN_MODE=0

function print_usage_and_exit()
{
  set +x
  local STATUS=$1
  echo "Usage: ${PROGNAME} [-v] [-v] [--dry-run] [-h] [--help]"
  echo ""
  echo " Options -"
  echo "  -v                 enables verbose mode 1"
  echo "  -v -v              enables verbose mode 2"
  echo "      --dry-run      show what would have been dumped"
  echo "  -h, --help         shows this help message"
  exit ${STATUS:-0}
}

function debug()
{
  if [ "$VERBOSE_MODE" != 0 ]; then
    echo $@
  fi
}

GETOPT=`getopt -o vh --long dry-run,help -n "${PROGNAME}" -- "$@"`
if [ $? != 0 ] ; then print_usage_and_exit 1; fi

eval set -- "${GETOPT}"

while true
do case "$1" in
     -v)            let VERBOSE_MODE+=1; shift;;
     --dry-run)     DRY_RUN_MODE=1; shift;;
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

CORPUS_DIR=${CDIR}/UD_English

CONTEXT=${CORPUS_DIR}/context.pbtxt_p
TMP_DIR=${CORPUS_DIR}/tmp_p/syntaxnet-output
mkdir -p ${TMP_DIR}
cat ${CONTEXT} | sed "s=OUTPATH=${TMP_DIR}=" > ${TMP_DIR}/context
MODEL_DIR=${CDIR}/models

PARSER_HIDDEN_LAYER_SIZES=200,200
PARSER_HIDDEN_LAYER_PARAMS='200x200'
BATCH_SIZE=256
BEAM_SIZE=16

function convert_corpus {
	corpus_dir=$1
	for corpus in $(ls ${corpus_dir}/*.conllu); do
		${python} ${CDIR}/convert.py < ${corpus} > ${corpus}.conv
	done
}

LP_PARAMS=${PARSER_HIDDEN_LAYER_PARAMS}-0.08-4400-0.85-4
function pretrain_parser {
	${BINDIR}/parser_trainer \
	  --arg_prefix=brain_parser \
	  --batch_size=${BATCH_SIZE} \
	  --compute_lexicon \
	  --decay_steps=4400 \
	  --graph_builder=greedy \
	  --hidden_layer_sizes=${PARSER_HIDDEN_LAYER_SIZES} \
	  --learning_rate=0.08 \
	  --momentum=0.85 \
	  --output_path=${TMP_DIR} \
	  --task_context=${TMP_DIR}/context \
	  --seed=4 \
	  --projectivize_training_set \
	  --training_corpus=tagged-training-corpus \
	  --tuning_corpus=tagged-tuning-corpus \
	  --params=${LP_PARAMS} \
	  --num_epochs=12 \
	  --beam_size=1 \
	  --report_every=100 \
	  --checkpoint_every=1000 \
	  --logtostderr
}

function evaluate_pretrained_parser {
	for SET in training tuning test; do
		${BINDIR}/parser_eval \
		--task_context=${TMP_DIR}/brain_parser/greedy/${LP_PARAMS}/context \
		--hidden_layer_sizes=${PARSER_HIDDEN_LAYER_SIZES} \
		--beam_size=1 \
		--batch_size=${BATCH_SIZE} \
		--input=tagged-$SET-corpus \
		--output=parsed-$SET-corpus \
		--arg_prefix=brain_parser \
		--graph_builder=greedy \
		--model_path=${TMP_DIR}/brain_parser/greedy/${LP_PARAMS}/model
	done
}

GP_PARAMS=${PARSER_HIDDEN_LAYER_PARAMS}-0.02-100-0.9-0
function train_parser {
	${BINDIR}/parser_trainer \
	  --arg_prefix=brain_parser \
	  --batch_size=${BATCH_SIZE} \
	  --compute_lexicon \
	  --decay_steps=100 \
	  --graph_builder=structured \
	  --hidden_layer_sizes=${PARSER_HIDDEN_LAYER_SIZES} \
	  --learning_rate=0.02 \
	  --momentum=0.9 \
	  --beam_size=${BEAM_SIZE} \
	  --output_path=${TMP_DIR} \
	  --task_context=${TMP_DIR}/brain_parser/greedy/${LP_PARAMS}/context \
	  --seed=0 \
	  --training_corpus=projectivized-training-corpus \
	  --tuning_corpus=tagged-tuning-corpus \
	  --params=${GP_PARAMS} \
	  --pretrained_params=${TMP_DIR}/brain_parser/greedy/${LP_PARAMS}/model \
	  --pretrained_params_names=embedding_matrix_0,embedding_matrix_1,embedding_matrix_2,bias_0,weights_0,bias_1,weights_1 \
	  --num_epochs=20 \
	  --report_every=25 \
	  --checkpoint_every=200 \
	  --logtostderr
}

function evaluate_parser {
	for SET in training tuning test; do
		${BINDIR}/parser_eval \
		--task_context=${TMP_DIR}/brain_parser/structured/${GP_PARAMS}/context \
		--hidden_layer_sizes=${PARSER_HIDDEN_LAYER_SIZES} \
		--beam_size=${BEAM_SIZE} \
		--batch_size=${BATCH_SIZE} \
		--input=tagged-$SET-corpus \
		--output=beam-parsed-$SET-corpus \
		--arg_prefix=brain_parser \
		--graph_builder=structured \
		--model_path=${TMP_DIR}/brain_parser/structured/${GP_PARAMS}/model
	done
}

function copy_model {
	# needs : category-map  label-map	lcword-map  prefix-table  suffix-table	tag-map  tag-to-category  word-map
	cp -rf ${TMP_DIR}/brain_parser/structured/${GP_PARAMS}/model ${MODEL_DIR}/parser-params
	cp -rf ${TMP_DIR}/*-map ${MODEL_DIR}/
	cp -rf ${TMP_DIR}/*-table ${MODEL_DIR}/
	cp -rf ${TMP_DIR}/tag-to-category ${MODEL_DIR}/
}

convert_corpus ${CORPUS_DIR}
pretrain_parser
evaluate_pretrained_parser
train_parser
evaluate_parser
copy_model

close_fd

# end main
# -----------------------------------------------------------------------------
