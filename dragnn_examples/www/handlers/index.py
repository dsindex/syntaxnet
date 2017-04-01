# -*- coding: utf-8 -*-
import os
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import logging
import tornado.web

from handlers.base import BaseHandler

import json
import time

# dragnn
sys.path.append(os.path.abspath('../'))
import model_dragnn as model

class IndexHandler(BaseHandler):
	def get(self):
		q = self.get_argument('q', '')
		self.render('index.html', q=q)

class HCheckHandler(BaseHandler):
    def get(self):
        self.set_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        templates_dir = 'templates'
        hdn_filename = '_hcheck.hdn'
        err_filename = 'error.html'
        try : fid = open(templates_dir + "/" + hdn_filename, 'r')
        except :
            self.set_status(404)
            self.render(err_filename)
        else :
            fid.close()
            self.render(hdn_filename)

class DragnnHandler(BaseHandler):
	def get(self) :
		start_time = time.time()
		
		callback = self.get_argument('callback', '')
		mode = self.get_argument('mode', 'product')
		try :
			# unicode
			query = self.get_argument('q', '')
		except :
			query = "Invalid unicode in q"

		debug = {}
		debug['callback'] = callback
		debug['mode'] = mode

		rst = {}
		rst['msg'] = ''
		rst['query'] = query
		if mode == 'debug' : rst['debug'] = debug

		try :
			# convert to utf-8 
			query = query.encode('utf-8')
		except :
			rst['status'] = 500
			rst['msg'] = "input query encode('utf-8') fail"
			rst['output'] = []
		else :
			dragnn = self.dragnn
			sess = dragnn['session']
			graph = dragnn['graph']
			builder = dragnn['builder']
			annotator = dragnn['annotator']
			enable_tracing = self.enable_tracing
			try :
				out = {}
				sentence = model.inference(sess, graph, builder, annotator, query, enable_tracing)
				out['text'] = query
				out['conll'] = []
				for i, token in enumerate(sentence.token) :
					id = i + 1
					word = token.word.encode('utf-8')
					attributed_tag = token.tag.encode('utf-8')
					attr_dict = model.attributed_tag_to_dict(attributed_tag)
					fPOS = attr_dict['fPOS']
					tag = fPOS.replace('++',' ').split()
					head = token.head + 1
					label = token.label.encode('utf-8').split(':')[0]
					entry = {}
					entry['id'] = id
					entry['form'] = word
					entry['lemma'] = word
					entry['upostag'] = tag[0]
					entry['xpostag'] = tag[1]
					entry['feats'] = None
					entry['head'] = head
					entry['deprel'] = label
					entry['deps'] = None
					entry['misc'] = None
					out['conll'].append(entry)
				rst['output'] = {}
			except :
				rst['status'] = 500
				rst['msg'] = 'analyze() fail'
			else :
				rst['status'] = 200
				rst['output'] = {'out':out}

			if mode == 'debug' :
				duration_time = time.time() - start_time
				debug['exectime'] = duration_time

		try :
			ret = json.dumps(rst,ensure_ascii=False,encoding="utf-8")
		except :
			msg = "json.dumps() fail for query %s" % (query)
			self.log.debug(msg + "\n")
			err = {}
			err['status'] = 500
			err['msg'] = msg
			ret = json.dumps(err)

		if mode == 'debug' :
			self.set_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')

		if callback.strip() :
			self.set_header('Content-Type', 'application/javascript; charset=utf-8')
			ret = 'if (typeof %s === "function") %s(%s);' % (callback, callback, ret)
		else :
			self.set_header('Content-Type', 'application/json; charset=utf-8')

		self.write(ret)
		self.finish()	
		

	def post(self):
		try :
			content = self.get_argument('content', "", True)
			content = content.encode('utf-8')
		except Exception, e :
			ret = str(e)
			self.write(dict(success=True, info=ret))
		else :
			dragnn = self.dragnn
			# analyze line by line
			out_list=[]
			idx = 0
			for line in content.split('\n') :
				line = line.strip()
				if not line : continue
				out = {} # dragnn.analyze(line)
				out_list.append(out)
				idx += 1
			self.write(dict(success=True, record=out_list, info=None))

		self.finish()

class DragnnTestHandler(BaseHandler):
	def post(self):
		try :
			content = self.get_argument('content', "", True)
			content = content.encode('utf-8')
		except Exception, e :
			ret = str(e)
			self.write(dict(success=True, info=ret))
		else :
			dragnn = self.dragnn
			# analyze line by line
			out_list=[]
			idx = 0
			for line in content.split('\n') :
				line = line.strip()
				if not line : continue
				out = {} # dragnn.analyze(line)
				out_list.append(out)
				idx += 1
			self.write(dict(success=True, record=out_list, info=None, filename='static/img/tree.png'))

		self.finish()

