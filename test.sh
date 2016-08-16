#!/bin/bash

# To run on a conll formatted file, add the --conll command line argument.

CDIR=$(readlink -f $(dirname $(readlink -f ${BASH_SOURCE[0]})))
PDIR=$(readlink -f $(dirname $(readlink -f ${BASH_SOURCE[0]}))/..)
cd ${PDIR}

SYNTAXNET_HOME=${PDIR}
BINDIR=${SYNTAXNET_HOME}/bazel-bin/syntaxnet

PARSER_EVAL=${BINDIR}/parser_eval
CONLL2TREE=${BINDIR}/conll2tree

MODEL_DIR=${CDIR}/models

[[ "$1" == "--conll" ]] && INPUT_FORMAT=stdin-conll || INPUT_FORMAT=stdin

${PARSER_EVAL} \
  --input=${INPUT_FORMAT} \
  --output=stdout-conll \
  --hidden_layer_sizes=128 \
  --arg_prefix=brain_pos \
  --graph_builder=greedy \
  --task_context=${MODEL_DIR}/context.pbtxt \
  --resource_dir=${MODEL_DIR} \
  --model_path=${MODEL_DIR}/tagger-params \
  --slim_model \
  --batch_size=1024 \
  --alsologtostderr \
   | \
${PARSER_EVAL} \
  --input=stdin-conll \
  --output=stdout-conll \
  --hidden_layer_sizes=200,200 \
  --arg_prefix=brain_parser \
  --graph_builder=structured \
  --task_context=${MODEL_DIR}/context.pbtxt \
  --resource_dir=${MODEL_DIR} \
  --model_path=${MODEL_DIR}/parser-params \
  --slim_model \
  --batch_size=1024 \
  --alsologtostderr \
  | \
${CONLL2TREE} \
  --task_context=${MODEL_DIR}/context.pbtxt \
  --alsologtostderr
