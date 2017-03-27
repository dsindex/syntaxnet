#!/bin/bash
set -eux

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
CONTEXT=${CDIR}/testdata/context.pbtxt
TMP_DIR=${CDIR}/testdata/tmp/syntaxnet-output

mkdir -p $TMP_DIR
cat $CONTEXT | sed "s=OUTPATH=$TMP_DIR=" > $TMP_DIR/context

PARAMS=128-0.08-3600-0.9-0

"$BINDIR/parser_trainer" \
  --arg_prefix=brain_parser \
  --batch_size=32 \
  --compute_lexicon \
  --decay_steps=3600 \
  --graph_builder=greedy \
  --hidden_layer_sizes=128 \
  --learning_rate=0.08 \
  --momentum=0.9 \
  --output_path=$TMP_DIR \
  --task_context=$TMP_DIR/context \
  --training_corpus=training-corpus \
  --tuning_corpus=tuning-corpus \
  --params=$PARAMS \
  --num_epochs=12 \
  --report_every=100 \
  --checkpoint_every=1000 \
  --logtostderr

"$BINDIR/parser_eval" \
  --task_context=$TMP_DIR/brain_parser/greedy/$PARAMS/context \
  --hidden_layer_sizes=128 \
  --input=tuning-corpus \
  --output=stdout \
  --arg_prefix=brain_parser \
  --graph_builder=greedy \
  --model_path=$TMP_DIR/brain_parser/greedy/$PARAMS/model \
  --logtostderr \
  > $TMP_DIR/greedy-out

"$BINDIR/parser_eval" \
  --task_context=$TMP_DIR/context \
  --hidden_layer_sizes=128 \
  --beam_size=1 \
  --input=tuning-corpus \
  --output=stdout \
  --arg_prefix=brain_parser \
  --graph_builder=structured \
  --model_path=$TMP_DIR/brain_parser/greedy/$PARAMS/model \
  --logtostderr \
  > $TMP_DIR/struct-beam1-out

diff $TMP_DIR/greedy-out $TMP_DIR/struct-beam1-out

STRUCT_PARAMS=128-0.001-3600-0.9-0

"$BINDIR/parser_trainer" \
  --arg_prefix=brain_parser \
  --batch_size=8 \
  --compute_lexicon \
  --decay_steps=3600 \
  --graph_builder=structured \
  --hidden_layer_sizes=128 \
  --learning_rate=0.001 \
  --momentum=0.9 \
  --pretrained_params=$TMP_DIR/brain_parser/greedy/$PARAMS/model \
  --pretrained_params_names=embedding_matrix_0,embedding_matrix_1,embedding_matrix_2,bias_0,weights_0 \
  --output_path=$TMP_DIR \
  --task_context=$TMP_DIR/context \
  --training_corpus=training-corpus \
  --tuning_corpus=tuning-corpus \
  --params=$STRUCT_PARAMS \
  --num_epochs=20 \
  --report_every=25 \
  --checkpoint_every=200 \
  --logtostderr

"$BINDIR/parser_eval" \
  --task_context=$TMP_DIR/context \
  --hidden_layer_sizes=128 \
  --beam_size=8 \
  --input=tuning-corpus \
  --output=stdout \
  --arg_prefix=brain_parser \
  --graph_builder=structured \
  --model_path=$TMP_DIR/brain_parser/structured/$STRUCT_PARAMS/model \
  --logtostderr \
  > $TMP_DIR/struct-beam8-out

echo "PASS"
