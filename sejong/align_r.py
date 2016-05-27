#!/usr/bin/env python
#-*- coding: utf8 -*-

import os
from optparse import OptionParser

# global variable
VERBOSE = 0

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

def n_spill(n_bucket, seq, mseq2seq) :
	ptst = n_bucket[-1][4]
	idx = 1
	mseq_list = []
	analyzed = []
	mgov_list = []
	for mseq, morph, tag, mgov, mptst in n_bucket :
		mseq_list.append(mseq)
		analyzed.append(morph + '/' + tag)
		mgov_list.append(mgov)
		mseq2seq[mseq] = seq
		idx += 1
	out = [seq, mseq_list, analyzed, mgov_list, ptst]
	seq += 1
	return seq, out

def spill(bucket) :
	result = []
	mseq2seq = {0:0}
	seq = 1
	n_bucket = []
	prev_deprel = None
	for line in bucket :
		mseq,morph,_,tag,_,_,mgov,mptst,_,_,deprel = line.split('\t',10)
		mseq = int(mseq)
		mgov = int(mgov)
		if prev_deprel == None :
			n_bucket.append([mseq, morph, tag, mgov, mptst])
		else :
			if prev_deprel != 'MOD' :
				seq, out = n_spill(n_bucket, seq, mseq2seq)
				result.append(out)
				n_bucket = []
			n_bucket.append([mseq, morph, tag, mgov, mptst])
		prev_deprel = deprel

	if len(n_bucket) != 0 :
		seq, out = n_spill(n_bucket, seq, mseq2seq)
		result.append(out)

	for seq, mseq_list, analyzed, mgov_list, ptst in result :
		if VERBOSE : 
			print str(seq) + '\t' +  ','.join([str(e) for e in mseq_list]) + '\t' + \
				' + '.join(analyzed) + '\t' + ','.join([str(e) for e in mgov_list]) + \
				'\t' + ptst
		gov = mseq2seq[mgov_list[-1]] 
		p = str(seq) + '\t' + ' + '.join(analyzed) + '\t' + ptst + '\t' + str(gov)
		print p
		if seq == gov :
			sys.stderr.write('[ERROR]' + '\t' + p + '\n')

	print '\n',

if __name__ == '__main__':

	parser = OptionParser()
	parser.add_option("--verbose", action="store_const", const=1, dest="verbose", help="verbose mode")
	(options, args) = parser.parse_args()

	if options.verbose : VERBOSE = 1

	number_of_sent = 0
	number_of_sent_skip = 0
	bucket = []
	while 1:
		try:
			line = sys.stdin.readline()
		except KeyboardInterrupt:
			break
		if not line:
			break
		line = line.strip()

		if not line and len(bucket) >= 1 : 
			ret = spill(bucket)
			bucket = []
			number_of_sent += 1
			if ret == -1 : number_of_sent_skip += 1
			continue

		if line : bucket.append(line)

	if len(bucket) != 0 :
		ret = spill(bucket)
		number_of_sent += 1
		if not ret : number_of_sent_skip += 1

	sys.stderr.write("number_of_sent = %d, number_of_sent_skip = %d\n" % (number_of_sent,number_of_sent_skip))
