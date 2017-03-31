#!/usr/bin/env python
#-*- coding: utf8 -*-
import sys
import os
import os.path
import random
import time
import tensorflow as tf

#from IPython.display import HTML
from tensorflow.python.platform import tf_logging as logging

import model_dragnn as model

# for inference
from syntaxnet import load_parser_ops  # This loads the actual op definitions
from dragnn.python import load_dragnn_cc_impl
from dragnn.python import render_parse_tree_graphviz
from dragnn.python import visualization
from syntaxnet import sentence_pb2

flags = tf.app.flags
FLAGS = flags.FLAGS
flags.DEFINE_string('resource_path', '',
                    'Path to constructed resources.')
flags.DEFINE_string('checkpoint_filename', '',
                    'Filename to save the best checkpoint to.')

def inference(graph, builder, annotator, text) :
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
    if len(sys.argv) == 1 :
        flags._global_parser.print_help()
        sys.exit(0)

    logging.set_verbosity(logging.WARN)

    # build master spec and graph
    master_spec = model.build_master_spec(FLAGS)
    graph, builder, annotator = model.build_graph(master_spec, mode='inference')
    startTime = time.time()
    while 1 :
        try : line = sys.stdin.readline()
        except KeyboardInterrupt : break
        if not line : break
        line = line.strip()
        if not line : continue
        sentence = inference(graph, builder, annotator, line)
        f = sys.stdout
        f.write('#' + line.encode('utf-8') + '\n')
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
    
if __name__ == '__main__':
    tf.app.run()

