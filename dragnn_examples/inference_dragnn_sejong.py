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

# for inference
from syntaxnet import sentence_pb2
from dragnn.python import render_parse_tree_graphviz
from dragnn.python import visualization

flags = tf.app.flags
FLAGS = flags.FLAGS
flags.DEFINE_string('resource_path', '',
                    'Path to constructed resources.')
flags.DEFINE_string('checkpoint_filename', '',
                    'Filename to save the best checkpoint to.')

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

    FLAGS.mode = 'inference'
    # prepare korean morphological analyzer for segmentation
    from konlpy.tag import Komoran
    komoran = Komoran()
    # build master spec and graph
    master_spec = model.build_master_spec(FLAGS)
    graph, builder, annotator = model.build_graph(FLAGS, master_spec)
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
        sentence = test(graph, builder, annotator, line)
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
    
if __name__ == '__main__':
    tf.app.run()

