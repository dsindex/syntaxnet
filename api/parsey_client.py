#!/usr/bin/env python2.7

"""A client that talks to parsey-mcparseface-api service.

Typical usage example:

    parsey_client.py --server=localhost:9000
"""

import sys
import threading

from grpc.beta import implementations
import numpy
import tensorflow as tf

from tensorflow_serving.example import parsey_api_pb2

tf.app.flags.DEFINE_string('server', '', 'mlp_mnist_inference service host:port')
FLAGS = tf.app.flags.FLAGS


def do_inference(hostport):
  host, port = hostport.split(':')
  channel = implementations.insecure_channel(host, int(port))
  stub = parsey_api_pb2.beta_create_ParseyService_stub(channel)

  request = parsey_api_pb2.ParseyRequest()
  request.text.append("This is a first sentence")
  response = stub.Parse(request)
  print response

def main(_):
  if not FLAGS.server:
    print 'please specify server host:port'
    return
  do_inference(FLAGS.server)

if __name__ == '__main__':
  tf.app.run()
