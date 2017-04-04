#!/usr/bin/env python
#-*- coding: utf8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import os
import time
import tensorflow as tf
import model_dragnn as model

flags = tf.app.flags
FLAGS = flags.FLAGS
flags.DEFINE_string('tf_master', '',
                    'TensorFlow execution engine to connect to.')
flags.DEFINE_string('dragnn_spec', '', 
                    'Path to the spec defining the model.')
flags.DEFINE_string('resource_path', '',
                    'Path to constructed resources.')
flags.DEFINE_string('checkpoint_filename', '',
                    'Filename to save the best checkpoint to.')
flags.DEFINE_bool('enable_tracing', False, 
                    'Whether tracing annotations')
 
def main(unused_argv) :

    if len(sys.argv) == 1 :
        flags._global_parser.print_help()
        sys.exit(0)

    # Loading model
    m = model.load_model(FLAGS.dragnn_spec,
                         FLAGS.resource_path,
                         FLAGS.checkpoint_filename,
                         enable_tracing=FLAGS.enable_tracing,
                         tf_master=FLAGS.tf_master)
    sess = m['session']
    graph = m['graph']
    builder = m['builder']
    annotator = m['annotator']

    # Analyze
    startTime = time.time()
    while 1 :
        try : line = sys.stdin.readline()
        except KeyboardInterrupt : break
        if not line : break
        line = line.strip()
        if not line : continue
        parsed_sentence = model.inference(sess, graph, builder, annotator, line, FLAGS.enable_tracing)
        out = model.parse_to_conll(parsed_sentence)
        f = sys.stdout
        f.write('# text = ' + line.encode('utf-8') + '\n')
        for entry in out['conll'] :
            id = entry['id']
            form = entry['form']
            lemma = entry['lemma']
            upostag = entry['upostag']
            xpostag = entry['xpostag']
            feats = entry['feats']
            head = entry['head']
            deprel = entry['deprel']
            deps = entry['deps']
            misc = entry['misc']
            li = [id, form, lemma, upostag, xpostag, feats, head, deprel, deps, misc]
            f.write('\t'.join([str(e) for e in li]) + '\n')
        f.write('\n\n')
    durationTime = time.time() - startTime
    sys.stderr.write("duration time = %f\n" % durationTime)

    # Unloading model
    model.unload_model(m)
    
if __name__ == '__main__':
    tf.app.run()

