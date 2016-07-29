#!/usr/bin/env python
#-*- coding: utf8 -*-

"""A client that talks to parsey_api service.

Typical usage example:

    parsey_client.py --server=localhost:9000
"""

import sys
from konlpy.tag import Komoran
reload(sys)
sys.setdefaultencoding('utf-8')
import json
import protobuf_json

from grpc.beta import implementations
import numpy
import tensorflow as tf
from tensorflow_serving.example import parsey_api_pb2

tf.app.flags.DEFINE_string('server', '', 'parsey_api service host:port')
FLAGS = tf.app.flags.FLAGS

def do_tagging(komoran, line) :
  analyzed = komoran.pos(line)
  output = []
  seq = 1
  for morph, tag in analyzed :
    tp = [seq, morph, morph, tag, tag, '_', 0, '_', '_', '_']
    out = '\t'.join([str(e) for e in tp])
    output.append(out)
    seq += 1
  return '\n'.join(output)

def do_inference(hostport):
  host, port = hostport.split(':')
  channel = implementations.insecure_channel(host, int(port))
  stub = parsey_api_pb2.beta_create_ParseyService_stub(channel)

  komoran = Komoran()

  while 1 :
    try : line = sys.stdin.readline()
    except KeyboardInterrupt : break
    if not line : break
    line = line.strip()
    request = parsey_api_pb2.ParseyRequest()
    conll_in = do_tagging(komoran, line)
    request.text.append(conll_in)
    response = stub.Parse(request, 5.0) # timeout 5 seconds
    json_obj=protobuf_json.pb2json(response)
    ret = json.dumps(json_obj,ensure_ascii=False,encoding='utf-8')
    print "Input : ", line
    print "Parsing :"
    print ret

def main(_):
  if not FLAGS.server:
    print 'please specify server host:port'
    return
  do_inference(FLAGS.server)

if __name__ == '__main__':
  tf.app.run()
