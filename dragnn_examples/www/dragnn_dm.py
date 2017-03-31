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

sys.path.append(os.path.abspath('.'))


define('port', default=8897, help='run on the given port', type=int)
define('debug', default=True, help='run on debug mode', type=bool)
define('process', default=3, help='number of process for service mode', type=int)

log = logging.getLogger('tornado.application')

def setupAppLogger():
	fmtStr = '%(asctime)s - %(levelname)s - %(module)s - %(message)s'
	formatter = logging.Formatter(fmt=fmtStr)
        stub_filename = os.path.abspath(sys.argv[0])
	logfile = 'log/application.log'

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

		self.log.info('initialize...')
		self.dragnn = None
		self.log.info('initialize... done')

		log.info('start http start...')

		
	def finalize(self):
		# finalize resources
		self.log.info('finalize resources...')
		## finalize something....
		
		log.info('Close logger...')
		x = list(log.handlers)
		for i in x:
			log.removeHandler(i)
			i.flush()
			i.close()

def main():
	tornado.options.parse_command_line()

	application = Application()
	httpServer = tornado.httpserver.HTTPServer(application, no_keep_alive=True)
	if options.debug == True :
		httpServer.listen(options.port)
	else :
		httpServer.bind(options.port)
		if options.process == 0 :
			httpServer.start(0) # Forks multiple sub-processes, maximum to number of cores
		else :
			if options.process < 0 :
				options.process = 1
			httpServer.start(options.process) # Forks multiple sub-processes, given number

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
