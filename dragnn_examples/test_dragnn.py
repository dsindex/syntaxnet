import os
import os.path
import random
import time
import tensorflow as tf

#from IPython.display import HTML
from tensorflow.python.platform import gfile
from tensorflow.python.platform import tf_logging as logging

from google.protobuf import text_format

from syntaxnet.ops import gen_parser_ops
from syntaxnet import load_parser_ops  # This loads the actual op definitions
from syntaxnet import task_spec_pb2
from syntaxnet import sentence_pb2

from dragnn.protos import spec_pb2
from dragnn.python.sentence_io import ConllSentenceReader

from dragnn.python import evaluation
from dragnn.python import graph_builder
from dragnn.python import lexicon
from dragnn.python import load_dragnn_cc_impl
from dragnn.python import render_parse_tree_graphviz
from dragnn.python import render_spec_with_graphviz
from dragnn.python import spec_builder
from dragnn.python import trainer_lib
from dragnn.python import visualization


flags = tf.app.flags
FLAGS = flags.FLAGS
flags.DEFINE_string('mode', 'train',
                    'Option for train or test')
flags.DEFINE_string('resource_path', '', 'Path to constructed resources.')
flags.DEFINE_string('training_corpus_path', '', 'Path to training data.')
flags.DEFINE_string('tune_corpus_path', '', 'Path to tuning set data.')
flags.DEFINE_string('checkpoint_filename', '',
                    'Filename to save the best checkpoint to.')
flags.DEFINE_string('tensorboard_dir', '',
                    'Directory for TensorBoard logs output.')
flags.DEFINE_integer('n_steps', 20, 'Number of training steps')
flags.DEFINE_integer('batch_size', 64, 'Batch size.')

# global
DATA_DIR = FLAGS.resource_path
TRAINING_CORPUS_PATH = FLAGS.training_corpus_path
DEV_CORPUS_PATH = FLAGS.tune_corpus_path
CHECKPOINT_FILENAME = FLAGS.checkpoint_filename
TENSORBOARD_DIR = FLAGS.tensorboard_dir
N_STEPS = FLAGS.n_steps
BATCH_SIZE = FLAGS.batch_size


def build_master_spec() :
  '''
  # Left-to-right, character-based LSTM.
  char2word = spec_builder.ComponentSpecBuilder('char_lstm')
  char2word.set_network_unit(
      name='wrapped_units.LayerNormBasicLSTMNetwork',
      hidden_layer_sizes='256')
  char2word.set_transition_system(name='char-shift-only', left_to_right='true')
  char2word.add_fixed_feature(name='chars', fml='char-input.text-char',
                              embedding_dim=16)
  char2word.fill_from_resources(DATA_DIR)

  # Lookahead LSTM reads right-to-left to represent the rightmost context of the
  # words. It gets word embeddings from the char model.
  lookahead = spec_builder.ComponentSpecBuilder('lookahead')
  lookahead.set_network_unit(
      name='wrapped_units.LayerNormBasicLSTMNetwork',
      hidden_layer_sizes='256')
  lookahead.set_transition_system(name='shift-only', left_to_right='false')
  lookahead.add_link(source=char2word, fml='input.last-char-focus',
                     embedding_dim=64)
  lookahead.fill_from_resources(DATA_DIR)
  '''

  # Construct the 'lookahead' ComponentSpec. This is a simple right-to-left RNN
  # sequence model, which encodes the context to the right of each token. It has
  # no loss except for the downstream components.
  lookahead = spec_builder.ComponentSpecBuilder('lookahead')
  lookahead.set_network_unit(
      name='FeedForwardNetwork', hidden_layer_sizes='256')
  lookahead.set_transition_system(name='shift-only', left_to_right='true')
  lookahead.add_fixed_feature(name='words', fml='input.word', embedding_dim=64)
  lookahead.add_rnn_link(embedding_dim=-1)
  lookahead.fill_from_resources(DATA_DIR)

  # Construct the tagger. This is a simple left-to-right LSTM sequence tagger.
  tagger = spec_builder.ComponentSpecBuilder('tagger')
  tagger.set_network_unit(
      name='wrapped_units.LayerNormBasicLSTMNetwork',
      hidden_layer_sizes='256')
  tagger.set_transition_system(name='tagger')
  tagger.add_token_link(source=lookahead, fml='input.focus', embedding_dim=64)
  tagger.fill_from_resources(DATA_DIR)

  # Construct the parser.
  parser = spec_builder.ComponentSpecBuilder('parser')
  parser.set_network_unit(name='FeedForwardNetwork', hidden_layer_sizes='256',
                          layer_norm_hidden='true')
  parser.set_transition_system(name='arc-standard')
  parser.add_token_link(source=lookahead, fml='input.focus', embedding_dim=64)
  parser.add_token_link(
      source=tagger, fml='input.focus stack.focus stack(1).focus',
      embedding_dim=64)

  # Add discrete features of the predicted parse tree so far, like in Parsey
  # McParseface.
  parser.add_fixed_feature(name='labels', embedding_dim=16,
                           fml=' '.join([
                               'stack.child(1).label',
                               'stack.child(1).sibling(-1).label',
                               'stack.child(-1).label',
                               'stack.child(-1).sibling(1).label',
                               'stack(1).child(1).label',
                               'stack(1).child(1).sibling(-1).label',
                               'stack(1).child(-1).label',
                               'stack(1).child(-1).sibling(1).label',
                               'stack.child(2).label',
                               'stack.child(-2).label',
                               'stack(1).child(2).label',
                               'stack(1).child(-2).label']))

  # Recurrent connection for the arc-standard parser. For both tokens on the
  # stack, we connect to the last time step to either SHIFT or REDUCE that
  # token. This allows the parser to build up compositional representations of
  # phrases.
  parser.add_link(
      source=parser,  # recurrent connection
      name='rnn-stack',  # unique identifier
      fml='stack.focus stack(1).focus',  # look for both stack tokens
      source_translator='shift-reduce-step',  # maps token indices -> step
      embedding_dim=64)  # project down to 64 dims

  parser.fill_from_resources(DATA_DIR)

  master_spec = spec_pb2.MasterSpec()
  '''
  master_spec.component.extend(
      [char2word.spec, lookahead.spec, tagger.spec, parser.spec])
  '''
  master_spec.component.extend(
      [lookahead.spec, tagger.spec, parser.spec])
  #HTML(render_spec_with_graphviz.master_spec_graph(master_spec))
  
  return master_spec

def build_graph(master_spec) :

    # Build the TensorFlow graph based on the DRAGNN network spec.
    graph = tf.Graph()
    with graph.as_default():
        hyperparam_config = spec_pb2.GridPoint(
            learning_method='adam',
            learning_rate=0.0005, 
            adam_beta1=0.9, adam_beta2=0.9, adam_eps=0.001,
            dropout_rate=0.8, gradient_clip_norm=1,
            use_moving_average=True,
            seed=1)
        builder = graph_builder.MasterBuilder(master_spec, hyperparam_config)
        if FLAGS.mode == 'train' :
            '''
            target = spec_pb2.TrainTarget(
                name='all',
                unroll_using_oracle=[False, False, True, True], # train tagger & parser on gold unrolling, skip char_lstm/lookahead
                component_weights=[0, 0, 0.5, 0.5]) # tagger and parser losses have equal weights
            '''
            target = spec_pb2.TrainTarget(
                name='all',
                unroll_using_oracle=[False, True, True], # train tagger & parser on gold unrolling, skip lookahead
                component_weights=[0, 0.5, 0.5]) # tagger and parser losses have equal weights
            trainer = builder.add_training_from_config(target)
            annotator = builder.add_annotation(enable_tracing=True)
            builder.add_saver()
            return graph, builder, trainer, annotator
        else :
            annotator = builder.add_annotation(enable_tracing=True)
            builder.add_saver()
            return graph, builder, annotator

def train(graph, builder, trainer, annotator) :
    # Train on data for N_STEPS steps and evaluate.
    with tf.Session(graph=graph) as sess:
        sess.run(tf.global_variables_initializer())
        training_corpus = ConllSentenceReader(
            TRAINING_CORPUS_PATH, projectivize=True).corpus()
        dev_corpus = ConllSentenceReader(DEV_CORPUS_PATH).corpus()[:200]
        for step in xrange(N_STEPS):
            trainer_lib.run_training_step(sess, trainer, training_corpus, batch_size=BATCH_SIZE)
            tf.logging.warning('Step %d/%d', step + 1, N_STEPS)
        parsed_dev_corpus = trainer_lib.annotate_dataset(sess, annotator, dev_corpus)
        pos, uas, las = evaluation.calculate_parse_metrics(dev_corpus, parsed_dev_corpus)
        tf.logging.warning('POS %.2f UAS %.2f LAS %.2f', pos, uas, las)
        builder.saver.save(sess, CHECKPOINT_FILENAME)

def test(graph, builder, annotator, text) :
    # Visualize the output of our mini-trained model on a test sentence.
    tokens = [sentence_pb2.Token(word=word, start=-1, end=-1) for word in text.split()]
    sentence = sentence_pb2.Sentence()
    sentence.token.extend(tokens)

    with tf.Session(graph=graph) as sess:
        # Restore the model we just trained.
        builder.saver.restore(sess, CHECKPOINT_FILENAME)
        annotations, traces = sess.run([annotator['annotations'], annotator['traces']],
                          feed_dict={annotator['input_batch']: [sentence.SerializeToString()]})

    #HTML(visualization.trace_html(traces[0]))

    parsed_sentence = sentence_pb2.Sentence.FromString(annotations[0])
    #HTML(render_parse_tree_graphviz.parse_tree_graph(parsed_sentence))
    return parsed_sentence

def main(unused_argv) :

    logging.set_verbosity(logging.WARN)

    if FLAGS.mode == 'train' :
        # Some of the IO functions fail miserably if data is missing.
        assert os.path.isfile(TRAINING_CORPUS_PATH), 'Could not find training corpus'
        # Constructs lexical resources for SyntaxNet in the given resource path, from
        # the training data.
        lexicon.build_lexicon(DATA_DIR, TRAINING_CORPUS_PATH)
        master_spec = build_master_spec()
        graph, builder, trainer, annotator = build_graph(master_spec)
        train(graph, builder, trainer, annotator)
    else :
        master_spec = build_master_spec()
        graph, builder, annotator = build_graph(master_spec)
        text = 'this is an example for dragnn'
        parsed_sentence = test(graph, builder, annotator, text)
        print parsed_sentence
    
if __name__ == '__main__':
    tf.app.run()

