#!/usr/bin/env python
#-*- coding: utf8 -*-
import tensorflow as tf

# for master spec, graph
from dragnn.protos import spec_pb2
from dragnn.python import graph_builder
from dragnn.python import spec_builder

# for writing and loading master spec
from tensorflow.python.platform import gfile
from google.protobuf import text_format

# for inference
from syntaxnet.ops import gen_parser_ops
from syntaxnet import load_parser_ops  # This loads the actual op definitions
from syntaxnet.util import check
from dragnn.python import load_dragnn_cc_impl
from dragnn.python import render_parse_tree_graphviz
from dragnn.python import visualization
from syntaxnet import sentence_pb2
#from IPython.display import HTML


from tensorflow.python.platform import tf_logging as logging

def build_master_spec() :
    '''
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
    '''
    master_spec.component.extend(
        [char2word.spec, lookahead.spec, tagger.spec, parser.spec])
    '''
    master_spec.component.extend(
        [lookahead.spec, tagger.spec, parser.spec])
    return master_spec

def build_complete_master_spec(resource_path) :
    tf.logging.info('Building MasterSpec...')
    master_spec = build_master_spec()
    spec_builder.complete_master_spec(master_spec, None, resource_path)
    logging.info('Constructed master spec: %s', str(master_spec))
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

def build_train_graph(master_spec, hyperparam_config=None) :
    # Build the TensorFlow graph based on the DRAGNN network spec.
    tf.logging.info('Building Graph...')
    if not hyperparam_config :
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
        annotator = builder.add_annotation(enable_tracing=True)
        builder.add_saver()
        return graph, builder, trainers, annotator

def build_inference_graph(master_spec, enable_tracing=False) :
    # Initialize a graph
    tf.logging.info('Building Graph...')
    graph = tf.Graph()
    with graph.as_default():
        hyperparam_config = spec_pb2.GridPoint()
        builder = graph_builder.MasterBuilder(master_spec, hyperparam_config)
        # This is the component that will annotate test sentences.
        annotator = builder.add_annotation(enable_tracing=enable_tracing)
        builder.add_saver()
    return graph, builder, annotator

def load_model(dragnn_spec, resource_path, checkpoint_filename, enable_tracing=False, tf_master='') :
    logging.set_verbosity(logging.WARN)
    # check
    check.IsTrue(dragnn_spec)
    check.IsTrue(resource_path)
    check.IsTrue(checkpoint_filename)
    # Load master spec
    master_spec = load_master_spec(dragnn_spec, resource_path)
    # Build graph
    graph, builder, annotator = build_inference_graph(master_spec, enable_tracing=enable_tracing)
    with graph.as_default() :
        # Restore model
        sess = tf.Session(target=tf_master, graph=graph)
        # Make sure to re-initialize all underlying state.
        sess.run(tf.global_variables_initializer())
        builder.saver.restore(sess, checkpoint_filename)
    m = {}
    m['session'] = sess
    m['graph'] = graph
    m['builder'] = builder
    m['annotator'] = annotator
    return m

def unload_model(m) :
    sess = m['session']
    sess.close()

def inference(sess, graph, builder, annotator, text, enable_tracing=False) :
    tokens = [sentence_pb2.Token(word=word, start=-1, end=-1) for word in text.split()]
    sentence = sentence_pb2.Sentence()
    sentence.token.extend(tokens)
    if enable_tracing :
        annotations, traces = sess.run([annotator['annotations'], annotator['traces']],
                          feed_dict={annotator['input_batch']: [sentence.SerializeToString()]})
        #HTML(visualization.trace_html(traces[0]))
    else :
        annotations = sess.run(annotator['annotations'],
                          feed_dict={annotator['input_batch']: [sentence.SerializeToString()]})

    parsed_sentence = sentence_pb2.Sentence.FromString(annotations[0])
    #HTML(render_parse_tree_graphviz.parse_tree_graph(parsed_sentence))
    return parsed_sentence

def parse_tree_graph(parsed_sentence) :
    return render_parse_tree_graphviz.parse_tree_graph(parsed_sentence)

def attributed_tag_to_dict(attributed_tag) :
    '''
    ex) attribute { name: \"Case\" value: \"Nom\" }
        attribute { name: \"Number\" value: \"Sing\" } 
        attribute { name: \"Person\" value: \"1\" } 
        attribute { name: \"PronType\" value: \"Prs\" } 
        attribute { name: \"fPOS\" value: \"PRP++PRP\" }
    => 
        {'Case':'Nom', ..., 'fPOS':'PRP++PRP'} 
    '''
    attr_dict = {}
    toks = [tok for tok in attributed_tag.split() if tok not in ['attribute', 'name:', 'value:', '{', '}']]
    i = 0
    key = None
    for tok in toks :
        tok = tok[1:-1]  # strip \"
        if i % 2 == 0 :
            key = tok
        else :
            val = tok
            if key :
                attr_dict[key] = val
                key = None
        i += 1
    return attr_dict

def parse_to_conll(parsed_sentence, tagged=None) :
    out = {}
    out['conll'] = []
    for i, token in enumerate(parsed_sentence.token) :
        id = i + 1
        word = token.word.encode('utf-8')
        attributed_tag = token.tag.encode('utf-8')
        attr_dict = attributed_tag_to_dict(attributed_tag)
        fPOS = attr_dict['fPOS']
        tag = fPOS.replace('++',' ').split()
        if tagged :
          tag[0] = tagged[i][1] # pos tag from komoran
          tag[1] = tagged[i][1]
        head = token.head + 1
        label = token.label.encode('utf-8').split(':')[0]
        entry = {}
        entry['id'] = id
        entry['form'] = word
        entry['lemma'] = word
        entry['upostag'] = tag[0]
        entry['xpostag'] = tag[1]
        entry['feats'] = '_'
        entry['head'] = head
        entry['deprel'] = label
        entry['deps'] = '_'
        entry['misc'] = '_'
        out['conll'].append(entry)
    return out

def segment_by_konlpy(line, komoran) :
    tagged = komoran.pos(line.decode('utf-8'))
    segmented = []
    seq = 1
    for morph, tag in tagged :
        '''
        tp = [seq, morph, morph, tag, tag, '_', 0, '_', '_', '_']
        print '\t'.join([str(e) for e in tp])
        '''
        segmented.append(morph)
        seq += 1
    return segmented, tagged

