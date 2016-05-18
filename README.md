syntaxnet
===

- description
  - test code for syntaxnet

- how to test
```
(after installing syntaxnet)
$ pwd
/root/syntaxnet/models/syntaxnet
$ git clone https://github.com/dsindex/syntaxnet.git work
$ cd work
$ echo "hello syntaxnet" | ./demo.sh
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

- training other corpus
```
(for example, training UD_English)
(follow instructions in https://github.com/tensorflow/models/tree/master/syntaxnet)
$ ./train.sh
...
#preprocessing with tagger
...
INFO:tensorflow:Seconds elapsed in evaluation: 9.77, eval metric: 99.71%
...
INFO:tensorflow:Seconds elapsed in evaluation: 1.26, eval metric: 92.04%
...
#pretrain parser
...
INFO:tensorflow:Seconds elapsed in evaluation: 4.97, eval metric: 82.20%
...
#evaluate parser
...
INFO:tensorflow:Seconds elapsed in evaluation: 44.30, eval metric: 92.36%
...
INFO:tensorflow:Seconds elapsed in evaluation: 5.42, eval metric: 82.67%
...
#train parser
...
INFO:tensorflow:Seconds elapsed in evaluation: 57.69, eval metric: 83.95%
...
```

- test training model
```
$ echo "this is my own tagger and parser" | ./test.sh
```
