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
flags.DEFINE_string('resource_path', '',
                    'Path to constructed resources.')
flags.DEFINE_string('training_corpus_path', '',
                    'Path to training data.')
flags.DEFINE_string('tune_corpus_path', '',
                    'Path to tuning set data.')
flags.DEFINE_string('checkpoint_filename', '',
                    'Filename to save the best checkpoint to.')
flags.DEFINE_string('tensorboard_dir', '',
                    'Directory for TensorBoard logs output.')
flags.DEFINE_integer('n_steps', 1000,
                     'Number of training steps')
flags.DEFINE_integer('batch_size', 64,
                     'Batch size.')
flags.DEFINE_integer('report_every', 200,
                     'Report cost and training accuracy every this many steps.')

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
    char2word.fill_from_resources(FLAGS.resource_path)

    # Lookahead LSTM reads right-to-left to represent the rightmost context of the
    # words. It gets word embeddings from the char model.
    lookahead = spec_builder.ComponentSpecBuilder('lookahead')
    lookahead.set_network_unit(
        name='wrapped_units.LayerNormBasicLSTMNetwork',
        hidden_layer_sizes='256')
    lookahead.set_transition_system(name='shift-only', left_to_right='false')
    lookahead.add_link(source=char2word, fml='input.last-char-focus',
                       embedding_dim=64)
    lookahead.fill_from_resources(FLAGS.resource_path)
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
    lookahead.fill_from_resources(FLAGS.resource_path)

    # Construct the tagger. This is a simple left-to-right LSTM sequence tagger.
    tagger = spec_builder.ComponentSpecBuilder('tagger')
    tagger.set_network_unit(
        name='wrapped_units.LayerNormBasicLSTMNetwork',
        hidden_layer_sizes='256')
    tagger.set_transition_system(name='tagger')
    tagger.add_token_link(source=lookahead, fml='input.focus', embedding_dim=64)
    tagger.fill_from_resources(FLAGS.resource_path)

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

    parser.fill_from_resources(FLAGS.resource_path)

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
    # Train on data for FLAGS.n_steps steps and evaluate.
    with tf.Session(graph=graph) as sess:
        sess.run(tf.global_variables_initializer())
        training_corpus = ConllSentenceReader(
            FLAGS.training_corpus_path, projectivize=True).corpus()
        dev_corpus = ConllSentenceReader(FLAGS.tune_corpus_path).corpus()[:2002]
        for step in xrange(FLAGS.n_steps):
            trainer_lib.run_training_step(sess, trainer, training_corpus, batch_size=FLAGS.batch_size)
            tf.logging.warning('Step %d/%d', step + 1, FLAGS.n_steps)
            if step % FLAGS.report_every == 0 :
                parsed_dev_corpus = trainer_lib.annotate_dataset(sess, annotator, dev_corpus)
                pos, uas, las = evaluation.calculate_parse_metrics(dev_corpus, parsed_dev_corpus)
                tf.logging.warning('POS %.2f UAS %.2f LAS %.2f', pos, uas, las)
                builder.saver.save(sess, FLAGS.checkpoint_filename)

def test(graph, builder, annotator, text) :
    # Visualize the output of our mini-trained model on a test sentence.
    tokens = [sentence_pb2.Token(word=word, start=-1, end=-1) for word in text.split()]
    sentence = sentence_pb2.Sentence()
    sentence.token.extend(tokens)

    with tf.Session(graph=graph) as sess:
        # Restore the model we just trained.
        builder.saver.restore(sess, FLAGS.checkpoint_filename)
        annotations, traces = sess.run([annotator['annotations'], annotator['traces']],
                          feed_dict={annotator['input_batch']: [sentence.SerializeToString()]})

    #HTML(visualization.trace_html(traces[0]))

    parsed_sentence = sentence_pb2.Sentence.FromString(annotations[0])
    #HTML(render_parse_tree_graphviz.parse_tree_graph(parsed_sentence))
    return parsed_sentence

def main(unused_argv) :
    import sys
    if len(sys.argv) == 1 :
        flags._global_parser.print_help()
        sys.exit(0)

    logging.set_verbosity(logging.WARN)

    if FLAGS.mode == 'train' :
        # Some of the IO functions fail miserably if data is missing.
        assert os.path.isfile(FLAGS.training_corpus_path), 'Could not find training corpus'
        # Constructs lexical resources for SyntaxNet in the given resource path, from
        # the training data.
        lexicon.build_lexicon(FLAGS.resource_path, FLAGS.training_corpus_path)
        # build master spec and graph
        master_spec = build_master_spec()
        graph, builder, trainer, annotator = build_graph(master_spec)
        train(graph, builder, trainer, annotator)
    elif FLAGS.mode == 'test' :
        # prepare korean morphological analyzer for segmentation
        import konlpy.tag import Komoran
        komoran = Komoran()
        # build master spec and graph
        master_spec = build_master_spec()
        graph, builder, annotator = build_graph(master_spec)
        startTime = time.time()
        while 1 :
            try : line = sys.stdin.readline()
            except KeyboardInterrupt : break
            if not line : break
            line = line.strip()
            if not line : continue
            analyzed = komoran.pos(line)
            tokenized = []
            seq = 1
            for morph, tag in analyzed :
                '''
                tp = [seq, morph, morph, tag, tag, '_', 0, '_', '_', '_']
                print '\t'.join([str(e) for e in tp])
                '''
                tokenized.append(morph)
                seq += 1
            # ex) line = '제주 로 가다 는 비행기 가 심하다 는 비바람 에 회항 하 었 다 .'
            line = ' '.join(tokenized)
            sentence = test(graph, builder, annotator, line)
            f = sys.stdout
            f.write('#' + line + '\n')
            for i, token in enumerate(sentence.token) :
                head = token.head + 1
                f.write('%s\t%s\t%s\t%s\t%s\t_\t%d\t%s\t_\t_\n'%(
                        i + 1,
                        token.word.encode('utf-8'),
                        token.word.encode('utf-8'),
                        token.tag.encode('utf-8'),
                        token.tag.encode('utf-8'),
                        head,
                        token.label.encode('utf-8')))
            f.write('\n\n')
        durationTime = time.time() - startTime
        sys.stderr.write("duration time = %f\n" % durationTime)
    else :
        flags._global_parser.print_help()
    
if __name__ == '__main__':
    tf.app.run()

