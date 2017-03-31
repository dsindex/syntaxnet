#!/usr/bin/env python
#-*- coding: utf8 -*-
import tensorflow as tf

import model_dragnn as model

flags = tf.app.flags
FLAGS = flags.FLAGS

flags.DEFINE_string('spec_file', 'parser_spec.textproto',
                    'Filename to save the spec to.')

def main(unused_argv) :
    master_spec = model.build_master_spec()
    model.write_master_spec(master_spec, FLAGS.spec_file)

if __name__ == '__main__':
  tf.app.run()
