#!/usr/bin/env python
#-*- coding: utf8 -*-
import tensorflow as tf

#from IPython.display import HTML

# for spec, graph
from dragnn.protos import spec_pb2
from dragnn.python import graph_builder
from dragnn.python import render_spec_with_graphviz
from dragnn.python import spec_builder

def build_master_spec(FLAGS) :
    '''
    # Left-to-right, character-based LSTM.
    char2word = spec_builder.ComponentSpecBuilder('char_lstm')
    char2word.set_network_unit(
        name='wrapped_units.LayerNormBasicLSTMNetwork',
        hidden_layer_sizes='256')
    char2word.set_transition_system(name='char-shift-only', left_to_right='true')
    char2word.add_fixed_feature(name='chars', fml='char-input.text-char',
                                embedding_dim=16)
    char2word.fill_from_resources(FLAGS.resource_path)

    # Lookahead LSTM reads right-to-left to represent the rightmost context of the
    # words. It gets word embeddings from the char model.
    lookahead = spec_builder.ComponentSpecBuilder('lookahead')
    lookahead.set_network_unit(
        name='wrapped_units.LayerNormBasicLSTMNetwork',
        hidden_layer_sizes='256')
    lookahead.set_transition_system(name='shift-only', left_to_right='false')
    lookahead.add_link(source=char2word, fml='input.last-char-focus',
                       embedding_dim=64)
    lookahead.fill_from_resources(FLAGS.resource_path)
    '''

    # Construct the 'lookahead' ComponentSpec. This is a simple right-to-left RNN
    # sequence model, which encodes the context to the right of each token. It has
    # no loss except for the downstream components.
    lookahead = spec_builder.ComponentSpecBuilder('lookahead')
    lookahead.set_network_unit(
        name='FeedForwardNetwork', hidden_layer_sizes='256')
    lookahead.set_transition_system(name='shift-only', left_to_right='true')
    lookahead.add_fixed_feature(name='words', fml='input.word', embedding_dim=64)
    lookahead.add_rnn_link(embedding_dim=-1)
    lookahead.fill_from_resources(FLAGS.resource_path)

    # Construct the tagger. This is a simple left-to-right LSTM sequence tagger.
    tagger = spec_builder.ComponentSpecBuilder('tagger')
    tagger.set_network_unit(
        name='wrapped_units.LayerNormBasicLSTMNetwork',
        hidden_layer_sizes='256')
    tagger.set_transition_system(name='tagger')
    tagger.add_token_link(source=lookahead, fml='input.focus', embedding_dim=64)
    tagger.fill_from_resources(FLAGS.resource_path)

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

    parser.fill_from_resources(FLAGS.resource_path)

    master_spec = spec_pb2.MasterSpec()
    '''
    master_spec.component.extend(
        [char2word.spec, lookahead.spec, tagger.spec, parser.spec])
    '''
    master_spec.component.extend(
        [lookahead.spec, tagger.spec, parser.spec])
    #HTML(render_spec_with_graphviz.master_spec_graph(master_spec))
  
    return master_spec

def build_graph(FLAGS, master_spec) :

    # Build the TensorFlow graph based on the DRAGNN network spec.
    graph = tf.Graph()
    with graph.as_default():
        hyperparam_config = spec_pb2.GridPoint(
            learning_method='adam',
            learning_rate=0.0005, 
            adam_beta1=0.9, adam_beta2=0.9, adam_eps=0.001,
            dropout_rate=0.8, gradient_clip_norm=1,
            use_moving_average=True,
            seed=1)
        builder = graph_builder.MasterBuilder(master_spec, hyperparam_config)
        if FLAGS.mode == 'train' :
            '''
            target = spec_pb2.TrainTarget(
                name='all',
                unroll_using_oracle=[False, False, True, True], # train tagger & parser on gold unrolling, skip char_lstm/lookahead
                component_weights=[0, 0, 0.5, 0.5]) # tagger and parser losses have equal weights
            '''
            target = spec_pb2.TrainTarget(
                name='all',
                unroll_using_oracle=[False, True, True], # train tagger & parser on gold unrolling, skip lookahead
                component_weights=[0, 0.5, 0.5]) # tagger and parser losses have equal weights
            trainer = builder.add_training_from_config(target)
            annotator = builder.add_annotation(enable_tracing=True)
            builder.add_saver()
            return graph, builder, trainer, annotator
        else :
            annotator = builder.add_annotation(enable_tracing=True)
            builder.add_saver()
            return graph, builder, annotator

