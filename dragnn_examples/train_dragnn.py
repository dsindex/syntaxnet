#!/usr/bin/env python
#-*- coding: utf8 -*-
import sys
import os
import os.path
import random
import time
import tensorflow as tf

import model_dragnn as model

# for train
from syntaxnet.ops import gen_parser_ops
from syntaxnet import load_parser_ops  # This loads the actual op definitions
from syntaxnet.util import check
from dragnn.python import load_dragnn_cc_impl
from dragnn.python.sentence_io import ConllSentenceReader
from dragnn.python import evaluation
from dragnn.python import lexicon
from dragnn.python import trainer_lib

from tensorflow.python.framework import errors
from tensorflow.python.platform import gfile
from tensorflow.python.platform import tf_logging as logging

flags = tf.app.flags
FLAGS = flags.FLAGS
flags.DEFINE_string('tf_master', '',
                    'TensorFlow execution engine to connect to.')
flags.DEFINE_string('dragnn_spec', '', 
                    'Path to the spec defining the model.')
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
flags.DEFINE_integer('n_steps', 100000,
                     'Number of training steps')
flags.DEFINE_bool('compute_lexicon', False, '')
flags.DEFINE_bool('projectivize_training_set', True, '')
flags.DEFINE_integer('batch_size', 64,
                     'Batch size.')
flags.DEFINE_integer('report_every', 200,
                     'Report cost and training accuracy every this many steps.')
flags.DEFINE_integer('job_id', 0, 
                     'The trainer will clear checkpoints if the '
                     'saved job id is less than the id this flag. If you want '
                     'training to start over, increment this id.')

def train(graph, builder, trainers, annotator, summary_writer, do_restore, stats) :
    training_corpus_path = gfile.Glob(FLAGS.training_corpus_path)[0]
    tune_corpus_path = gfile.Glob(FLAGS.tune_corpus_path)[0]

    # Read in serialized protos from training data.
    training_set = ConllSentenceReader(
        training_corpus_path,
        projectivize=FLAGS.projectivize_training_set,
        morph_to_pos=True).corpus()
    tune_set = ConllSentenceReader(
        tune_corpus_path, projectivize=False, morph_to_pos=True).corpus()

    # Ready to train!
    logging.info('Training on %d sentences.', len(training_set))
    logging.info('Tuning on %d sentences.', len(tune_set))

    # Set training steps
    pretrain_steps = [10000, 0]
    tagger_steps = FLAGS.n_steps
    train_steps = [tagger_steps, 8 * tagger_steps]

    with tf.Session(target=FLAGS.tf_master, graph=graph) as sess:
        # Make sure to re-initialize all underlying state.
        sess.run(tf.global_variables_initializer())

        if do_restore :
            tf.logging.info('Restoring from checkpoint...')
            builder.saver.restore(sess, FLAGS.checkpoint_filename)

            prev_tagger_steps = stats[1]
            prev_parser_steps = stats[2]
            tf.logging.info('adjusting schedule from steps: %d, %d',
                            prev_tagger_steps, prev_parser_steps)
            pretrain_steps[0] = max(pretrain_steps[0] - prev_tagger_steps, 0)
            tf.logging.info('new pretrain steps: %d', pretrain_steps[0])

        trainer_lib.run_training(
              sess, trainers, annotator, evaluation.parser_summaries, pretrain_steps,
              train_steps, training_set, tune_set, tune_set, FLAGS.batch_size,
              summary_writer, FLAGS.report_every, builder.saver,
              FLAGS.checkpoint_filename, stats)

def main(unused_argv) :
    if len(sys.argv) == 1 :
        flags._global_parser.print_help()
        sys.exit(0)

    logging.set_verbosity(logging.INFO)
    check.IsTrue(FLAGS.training_corpus_path)
    check.IsTrue(FLAGS.tune_corpus_path)
    check.IsTrue(FLAGS.resource_path)
    check.IsTrue(FLAGS.checkpoint_filename)

    if not gfile.IsDirectory(FLAGS.resource_path):
        gfile.MakeDirs(FLAGS.resource_path)

    training_corpus_path = gfile.Glob(FLAGS.training_corpus_path)[0]
    tune_corpus_path = gfile.Glob(FLAGS.tune_corpus_path)[0]

    # SummaryWriter for TensorBoard
    tf.logging.info('TensorBoard directory: "%s"', FLAGS.tensorboard_dir)
    tf.logging.info('Deleting prior data if exists...')

    stats_file = '%s.stats' % FLAGS.checkpoint_filename
    try :
        stats = gfile.GFile(stats_file, 'r').readlines()[0].split(',')
        stats = [int(x) for x in stats]
    except errors.OpError :
        stats = [-1, 0, 0]

    tf.logging.info('Read ckpt stats: %s', str(stats))
    do_restore = True
    if stats[0] < FLAGS.job_id :
        do_restore = False
        tf.logging.info('Deleting last job: %d', stats[0])
        try :
            gfile.DeleteRecursively(FLAGS.tensorboard_dir)
            gfile.Remove(FLAGS.checkpoint_filename)
        except errors.OpError as err :
            tf.logging.error('Unable to delete prior files: %s', err)
        stats = [FLAGS.job_id, 0, 0]

    tf.logging.info('Creating the directory again...')
    gfile.MakeDirs(FLAGS.tensorboard_dir)
    tf.logging.info('Created! Instatiating SummaryWriter...')
    summary_writer = trainer_lib.get_summary_writer(FLAGS.tensorboard_dir)
    tf.logging.info('Creating TensorFlow checkpoint dir...')
    gfile.MakeDirs(os.path.dirname(FLAGS.checkpoint_filename))

    # Constructs lexical resources for SyntaxNet in the given resource path, from
    # the training data.
    if FLAGS.compute_lexicon : 
        logging.info('Computing lexicon...')
        lexicon.build_lexicon(FLAGS.resource_path, training_corpus_path, morph_to_pos=True)

    # Load master spec
    master_spec = model.load_master_spec(FLAGS.dragnn_spec, FLAGS.resource_path)
    # Build graph
    graph, builder, trainers, annotator = model.build_train_graph(master_spec)
    # Train
    train(graph, builder, trainers, annotator, summary_writer, do_restore, stats)
    
if __name__ == '__main__':
    tf.app.run()

