#!/usr/bin/env python
#-*- coding: utf8 -*-
import sys
import os
import os.path
import random
import time
import tensorflow as tf

import model_dragnn as model

# for inference
from syntaxnet.ops import gen_parser_ops
from syntaxnet import load_parser_ops  # This loads the actual op definitions
from syntaxnet.util import check
from dragnn.python import load_dragnn_cc_impl
from dragnn.python import render_parse_tree_graphviz
from dragnn.python import visualization
from syntaxnet import sentence_pb2

#from IPython.display import HTML
from tensorflow.python.platform import tf_logging as logging

flags = tf.app.flags
FLAGS = flags.FLAGS
flags.DEFINE_string('dragnn_spec', '', 
                    'Path to the spec defining the model.')
flags.DEFINE_string('resource_path', '',
                    'Path to constructed resources.')
flags.DEFINE_string('checkpoint_filename', '',
                    'Filename to save the best checkpoint to.')

def inference(sess, graph, builder, annotator, text) :
    tokens = [sentence_pb2.Token(word=word, start=-1, end=-1) for word in text.split()]
    sentence = sentence_pb2.Sentence()
    sentence.token.extend(tokens)

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
    check.IsTrue(FLAGS.dragnn_spec)
    check.IsTrue(FLAGS.resource_path)
    check.IsTrue(FLAGS.checkpoint_filename)

    # Prepare korean morphological analyzer for segmentation
    from konlpy.tag import Komoran
    komoran = Komoran()
    # Load master spec
    master_spec = model.load_master_spec(FLAGS.dragnn_spec, FLAGS.resource_path)
    # Build graph
    graph, builder, annotator = model.build_inference_graph(master_spec)
    # Restore model
    sess = tf.Session(graph=graph)
    # Make sure to re-initialize all underlying state.
    sess.run(tf.global_variables_initializer())
    builder.saver.restore(sess, FLAGS.checkpoint_filename)

    startTime = time.time()
    while 1 :
        try : line = sys.stdin.readline()
        except KeyboardInterrupt : break
        if not line : break
        line = line.strip()
        if not line : continue
        analyzed = komoran.pos(line.decode('utf-8'))
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
        sentence = inference(sess, graph, builder, annotator, line)
        f = sys.stdout
        f.write('#' + line.encode('utf-8') + '\n')
        for i, token in enumerate(sentence.token) :
            head = token.head + 1
            f.write('%s\t%s\t%s\t%s\t%s\t_\t%d\t%s\t_\t_\n'%(
                    i + 1,
                    token.word.encode('utf-8'),
                    token.word.encode('utf-8'),
                    analyzed[i][1].encode('utf-8'),
                    analyzed[i][1].encode('utf-8'),
                    head,
                    token.label.encode('utf-8')))
        f.write('\n\n')
    durationTime = time.time() - startTime
    sys.stderr.write("duration time = %f\n" % durationTime)
    sess.close()

if __name__ == '__main__':
    tf.app.run()

