import os
import os.path
import random
import time
import tensorflow as tf

#from IPython.display import HTML
from tensorflow.python.platform import gfile
from tensorflow.python.platform import tf_logging as logging

from google.protobuf import text_format

from syntaxnet.ops import gen_parser_ops
from syntaxnet import load_parser_ops  # This loads the actual op definitions
from syntaxnet import task_spec_pb2
from syntaxnet import sentence_pb2

from dragnn.protos import spec_pb2
from dragnn.python.sentence_io import ConllSentenceReader

from dragnn.python import evaluation
from dragnn.python import graph_builder
from dragnn.python import lexicon
from dragnn.python import load_dragnn_cc_impl
from dragnn.python import render_parse_tree_graphviz
from dragnn.python import render_spec_with_graphviz
from dragnn.python import spec_builder
from dragnn.python import trainer_lib
from dragnn.python import visualization

# global
DATA_DIR = ''
TRAINING_CORPUS_PATH = ''
DEV_CORPUS_PATH = ''
CHECKPOINT_FILENAME = ''
TENSORBOARD_DIR = ''
N_STEPS = 20
BATCH_SIZE = 64

import sys
from optparse import OptionParser

def build_graph() :
	# Constructs lexical resources for SyntaxNet in the given resource path, from
	# the training data.
	lexicon.build_lexicon(DATA_DIR, TRAINING_CORPUS_PATH)

	# Construct the 'lookahead' ComponentSpec. This is a simple right-to-left RNN
	# sequence model, which encodes the context to the right of each token. It has
	# no loss except for the downstream components.
	lookahead = spec_builder.ComponentSpecBuilder('lookahead')
	lookahead.set_network_unit(
		name='FeedForwardNetwork', hidden_layer_sizes='256')
	lookahead.set_transition_system(name='shift-only', left_to_right='true')
	lookahead.add_fixed_feature(name='words', fml='input.word', embedding_dim=64)
	lookahead.add_rnn_link(embedding_dim=-1)
	lookahead.fill_from_resources(DATA_DIR)

	# Construct the ComponentSpec for tagging. This is a simple left-to-right RNN
	# sequence tagger.
	tagger = spec_builder.ComponentSpecBuilder('tagger')
	tagger.set_network_unit(name='FeedForwardNetwork', hidden_layer_sizes='256')
	tagger.set_transition_system(name='tagger')
	tagger.add_rnn_link(embedding_dim=-1)
	tagger.add_token_link(source=lookahead, fml='input.focus', embedding_dim=32)
	tagger.fill_from_resources(DATA_DIR)

	# Construct the ComponentSpec for parsing.
	parser = spec_builder.ComponentSpecBuilder('parser')
	parser.set_network_unit(name='FeedForwardNetwork', hidden_layer_sizes='256')
	parser.set_transition_system(name='arc-standard')
	parser.add_token_link(source=lookahead, fml='input.focus', embedding_dim=32)
	parser.add_token_link(
		source=tagger,
		fml='input.focus stack.focus stack(1).focus',
		embedding_dim=32)

	# Recurrent connection for the arc-standard parser. For both tokens on the
	# stack, we connect to the last time step to either SHIFT or REDUCE that
	# token. This allows the parser to build up compositional representations of
	# phrases.
	parser.add_link(
		source=parser,                          # recurrent connection
		name='rnn-stack',                       # unique identifier
		fml='stack.focus stack(1).focus',       # look for both stack tokens
		source_translator='shift-reduce-step',  # maps token indices -> step
		embedding_dim=32)                       # project down to 32 dims

	parser.fill_from_resources(DATA_DIR)

	master_spec = spec_pb2.MasterSpec()
	master_spec.component.extend([lookahead.spec, tagger.spec, parser.spec])
	#HTML(render_spec_with_graphviz.master_spec_graph(master_spec))

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
		target = spec_pb2.TrainTarget(
			name='all',
			unroll_using_oracle=[False, True, True], # train tagger & parser on gold unrolling, skip lookahead
			component_weights=[0, 0.5, 0.5]) # tagger and parser losses have equal weights
		trainer = builder.add_training_from_config(target)
		annotator = builder.add_annotation(enable_tracing=True)
		builder.add_saver()
	return graph, trainer, annotator

def train(graph, trainer, annotator) :
	# Train on data for N_STEPS steps and evaluate.
	with tf.Session(graph=graph) as sess:
		sess.run(tf.global_variables_initializer())
		training_corpus = ConllSentenceReader(
			TRAINING_CORPUS_PATH, projectivize=True).corpus()
		dev_corpus = ConllSentenceReader(DEV_CORPUS_PATH).corpus()[:200]
		for step in xrange(N_STEPS):
			trainer_lib.run_training_step(sess, trainer, training_corpus, batch_size=BATCH_SIZE)
			tf.logging.warning('Step %d/%d', step + 1, N_STEPS)
		parsed_dev_corpus = trainer_lib.annotate_dataset(sess, annotator, dev_corpus)
		pos, uas, las = evaluation.calculate_parse_metrics(dev_corpus, parsed_dev_corpus)
		tf.logging.warning('POS %.2f UAS %.2f LAS %.2f', pos, uas, las)
		builder.saver.save(sess, CHECKPOINT_FILENAME)

def test(graph, annotator, text) :
	# Visualize the output of our mini-trained model on a test sentence.
	tokens = [sentence_pb2.Token(word=word, start=-1, end=-1) for word in text.split()]
	sentence = sentence_pb2.Sentence()
	sentence.token.extend(tokens)

	with tf.Session(graph=graph) as sess:
		# Restore the model we just trained.
		builder.saver.restore(sess, CHECKPOINT_FILENAME)
		annotations, traces = sess.run([annotator['annotations'], annotator['traces']],
						  feed_dict={annotator['input_batch']: [sentence.SerializeToString()]})

	#HTML(visualization.trace_html(traces[0]))

	parsed_sentence = sentence_pb2.Sentence.FromString(annotations[0])
	#HTML(render_parse_tree_graphviz.parse_tree_graph(parsed_sentence))
	return parsed_sentence

if __name__ == '__main__':

	parser = OptionParser()
	parser.add_option("--verbose", action="store_const", const=1, dest="verbose", help="verbose mode")
	parser.add_option("-d", "--data_dir", dest="data_dir", help="data dir path", metavar="data_dir")
	parser.add_option("-x", "--train_file", dest="train_file", help="train file path", metavar="train_file")
	parser.add_option("-y", "--dev_file", dest="dev_file", help="dev file path", metavar="dev_file")
	parser.add_option("-n", "--n_steps", dest="n_steps", type="int", default=20, help="number of steps(iterations)", metavar="n_steps")
	parser.add_option("-b", "--batch_size", dest="batch_size", type="int", default=64, help="batch size", metavar="batch_size")
	(options, args) = parser.parse_args()

	data_dir = options.data_dir
	train_file = options.train_file
	dev_file = options.dev_file
	if not data_dir or not train_file or not dev_file :
		parser.print_help()
		sys.exit(1)
	DATA_DIR = data_dir
	TRAINING_CORPUS_PATH = train_file
	DEV_CORPUS_PATH = dev_file
	CHECKPOINT_FILENAME = '{}/model.checkpoint'.format(DATA_DIR)
	TENSORBOARD_DIR = '{}/notebooks/tensorboard'.format(DATA_DIR)
	N_STEPS = options.n_steps
	BATCH_SIZE = options.batch_size

	# Some of the IO functions fail miserably if data is missing.
	assert os.path.isfile(TRAINING_CORPUS_PATH), 'Could not find training corpus'

	logging.set_verbosity(logging.WARN)

	graph, trainer, annotator = build_graph()
	train(graph, trainer, annotator)
	text = 'this is an example for dragnn'
	parsed_sentence = test(graph, annotator, text)
