#!/usr/bin/env python
#-*- coding: utf8 -*-

import os
from optparse import OptionParser

# global variable
VERBOSE = 0

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

# -------------------------------------------------------------------------
# build tree
# -------------------------------------------------------------------------
def next_paren(tokens, i) :
	'''
	tokens[i]에서 시작해서 다음 '(' 혹은 ')'의 위치를 탐색
	못찾은 경우 return -1 
	'''
	j = 0
	found = False
	for token in tokens[i:] :
		if token == '(' or token == ')' : 
			found = True
			break
		j += 1
	if found : return i + j
	return -1

def node_string(node, enable_eoj=True) :
	if node['leaf'] : 
		if enable_eoj :
			return '(' + node['label'] + ' ' + node['eoj'] + '/' + str(node['eoj_idx']) + ' ' + node['morphs'] + ')'
		else :
			return '(' + node['label'] + ' ' + node['morphs'] + ')'
	else :
		return '(' + node['label'] + ')'

def create_node(tokens, i, j) :
	'''
	i ~ j까지가 label,morphs 영역
	i + 1 = j  : label
	             ex) '( NP ('
				        i  j
	i + 1 < j  : label,morphs
	             ex) '( NP_MOD 프랑스/NNP+의/JKG )'
				        i                        j
	'''
	node = {'lchild':{}, 'rchild':{}, 'parent':{}, 'sibling':{}}
	if i + 1 == j :
		node['label'] = tokens[i]
		node['leaf']  = False
		return node
	elif i + 1 < j :
		node['label'] = tokens[i]
		node['morphs']  = tokens[i+1]
		node['leaf']  = True
		node['nleaf'] = {}
		node['pleaf'] = {}
		return node
	else :
		return None

def make_edge(top, node) :
	if not top['lchild'] : # link to left child
		top['lchild'] = node
		node['parent'] = top
		if VERBOSE : print node_string(top) + '-[left]->' + node_string(node)
	elif not top['rchild'] : # link to right child
		top['rchild'] = node
		node['parent'] = top
		top['lchild']['sibling'] = node
		if VERBOSE : print node_string(top) + '-[right]->' + node_string(node)
	else :
		return False
	return True	

def make_leaf_edge(node, history, depth=0) :
	'''
	tree의 leaf간 next,prev link 연결
	즉, node['nleaf'], node['pleaf'] 설정
	'''
	if node['leaf'] :
		length = len(history)
		if length != 0 :
			prev = history[-1]
			prev['nleaf'] = node
			node['pleaf'] = prev
		history.append(node)

	if node['lchild'] : 
		make_leaf_edge(node['lchild'], history, depth+1)
	if node['rchild'] : 
		make_leaf_edge(node['rchild'], history, depth+1)

def build_tree(sent, tokens) :
	'''
	sent = ; 프랑스의 세계적인 의상 디자이너 엠마누엘 웅가로가 실내 장식용 직물 디자이너로 나섰다.
	tokens = ( S ( NP_SBJ ( NP ( NP_MOD 프랑스/NNP+의/JKG ) \
			( NP ( VNP_MOD 세계/NNG+적/XSN+이/VCP+ᆫ/ETM ) ( NP ( NP 의상/NNG ) ( NP 디자이너/NNG ) ) ) ) \
			( NP_SBJ ( NP 엠마누엘/NNP ) ( NP_SBJ 웅가로/NNP+가/JKS ) ) ) \
			( VP ( NP_AJT ( NP ( NP ( NP 실내/NNG ) ( NP 장식/NNG+용/XSN ) ) ( NP 직물/NNG ) ) \
			( NP_AJT 디자이너/NNG+로/JKB ) ) ( VP 나서/VV+었/EP+다/EF+./SF ) ) )
	'''
	err = ' '.join(tokens)
	root = {'lchild':{}, 'rchild':{}, 'parent':{}, 'sibling':{}, 'leaf':False, 'label':'ROOT'}
	stack = []
	stack.append(root)
	max = len(tokens)
	i = 0
	eoj_idx = 1
	eoj_max = len(sent)
	while i < max :
		token = tokens[i]
		if token == '(' : # create node and push
			j = next_paren(tokens, i+1)
			if j == -1 or i+1 == j : 
				sys.stderr.write("ill-formed parentheses[1] : %s\n" % (err))
				return None
			node = create_node(tokens, i+1, j)
			if not node : return None
			# assign eoj/eoj_idx to leaf node
			if node['leaf'] :
				if eoj_idx >= eoj_max :
					sys.stderr.write("not aligned sentence %s : %s\n" % (' '.join(sent), err))
					return None
				node['eoj'] = sent[eoj_idx]
				node['eoj_idx'] = eoj_idx
				eoj_idx += 1
			if VERBOSE : print node_string(node)
			# push to stack
			stack.append(node)
		if token == ')' :
			# pop and make edge
			if len(stack) == 0 : 
				sys.stderr.write("ill-formed parentheses[2] : %s\n" % (err))
				return None
			node = stack.pop()
			if len(stack) == 0 : 
				sys.stderr.write("ill-formed parentheses[3] : %s\n" % (err))
				return None
			top  = stack[-1]
			if not make_edge(top, node) :
				sys.stderr.write("can't make edge : %s\n" % (err))
				return None
		i += 1

	if len(stack) == 1 and stack[-1]['label'] == 'ROOT' :
		history = []
		make_leaf_edge(root['lchild'], history, depth=0)
		return root
	else :
		sys.stderr.write("build failure : %s\n" % (err))
		return None
# -------------------------------------------------------------------------

# -------------------------------------------------------------------------
# preprocessing
# -------------------------------------------------------------------------
def modify_illformed_1(tokens) :
	# ex) '( NP ( NP ( NP ( NP+포로/NNG )'
	# '(' 다음이 label인데 '+'가 포함되어 있으면 처음 '+'만 공백으로
	n_tokens = []
	max = len(tokens)
	i = 0
	while i < max :
		token = tokens[i]
		if token == '(' :
			n_tokens.append(token)
			if '+' in tokens[i+1] :
				t_list = tokens[i+1].split('+')
				n_tokens.append(t_list[0]) # label
				n_tokens.append(''.join(t_list[1:])) # morphs
				i += 1
		else :
			n_tokens.append(token)
		i += 1
	return n_tokens

def tokenize(bucket) :
	'''
	* 다루기 쉽도록 공백으로 분리된 token 단위로 변환한다. 
	예) bucket
	; 프랑스의 세계적인 의상 디자이너 엠마누엘 웅가로가 실내 장식용 직물 디자이너로 나섰다.
	(S	(NP_SBJ	(NP	(NP_MOD 프랑스/NNP + 의/JKG)
				(NP	(VNP_MOD 세계/NNG + 적/XSN + 이/VCP + ᆫ/ETM)
					(NP	(NP 의상/NNG)
						(NP 디자이너/NNG))))
			(NP_SBJ	(NP 엠마누엘/NNP)
				(NP_SBJ 웅가로/NNP + 가/JKS)))
		(VP	(NP_AJT	(NP	(NP	(NP 실내/NNG)
						(NP 장식/NNG + 용/XSN))
					(NP 직물/NNG))
				(NP_AJT 디자이너/NNG + 로/JKB))
			(VP 나서/VV + 었/EP + 다/EF + ./SF)))
	'''
	sent = bucket[0].split()
	if sent[0] != ';' : return None,None
	paren_parse = ' '.join([s.strip('\t').replace('\t',' ') for s in bucket[1:]])
	paren_parse = paren_parse.replace(' + ','+')
	paren_parse = paren_parse.replace('(/','^[/').replace(')/','^]/')
	paren_parse = paren_parse.replace('(',' ( ').replace(')',' ) ')
	paren_parse = paren_parse.replace('^[/','(/').replace('^]/',')/')
	paren_parse = paren_parse.replace('+ ','+')
	tokens = paren_parse.split()
	tokens = modify_illformed_1(tokens)

	if VERBOSE : print ' '.join(tokens)
	return sent, tokens
# -------------------------------------------------------------------------

# -------------------------------------------------------------------------
# tree traversal
# -------------------------------------------------------------------------
def tree2tokens(node, tokens, depth=0) :
	'''
	입력을 tree로 변환하기 전 tokenizing 했는데,
	여기서는 tree를 가지고 역으로 tokenizing 결과를 만든다. 
	'''
	if node['leaf'] :
		tokens.append('(')
		tokens.append(node['label'])
		tokens.append(node['morphs'])
		tokens.append(')')
	else :
		tokens.append('(')
		tokens.append(node['label'])

	if node['lchild'] : 
		tree2tokens(node['lchild'], tokens, depth=depth+1)
		if not node['rchild'] :
			tokens.append(')') # closed
	if node['rchild'] : 
		tree2tokens(node['rchild'], tokens, depth=depth+1)
		tokens.append(')') # closed

def modify_morphs(morphs) :
	try : 
		t_morphs = morphs.replace('++/','+\t/') # + -> tab
		t_morphs = t_morphs.replace('+',' + ')
		t_morphs = t_morphs.replace('\t','+')   # tab -> +
	except :
		return morphs
	return t_morphs

def tree2con(node, tokens, history, depth=0) :
	'''
	입력을 tree로 변환했다면, 여기서 다시
	tree를 입력과 같은 형태(constituent, phrase structure)로 출력한다. 
	'''
	if depth == 0 : prev_node = None
	else : prev_node = history[-1]
	if prev_node and prev_node['leaf'] : # 바로 전에 leaf를 찍었다면
		tokens.append('\n')
		for i in xrange(depth) :
			tokens.append('\t')

	if node['leaf'] :
		tokens.append('(' + node['label'] + ' ' + modify_morphs(node['morphs']) + ')')
	else :
		tokens.append('(' + node['label'] + '\t')
	history.append(node)

	if node['lchild'] : 
		tree2con(node['lchild'], tokens, history, depth+1)
		if not node['rchild'] :
			tokens.append(')') # closed
	if node['rchild'] : 
		tree2con(node['rchild'], tokens, history, depth+1)
		tokens.append(')') # closed

def is_vx(gov_node) :
	morphs = gov_node['morphs']
	tokens = morphs.split('+')
	if '/VX' in tokens[0] : return True
	# VX는 아니지만 VX처럼 동작하는 용언, ex) '지니게 되다'
	if '되/' in tokens[0] :
		pleaf = None
		if gov_node['pleaf'] : pleaf = gov_node['pleaf']
		if pleaf :
			morphs = pleaf['morphs']
			tokens = morphs.split('+')
			if '게/EC' in tokens[-1] : return True
			if '면/EC' in tokens[-1] : return True
			if '아도/EC' in tokens[-1] : return True
	if '않/' in tokens[0] :
		pleaf = None
		if gov_node['pleaf'] : pleaf = gov_node['pleaf']
		if pleaf :
			morphs = pleaf['morphs']
			tokens = morphs.split('+')
			if '지/EC' in tokens[-1] : return True
	return False

def is_vnp(morphs) :
	tokens = morphs.split('+')
	if len(tokens) <= 2 : return False
	if '/NNB' in tokens[0] and '/VCP' in tokens[1] : return True
	return False

def is_va(morphs) :
	tokens = morphs.split('+')
	# '/VV'로 잘못 태깅된 케이스도 커버
	if '있/VA' in tokens[0] or \
		'있/VV' in tokens[0] or \
		'없/VA' in tokens[0] or \
		'없/VV' in tokens[0] or \
		'같/VA' in tokens[0] : return True
	else : return False

def is_nnb(morphs) :
	tokens = morphs.split('+')
	if '/NNB' in tokens[0] : return True
	return False

def is_etm(morphs) :
	tokens = morphs.split('+')
	if 'ᆫ/ETM' in tokens[-1] : return True
	if '는/ETM' in tokens[-1] : return True
	if 'ᆯ/ETM' in tokens[-1] : return True
	if '을/ETM' in tokens[-1] : return True
	if '를/ETM' in tokens[-1] : return True
	return False

def check_vx_rule(gov_node) :
	if not gov_node['parent'] : return False
	if not gov_node['parent']['lchild'] : return False
	if not is_vx(gov_node) : return False
	return True

def check_vnp_rule(gov_node) :
	if not gov_node['parent'] : return False
	if not gov_node['parent']['lchild'] : return False
	# 'VNP 것/NNB + 이/VCP + 다/EF' 형태인지 검사
	if not is_vnp(gov_node['morphs']) : return False
	return True

def check_va_rule(gov_node) :
	if not gov_node['parent'] : return False
	if not gov_node['parent']['lchild'] : return False
	# 'ㄹ NNB 있다/없다/같다' 형태인지 검사
	# 'NNB'는 어절의 시작이 NNB이면 된다. 즉, '~ㄹ 수가 없다' 형태도 허용
	if is_va(gov_node['morphs']) : 
		pleaf = None
		if gov_node['pleaf'] : pleaf = gov_node['pleaf']
		if pleaf and is_nnb(pleaf['morphs']) :
			ppleaf = None
			if pleaf['pleaf'] : 
				ppleaf = pleaf['pleaf']
			if ppleaf and is_etm(ppleaf['morphs']) : 
				return True
	return False

def find_for_vx_rule(node, gov_node) :
	found = None
	t_next = gov_node['parent']
	while t_next :
		# 새로운 지배소가 앞쪽에 있거나 같으면 안됨
		if t_next['leaf'] and ('VP' in t_next['label'] or 'VNP' in t_next['label']) and t_next['eoj_idx'] > node['eoj_idx'] :
			found = t_next
			break
		if t_next['lchild'] :
			if 'S' in t_next['lchild']['label'] or 'VP' in t_next['lchild']['label'] or 'VNP' in t_next['lchild']['label'] :
				t_next = t_next['lchild']
				continue
		if t_next['rchild'] :
			if 'VP' in t_next['rchild']['label'] or 'VNP' in t_next['rchild']['label'] :
				t_next = t_next['rchild']
				continue
		t_next = t_next['lchild']
	return found

def find_for_vnp_rule(node, gov_node) :
	found = None
	t_next = gov_node['parent']
	while t_next :
		# 새로운 지배소가 앞쪽에 있거나 같으면 안됨
		if t_next['leaf'] and ('VP' in t_next['label'] or 'VNP' in t_next['label']) and t_next['eoj_idx'] > node['eoj_idx'] :
			# 새로운 지배소와 기존 지배소간 거리가 너무 멀어도 안됨
			if abs(gov_node['eoj_idx'] - t_next['eoj_idx']) <= 3 : 
				found = t_next
				break
		if t_next['lchild'] :
			if 'S' in t_next['lchild']['label'] or 'VP' in t_next['lchild']['label'] or 'VNP' in t_next['lchild']['label'] :
				t_next = t_next['lchild']
				continue
		if t_next['rchild'] :
			if 'VP' in t_next['rchild']['label'] or 'VNP' in t_next['rchild']['label'] :
				t_next = t_next['rchild']
				continue
		t_next = t_next['lchild']
	return found

def find_for_va_rule(node, gov_node, search_mode=1) :
	found = None
	if search_mode == 2 : # parent->parent 부터 탐색이 필요한 경우
		t_next = gov_node['parent']
		if t_next and t_next['parent'] : 
			t_next = t_next['parent']
	else : # 일반적인 경우
		t_next = gov_node['parent']
	while t_next :
		# 새로운 지배소가 앞쪽에 있거나 같으면 안됨
		if t_next['leaf'] and ('VP' in t_next['label'] or 'VNP' in t_next['label']) and t_next['eoj_idx'] > node['eoj_idx'] :
			# 새로운 지배소와 기존 지배소간 거리가 너무 멀어도 안됨
			if abs(gov_node['eoj_idx'] - t_next['eoj_idx']) <= 3 : 
				found = t_next
				break
		t_next = t_next['lchild']
	return found

def find_gov(node) :
	'''
	* node = leaf node

	1. head final rule
	  - 현재 node에서 parent를 따라가면서
 	    첫번째로 right child가 있는 node를 만나면
	    해당 node의 right child를 따라서 leaf node까지 이동
	2. VX rule
	  - 보조용언을 governor로 갖는다면 본용언으로 바꿔준다. 
	  - 보조용언은 아니지만 보조용언처럼 동작하는 용언도 비슷하게 처리한다. ex) '지니게 되다'
	3. VNP rule
	  - 'VNP 것/NNB + 이/VCP + 다/EF' 형태를 governor로 갖는다면 앞쪽 용언으로 바꿔준다. 
	4. VA rule
	  - '있/VA, 없/VA, 같/VA'가 governor인 경우, 앞쪽에 'ㄹ NNB' 형태가 오면 앞쪽 용언으로 바꿔준다. 
	    node['pleaf'] 링크를 활용한다. 
	'''
	# 첫번째로 right child가 있는 node를 탐색
	# sibling link를 활용한다. 
	next = node
	found = None
	while next :
		if next['sibling'] :
			found = next['sibling']['parent']
			break
		next = next['parent']

	gov_node = None
	if found :
		# right child를 따라서 leaf node까지
		next = found
		while next :
			if next['leaf'] :
				gov_node = next
				# -----------------------------------------------------------------
				# gov_node가 vx rule을 만족하는 경우 parent->lchild를 따라간다. 
				if check_vx_rule(gov_node) :
					new_gov_node = find_for_vx_rule(node, gov_node)
					if new_gov_node : gov_node = new_gov_node
				# gov_node가 vnp rule을 만족하는 경우 parent->lchild를 따라간다. 
				if check_vnp_rule(gov_node) :
					new_gov_node = find_for_vnp_rule(node, gov_node)
					if new_gov_node :
						gov_node = new_gov_node
						# 새로운 지배소가 '있다,없다,같다'인 경우 
						# check_va_rule을 한번 태워본다. 
						if check_va_rule(gov_node) :
							new_gov_node = find_for_va_rule(node, gov_node, search_mode=2)
							if new_gov_node : gov_node = new_gov_node
				# gov_node가 va rule을 만족하는 경우 parent->lchild를 따라간다. 
				if check_va_rule(gov_node) :
					new_gov_node = find_for_va_rule(node, gov_node, search_mode=1)
					if new_gov_node : gov_node = new_gov_node
				# -----------------------------------------------------------------
				break
			next = next['rchild']
	if gov_node :
		return gov_node['eoj_idx']
	return 0
		

def tree2dep(node, depth=0) :
	'''
	tree에서 dependency 구조를 뽑아낸다. 
	'''
	if node['leaf'] :
		eoj_idx = node['eoj_idx']
		eoj     = node['eoj']
		morphs  = modify_morphs(node['morphs'])
		label   = node['label']
		gov     = find_gov(node)
		out = [eoj_idx, eoj, morphs, label, gov]
		print '\t'.join([str(e) for e in out])
	if node['lchild'] : 
		tree2dep(node['lchild'], depth+1)
	if node['rchild'] : 
		tree2dep(node['rchild'], depth+1)

def find_ep(node) :
	'''
	parent를 따라서 처음으로 VP_MOD,S_MOD,VNP_MOD가 아닌 node를 탐색
	해당 node의 most left leaf  = ep begin
	해당 node의 most right leaf = ep end
	'''
	next = node
	found = None
	while next :
		if next['label'] not in ['VP_MOD','VNP_MOD','S_MOD'] :
			found = next
			break
		next = next['parent']

	left_ep = None
	right_ep = None
	if found :
		# left child를 따라서 leaf node까지
		next = found
		while next :
			if next['leaf'] :
				left_ep = next
				break
			next = next['lchild']
		# right child를 따라서 leaf node까지
		next = found
		while next :
			if next['leaf'] :
				right_ep = next
				break
			next = next['rchild']
	if left_ep and right_ep :
		return left_ep['eoj_idx'], right_ep['eoj_idx']
	return 0,0

def is_ec(morphs) :
	tokens = morphs.split('+')
	if '/EC' in tokens[-1] : return True
	if '/SP' in tokens[-1] and len(tokens) >= 2 and '/EC' in tokens[-2] : return True
	return False

def find_sp(node) :
	'''
	parent를 따라서 처음으로 VP,S,VNP_CMP가 아닌 node를 탐색
	단, 현재 node는 parent의 right child여야 한다.
	정지하기 전 node에 대해서
	해당 node의 most left leaf  = sp begin
	'''
	next = node
	prev = None
	found = None
	while next :
		if next['label'] not in ['VP','S','VNP_CMP'] :
			found = prev
			break
		if next['sibling'] :
			found = next
			break
		prev = next
		next = next['parent']

	left_sp = None
	if found :
		# left child를 따라서 leaf node까지
		next = found
		while next :
			if next['leaf'] :
				left_sp = next
				break
			next = next['lchild']
	if left_sp :
		return left_sp['eoj_idx']
	return 0

def tree2embedded(node, depth=0) :
	'''
	tree에서 embedded phrase/clause 구조를 뽑아낸다. 
	'''
	if node['leaf'] :
		eoj_idx = node['eoj_idx']
		eoj     = node['eoj']
		morphs  = modify_morphs(node['morphs'])
		label   = node['label']
		gov     = find_gov(node)
		ep_begin = 0
		ep_end   = 0
		if label in ['VP_MOD','VNP_MOD'] : 
			ep_begin,ep_end = find_ep(node)
		sp_begin = 0
		sp_end   = 0
		if label in ['VP','VNP','VNP_CMP'] and is_ec(node['morphs']) : 
			sp_begin = find_sp(node)
			if sp_begin != 0 :
				sp_end   = eoj_idx
				if sp_begin == sp_end : # 같은 경우는 의미없음
					sp_begin = 0
					sp_end = 0
		out = [eoj_idx, eoj, morphs, label, gov, ep_begin, ep_end, sp_begin, sp_end]
		print '\t'.join([str(e) for e in out])
	if node['lchild'] : 
		tree2embedded(node['lchild'], depth+1)
	if node['rchild'] : 
		tree2embedded(node['rchild'], depth+1)
# -------------------------------------------------------------------------

def spill(bucket, mode) :

	# --------------------------------------------------------------
	# ill-formed filtering and build tree
	sent, tokens = tokenize(bucket)
	if not sent : return False
	tree = build_tree(sent, tokens)
	if not tree : return False
	# begin with tree['lchild'](ROOT 제외)
	t_tokens = []
	tree2tokens(tree['lchild'], t_tokens, depth=0)
	if tokens != t_tokens :
		sys.stderr.write("input parentheses != tree2tokens\n")
		sys.stderr.write("input        = %s\n" % (' '.join(tokens)))
		sys.stderr.write("tree2tokens  = %s\n" % (' '.join(t_tokens)))
		return False
	# --------------------------------------------------------------

	if mode == 0 : # print constituent tree
		print ' '.join(sent)
		t_tokens = []
		history  = []
		tree2con(tree['lchild'], t_tokens, history, depth=0)
		print ''.join(t_tokens).strip()
	if mode == 1 : # print dependency tree
		tree2dep(tree['lchild'], depth=0)
	if mode == 2 : # print embedded phrase/clause tagged tree
		tree2embedded(tree['lchild'], depth=0)

	print '\n',
	return True

if __name__ == '__main__':

	parser = OptionParser()
	parser.add_option("--verbose", action="store_const", const=1, dest="verbose", help="verbose mode")
	parser.add_option("-m", "--mode", dest="mode", help="mode : 0(constituent), 1(dependency), 2(embedded phrase/clause)", metavar="mode")
	(options, args) = parser.parse_args()

	if options.verbose : VERBOSE = 1

	mode = options.mode
	if mode == None : mode = 0
	else : mode = int(mode)

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
			ret = spill(bucket, mode)
			bucket = []
			continue

		if line : bucket.append(line)

	if len(bucket) != 0 :
		ret = spill(bucket, mode)

