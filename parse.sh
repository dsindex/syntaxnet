#!/bin/bash

CDIR=$(readlink -f $(dirname $(readlink -f ${BASH_SOURCE[0]})))
PDIR=$(readlink -f $(dirname $(readlink -f ${BASH_SOURCE[0]}))/..)

SYNTAXNET_HOME=${PDIR}
BINDIR=${SYNTAXNET_HOME}/bazel-bin/syntaxnet

PARSER_EVAL=${BINDIR}/parser_eval
CONLL2TREE=${BINDIR}/conll2tree

MODEL_DIR=${CDIR}/English
CONTEXT=${MODEL_DIR}/context.pbtxt

cd ${PDIR}

${PARSER_EVAL} \
  --input=stdin-untoken \
  --output=stdin-untoken \
  --hidden_layer_sizes=128,128 \
  --arg_prefix=brain_tokenizer \
  --graph_builder=greedy \
  --task_context=${CONTEXT} \
  --resource_dir=${MODEL_DIR} \
  --model_path=${MODEL_DIR}/tokenizer-params \
  --batch_size=32 \
  --alsologtostderr \
  --slim_model \
  | \
${PARSER_EVAL} \
  --input=stdin \
  --output=stdout-conll \
  --hidden_layer_sizes=64 \
  --arg_prefix=brain_morpher \
  --graph_builder=structured \
  --task_context=${CONTEXT} \
  --resource_dir=${MODEL_DIR} \
  --model_path=${MODEL_DIR}/morpher-params \
  --slim_model \
  --batch_size=1024 \
  --alsologtostderr \
  | \
${PARSER_EVAL} \
  --input=stdin-conll \
  --output=stdout-conll \
  --hidden_layer_sizes=64 \
  --arg_prefix=brain_tagger \
  --graph_builder=structured \
  --task_context=${CONTEXT} \
  --resource_dir=${MODEL_DIR} \
  --model_path=${MODEL_DIR}/tagger-params \
  --slim_model \
  --batch_size=1024 \
  --alsologtostderr \
  | \
${PARSER_EVAL} \
  --input=stdin-conll \
  --output=stdout-conll \
  --hidden_layer_sizes=512,512 \
  --arg_prefix=brain_parser \
  --graph_builder=structured \
  --task_context=${CONTEXT} \
  --resource_dir=${MODEL_DIR} \
  --model_path=${MODEL_DIR}/parser-params \
  --slim_model \
  --batch_size=1024 \
  --alsologtostderr \
  | \
${CONLL2TREE} \
  --task_context=${MODEL_DIR}/context.pbtxt \
  --alsologtostderr
