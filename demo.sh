#!/bin/bash

# A script that runs a tokenizer, a part-of-speech tagger and a dependency
# parser on an English text file, with one sentence per line.
#
# Example usage:
#  echo "Parsey McParseface is my favorite parser!" | syntaxnet/demo.sh

# To run on a conll formatted file, add the --conll command line argument.
#

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
MODEL_DIR=${SYNTAXNET_HOME}/syntaxnet/models/parsey_mcparseface

[[ "$1" == "--conll" ]] && INPUT_FORMAT=stdin-conll || INPUT_FORMAT=stdin

${PARSER_EVAL} \
  --input=${INPUT_FORMAT} \
  --output=stdout-conll \
  --hidden_layer_sizes=64 \
  --arg_prefix=brain_tagger \
  --graph_builder=structured \
  --task_context=${MODEL_DIR}/context.pbtxt \
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
  --task_context=${MODEL_DIR}/context.pbtxt \
  --model_path=${MODEL_DIR}/parser-params \
  --slim_model \
  --batch_size=1024 \
  --alsologtostderr \
  | \
${CONLL2TREE} \
  --task_context=${MODEL_DIR}/context.pbtxt \
  --alsologtostderr
