syntaxnet
===

- description
  - test code for [syntaxnet](https://github.com/tensorflow/models/tree/master/syntaxnet)

- how to test
```
(after installing syntaxnet)
$ pwd
/path/to/models/syntaxnet
$ git clone https://github.com/dsindex/syntaxnet.git work
$ cd work
$ echo "hello syntaxnet" | ./demo.sh
(training parser only with parsed corpus)
$ ./parser_trainer_test.sh
```

- download univeral dependency treebank data 
  - http://universaldependencies.org/#en)
  ```
  $ cd work
  $ mkdir corpus
  $ cd corpus
  (downloading ud-treebanks-v1.2.tgz)
  $ tar -zxvf ud-treebanks-v1.2.tgz  
  $ ls universal-dependencies-1.2 
  $ UD_Ancient_Greek  UD_Basque  UD_Czech ....
  ```

- training tagger and parser with another corpus
```
(for example, training UD_English)
(detail instructions can be found 
 in https://github.com/tensorflow/models/tree/master/syntaxnet)
$ ./train.sh -v -v
...
#preprocessing with tagger
INFO:tensorflow:Seconds elapsed in evaluation: 9.77, eval metric: 99.71%
INFO:tensorflow:Seconds elapsed in evaluation: 1.26, eval metric: 92.04%
INFO:tensorflow:Seconds elapsed in evaluation: 1.26, eval metric: 92.07%
...
#pretrain parser
INFO:tensorflow:Seconds elapsed in evaluation: 4.97, eval metric: 82.20%
...
#evaluate pretrained parser
INFO:tensorflow:Seconds elapsed in evaluation: 44.30, eval metric: 92.36%
INFO:tensorflow:Seconds elapsed in evaluation: 5.42, eval metric: 82.67%
INFO:tensorflow:Seconds elapsed in evaluation: 5.59, eval metric: 82.36%
...
#train parser
INFO:tensorflow:Seconds elapsed in evaluation: 57.69, eval metric: 83.95%
...
#evaluate parser
INFO:tensorflow:Seconds elapsed in evaluation: 283.77, eval metric: 96.54%
INFO:tensorflow:Seconds elapsed in evaluation: 34.49, eval metric: 84.09%
INFO:tensorflow:Seconds elapsed in evaluation: 34.97, eval metric: 83.49%
...
```

- training parser only
```
(in case you have other pos-tagger 
 and want to build parser only from the parsed corpus) 
$ ./train_p.sh -v -v
...
#pretrain parser
...
#evaluate pretrained parser
INFO:tensorflow:Seconds elapsed in evaluation: 44.15, eval metric: 92.21%
INFO:tensorflow:Seconds elapsed in evaluation: 5.56, eval metric: 87.84%
INFO:tensorflow:Seconds elapsed in evaluation: 5.43, eval metric: 86.56%
...
#train parser
...
#evaluate parser
INFO:tensorflow:Seconds elapsed in evaluation: 279.04, eval metric: 94.60%
INFO:tensorflow:Seconds elapsed in evaluation: 33.19, eval metric: 88.60%
INFO:tensorflow:Seconds elapsed in evaluation: 32.57, eval metric: 87.77%
...
```

- test new model
```
$ echo "this is my own tagger and parser" | ./test.sh
...
Input: this is my own tagger and parser
Parse:
tagger NN ROOT
 +-- this DT nsubj
 +-- is VBZ cop
 +-- my PRP$ nmod:poss
 +-- own JJ amod
 +-- and CC cc
 +-- parser NN conj

* original model's output
$ echo "this is my own tagger and parser" | ./demo.sh
Input: this is my own tagger and parser
Parse:
tagger NN ROOT
 +-- this DT nsubj
 +-- is VBZ cop
 +-- my PRP$ poss
 +-- own JJ amod
 +-- and CC cc
 +-- parser ADD conj 

$ echo "Bob brought the pizza to Alice ." | ./test.sh
Input: Bob brought the pizza to Alice .
Parse:
brought VBD ROOT
 +-- Bob NNP nsubj
 +-- pizza NN dobj
 |   +-- the DT det
 +-- Alice NNP nmod
 |   +-- to IN case
 +-- . . punct

* original model's output
$ echo "Bob brought the pizza to Alice ." | ./demo.sh
Input: Bob brought the pizza to Alice .
Parse:
brought VBD ROOT
 +-- Bob NNP nsubj
 +-- pizza NN dobj
 |   +-- the DT det
 +-- to IN prep
 |   +-- Alice NNP pobj
 +-- . . punct
```

- training parser with korean sejong treebank corpus
```
$ ./sejong/split.sh
$ ./sejong/c2d.sh
$ ./train_sejong.sh
#pretrain parser
...
NFO:tensorflow:Seconds elapsed in evaluation: 14.18, eval metric: 93.43%
...
#evaluate pretrained parser
INFO:tensorflow:Seconds elapsed in evaluation: 116.08, eval metric: 95.11%
INFO:tensorflow:Seconds elapsed in evaluation: 14.60, eval metric: 93.76%
INFO:tensorflow:Seconds elapsed in evaluation: 14.45, eval metric: 93.78%
...
#evaluate pretrained parser by eoj-based
accuracy(UAS) = 0.903289
accuracy(UAS) = 0.876198
accuracy(UAS) = 0.876888
...
#train parser
INFO:tensorflow:Seconds elapsed in evaluation: 137.36, eval metric: 94.12%
...
#evaluate parser
INFO:tensorflow:Seconds elapsed in evaluation: 1806.21, eval metric: 96.37%
INFO:tensorflow:Seconds elapsed in evaluation: 224.40, eval metric: 94.19%
INFO:tensorflow:Seconds elapsed in evaluation: 223.75, eval metric: 94.25%
...

#evaluate parser by eoj-based
accuracy(UAS) = 0.928845
accuracy(UAS) = 0.886139
accuracy(UAS) = 0.887824
...
```

- comparison to [BIST parser](https://github.com/dsindex/bist-parser)
