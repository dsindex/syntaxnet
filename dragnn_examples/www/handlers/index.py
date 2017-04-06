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
		pid = os.getpid()
		debug['pid'] = pid

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
			m = self.dragnn[pid]
			sess = m['session']
			graph = m['graph']
			builder = m['builder']
			annotator = m['annotator']
			enable_tracing = self.enable_tracing
			enable_konlpy = self.enable_konlpy
			komoran = self.komoran
			try :
				out = {}
				if enable_konlpy :
					segmented, tagged = model.segment_by_konlpy(query, komoran)
					query = ' '.join(segmented)
					parsed_sentence = model.inference(sess, graph, builder, annotator, query, enable_tracing)
					out = model.parse_to_conll(parsed_sentence, tagged)
				else :
					parsed_sentence = model.inference(sess, graph, builder, annotator, query, enable_tracing)
					out = model.parse_to_conll(parsed_sentence)
				out['text'] = query
				rst['output'] = {}
			except :
				rst['status'] = 500
				rst['msg'] = 'analyze() fail'
			else :
				rst['status'] = 200
				rst['output'] = out

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
			pid = os.getpid()
			m = self.dragnn[pid]
			sess = m['session']
			graph = m['graph']
			builder = m['builder']
			annotator = m['annotator']
			enable_tracing = self.enable_tracing
			enable_konlpy = self.enable_konlpy
			komoran = self.komoran
			# analyze line by line
			out_list=[]
			idx = 0
			for line in content.split('\n') :
				line = line.strip()
				if not line : continue
				if enable_konlpy :
					segmented, tagged = model.segment_by_konlpy(line, komoran)
					line = ' '.join(segmented)
					parsed_sentence = model.inference(sess, graph, builder, annotator, line, enable_tracing)
					out = model.parse_to_conll(parsed_sentence, tagged)
				else :
					parsed_sentence = model.inference(sess, graph, builder, annotator, line, enable_tracing)
					out = model.parse_to_conll(parsed_sentence)
				out['text'] = line
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
			pid = os.getpid()
			m = self.dragnn[pid]
			sess = m['session']
			graph = m['graph']
			builder = m['builder']
			annotator = m['annotator']
			enable_tracing = self.enable_tracing
			enable_konlpy = self.enable_konlpy
			komoran = self.komoran
			# analyze line by line
			out_list=[]
			pgraph=None
			idx = 0
			for line in content.split('\n') :
				line = line.strip()
				if not line : continue
				if enable_konlpy :
					segmented, tagged = model.segment_by_konlpy(line, komoran)
					line = ' '.join(segmented)
					parsed_sentence = model.inference(sess, graph, builder, annotator, line, enable_tracing)
					out = model.parse_to_conll(parsed_sentence, tagged)
				else :
					parsed_sentence = model.inference(sess, graph, builder, annotator, line, enable_tracing)
					out = model.parse_to_conll(parsed_sentence)
				if idx == 0 :
					pgraph = model.parse_tree_graph(parsed_sentence)
				out['text'] = line
				out_list.append(out['conll'])
				idx += 1
			#self.write(dict(success=True, record=out_list, info=None, filename='static/img/tree.png'))
			self.write(dict(success=True, record=out_list, info=None, pgraph=pgraph))

		self.finish()

