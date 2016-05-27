#!/usr/bin/env python
#-*- coding: utf8 -*-

import os
from optparse import OptionParser

# global variable
VERBOSE = 0

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

def spill(bucket, idx, mode) :
	ok = False
	'''
	if mode == 1 : # dev
		if idx % 10 == 1 : ok = True
	if mode == 2 : # test
		if idx % 10 == 2 : ok = True
	if mode == 0 : # train
		if idx % 10 != 1 and idx % 10 != 2 : ok = True
	'''
	if mode == 1 : # dev
		if idx % 10 == 3 : ok = True
	if mode == 2 : # test
		if idx % 10 == 4 : ok = True
	if mode == 0 : # train
		if idx % 10 != 3 and idx % 10 != 4 : ok = True

	idx += 1
	if not ok : return idx

	for line in bucket :
		print line
	print '\n',

	return idx


if __name__ == '__main__':

	parser = OptionParser()
	parser.add_option("--verbose", action="store_const", const=1, dest="verbose", help="verbose mode")
	parser.add_option("-m", "--mode", dest="mode", help="mode : 0(train), 1(test)", metavar="mode")
	(options, args) = parser.parse_args()

	if options.verbose : VERBOSE = 1

	mode = options.mode
	if mode == None : mode = 0
	else : mode = int(mode)

	idx = 0
	bucket = []
	while 1:
		try:
			line = sys.stdin.readline()
		except KeyboardInterrupt:
			break
		if not line:
			break
		line = line.strip('\n')

		if not line and len(bucket) >= 1 : 
			idx = spill(bucket, idx, mode)
			bucket = []
			continue

		if line : bucket.append(line)

	if len(bucket) != 0 :
		idx = spill(bucket, idx, mode)

