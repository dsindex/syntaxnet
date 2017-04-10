# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import os.path
import logging
from logging.handlers import RotatingFileHandler
import signal
import time
import math

import tornado.web
import tornado.ioloop
import tornado.autoreload
import tornado.web
import tornado.httpserver
import tornado.process
import tornado.autoreload as autoreload

from tornado.options import define, options
from handlers.index import IndexHandler, HCheckHandler, DragnnHandler, DragnnTestHandler

# dragnn
sys.path.append(os.path.abspath('../'))
import model_dragnn as model

define('port', default=8897, help='run on the given port', type=int)
define('debug', default=True, help='run on debug mode', type=bool)
define('process', default=3, help='number of process for service mode', type=int)
define('enable_konlpy', default=False, help='to use konlpy', type=bool)
define('dragnn_spec', default='', help='path to the spec defining the model', type=str)
define('resource_path', default='', help='path to constructed resources', type=str)
define('checkpoint_filename', default='', help='filename to save the best checkpoint to', type=str)
define('enable_tracing', default=False, help='whether tracing annotations', type=bool)
define('tf_master', default='', help='tensorFlow execution engine to connect to', type=str)

log = logging.getLogger('tornado.application')

def setupAppLogger():
	fmtStr = '%(asctime)s - %(levelname)s - %(module)s - %(message)s'
	formatter = logging.Formatter(fmt=fmtStr)

        cdir = os.path.dirname(os.path.abspath(options.log_file_prefix))
	logfile = cdir + '/' + 'application.log'

	rotatingHandler = RotatingFileHandler(logfile, 'a', options.log_file_max_size, options.log_file_num_backups)
	rotatingHandler.setFormatter(formatter)
	
	if options.logging != 'none':
		log.setLevel(getattr(logging, options.logging.upper()))
	else:
		log.setLevel(logging.ERROR)

	log.propagate = False
	log.addHandler(rotatingHandler)

	return log

class Application(tornado.web.Application):
	def __init__(self):
		settings = dict(
			static_path = os.path.join(os.path.dirname(__file__), 'static'),
			template_path = os.path.join(os.path.dirname(__file__), 'templates'),
			autoescape = None,
			debug = options.debug,
			gzip = True
		)

		handlers = [
			(r'/', IndexHandler),
			(r'/_hcheck.hdn', HCheckHandler),
			(r'/dragnn', DragnnHandler),
			(r'/dragnntest', DragnnTestHandler),
		]

		tornado.web.Application.__init__(self, handlers, **settings)
		autoreload.add_reload_hook(self.finalize)

		self.log = setupAppLogger()
		ppid = os.getpid()
		self.log.info('initialize parent process[%s] ...' % (ppid))
		self.ppid = ppid
		self.enable_tracing = options.enable_tracing
		# import konlpy if enabled
		self.enable_konlpy = options.enable_konlpy
		self.komoran = None
		if options.enable_konlpy :
			from konlpy.tag import Komoran
			komoran = Komoran()
			self.komoran = komoran
		self.log.info('initialize parent process[%s] ... done' % (ppid))

		log.info('start http start...')

	def initialize(self) :
		pid = os.getpid()
		self.log.info('initialize per process[%s] ...' % (pid))
		# Loading model
		self.dragnn = {}
		m = model.load_model(options.dragnn_spec,
					options.resource_path,
					options.checkpoint_filename,
					enable_tracing=options.enable_tracing,
					tf_master=options.tf_master)
		self.dragnn[pid] = m
		self.log.info('initialize per process[%s] ... done' % (pid))
		
	def finalize(self):
		# finalize resources
		self.log.info('finalize resources...')
		## finalize something....
		for pid, m in self.dragnn.iteritems() :
			model.unload_model(m)
		
		log.info('Close logger...')
		x = list(log.handlers)
		for i in x:
			log.removeHandler(i)
			i.flush()
			i.close()

def main():
	tornado.options.parse_command_line()

	application = Application()
	application.initialize()
	httpServer = tornado.httpserver.HTTPServer(application, no_keep_alive=True)
	if options.debug == True :
		httpServer.listen(options.port)
	else :
		httpServer.bind(options.port)
		if options.process == 0 :
			httpServer.start(0) # Forks multiple sub-processes, maximum to number of cores
			if pid != application.ppid :
				application.initialize()
		else :
			if options.process < 0 :
				options.process = 1
			httpServer.start(options.process) # Forks multiple sub-processes, given number
			pid = os.getpid()
			if pid != application.ppid :
				application.initialize()

	MAX_WAIT_SECONDS_BEFORE_SHUTDOWN = 3

	def sig_handler(sig, frame):
		log.warning('Caught signal: %s', sig)
		tornado.ioloop.IOLoop.instance().add_callback(shutdown)

	def shutdown():
		log.info('Stopping http server')
		httpServer.stop()

		log.info('Will shutdown in %s seconds ...', MAX_WAIT_SECONDS_BEFORE_SHUTDOWN)
		io_loop = tornado.ioloop.IOLoop.instance()

		deadline = time.time() + MAX_WAIT_SECONDS_BEFORE_SHUTDOWN

		def stop_loop():
			now = time.time()
			if now < deadline and (io_loop._callbacks or io_loop._timeouts):
				io_loop.add_timeout(now + 1, stop_loop)
			else:
				io_loop.stop()
				log.info('Shutdown')

		stop_loop()

	signal.signal(signal.SIGTERM, sig_handler)
	signal.signal(signal.SIGINT, sig_handler)

	tornado.ioloop.IOLoop.instance().start()

	log.info('Exit...')

if __name__ == '__main__':
	main()
