#!/usr/bin/env python2.7

"""A client that talks to parsey_api service.

Typical usage example:

    parsey_client.py --server=localhost:9000
"""

import sys
import threading

from grpc.beta import implementations
import numpy
import tensorflow as tf

from tensorflow_serving.example import parsey_api_pb2

tf.app.flags.DEFINE_string('server', '', 'parsey_api service host:port')
FLAGS = tf.app.flags.FLAGS


def do_inference(hostport):
  host, port = hostport.split(':')
  channel = implementations.insecure_channel(host, int(port))
  stub = parsey_api_pb2.beta_create_ParseyService_stub(channel)

  while 1 :
    try : line = sys.stdin.readline()
    except KeyboardInterrupt : break
    if not line : break
    line = line.strip()
    request = parsey_api_pb2.ParseyRequest()
    request.text.append(line)
    response = stub.Parse(request, 5.0) # timeout 5 seconds
    print response

def main(_):
  if not FLAGS.server:
    print 'please specify server host:port'
    return
  do_inference(FLAGS.server)

if __name__ == '__main__':
  tf.app.run()
