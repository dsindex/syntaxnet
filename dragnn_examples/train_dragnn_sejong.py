#!/usr/bin/env python
#-*- coding: utf8 -*-
import os
import os.path
import random
import time
import tensorflow as tf

#from IPython.display import HTML
from tensorflow.python.platform import tf_logging as logging

import model_dragnn_sejong as model

# for train
from dragnn.python.sentence_io import ConllSentenceReader
from dragnn.python import evaluation
from dragnn.python import lexicon
from dragnn.python import trainer_lib

flags = tf.app.flags
FLAGS = flags.FLAGS
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

def main(unused_argv) :
    import sys
    if len(sys.argv) == 1 :
        flags._global_parser.print_help()
        sys.exit(0)

    logging.set_verbosity(logging.WARN)

    FLAGS.model = 'train'
    # Some of the IO functions fail miserably if data is missing.
    assert os.path.isfile(FLAGS.training_corpus_path), 'Could not find training corpus'
    # Constructs lexical resources for SyntaxNet in the given resource path, from
    # the training data.
    lexicon.build_lexicon(FLAGS.resource_path, FLAGS.training_corpus_path)
    # build master spec and graph
    master_spec = model.build_master_spec(FLAGS)
    graph, builder, trainer, annotator = model.build_graph(FLAGS, master_spec)
    train(graph, builder, trainer, annotator)
    
if __name__ == '__main__':
    tf.app.run()

