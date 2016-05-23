#!/usr/bin/env python
#-*- coding: utf8 -*-

import os
import sys
from   optparse import OptionParser

# --verbose
VERBOSE = 0

def open_file(filename, mode) :
	try : fid = open(filename, mode)
	except :
		sys.stderr.write("open_file(), file open error : %s\n" % (filename))
		exit(1)
	else :
		return fid

def close_file(fid) :
	fid.close()

def read_file(filename) :
	data = []
	fid = open_file(filename, 'r')
	for line in fid :
		line = line.strip()
		if not line : continue
		tokens = line.split('\t')
		length = len(tokens)
		if length != 10 : continue
		# ex) 1  의상  의상  NNG  NNG  _  2  MOD     _  _
		#     2  서    서    JKB  JKB  _  4  NP_AJT  _  _
		idx = tokens[0]
		morph = tokens[1]
		tag = tokens[3]
		gov = tokens[6]
		label = tokens[7]
		entry = [idx, morph, tag, gov, label]
		data.append(entry)
	close_file(fid)
	return data

def compare(entry_a, entry_b) :
	'''
	-1 : 비교 불가능
	0  : 다름
	1  : 같음

	entry : [idx, morph, tag, gov, label]
	'''
	if entry_a[0] != entry_b[0] or entry_a[1] != entry_b[1] : return -1
	if entry_a[3] == entry_b[3] : return 1
	return 0

if __name__ == '__main__':

	parser = OptionParser()
	parser.add_option("--verbose", action="store_const", const=1, dest="verbose", help="verbose mode")
	parser.add_option("-a", "--aa", dest="a_path", help="a file path", metavar="a_path")
	parser.add_option("-b", "--bb", dest="b_path", help="b file path", metavar="b_path")
	(options, args) = parser.parse_args()
	
	if options.verbose == 1 : VERBOSE = 1
	a_path = options.a_path
	if a_path == None :
		parser.print_help()
		exit(1)
	b_path = options.b_path
	if b_path == None :
		parser.print_help()
		exit(1)

	a_data = read_file(a_path)
	b_data = read_file(b_path)

	if len(a_data) != len(b_data) :
		sys.stderr.write("can't compare\n")
		sys.exit(1)

	max = len(a_data)
	success = 0
	failure = 0
	for i in xrange(max) :
		entry_a = a_data[i]
		entry_b = b_data[i]
		if VERBOSE :
			if entry_a[4] != 'MOD' and entry_b[4] == 'MOD' :
				if compare(entry_a, entry_b) == 1 :
					msg = '\t'.join(entry_a + entry_b) + '\t' + '[noise]' + '\t' + '[success]'
				else :
					msg = '\t'.join(entry_a + entry_b) + '\t' + '[noise]' + '\t' + '[failure]'
				print msg
			else :
				msg = '\t'.join(entry_a + entry_b)
				print msg
		# entry : [idx, morph, tag, gov, label]
		if entry_a[4] == 'MOD' : continue
		ret = compare(entry_a, entry_b)
		if ret == -1 : 
			sys.stderr.write("input files are not aligned\n")
			sys.exit(1)
		if ret == 1 : success += 1
		if ret == 0 : failure += 1

	accuracy = success / float(success + failure)
	print 'accuracy(UAS) = %f' % (accuracy)

