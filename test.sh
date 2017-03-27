#!/bin/bash

# To run on a conll formatted file, add the --conll command line argument.

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

CDIR=$(readlink -f $(dirname $(readlink -f ${BASH_SOURCE[0]})))
PDIR=$(readlink -f $(dirname $(readlink -f ${BASH_SOURCE[0]}))/..)
cd ${PDIR}

SYNTAXNET_HOME=${PDIR}
BINDIR=${SYNTAXNET_HOME}/bazel-bin/syntaxnet

PARSER_EVAL=${BINDIR}/parser_eval
CONLL2TREE=${BINDIR}/conll2tree

MODEL_DIR=${CDIR}/models

CONTEXT=${MODEL_DIR}/context.pbtxt
cat ${CONTEXT}.template | sed "s=OUTPATH=${MODEL_DIR}=" > ${MODEL_DIR}/context
CONTEXT=${MODEL_DIR}/context
TAGGER_MODEL_PATH=${MODEL_DIR}/tagger-params/model
PARSER_MODEL_PATH=${MODEL_DIR}/parser-params/model
XTAGGER_MODEL_PATH=${MODEL_DIR}/tagger-params
XPARSER_MODEL_PATH=${MODEL_DIR}/parser-params
TAGGER_MODEL_PATH=${TAGGER_MODEL_PATH}
PARSER_MODEL_PATH=${PARSER_MODEL_PATH}

TAGGER_HIDDEN_LAYER_SIZES=64

PARSER_HIDDEN_LAYER_SIZES=512,512
BATCH_SIZE=256
BEAM_SIZE=16

[[ "$1" == "--conll" ]] && INPUT_FORMAT=stdin-conll || INPUT_FORMAT=stdin

${PARSER_EVAL} \
  --input=${INPUT_FORMAT} \
  --output=stdout-conll \
  --hidden_layer_sizes=${TAGGER_HIDDEN_LAYER_SIZES} \
  --arg_prefix=brain_tagger \
  --graph_builder=greedy \
  --task_context=${CONTEXT} \
  --resource_dir=${MODEL_DIR} \
  --model_path=${TAGGER_MODEL_PATH} \
  --slim_model \
  --batch_size=${BATCH_SIZE} \
  --alsologtostderr \
   | \
${PARSER_EVAL} \
  --input=stdin-conll \
  --output=stdout-conll \
  --hidden_layer_sizes=${PARSER_HIDDEN_LAYER_SIZES} \
  --arg_prefix=brain_parser \
  --graph_builder=structured \
  --task_context=${CONTEXT} \
  --resource_dir=${MODEL_DIR} \
  --model_path=${PARSER_MODEL_PATH} \
  --slim_model \
  --beam_size=${BEAM_SIZE} \
  --batch_size=${BATCH_SIZE} \
  --alsologtostderr \
  | \
${CONLL2TREE} \
  --task_context=${MODEL_DIR}/context.pbtxt \
  --alsologtostderr
