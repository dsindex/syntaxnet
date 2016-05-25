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
		
		if length == 5 :
			seq = tokens[0]
			eoj = tokens[1]
			analyzed = tokens[2]
			ptst = tokens[3]
			gov = tokens[4]
		if length == 4 :
			seq = tokens[0]
			eoj = ''
			analyzed = tokens[1]
			ptst = tokens[2]
			gov = tokens[3]

		entry = [seq, eoj, analyzed, ptst, gov]
		data.append(entry)
	close_file(fid)
	return data

def compare(entry_a, entry_b) :
	'''
	-1 : 비교 불가능
	0  : 다름
	1  : 같음

	entry : [seq, eoj, analyzed, ptst, gov]
	'''
	if entry_a[0] != entry_b[0] : return -1
	if entry_a[2].replace(' ','') != entry_b[2].replace(' ','') : return -1
	if entry_a[4] == entry_b[4] : return 1
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
		ret = compare(entry_a, entry_b)
		if ret == -1 : 
			sys.stderr.write("input files are not aligned\n")
			sys.exit(1)
		if ret == 1 : success += 1
		if ret == 0 : failure += 1

	accuracy = success / float(success + failure)
	print 'accuracy(UAS) = %f' % (accuracy)

