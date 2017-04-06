#!/usr/bin/env python
#-*- coding: utf8 -*-
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
    tf.logging.info('Start master server...')
    server = tf.train.Server.create_local_server()
    # Loading model
    m = model.load_model(FLAGS.dragnn_spec,
                         FLAGS.resource_path,
                         FLAGS.checkpoint_filename,
                         enable_tracing=FLAGS.enable_tracing,
                         tf_master=server.target)
    print '[target]' + '\t' + server.target  # for other processes to connect
    server.join()

if __name__ == '__main__':
  tf.app.run()
