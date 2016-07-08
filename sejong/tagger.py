#!/usr/bin/env python
#-*- coding: utf8 -*-

import os
from optparse import OptionParser
from konlpy.tag import Komoran


# global variable
VERBOSE = 0

import sys
reload(sys)
sys.setdefaultencoding('utf-8')


if __name__ == '__main__':

	parser = OptionParser()
	parser.add_option("--verbose", action="store_const", const=1, dest="verbose", help="verbose mode")
	(options, args) = parser.parse_args()

	if options.verbose : VERBOSE = 1

	komoran = Komoran()

	while 1:
		try:
			line = sys.stdin.readline()
		except KeyboardInterrupt:
			break
		if not line:
			break

		analyzed = komoran.pos(line)
		seq = 1
		for morph, tag in analyzed :
			tp = [seq, morph, morph, tag, tag, '_', 0, '_', '_', '_']
			print '\t'.join([str(e) for e in tp])
			seq += 1
		print '\n',




