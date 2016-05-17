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
  $ cp -rf universal-dependencies-1.2/UD_English ../
  ```

- training other corpus
```
(for example, training UD_English)
$ ./train.sh
(and follow instructions in https://github.com/tensorflow/models/tree/master/syntaxnet)
```
