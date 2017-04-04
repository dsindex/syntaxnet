#!/usr/bin/env python
#-*- coding: utf8 -*-
import tensorflow as tf

def main(unused_argv) :
    tf.logging.info('Start master server...')
    server = tf.train.Server.create_local_server()
    print server.target  # for other processes to connect
    server.join()

if __name__ == '__main__':
  tf.app.run()
