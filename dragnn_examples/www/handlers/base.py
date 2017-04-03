# -*- coding: utf-8 -*-
import tornado.web
import logging

class BaseHandler(tornado.web.RequestHandler):
	@property
	def log(self):
		return self.application.log
	@property
	def dragnn(self):
		return self.application.dragnn
	@property
	def enable_tracing(self):
		return self.application.enable_tracing
	@property
	def enable_konlpy(self):
		return self.application.enable_konlpy
	@property
	def komoran(self):
		return self.application.komoran
