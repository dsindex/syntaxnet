#!/usr/bin/env python
#-*- coding: utf8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import os
import os.path
import random
import time
import tensorflow as tf
import model_dragnn as model

flags = tf.app.flags
FLAGS = flags.FLAGS
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
                         FLAGS.enable_tracing)
    sess = m['session']
    graph = m['graph']
    builder = m['builder']
    annotator = m['annotator']

    # Analyze
    # Prepare korean morphological analyzer for segmentation
    from konlpy.tag import Komoran
    komoran = Komoran()
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
        sentence = model.inference(sess, graph, builder, annotator, line, FLAGS.enable_tracing)
        f = sys.stdout
        f.write('# text = ' + line.encode('utf-8') + '\n')
        for i, token in enumerate(sentence.token) :
            head = token.head + 1
            attributed_tag = token.tag.encode('utf-8')
            attr_dict = model.attributed_tag_to_dict(attributed_tag)
            fPOS = attr_dict['fPOS']
            tag = fPOS.replace('++',' ').split()
            label = token.label.encode('utf-8').split(':')[0]
            f.write('%s\t%s\t%s\t%s\t%s\t_\t%d\t%s\t_\t_\n'%(
                    i + 1,
                    token.word.encode('utf-8'),
                    token.word.encode('utf-8'),
                    analyzed[i][1].encode('utf-8'),
                    analyzed[i][1].encode('utf-8'),
                    head,
                    label))
        f.write('\n\n')
    durationTime = time.time() - startTime
    sys.stderr.write("duration time = %f\n" % durationTime)

    # Close session
    sess.close()

if __name__ == '__main__':
    tf.app.run()

