#!/bin/bash

# To run on a conll formatted file, add the --conll command line argument.

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

POS_HIDDEN_LAYER_SIZES=64

PARSER_HIDDEN_LAYER_SIZES=512,512
BATCH_SIZE=256
BEAM_SIZE=16

[[ "$1" == "--conll" ]] && INPUT_FORMAT=stdin-conll || INPUT_FORMAT=stdin

${PARSER_EVAL} \
  --input=${INPUT_FORMAT} \
  --output=stdout-conll \
  --hidden_layer_sizes=${POS_HIDDEN_LAYER_SIZES} \
  --arg_prefix=brain_pos \
  --graph_builder=greedy \
  --task_context=${MODEL_DIR}/context.pbtxt \
  --resource_dir=${MODEL_DIR} \
  --model_path=${MODEL_DIR}/tagger-params/model \
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
  --task_context=${MODEL_DIR}/context.pbtxt \
  --resource_dir=${MODEL_DIR} \
  --model_path=${MODEL_DIR}/parser-params/model \
  --slim_model \
  --beam_size=${BEAM_SIZE} \
  --batch_size=${BATCH_SIZE} \
  --alsologtostderr \
  | \
${CONLL2TREE} \
  --task_context=${MODEL_DIR}/context.pbtxt \
  --alsologtostderr
