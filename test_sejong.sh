#!/bin/bash

# To run on a conll formatted file, add the --conll command line argument.

CDIR=$(readlink -f $(dirname $(readlink -f ${BASH_SOURCE[0]})))
PDIR=$(readlink -f $(dirname $(readlink -f ${BASH_SOURCE[0]}))/..)
cd ${PDIR}

SYNTAXNET_HOME=${PDIR}
BINDIR=${SYNTAXNET_HOME}/bazel-bin/syntaxnet

PARSER_EVAL=${BINDIR}/parser_eval
CONLL2TREE=${BINDIR}/conll2tree

MODEL_DIR=${CDIR}/models_sejong

HIDDEN_LAYER_SIZES=512,512
BATCH_SIZE=256
BEAM_SIZE=16


[[ "$1" == "--conll" ]] && INPUT_FORMAT=stdin-conll || INPUT_FORMAT=stdin

${PARSER_EVAL} \
  --input=stdin-conll \
  --output=stdout-conll \
  --batch_size=${BATCH_SIZE} \
  --hidden_layer_sizes=${HIDDEN_LAYER_SIZES} \
  --beam_size=${BEAM_SIZE} \
  --arg_prefix=brain_parser \
  --graph_builder=structured \
  --task_context=${MODEL_DIR}/context.pbtxt \
  --resource_dir=${MODEL_DIR} \
  --model_path=${MODEL_DIR}/parser-params \
  | \
${CONLL2TREE} \
  --task_context=${MODEL_DIR}/context.pbtxt \
  --alsologtostderr
