#!/usr/bin/env python
#-*- coding: utf8 -*-
import tensorflow as tf

# for master spec, graph
from dragnn.protos import spec_pb2
from dragnn.python import graph_builder
from dragnn.python import render_spec_with_graphviz
from dragnn.python import spec_builder

# for writing and loading master spec
from tensorflow.python.platform import gfile
from google.protobuf import text_format

#from IPython.display import HTML
from tensorflow.python.platform import tf_logging as logging

def build_master_spec() :
    # Left-to-right, character-based LSTM.
    char2word = spec_builder.ComponentSpecBuilder('char_lstm')
    char2word.set_network_unit(
        name='wrapped_units.LayerNormBasicLSTMNetwork',
        hidden_layer_sizes='256')
    char2word.set_transition_system(name='char-shift-only', left_to_right='true')
    char2word.add_fixed_feature(name='chars', fml='char-input.text-char',
                                embedding_dim=16)

    # Lookahead LSTM reads right-to-left to represent the rightmost context of the
    # words. It gets word embeddings from the char model.
    lookahead = spec_builder.ComponentSpecBuilder('lookahead')
    lookahead.set_network_unit(
        name='wrapped_units.LayerNormBasicLSTMNetwork',
        hidden_layer_sizes='256')
    lookahead.set_transition_system(name='shift-only', left_to_right='false')
    lookahead.add_link(source=char2word, fml='input.last-char-focus',
                       embedding_dim=64)

    # Construct the tagger. This is a simple left-to-right LSTM sequence tagger.
    tagger = spec_builder.ComponentSpecBuilder('tagger')
    tagger.set_network_unit(
        name='wrapped_units.LayerNormBasicLSTMNetwork',
        hidden_layer_sizes='256')
    tagger.set_transition_system(name='tagger')
    tagger.add_token_link(source=lookahead, fml='input.focus', embedding_dim=64)

    # Construct the parser.
    parser = spec_builder.ComponentSpecBuilder('parser')
    parser.set_network_unit(name='FeedForwardNetwork', hidden_layer_sizes='256',
                            layer_norm_hidden='true')
    parser.set_transition_system(name='arc-standard')
    parser.add_token_link(source=lookahead, fml='input.focus', embedding_dim=64)
    parser.add_token_link(
        source=tagger, fml='input.focus stack.focus stack(1).focus',
        embedding_dim=64)

    # Add discrete features of the predicted parse tree so far, like in Parsey
    # McParseface.
    parser.add_fixed_feature(name='labels', embedding_dim=16,
                             fml=' '.join([
                                 'stack.child(1).label',
                                 'stack.child(1).sibling(-1).label',
                                 'stack.child(-1).label',
                                 'stack.child(-1).sibling(1).label',
                                 'stack(1).child(1).label',
                                 'stack(1).child(1).sibling(-1).label',
                                 'stack(1).child(-1).label',
                                 'stack(1).child(-1).sibling(1).label',
                                 'stack.child(2).label',
                                 'stack.child(-2).label',
                                 'stack(1).child(2).label',
                                 'stack(1).child(-2).label']))

    # Recurrent connection for the arc-standard parser. For both tokens on the
    # stack, we connect to the last time step to either SHIFT or REDUCE that
    # token. This allows the parser to build up compositional representations of
    # phrases.
    parser.add_link(
        source=parser,  # recurrent connection
        name='rnn-stack',  # unique identifier
        fml='stack.focus stack(1).focus',  # look for both stack tokens
        source_translator='shift-reduce-step',  # maps token indices -> step
        embedding_dim=64)  # project down to 64 dims

    master_spec = spec_pb2.MasterSpec()
    master_spec.component.extend(
        [char2word.spec, lookahead.spec, tagger.spec, parser.spec])
    #HTML(render_spec_with_graphviz.master_spec_graph(master_spec))
    return master_spec

def write_master_spec(master_spec, spec_file) :
    with gfile.FastGFile(spec_file, 'w') as f :
       f.write(str(master_spec).encode('utf-8'))

def load_master_spec(spec_file, resource_path) :
    tf.logging.info('Loading MasterSpec...')
    master_spec = spec_pb2.MasterSpec()
    with gfile.FastGFile(spec_file, 'r') as fin :
        text_format.Parse(fin.read(), master_spec)
    spec_builder.complete_master_spec(master_spec, None, resource_path)
    logging.info('Constructed master spec: %s', str(master_spec))
    return master_spec

def build_graph(master_spec) :
    # Build the TensorFlow graph based on the DRAGNN network spec.
    tf.logging.info('Building Graph...')
    hyperparam_config = spec_pb2.GridPoint(
        learning_method='adam',
        learning_rate=0.0005, 
        adam_beta1=0.9, adam_beta2=0.9, adam_eps=0.00001,
        decay_steps=128000,
        dropout_rate=0.8, gradient_clip_norm=1,
        use_moving_average=True,
        seed=1)
    graph = tf.Graph()
    with graph.as_default() :
        builder = graph_builder.MasterBuilder(master_spec, hyperparam_config)
        component_targets = [
            spec_pb2.TrainTarget(
                name=component.name,
                max_index=idx + 1,
                unroll_using_oracle=[False] * idx + [True])
            for idx, component in enumerate(master_spec.component)
            if 'shift-only' not in component.transition_system.registered_name
        ]
        trainers = [
            builder.add_training_from_config(target) for target in component_targets
        ]
        annotator = builder.add_annotation()
        builder.add_saver()
        return graph, builder, trainers, annotator
