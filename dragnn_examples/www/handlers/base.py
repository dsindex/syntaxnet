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
